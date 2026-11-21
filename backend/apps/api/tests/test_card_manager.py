"""薪火卡管家权限：关键词解析、/me/ 返回、管理接口权限。"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from backend.apps.catalog import card_manager
from backend.apps.catalog.roles import GUEST_GROUP_NAME, ensure_boss_group


class ParseTests(TestCase):
    def test_parse(self):
        self.assertEqual(card_manager.parse_keywords("冬\n苏橘， 薪卡,冬 ;"), ["冬", "苏橘", "薪卡"])
        self.assertEqual(card_manager.parse_keywords(["  a ", "", "a", "b"]), ["a", "b"])
        self.assertEqual(card_manager.parse_keywords(None), [])
        with self.assertRaisesMessage(ValueError, "太长"):
            card_manager.parse_keywords("x" * 31)
        with self.assertRaisesMessage(ValueError, "最多"):
            card_manager.parse_keywords([str(i) for i in range(51)])


class ApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.su = User.objects.create_user("root", password="p", is_staff=True, is_superuser=True)
        self.boss = User.objects.create_user("boss", password="p", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.a = User.objects.create_user("staffA", password="p", is_staff=True)
        self.guest = User.objects.create_user("guest", password="p", is_staff=True)
        self.guest.groups.add(Group.objects.get_or_create(name=GUEST_GROUP_NAME)[0])
        self.c = APIClient()

    def as_(self, u):
        self.c.force_authenticate(u)
        return self.c

    def test_me_staff(self):
        card_manager.set_keywords(self.a, ["冬", "苏橘"], self.su)
        r = self.as_(self.a).get("/api/card-manager/me/")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["is_admin"])
        self.assertEqual(r.data["keywords"], ["冬", "苏橘"])
        self.assertNotIn("staff", r.data)

    def test_me_admin_lists_staff(self):
        card_manager.set_keywords(self.a, ["冬"], self.su)
        r = self.as_(self.boss).get("/api/card-manager/me/")
        self.assertTrue(r.data["is_admin"])
        names = {x["username"]: x["keywords"] for x in r.data["staff"]}
        self.assertEqual(names["staffA"], ["冬"])
        self.assertNotIn("guest", names)

    def test_admin_keywords_for_claiming(self):
        # 老板也能填关键词（认领用）：照样能看全部，staff 列表里带上自己的关键词
        r = self.as_(self.su).put(f"/api/card-manager/scopes/{self.boss.pk}/", {"keywords": ["hazen"]}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["keywords"], ["hazen"])
        r = self.as_(self.boss).get("/api/card-manager/me/")
        self.assertTrue(r.data["is_admin"])
        self.assertEqual(r.data["keywords"], ["hazen"])
        names = {x["username"]: x["keywords"] for x in r.data["staff"]}
        self.assertEqual(names[self.boss.username], ["hazen"])

    def test_guest_forbidden(self):
        self.assertEqual(self.as_(self.guest).get("/api/card-manager/me/").status_code, 403)

    def test_scopes_superuser_only(self):
        self.assertEqual(self.as_(self.boss).get("/api/card-manager/scopes/").status_code, 403)
        self.assertEqual(self.as_(self.a).put(f"/api/card-manager/scopes/{self.a.pk}/", {"keywords": ["x"]}, format="json").status_code, 403)
        r = self.as_(self.su).put(f"/api/card-manager/scopes/{self.a.pk}/", {"keywords": "冬\n薪卡"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["keywords"], ["冬", "薪卡"])
        rows = self.as_(self.su).get("/api/card-manager/scopes/").data["results"]
        self.assertEqual(next(x for x in rows if x["username"] == "staffA")["keywords"], ["冬", "薪卡"])

    def test_put_unknown_or_guest(self):
        self.assertEqual(self.as_(self.su).put("/api/card-manager/scopes/99999/", {"keywords": []}, format="json").status_code, 404)
        self.assertEqual(self.as_(self.su).put(f"/api/card-manager/scopes/{self.guest.pk}/", {"keywords": []}, format="json").status_code, 404)


class RiskHandledTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.boss = User.objects.create_user("boss", password="p", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.a = User.objects.create_user("staffA", password="p", is_staff=True)
        self.b = User.objects.create_user("staffB", password="p", is_staff=True)
        self.none = User.objects.create_user("noscope", password="p", is_staff=True)
        card_manager.set_keywords(self.a, ["冬"], self.boss)
        card_manager.set_keywords(self.b, ["苏橘"], self.boss)
        self.c = APIClient()

    def as_(self, u):
        self.c.force_authenticate(u)
        return self.c

    def item(self, **kw):
        d = {"card_id": "C1", "risk": "cvv", "mark": "2026-11-21 10:00:00", "result": "ok", "card_suffix": "1234", "card_remark": "冬卡7"}
        d.update(kw)
        return d

    def test_mark_list_and_scope(self):
        r = self.as_(self.a).post("/api/card-manager/risk-handled/", {"items": [self.item()]}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["results"][0]["handled_by"], "staffA")
        # 自己、老板能看到；别的员工看不到
        self.assertEqual(len(self.as_(self.a).get("/api/card-manager/risk-handled/").data["results"]), 1)
        self.assertEqual(len(self.as_(self.boss).get("/api/card-manager/risk-handled/").data["results"]), 1)
        self.assertEqual(len(self.as_(self.b).get("/api/card-manager/risk-handled/").data["results"]), 0)

    def test_same_card_risk_keeps_latest(self):
        self.as_(self.a).post("/api/card-manager/risk-handled/", {"items": [self.item()]}, format="json")
        self.as_(self.boss).post("/api/card-manager/risk-handled/", {"items": [self.item(mark="2026-11-22 09:00:00", result="locked")]}, format="json")
        rows = self.as_(self.boss).get("/api/card-manager/risk-handled/").data["results"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["mark"], rows[0]["result"], rows[0]["handled_by"]), ("2026-11-22 09:00:00", "locked", "boss"))

    def test_staff_cannot_mark_others_card(self):
        r = self.as_(self.b).post("/api/card-manager/risk-handled/", {"items": [self.item()]}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_bad_input(self):
        self.assertEqual(self.as_(self.a).post("/api/card-manager/risk-handled/", {"items": [self.item(risk="xx")]}, format="json").status_code, 400)
        self.assertEqual(self.as_(self.a).post("/api/card-manager/risk-handled/", {"items": []}, format="json").status_code, 400)
        self.assertEqual(self.as_(self.none).get("/api/card-manager/risk-handled/").status_code, 403)

    def test_undo(self):
        self.as_(self.a).post("/api/card-manager/risk-handled/", {"items": [self.item()]}, format="json")
        self.assertEqual(self.as_(self.b).post("/api/card-manager/risk-handled/undo/", {"card_id": "C1", "risk": "cvv"}, format="json").status_code, 403)
        self.assertEqual(self.as_(self.a).post("/api/card-manager/risk-handled/undo/", {"card_id": "C1", "risk": "cvv"}, format="json").status_code, 200)
        self.assertEqual(self.as_(self.a).post("/api/card-manager/risk-handled/undo/", {"card_id": "C1", "risk": "cvv"}, format="json").status_code, 404)


class OtpLinkTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()  # 清掉限流计数
        User = get_user_model()
        self.boss = User.objects.create_user("boss2", password="p", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.a = User.objects.create_user("otpA", password="p", is_staff=True)
        self.b = User.objects.create_user("otpB", password="p", is_staff=True)
        card_manager.set_keywords(self.a, ["冬"], self.boss)
        card_manager.set_keywords(self.b, ["苏橘"], self.boss)
        self.c = APIClient()
        self.card = {"card_id": "C9", "card_bin": "493724", "card_suffix": "6234", "card_remark": "冬卡7"}

    def as_(self, u):
        self.c.force_authenticate(u)
        return self.c

    def now_cst(self, minutes_ago=0):
        from datetime import timedelta
        from zoneinfo import ZoneInfo

        from django.utils import timezone

        return (timezone.now() - timedelta(minutes=minutes_ago)).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")

    def test_create_get_renew_revoke(self):
        url = "/api/card-manager/otp-link/"
        self.assertIsNone(self.as_(self.a).post(url, {**self.card, "action": "get"}, format="json").data["link"])
        t1 = self.as_(self.a).post(url, {**self.card, "action": "create"}, format="json").data["link"]["token"]
        # 再 create 还是同一个链接
        self.assertEqual(self.as_(self.a).post(url, {**self.card, "action": "create"}, format="json").data["link"]["token"], t1)
        t2 = self.as_(self.a).post(url, {**self.card, "action": "renew"}, format="json").data["link"]["token"]
        self.assertNotEqual(t1, t2)
        pub = APIClient()
        self.assertEqual(pub.get(f"/api/otp/{t1}/json/").status_code, 404)  # 旧链接作废
        self.assertEqual(pub.get(f"/api/otp/{t2}/json/").status_code, 200)
        self.assertTrue(self.as_(self.a).post(url, {**self.card, "action": "revoke"}, format="json").data["ok"])
        self.assertEqual(pub.get(f"/api/otp/{t2}/json/").status_code, 404)

    def test_staff_scope(self):
        r = self.as_(self.b).post("/api/card-manager/otp-link/", {**self.card, "action": "create"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_upload_and_public(self):
        token = self.as_(self.a).post("/api/card-manager/otp-link/", {**self.card, "action": "create"}, format="json").data["link"]["token"]
        items = [
            {"card_id": "C9", "payment_no": "P1", "code": "814362", "trans_time": self.now_cst(1)},
            {"card_id": "C9", "payment_no": "P0", "code": "111111", "trans_time": self.now_cst(30)},  # 太旧，不显示
            {"card_id": "OTHER", "payment_no": "P2", "code": "222222", "trans_time": self.now_cst(1)},  # 别的卡
            {"card_id": "C9", "payment_no": "P3", "code": "abc", "trans_time": self.now_cst(1)},  # 格式不对
        ]
        self.assertEqual(self.as_(self.a).post("/api/card-manager/otp-codes/", {"items": items}, format="json").status_code, 403)  # 员工不能传
        r = self.as_(self.boss).post("/api/card-manager/otp-codes/", {"items": items}, format="json")
        self.assertEqual(r.data["created"], 3)
        self.assertEqual(self.as_(self.boss).post("/api/card-manager/otp-codes/", {"items": items}, format="json").data["created"], 0)  # 重复不再存
        d = APIClient().get(f"/api/otp/{token}/json/").data
        self.assertEqual(d["card"], "493724****6234")
        self.assertEqual([c["code"] for c in d["codes"]], ["814362"])
        self.assertNotIn("冬", str(d))  # 不给客户看备注
        page = APIClient().get(f"/api/otp/{token}/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("卡片验证码", page.content.decode())
