"""物料续费提醒：前一天 22:00 推明天到期的，当天 15:00 推今天到期的。"""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from backend.apps.catalog.models import MaterialRenewal

CMD = "backend.apps.catalog.management.commands.send_material_renewal_wecom_reminders"


@override_settings(WECOM_REMINDER_ENABLED=True, WECOM_GROUP_WEBHOOK_URL="", STAFF_FRONTEND_BASE_URL="https://staff.example")
@mock.patch.dict("os.environ", {"MATERIAL_WECOM_WEBHOOK_URL": "https://qyapi.example/hook"})
class MaterialReminderTests(TestCase):
    def setUp(self):
        MaterialRenewal.objects.create(name="域名 xinhuo.cloud", category="域名", amount=Decimal("85"), currency="CNY",
                                       next_due_at=date(2026, 11, 10), remark="阿里云")
        MaterialRenewal.objects.create(name="ChatGPT Plus", amount=Decimal("20"), currency="USD", cycle_type="monthly",
                                       next_due_at=date(2026, 11, 10))
        MaterialRenewal.objects.create(name="停用的", next_due_at=date(2026, 11, 10), is_active=False)
        MaterialRenewal.objects.create(name="后天的", next_due_at=date(2026, 11, 11))

    def run_cmd(self, *args):
        out = StringIO()
        with mock.patch(f"{CMD}.send_markdown") as sm, mock.patch(f"{CMD}.post_webhook_json") as pj:
            call_command("send_material_renewal_wecom_reminders", *args, stdout=out)
        return sm, pj, out.getvalue()

    def test_tomorrow_at_22(self):
        sm, _, _ = self.run_cmd("--due", "tomorrow", "--date", "2026-11-09")
        self.assertEqual(sm.call_count, 1)
        url, md = sm.call_args[0]
        self.assertEqual(url, "https://qyapi.example/hook")
        self.assertIn("物料明天到期", md)
        self.assertIn("11月10日 周二", md)
        self.assertIn("2 项", md)
        self.assertIn("域名 xinhuo.cloud", md)
        self.assertIn("$20/月", md)
        self.assertIn("¥85/年", md)
        self.assertNotIn("停用的", md)
        self.assertNotIn("后天的", md)
        self.assertIn("https://staff.example/material-renewal", md)

    def test_today_at_15(self):
        sm, _, _ = self.run_cmd("--due", "today", "--date", "2026-11-10")
        md = sm.call_args[0][1]
        self.assertIn("物料今天到期", md)
        self.assertIn("（今天）", md)

    def test_nothing_due_sends_nothing(self):
        sm, _, out = self.run_cmd("--due", "today", "--date", "2026-11-09")
        self.assertEqual(sm.call_count, 0)
        self.assertIn("不发送", out)

    def test_mention(self):
        with mock.patch.dict("os.environ", {"MATERIAL_REMIND_MENTION": "@all"}):
            _, pj, _ = self.run_cmd("--due", "today", "--date", "2026-11-10")
        self.assertEqual(pj.call_args[0][1]["text"]["mentioned_mobile_list"], ["@all"])
