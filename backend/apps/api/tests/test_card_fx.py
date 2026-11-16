"""日元充值汇率：计算（向上取整）、取数校验、接口权限、企微推送。"""

import io
from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from backend.apps.catalog import card_fx
from backend.apps.catalog.models import CardFxRate, CardFxSettings
from backend.apps.catalog.roles import GUEST_GROUP_NAME, ensure_boss_group

EXPECTED_160 = ["6.41", "12.82", "19.22", "25.63", "32.04", "38.44", "44.85", "51.25", "57.66", "64.07"]


class CalcTests(TestCase):
    def test_160_default_factor(self):
        got = [str(card_fx.charge_usd(a, Decimal("160.00"), Decimal("1.025"))) for a in card_fx.AMOUNTS]
        self.assertEqual(got, EXPECTED_160)

    def test_other_cases(self):
        self.assertEqual(str(card_fx.charge_usd(1000, Decimal("158.33"), Decimal("1.025"))), "6.48")
        self.assertEqual(str(card_fx.charge_usd(1000, Decimal("160.00"), Decimal("1.028"))), "6.43")
        self.assertEqual(card_fx.factor_percent(Decimal("1.0250")), "102.5")

    def test_parse_factor(self):
        self.assertEqual(card_fx.parse_factor("1.028"), Decimal("1.0280"))
        for bad, msg in (("0.99", "1.000 到 1.100"), ("1.2", "1.000 到 1.100"), ("abc", "数字"),
                         ("1.02501", "4 位小数"), ("", "请输入")):
            with self.assertRaisesMessage(ValueError, msg):
                card_fx.parse_factor(bad)


class FetchTests(TestCase):
    def q(self, **kw):
        base = dict(rate_date=date(2026, 11, 13), usd_jpy=Decimal("155.12"), usd_cny=Decimal("7.1"), source="t")
        base.update(kw)
        return card_fx.FxQuote(**base)

    def test_validate(self):
        today = date(2026, 11, 16)
        card_fx.validate(self.q(), today)
        for kw in ({"usd_jpy": Decimal("50")}, {"usd_cny": Decimal("11")}, {"rate_date": date(2026, 11, 17)}):
            with self.assertRaises(card_fx.CardFxError):
                card_fx.validate(self.q(**kw), today)

    def test_frankfurter_parse_and_upsert(self):
        js = {"amount": 1.0, "base": "USD", "date": "2026-11-13", "rates": {"CNY": 7.1234, "JPY": 155.5}}
        with mock.patch.object(card_fx, "_get_json", return_value=js):
            call_command("fetch_card_fx_rate", stdout=io.StringIO())
            call_command("fetch_card_fx_rate", stdout=io.StringIO())
        r = CardFxRate.objects.get()
        self.assertEqual((r.usd_jpy, r.usd_cny, r.source), (Decimal("155.5"), Decimal("7.1234"), "frankfurter"))

    def test_fallback_and_all_fail(self):
        er = {"result": "success", "base_code": "USD", "time_last_update_unix": 1763251200,
              "rates": {"CNY": 7.1, "JPY": 154.2}}

        def fake(url):
            if "frankfurter" in url:
                raise card_fx.CardFxError("网络错误: timed out")
            return er

        with mock.patch.object(card_fx, "_get_json", side_effect=fake):
            call_command("fetch_card_fx_rate", stdout=io.StringIO())
        self.assertEqual(CardFxRate.objects.get().source, "er-api")

        with mock.patch.object(card_fx, "_get_json", side_effect=card_fx.CardFxError("down")):
            with self.assertRaises(CommandError):
                call_command("fetch_card_fx_rate", stdout=io.StringIO())
        self.assertEqual(CardFxRate.objects.count(), 1)

    def test_bad_data_not_saved(self):
        js = {"base": "USD", "date": "2026-11-13", "rates": {"CNY": 7.1, "JPY": 1.55}}
        with mock.patch.object(card_fx, "_get_json", return_value=js):
            with self.assertRaises(CommandError):
                call_command("fetch_card_fx_rate", "--source", "frankfurter", stdout=io.StringIO())
        self.assertFalse(CardFxRate.objects.exists())


class ApiTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.staff = U.objects.create_user("s", password="x", is_staff=True)
        self.boss = U.objects.create_user("boss", password="x", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.admin = U.objects.create_superuser("admin", password="x")
        self.guest = U.objects.create_user("g", password="x", is_staff=True)
        self.guest.groups.add(Group.objects.get_or_create(name=GUEST_GROUP_NAME)[0])

    def c(self, u=None):
        c = APIClient()
        if u:
            c.force_authenticate(u)
        return c

    def test_no_data(self):
        r = self.c(self.staff).get("/api/card-fx/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["has_data"])
        self.assertEqual(r.data["items"], [])

    def test_permissions_and_payload(self):
        CardFxRate.objects.create(rate_date=date(2026, 11, 13), usd_jpy=Decimal("160"), usd_cny=Decimal("6.6719"))
        self.assertEqual(self.c().get("/api/card-fx/").status_code, 401)
        self.assertEqual(self.c(self.guest).get("/api/card-fx/").status_code, 403)
        r = self.c(self.staff).get("/api/card-fx/")
        self.assertEqual([i["usd"] for i in r.data["items"]], EXPECTED_160)
        self.assertEqual((r.data["factor"], r.data["factor_percent"], r.data["usd_cny"]), ("1.0250", "102.5", "6.6719"))

        for u in (self.staff, self.boss):
            self.assertEqual(self.c(u).patch("/api/card-fx/settings/", {"factor": "1.03"}, format="json").status_code, 403)
        bad = self.c(self.admin).patch("/api/card-fx/settings/", {"factor": "1.5"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("1.000 到 1.100", bad.data["detail"])
        self.assertEqual(self.c(self.staff).get("/api/card-fx/settings/").status_code, 403)
        pv = self.c(self.admin).get("/api/card-fx/settings/", {"factor": "1.028"})
        self.assertEqual((pv.data["items"][0]["usd"], pv.data["saved_factor"]), ("6.43", "1.0250"))
        self.assertEqual(CardFxSettings.objects.get().factor, Decimal("1.0250"))
        r = self.c(self.admin).patch("/api/card-fx/settings/", {"factor": "1.028"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["items"][0]["usd"], "6.43")
        self.assertEqual(CardFxSettings.objects.get().updated_by, self.admin)

    def test_stale(self):
        CardFxRate.objects.create(rate_date=date(2026, 11, 10), usd_jpy=Decimal("160"), usd_cny=Decimal("7"))
        p = card_fx.build_payload(date(2026, 11, 16))
        self.assertEqual((p["stale_days"], p["is_stale"]), (6, True))
        self.assertFalse(card_fx.build_payload(date(2026, 11, 14))["is_stale"])


@override_settings(WECOM_REMINDER_ENABLED=True, STAFF_FRONTEND_BASE_URL="https://xh.example")
class WecomTests(TestCase):
    def test_markdown_and_send(self):
        CardFxRate.objects.create(rate_date=date(2026, 11, 13), usd_jpy=Decimal("160"), usd_cny=Decimal("6.6719"))
        with mock.patch.dict("os.environ", {"CARD_FX_WECOM_WEBHOOK_URL": "https://hook.example"}), \
                mock.patch("backend.apps.catalog.management.commands.send_card_fx_wecom.send_markdown") as sm:
            call_command("send_card_fx_wecom", "--date", "2026-11-16", stdout=io.StringIO())
        url, text = sm.call_args[0]
        self.assertEqual(url, "https://hook.example")
        self.assertIn("11月16日 周一 · 汇率日期 11月13日", text)
        self.assertIn("> 8,000 日元 → 充 **$51.25**", text)
        self.assertIn("乘以 **102.5%**", text)
        self.assertIn("https://xh.example/hall", text)
        self.assertNotIn("未更新", text)
        stale = card_fx.build_wecom_markdown(date(2026, 11, 20))
        self.assertIn("汇率已 7 天未更新", stale)

    def test_no_data_sends_alert_and_fails(self):
        with mock.patch.dict("os.environ", {"CARD_FX_WECOM_WEBHOOK_URL": "https://hook.example"}), \
                mock.patch("backend.apps.catalog.management.commands.send_card_fx_wecom.send_markdown") as sm:
            with self.assertRaises(CommandError):
                call_command("send_card_fx_wecom", stdout=io.StringIO())
        self.assertIn("还没有数据", sm.call_args[0][1])

    @override_settings(WECOM_REMINDER_ENABLED=False)
    def test_disabled(self):
        with mock.patch("backend.apps.catalog.management.commands.send_card_fx_wecom.send_markdown") as sm:
            call_command("send_card_fx_wecom", stdout=io.StringIO())
        sm.assert_not_called()
