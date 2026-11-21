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
