"""数据大屏：同期对比、本月目标/月底预测、近 4 个月每日（权限）、月度目标接口。"""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from backend.apps.api import data_screen as ds
from backend.apps.catalog.models import MonthlyGmvTarget, PaymentRecord
from backend.apps.catalog.roles import GUEST_GROUP_NAME, ensure_boss_group

TODAY = date(2026, 11, 28)


def pay(user, d, amount, channel="淘宝", orders=1):
    return PaymentRecord.objects.create(user=user, record_date=d, amount=Decimal(str(amount)), channel=channel, order_count=orders)


class SamePeriodTests(TestCase):
    def test_ranges(self):
        self.assertEqual(ds.same_period_prev("month", date(2026, 11, 1), TODAY), (date(2026, 10, 1), date(2026, 10, 28)))
        # 3 月 31 日 → 2 月最后一天
        self.assertEqual(ds.same_period_prev("month", date(2026, 3, 1), date(2026, 3, 31)), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(ds.same_period_prev("month", date(2026, 1, 1), date(2026, 1, 15)), (date(2025, 12, 1), date(2025, 12, 15)))
        self.assertEqual(ds.same_period_prev("week", date(2026, 11, 23), TODAY), (date(2026, 11, 16), date(2026, 11, 21)))
        self.assertEqual(ds.same_period_prev("year", date(2028, 1, 1), date(2028, 2, 29)), (date(2027, 1, 1), date(2027, 2, 28)))


@mock.patch("django.utils.timezone.localdate", return_value=TODAY)
class PayloadTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.a = U.objects.create_user("金凤", password="x", is_staff=True)
        self.b = U.objects.create_user("李振宇", password="x", is_staff=True)
        self.boss = U.objects.create_user("老板", password="x", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.guest = U.objects.create_user("游客", password="x", is_staff=True)
        self.guest.groups.add(Group.objects.get_or_create(name=GUEST_GROUP_NAME)[0])
        pay(self.a, date(2026, 11, 3), 100)
        pay(self.a, date(2026, 11, 28), 50)
        pay(self.b, date(2026, 11, 10), 300)
        pay(self.a, date(2026, 10, 5), 80)
        pay(self.a, date(2026, 10, 30), 999)  # 不在同期（10/1–10/28）
        pay(self.a, date(2026, 11, 4), 20, channel="退款项")

    def test_month_vs_same_period(self, _):
        p = ds.build_data_screen_payload(self.a)
        s = p["month"]["summary"]
        self.assertEqual((s["total_gmv"], s["prev_total_gmv"], s["cmp_label"]), (430.0, 80.0, "上月同期"))
        self.assertEqual((s["cmp_from"], s["cmp_to"]), ("2026-10-01", "2026-10-28"))
        cmp = {r["user__username"]: r for r in p["month"]["staff_compare"]}
        self.assertEqual((cmp["金凤"]["gmv"], cmp["金凤"]["prev_gmv"]), (130.0, 80.0))
        self.assertEqual(cmp["李振宇"]["prev_gmv"], 0)
        self.assertNotIn("remote", [r["key"] for r in p["month"]["bot_business"]])

    def test_goal_forecast(self, _):
        g = ds.month_goal(TODAY)
        self.assertIsNone(g["target"])
        # 到昨天已收 380（含退款 -20），日均 380/27，剩 3 天（含今天）
        self.assertEqual(g["avg_daily"], round(380 / 27, 2))
        self.assertEqual(g["forecast"], round(380 + round(380 / 27, 2) * 3, 2))
        MonthlyGmvTarget.objects.create(month=date(2026, 11, 1), target=Decimal("1000"))
        g = ds.month_goal(TODAY)
        self.assertEqual((g["target"], g["done_pct"], g["per_day_needed"]), (1000.0, 43.0, 190.0))

    def test_daily_4m_permissions(self, _):
        staff = ds.daily_four_months(self.a, TODAY)
        self.assertEqual([o["key"] for o in staff["options"]], ["all", str(self.a.pk)])
        self.assertEqual(staff["default"], str(self.a.pk))
        self.assertNotIn(str(self.b.pk), staff["series"])
        self.assertEqual([m["label"] for m in staff["months"]], ["11月（本月）", "10月", "9月", "8月"])
        self.assertEqual(len(staff["series"]["all"][0]), 28)
        self.assertEqual(len(staff["series"]["all"][1]), 31)
        self.assertEqual(staff["series"][str(self.a.pk)][0][2], 100.0)
        self.assertEqual(staff["series"][str(self.a.pk)][0][3], -20.0)

        boss = ds.daily_four_months(self.boss, TODAY)
        self.assertEqual(boss["default"], "all")
        self.assertIn(str(self.b.pk), boss["series"])
        guest = ds.daily_four_months(self.guest, TODAY)
        self.assertEqual(list(guest["series"]), ["all"])


class GmvTargetApiTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.admin = U.objects.create_superuser("admin", password="x")
        self.staff = U.objects.create_user("s", password="x", is_staff=True)

    def test_crud_and_permission(self):
        c = APIClient()
        c.force_authenticate(self.staff)
        self.assertEqual(c.get("/api/admin/gmv-targets/").status_code, 403)
        c.force_authenticate(self.admin)
        self.assertEqual(c.put("/api/admin/gmv-targets/", {"month": "2026-11", "target": "abc"}, format="json").status_code, 400)
        self.assertEqual(c.put("/api/admin/gmv-targets/", {"month": "2026-11", "target": "0"}, format="json").status_code, 400)
        r = c.put("/api/admin/gmv-targets/", {"month": "2026-11", "target": "150,000"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(MonthlyGmvTarget.objects.get(month=date(2026, 11, 1)).target, Decimal("150000.00"))
        c.put("/api/admin/gmv-targets/", {"month": "2026-11", "target": ""}, format="json")
        self.assertFalse(MonthlyGmvTarget.objects.exists())
        self.assertEqual(len(c.get("/api/admin/gmv-targets/").data["rows"]), 13)
