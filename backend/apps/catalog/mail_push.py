"""邮件推送（QQ 邮箱 → 企微群）：把 mail_push_engine 接到数据库上。

收信服务（manage.py run_mail_push，systemd 服务 xinhuo-mailpush）和管理接口（api/mail_push_views.py）共用。
"""

from __future__ import annotations

import re
import time
from datetime import timedelta

from django.utils import timezone

from . import mail_push_engine as eng
from .models import MailPushAccount, MailPushRecord, MailPushRule, MailPushSettings

log = eng.log

WEBHOOK_PREFIX = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
WORKER_ALIVE_SECONDS = 180      # 收信服务超过 3 分钟没心跳，就当它没在运行
KEEP_DAYS = 90                  # 推送记录保留天数
STYLES = {c[0] for c in MailPushRule.STYLE_CHOICES}


def split_lines(text) -> list[str]:
    """一行一个（也接受逗号、顿号、分号分隔），去空、去重、保持顺序。"""
    if isinstance(text, (list, tuple)):
        text = "\n".join(str(x) for x in text)
    seen, out = set(), []
    for x in re.split(r"[\n\r,，、;；]+", text or ""):
        x = x.strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def mask_webhook(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"key=([\w-]+)", url)
    key = m.group(1) if m else ""
    return WEBHOOK_PREFIX + (key[:4] + "****" + key[-4:] if len(key) > 8 else "****")


class DbStore:
    """mail_push_engine.MailPusher 需要的存储接口；key 是邮箱地址。"""

    def get_state(self, key):
        row = MailPushAccount.objects.filter(email=key).values_list("uidvalidity", "last_uid").first()
        return row if row else (None, None)

    def set_state(self, key, uidvalidity, last_uid):
        MailPushAccount.objects.filter(email=key).update(uidvalidity=uidvalidity, last_uid=last_uid)

    def get_record(self, key, uidvalidity, uid):
        return (
            MailPushRecord.objects.filter(account__email=key, uidvalidity=uidvalidity, uid=uid)
            .values_list("status", "attempts")
            .first()
        )

    def save_record(self, key, account_name, uidvalidity, uid, sender, subject, rule, status, error=None):
        account_id = MailPushAccount.objects.filter(email=key).values_list("id", flat=True).first()
        if account_id is None:
            return
        fields = {
            "sender": (sender or "")[:200],
            "subject": (subject or "")[:300],
            "rule_name": (rule or "")[:60],
            "status": status,
            "error": (error or "")[:300],
        }
        rec = MailPushRecord.objects.filter(account_id=account_id, uidvalidity=uidvalidity, uid=uid).first()
        if rec:
            for k, v in fields.items():
                setattr(rec, k, v)
            rec.attempts += 1
            rec.save()
        else:
            MailPushRecord.objects.create(account_id=account_id, uidvalidity=uidvalidity, uid=uid, **fields)

    def failed_uids(self, key, uidvalidity):
        return list(
            MailPushRecord.objects.filter(
                account__email=key, uidvalidity=uidvalidity, status="failed", attempts__lt=eng.MAX_RETRY_ROUNDS
            ).values_list("uid", flat=True)
        )


def build_cfg(s: MailPushSettings) -> dict:
    """把数据库里的设置 / 邮箱 / 规则整理成引擎用的配置。"""
    rules = []
    for r in MailPushRule.objects.filter(enabled=True).prefetch_related("accounts"):
        rules.append({
            "name": r.name,
            "senders": [x.lower() for x in split_lines(r.senders)],
            "subject_keywords": split_lines(r.subject_keywords),
            "style": r.style,
            "accounts": [a.name for a in r.accounts.all()],
        })
    accounts = [
        {"name": a.name, "user": a.email, "password": a.auth_code, "enabled": True}
        for a in MailPushAccount.objects.filter(enabled=True)
    ]
    return {
        "dry_run": s.dry_run,
        "summary_chars": s.summary_chars,
        "exclude": {
            "senders": [x.lower() for x in split_lines(s.exclude_senders)],
            "subject_keywords": split_lines(s.exclude_keywords),
        },
        "rules": rules,
        "accounts": accounts,
    }


class Runner:
    """检查一轮所有启用的邮箱。connect / sender 可替换（测试用）。"""

    def __init__(self, connect=eng.connect_imap, sender=None):
        self.sender = sender or eng.WeComSender()
        self.pusher = eng.MailPusher({}, DbStore(), self.sender, connect=connect)

    def run_round(self):
        s = MailPushSettings.load()
        cfg = build_cfg(s)
        if hasattr(self.sender, "webhook"):
            self.sender.webhook = s.webhook_url
        self.pusher.cfg = cfg
        self.pusher.run_once()
        now = timezone.now()
        for acc in cfg["accounts"]:
            st = self.pusher.status.get(acc["user"])
            if not st:
                continue
            MailPushAccount.objects.filter(email=acc["user"]).update(
                last_check_at=now,
                last_ok=st["ok"],
                last_error=(st.get("error") or "")[:300],
                fail_count=0 if st["ok"] else st.get("fails", 1),
            )
        MailPushSettings.objects.filter(pk=s.pk).update(last_round_at=now)


def cleanup_old_records(days: int = KEEP_DAYS) -> int:
    deleted, _ = MailPushRecord.objects.filter(created_at__lt=timezone.now() - timedelta(days=days)).delete()
    return deleted


def worker_alive(s: MailPushSettings) -> bool:
    if not s.worker_heartbeat_at:
        return False
    return (timezone.now() - s.worker_heartbeat_at).total_seconds() < WORKER_ALIVE_SECONDS


def sample_mail(rule: dict) -> dict:
    """管理后台「群消息预览」用的示例邮件。"""
    senders = rule.get("senders") or []
    first = senders[0] if senders else "noreply@example.com"
    sender = ("noreply" + first) if first.startswith("@") else first
    kws = rule.get("subject_keywords") or []
    if rule.get("style") == MailPushRule.STYLE_CODE:
        subject = "Your verification code is 583920"
        body = "Your verification code is 583920. It expires in 10 minutes."
    else:
        subject = f"示例邮件：{kws[0]}" if kws else "示例邮件标题"
        body = "这里会显示邮件正文的开头部分，回复邮件里引用的旧内容会自动去掉。\n第二行内容……"
    return {
        "sender_name": "",
        "sender": sender,
        "subject": subject,
        "date": time.strftime("%m-%d %H:%M"),
        "body": body,
        "attachments": [],
    }
