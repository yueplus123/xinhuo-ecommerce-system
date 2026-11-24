"""邮件推送引擎：QQ 邮箱（IMAP）里符合规则的邮件 → 企业微信群（消息推送 Webhook）。

只用 Python 标准库、不依赖 Django，方便单独测试。存储由调用方提供（见 mail_push.DbStore），
需要实现 get_state / set_state / get_record / save_record / failed_uids 五个方法。

收信用只读方式（select readonly + BODY.PEEK），不会把邮件标成已读，也不会删除或移动邮件。
"""

import email
import html
import imaplib
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime

IMAP_HOST = "imap.qq.com"
IMAP_PORT = 993
MAX_PER_ROUND = 50          # 每个邮箱每轮最多处理的新邮件数，防止一次刷屏
MAX_RETRY_ROUNDS = 5        # 推送失败的邮件，最多在后续几轮里重试
WECOM_MAX_BYTES = 3800      # 企业微信 markdown 单条上限约 4096 字节，留余量

log = logging.getLogger("xinhuo.mail_push")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------------------------------------------------------
# 邮件解析
# ----------------------------------------------------------------------------

def decode_str(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


def _charset(part):
    cs = (part.get_content_charset() or "utf-8").lower()
    if cs in ("gb2312", "gbk", "gb_2312-80", "x-gbk"):
        cs = "gb18030"
    return cs


def _decode_payload(part):
    payload = part.get_payload(decode=True) or b""
    try:
        return payload.decode(_charset(part), errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def html_to_text(raw):
    text = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", "", raw)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|table)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return html.unescape(text).replace("\xa0", " ")


QUOTE_MARKERS = [
    r"^-{3,}\s*原始邮件\s*-{3,}",
    r"^-{3,}\s*Original Message\s*-{3,}",
    r"^\s*在.{1,80}写道[:：]\s*$",
    r"^\s*On .{1,200}wrote:\s*$",
    r"^\s*发件人[:：]",
    r"^\s*From:\s",
]


def clean_body(text):
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if any(re.match(p, line, re.I) for p in QUOTE_MARKERS):
            break
        if line.lstrip().startswith(">"):
            continue
        lines.append(line.rstrip())
    text = "\n".join(lines)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def parse_message(raw_bytes):
    msg = email.message_from_bytes(raw_bytes)
    name, addr = parseaddr(decode_str(msg.get("From")))
    subject = decode_str(msg.get("Subject")).replace("\n", " ").strip() or "（无标题）"
    try:
        date_str = parsedate_to_datetime(msg.get("Date")).astimezone().strftime("%m-%d %H:%M")
    except Exception:
        date_str = ""

    plain, html_part, attachments = None, None, []
    for part in msg.walk():
        if part.is_multipart():
            continue
        disposition = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        if filename or "attachment" in disposition:
            size = len(part.get_payload(decode=True) or b"")
            attachments.append((decode_str(filename) or "未命名附件", size))
            continue
        ctype = part.get_content_type()
        if ctype == "text/plain" and plain is None:
            plain = _decode_payload(part)
        elif ctype == "text/html" and html_part is None:
            html_part = _decode_payload(part)

    body = plain if plain and plain.strip() else html_to_text(html_part or "")
    return {
        "sender_name": name.strip(),
        "sender": addr.strip().lower(),
        "subject": subject,
        "date": date_str,
        "body": clean_body(body),
        "attachments": attachments,
    }


CODE_PATTERNS = [
    r"(?:验证码|校验码|动态码|确认码|安全码|verification code|security code|one-time code|"
    r"login code|passcode|\bcode\b|\bOTP\b|\bPIN\b)\D{0,15}?(?<![A-Za-z0-9])([A-Za-z0-9]{4,8})(?![A-Za-z0-9])",
    r"(?<![A-Za-z0-9])([A-Za-z0-9]{4,8})(?![A-Za-z0-9])\s*(?:is your|为您的|是您的|是你的|为你的)",
]
CODE_STOPWORDS = {"code", "your", "from", "this", "that", "with", "please", "login"}


def extract_code(subject, body):
    text = subject + "\n" + body[:2000]
    for pattern in CODE_PATTERNS:
        for m in re.finditer(pattern, text, re.I):
            code = m.group(1)
            if code.lower() in CODE_STOPWORDS:
                continue
            if any(c.isdigit() for c in code):
                return code
    return None


# ----------------------------------------------------------------------------
# 规则匹配
# ----------------------------------------------------------------------------

def sender_matches(addr, patterns):
    addr = addr.lower()
    domain = addr.split("@")[-1] if "@" in addr else ""
    for p in patterns:
        p = p.strip().lower()
        if not p:
            continue
        if p.startswith("@"):
            d = p[1:]
            if domain == d or domain.endswith("." + d):
                return True
        elif addr == p:
            return True
    return False


def contains_any(text, keywords):
    text = text.casefold()
    return any(k.casefold() in text for k in keywords if k)


def match_rules(mail, account_name, cfg):
    """返回 (状态, 命中的规则)。状态：matched / excluded / ignored"""
    ex = cfg.get("exclude", {})
    if sender_matches(mail["sender"], ex.get("senders", [])):
        return "excluded", {"name": "排除:发件人"}
    if contains_any(mail["subject"], ex.get("subject_keywords", [])):
        return "excluded", {"name": "排除:标题"}

    for rule in cfg.get("rules", []):
        if rule.get("enabled", True) is False:
            continue
        if not rule.get("senders") and not rule.get("subject_keywords"):
            continue                                    # 空规则不生效，避免误推全部邮件
        if rule.get("accounts") and account_name not in rule["accounts"]:
            continue
        if rule.get("senders") and not sender_matches(mail["sender"], rule["senders"]):
            continue
        if rule.get("subject_keywords") and not contains_any(mail["subject"], rule["subject_keywords"]):
            continue
        return "matched", rule
    return "ignored", None


# ----------------------------------------------------------------------------
# 企业微信推送
# ----------------------------------------------------------------------------

def _fmt_size(n):
    return f"{n / 1024 / 1024:.1f}MB" if n >= 1024 * 1024 else f"{max(1, n // 1024)}KB"


def _truncate_bytes(text, limit):
    data = text.encode("utf-8")
    if len(data) <= limit:
        return text
    return data[:limit].decode("utf-8", errors="ignore") + "…"


def build_message(mail, account_name, rule, summary_chars):
    code = extract_code(mail["subject"], mail["body"])
    sender = f"{mail['sender_name']} <{mail['sender']}>" if mail["sender_name"] else mail["sender"]
    style = rule.get("style", "summary")

    if style == "code" and code:
        return "\n".join([
            f"**【验证码】<font color=\"warning\">{code}</font>**",
            f"> 规则：{rule['name']}",
            f"> 邮箱：{account_name}",
            f"> 来自：{sender}",
            f"> 标题：{mail['subject']}",
            f"> 时间：{mail['date']}",
        ])

    lines = [
        f"**【{rule['name']}】{mail['subject']}**",
        f"> 邮箱：{account_name}",
        f"> 发件人：{sender}",
        f"> 时间：{mail['date']}",
    ]
    if code:
        lines.append(f"> 验证码：<font color=\"warning\">{code}</font>")
    if mail["attachments"]:
        att = "、".join(f"{n}({_fmt_size(s)})" for n, s in mail["attachments"][:5])
        lines.append(f"> 附件：{att}")

    if style != "title_only":
        summary = mail["body"][:summary_chars]
        if len(mail["body"]) > summary_chars:
            summary += "…\n（内容较长，完整内容请到邮箱查看）"
        if summary:
            lines.append("")
            lines.append(summary)

    return _truncate_bytes("\n".join(lines), WECOM_MAX_BYTES)


class WeComSender:
    """企业微信群机器人。每个机器人每分钟最多 20 条，这里按 18 条控制。"""

    def __init__(self, webhook="", per_minute=18):
        self.webhook = webhook
        self.per_minute = per_minute
        self.sent_times = deque()
        self.lock = threading.Lock()
        # 企业微信是国内服务，优先直连，不走系统代理（电脑开过 Clash 等代理时，系统代理常导致"目标计算机积极拒绝"）
        self.openers = [("直连", urllib.request.build_opener(urllib.request.ProxyHandler({}))),
                        ("系统代理", urllib.request.build_opener())]

    def _post(self, body):
        errors = []
        for label, opener in self.openers:
            req = urllib.request.Request(self.webhook, data=body, headers={"Content-Type": "application/json"})
            try:
                with opener.open(req, timeout=15) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError:
                raise
            except (urllib.error.URLError, OSError) as e:
                errors.append(f"{label}：{getattr(e, 'reason', e)}")
        raise OSError("连接不上企业微信服务器（" + "；".join(errors) + "）。请检查网络，或关闭代理/加速器后重试")

    def _wait_for_slot(self):
        with self.lock:
            now = time.time()
            while self.sent_times and now - self.sent_times[0] > 60:
                self.sent_times.popleft()
            if len(self.sent_times) >= self.per_minute:
                wait = 60 - (now - self.sent_times[0]) + 1
                log.info("达到每分钟发送上限，等待 %.0f 秒", wait)
                time.sleep(wait)
            self.sent_times.append(time.time())

    def send_markdown(self, content, retries=3):
        if not self.webhook:
            raise RuntimeError("还没有设置企业微信 Webhook 地址")
        body = json.dumps({"msgtype": "markdown", "markdown": {"content": content}}).encode("utf-8")
        last_err = None
        for attempt in range(1, retries + 1):
            self._wait_for_slot()
            try:
                result = self._post(body)
                if result.get("errcode") == 0:
                    return
                last_err = f"errcode={result.get('errcode')} {result.get('errmsg')}"
                if result.get("errcode") == 45009:
                    time.sleep(60)
                    continue
                if result.get("errcode") in (93000, 40008, 40058):    # key 无效等，重试没用
                    break
            except (urllib.error.URLError, OSError, ValueError) as e:
                last_err = str(e)
            time.sleep(2 * attempt)
        raise RuntimeError(f"推送失败：{last_err}")


# ----------------------------------------------------------------------------
# 收信
# ----------------------------------------------------------------------------

def connect_imap(user, password):
    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
    except OSError as e:
        raise RuntimeError(f"连接不上 {IMAP_HOST}（请检查网络，或是否开了代理/防火墙拦截）：{e}")
    try:
        conn.login(user, password)
    except imaplib.IMAP4.error as e:
        raise RuntimeError(f"登录失败（请检查邮箱地址、授权码，以及 QQ 邮箱是否已开启 IMAP）：{e}")
    return conn


def _uid_list(conn, criteria):
    typ, data = conn.uid("search", None, criteria)
    if typ != "OK" or not data or not data[0]:
        return []
    return sorted(int(x) for x in data[0].split())


def _fetch_raw(conn, uid):
    typ, data = conn.uid("fetch", str(uid), "(BODY.PEEK[])")   # PEEK：不把邮件标记为已读
    if typ != "OK":
        return None
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2:
            return item[1]
    return None


def check_login(user, password, connect=connect_imap):
    conn = connect(user, password)
    try:
        conn.select("INBOX", readonly=True)
        return len(_uid_list(conn, "ALL"))
    finally:
        try:
            conn.logout()
        except Exception:
            pass


class MailPusher:
    def __init__(self, cfg, store, sender, connect=connect_imap):
        self.cfg = cfg
        self.store = store
        self.sender = sender
        self.connect = connect
        self.fail_count = {}
        self.alerted = set()
        self.status = {}            # 邮箱地址 → {ok, last_check, error}

    def alert(self, text):
        log.warning(text.replace("**", ""))
        try:
            self.sender.send_markdown(text)
        except Exception as e:
            log.error("告警推送失败：%s", e)

    def run_once(self):
        for acc in self.cfg.get("accounts", []):
            if acc.get("enabled", True) is False:
                continue
            key, name = acc["user"], acc["name"]
            try:
                self.check_account(acc)
                if key in self.alerted:
                    self.alerted.discard(key)
                    self.alert(f"**【邮件推送】{name} 已恢复正常**")
                self.fail_count[key] = 0
                self.status[key] = {"ok": True, "last_check": now_str(), "error": ""}
            except Exception as e:
                n = self.fail_count.get(key, 0) + 1
                self.fail_count[key] = n
                self.status[key] = {"ok": False, "last_check": now_str(), "error": str(e)[:300], "fails": n}
                log.error("[%s] 检查失败（连续第 %d 次）：%s", name, n, e)
                if n >= 3 and key not in self.alerted:
                    self.alerted.add(key)
                    self.alert(
                        f"**【邮件推送告警】{name} 连续 {n} 次检查失败**\n"
                        f"> 邮箱：{acc['user']}\n> 错误：{str(e)[:200]}\n"
                        f"> 请检查网络、IMAP 是否开启、授权码是否失效")

    def check_account(self, acc):
        key, name = acc["user"], acc["name"]
        password = acc.get("password", "")
        if not password:
            raise RuntimeError("还没有填写授权码")

        conn = self.connect(acc["user"], password)
        try:
            typ, _ = conn.select("INBOX", readonly=True)
            if typ != "OK":
                raise RuntimeError("无法打开收件箱")
            _, uv = conn.response("UIDVALIDITY")
            uidvalidity = int(uv[0]) if uv and uv[0] else 0

            saved_uv, last_uid = self.store.get_state(key)
            if saved_uv != uidvalidity or last_uid is None:
                uids = _uid_list(conn, "ALL")
                last_uid = uids[-1] if uids else 0
                self.store.set_state(key, uidvalidity, last_uid)
                log.info("[%s] 首次检查，从现在开始监控新邮件（历史邮件不推送）", name)
                return

            for uid in self.store.failed_uids(key, uidvalidity):
                self.process(conn, acc, uidvalidity, uid)

            new_uids = [u for u in _uid_list(conn, f"UID {last_uid + 1}:*") if u > last_uid]
            if not new_uids:
                return
            if len(new_uids) > MAX_PER_ROUND:
                log.warning("[%s] 新邮件 %d 封，本轮只处理前 %d 封", name, len(new_uids), MAX_PER_ROUND)
                new_uids = new_uids[:MAX_PER_ROUND]

            for uid in new_uids:
                self.process(conn, acc, uidvalidity, uid)
                self.store.set_state(key, uidvalidity, uid)
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def process(self, conn, acc, uidvalidity, uid):
        key, name = acc["user"], acc["name"]
        existing = self.store.get_record(key, uidvalidity, uid)
        if existing and existing[0] != "failed":
            return

        raw = _fetch_raw(conn, uid)
        if raw is None:
            log.warning("[%s] UID %d 读取失败，可能已被删除", name, uid)
            return
        mail = parse_message(raw)
        status, rule = match_rules(mail, name, self.cfg)
        rule_name = rule["name"] if rule else ""

        def save(st, err=None):
            self.store.save_record(key, name, uidvalidity, uid, mail["sender"], mail["subject"], rule_name, st, err)

        if status != "matched":
            save(status)
            log.info("[%s] 跳过(%s)：%s | %s", name, rule_name or "未命中规则", mail["sender"], mail["subject"])
            return

        if self.cfg.get("dry_run", True):
            save("dry_run")
            log.info("[%s] 观察模式·会推送(%s)：%s | %s", name, rule_name, mail["sender"], mail["subject"])
            return

        content = build_message(mail, name, rule, self.cfg.get("summary_chars", 400))
        try:
            self.sender.send_markdown(content)
            save("pushed")
            log.info("[%s] 已推送(%s)：%s | %s", name, rule_name, mail["sender"], mail["subject"])
        except Exception as e:
            save("failed", str(e)[:300])
            log.error("[%s] 推送失败，下一轮重试：%s", name, e)
