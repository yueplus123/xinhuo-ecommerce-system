"""邮件推送（QQ 邮箱 → 企微群）：解析、规则、收信流程（模拟邮箱）、管理接口权限与校验、迁移一致性。"""

import io
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from backend.apps.catalog import mail_push
from backend.apps.catalog import mail_push_engine as eng
from backend.apps.catalog.models import MailPushAccount, MailPushRecord, MailPushRule, MailPushSettings


def make_mail(sender, subject, body, html=False, charset="utf-8", name="", attachment=None):
    msg = MIMEMultipart()
    msg["From"] = formataddr((str(Header(name, "utf-8")), sender)) if name else sender
    msg["Subject"] = Header(subject, charset)
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body, "html" if html else "plain", charset))
    if attachment:
        part = MIMEApplication(b"x" * 2048)
        part.add_header("Content-Disposition", "attachment", filename=("utf-8", "", attachment))
        msg.attach(part)
    return msg.as_bytes()


class FakeIMAP:
    """模拟 QQ 邮箱 IMAP：只读、PEEK，模拟 UID n:* 在没有新邮件时也返回最后一封。"""

    def __init__(self, mails, uidvalidity=1):
        self.mails = mails
        self.uidvalidity = uidvalidity

    def select(self, box, readonly=False):
        assert readonly
        return "OK", [b"1"]

    def response(self, code):
        return code, [str(self.uidvalidity).encode()]

    def uid(self, cmd, *args):
        if cmd == "search":
            crit = args[1]
            uids = sorted(self.mails)
            if crit.startswith("UID "):
                start = int(crit.split()[1].split(":")[0])
                sel = [u for u in uids if u >= start]
                uids = sel or uids[-1:]
            return "OK", [" ".join(map(str, uids)).encode()]
        if cmd == "fetch":
            assert "PEEK" in args[1]
            uid = int(args[0])
            return "OK", [(f"1 (UID {uid} BODY[]".encode(), self.mails[uid]), b")"]
        raise AssertionError(cmd)

    def logout(self):
        pass


class FakeSender:
    def __init__(self):
        self.sent = []
        self.fail = False
        self.webhook = ""

    def send_markdown(self, content, retries=3):
        if self.fail:
            raise RuntimeError("模拟网络错误")
        self.sent.append(content)


class EngineTests(TestCase):
    def test_parse_gbk_html_attachment_quote(self):
        m = eng.parse_message(make_mail("a@x.com", "你好", "正文\n-----Original Message-----\n旧", charset="gb2312"))
        self.assertEqual(m["body"], "正文")
        m = eng.parse_message(make_mail("a@x.com", "t", "<p>你好<br>世界</p>", html=True, attachment="收据.pdf"))
        self.assertIn("你好\n世界", m["body"])
        self.assertEqual(m["attachments"][0][0], "收据.pdf")

    def test_code_and_sender(self):
        self.assertEqual(eng.extract_code("", "您的验证码：A1B2C3"), "A1B2C3")
        self.assertEqual(eng.extract_code("Your code is 583920", ""), "583920")
        self.assertIsNone(eng.extract_code("Your order", "enter the code below"))
        self.assertTrue(eng.sender_matches("a@mail.paypal.com", ["@paypal.com"]))
        self.assertFalse(eng.sender_matches("a@fakepaypal.com", ["@paypal.com"]))

    def test_empty_rule_never_matches(self):
        mail = eng.parse_message(make_mail("a@x.com", "t", "b"))
        cfg = {"exclude": {}, "rules": [{"name": "空", "senders": [], "subject_keywords": []}]}
        self.assertEqual(eng.match_rules(mail, "邮箱1", cfg)[0], "ignored")

    def test_long_message_truncated(self):
        mail = eng.parse_message(make_mail("a@paypal.com", "t", "长" * 5000))
        content = eng.build_message(mail, "邮箱1", {"name": "r", "style": "summary"}, 1500)
        self.assertLess(len(content.encode()), 4096)


class RunnerTests(TestCase):
    def setUp(self):
        s = MailPushSettings.load()
        s.dry_run = False
        s.webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        s.save()
        self.acc = MailPushAccount.objects.create(name="邮箱1", email="a@qq.com", auth_code="x")
        self.acc2 = MailPushAccount.objects.create(name="邮箱2", email="b@qq.com", auth_code="y")
        MailPushRule.objects.create(name="PayPal收款", senders="@paypal.com", subject_keywords="收到\n付款")
        r = MailPushRule.objects.create(name="验证码", senders="@openai.com", subject_keywords="code", style="code")
        r.accounts.set([self.acc2])
        self.box1 = FakeIMAP({1: make_mail("old@x.com", "历史", "旧")})
        self.box2 = FakeIMAP({5: make_mail("old@x.com", "历史", "旧")})
        boxes = {"a@qq.com": self.box1, "b@qq.com": self.box2}
        self.sender = FakeSender()
        self.runner = mail_push.Runner(connect=lambda u, p: boxes[u], sender=self.sender)

    def test_flow(self):
        self.runner.run_round()                       # 首次：只记住位置
        self.assertEqual(self.sender.sent, [])
        self.assertEqual(MailPushAccount.objects.get(pk=self.acc.pk).last_uid, 1)
        self.runner.run_round()                       # 没新邮件
        self.assertEqual(MailPushRecord.objects.count(), 0)

        self.box1.mails[2] = make_mail("service@paypal.com", "您收到了一笔付款 $25", "张三付款", name="PayPal")
        self.box1.mails[3] = make_mail("promo@paypal.com", "PayPal 促销", "广告")         # 排除
        self.box1.mails[4] = make_mail("x@zhihu.com", "热门", "x")                        # 未命中
        self.box1.mails[6] = make_mail("noreply@openai.com", "Your code is 111222", "x")   # 规则只限邮箱2
        self.box2.mails[6] = make_mail("noreply@tm.openai.com", "Your code is 583920", "x")
        self.runner.run_round()
        self.assertEqual(len(self.sender.sent), 2)
        self.assertIn("PayPal收款", self.sender.sent[0])
        self.assertIn("583920", self.sender.sent[1])
        statuses = dict(MailPushRecord.objects.filter(account=self.acc).values_list("uid", "status"))
        self.assertEqual(statuses, {2: "pushed", 3: "excluded", 4: "ignored", 6: "ignored"})

        self.runner.run_round()                       # 不重复推
        self.assertEqual(len(self.sender.sent), 2)
        a = MailPushAccount.objects.get(pk=self.acc.pk)
        self.assertTrue(a.last_ok)
        self.assertIsNotNone(a.last_check_at)

    def test_dry_run_and_retry(self):
        s = MailPushSettings.load()
        s.dry_run = True
        s.save()
        self.runner.run_round()
        self.box1.mails[2] = make_mail("service@paypal.com", "收到付款", "钱")
        self.runner.run_round()
        self.assertEqual(self.sender.sent, [])
        self.assertEqual(MailPushRecord.objects.get().status, "dry_run")

        s.dry_run = False
        s.save()
        self.box1.mails[3] = make_mail("service@paypal.com", "又收到付款", "钱")
        self.sender.fail = True
        self.runner.run_round()
        self.assertEqual(MailPushRecord.objects.get(uid=3).status, "failed")
        self.sender.fail = False
        self.runner.run_round()                       # 自动补推
        self.assertEqual(MailPushRecord.objects.get(uid=3).status, "pushed")
        self.assertEqual(len(self.sender.sent), 1)

    def test_login_failure_status_and_alert(self):
        def bad(u, p):
            raise RuntimeError("登录失败")

        self.runner.pusher.connect = bad
        for _ in range(3):
            self.runner.run_round()
        a = MailPushAccount.objects.get(pk=self.acc.pk)
        self.assertFalse(a.last_ok)
        self.assertEqual(a.fail_count, 3)
        self.assertIn("登录失败", a.last_error)
        self.assertEqual(sum("告警" in m for m in self.sender.sent), 2)   # 两个邮箱各告警一次

    def test_once_command_and_cleanup(self):
        MailPushAccount.objects.update(enabled=False)                     # 不连真实邮箱
        call_command("run_mail_push", "--once", stdout=io.StringIO())
        self.assertEqual(mail_push.cleanup_old_records(), 0)


class ApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser("root", password="x")
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.c = APIClient()
        self.c.force_authenticate(self.admin)

    def test_superuser_only(self):
        c = APIClient()
        c.force_authenticate(self.staff)
        self.assertEqual(c.get("/api/mail-push/").status_code, 403)
        self.assertIn(APIClient().get("/api/mail-push/").status_code, (401, 403))

    def test_accounts_never_return_code(self):
        r = self.c.post("/api/mail-push/accounts/", {"name": "邮箱1", "email": "A@qq.com", "auth_code": "ab cd"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertNotIn("auth_code", r.json())
        a = MailPushAccount.objects.get()
        self.assertEqual((a.email, a.auth_code), ("a@qq.com", "abcd"))
        r = self.c.patch(f"/api/mail-push/accounts/{a.id}/", {"name": "主邮箱", "auth_code": ""}, format="json")
        self.assertEqual(r.status_code, 200)
        a.refresh_from_db()
        self.assertEqual((a.name, a.auth_code), ("主邮箱", "abcd"))
        ov = self.c.get("/api/mail-push/").json()
        self.assertTrue(ov["accounts"][0]["has_auth_code"])
        self.assertNotIn("abcd", str(ov))
        dup = self.c.post("/api/mail-push/accounts/", {"name": "x", "email": "a@qq.com", "auth_code": "1"}, format="json")
        self.assertEqual(dup.status_code, 400)

    def test_rules_validation_and_preview(self):
        bad = self.c.post("/api/mail-push/rules/", {"name": "空"}, format="json")
        self.assertEqual(bad.status_code, 400)
        r = self.c.post(
            "/api/mail-push/rules/",
            {"name": "PayPal收款", "senders": "@PayPal.com", "subject_keywords": "收到，付款", "style": "summary"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["senders"], ["@paypal.com"])
        self.assertEqual(r.json()["subject_keywords"], ["收到", "付款"])
        rid = r.json()["id"]
        self.assertEqual(self.c.patch(f"/api/mail-push/rules/{rid}/", {"enabled": False}, format="json").status_code, 200)
        self.assertFalse(MailPushRule.objects.get().enabled)
        pv = self.c.post("/api/mail-push/preview/", {"name": "验证码", "style": "code", "senders": "@openai.com"}, format="json")
        self.assertIn("583920", pv.json()["content"])

    def test_settings_masked_webhook(self):
        url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abcd1234-zzzz-yyyy"
        self.assertEqual(self.c.patch("/api/mail-push/settings/", {"webhook_url": "http://x"}, format="json").status_code, 400)
        r = self.c.patch("/api/mail-push/settings/", {"webhook_url": url, "poll_interval": 30}, format="json")
        masked = r.json()["settings"]["webhook_url"]
        self.assertNotIn("1234-zzzz", masked)
        self.c.patch("/api/mail-push/settings/", {"webhook_url": masked, "dry_run": False}, format="json")
        s = MailPushSettings.load()
        self.assertEqual((s.webhook_url, s.dry_run, s.poll_interval), (url, False, 30))
        self.assertEqual(self.c.patch("/api/mail-push/settings/", {"poll_interval": 5}, format="json").status_code, 400)

    def test_retry_and_records(self):
        a = MailPushAccount.objects.create(name="邮箱1", email="a@qq.com", auth_code="x")
        rec = MailPushRecord.objects.create(account=a, uidvalidity=1, uid=9, sender="s@x.com", subject="标题", status="pushed")
        self.assertEqual(self.c.post(f"/api/mail-push/records/{rec.id}/retry/").status_code, 200)
        rec.refresh_from_db()
        self.assertEqual((rec.status, rec.attempts), ("failed", 0))
        self.assertIsNotNone(MailPushSettings.load().check_requested_at)
        rows = self.c.get("/api/mail-push/records/?status=failed&q=标题").json()["results"]
        self.assertEqual(len(rows), 1)


class MigrationTests(TestCase):
    def test_no_missing_migrations(self):
        """手写的 0085 迁移要和模型完全一致（只检查邮件推送相关的模型）。"""
        out = io.StringIO()
        call_command("makemigrations", "catalog", "--dry-run", "-v", "3", stdout=out)
        self.assertNotIn("mailpush", out.getvalue().lower(), out.getvalue())
