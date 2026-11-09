"""值班打卡接口：排班规则、只能当天打卡、权限。"""

from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.catalog import duty
from backend.apps.catalog.models import DutyRecord, DutySettings
from backend.apps.catalog.roles import ensure_boss_group


def _png():
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (10, 10), (0, 112, 74)).save(buf, "PNG")
    return SimpleUploadedFile("s.png", buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT="/tmp/xh-duty-test-media")
class DutyTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.a = U.objects.create_user("lin", password="x", is_staff=True)
        self.b = U.objects.create_user("jie", password="x", is_staff=True)
        self.boss = U.objects.create_user("boss", password="x", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.other = U.objects.create_user("other", password="x", is_staff=True)
        self.today = timezone.localdate()
        DutySettings.objects.create(config={"a_user": self.a.id, "b_user": self.b.id, "rotStart": self.today.isoformat(),
                                            "rotFirst": "a"})

    def client_for(self, u):
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_rules(self):
        cfg = duty.load_config()
        t0 = {t["task"]: t for t in duty.tasks_on(self.today, cfg)}
        self.assertEqual(t0["sell"]["who"], "a")
        self.assertEqual(t0["stock"]["who"], "b")
        t1 = {t["task"]: t for t in duty.tasks_on(self.today + timedelta(days=1), cfg)}
        self.assertEqual(t1["sell"]["who"], "b")
        first = date(2026, 11, 1)
        self.assertEqual(duty.stock_target(first, cfg), 200)
        self.assertEqual(duty.stock_target(date(2026, 11, 30), cfg), 500)
        self.assertIn("clean", [t["task"] for t in duty.tasks_on(date(2026, 11, 30), cfg)])
        self.assertIn("unbind", [t["task"] for t in duty.tasks_on(date(2026, 11, 2), cfg)])

    def test_checkin_today_and_lock(self):
        c = self.client_for(self.a)
        r = c.post("/api/duty/checkin/", {"date": self.today.isoformat(), "task": "sell",
                                          "data": '{"qty": 30, "note": "ok"}', "image": _png()}, format="multipart")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["data"]["qty"], 30)
        self.assertTrue(r.json()["img"].startswith("/media/duty/"))
        # 过去的日子不能补
        y = (self.today - timedelta(days=1)).isoformat()
        r = c.post("/api/duty/checkin/", {"date": y, "task": "sell", "data": "{}"}, format="multipart")
        self.assertEqual(r.status_code, 400)
        # 不是自己的事
        r = c.post("/api/duty/checkin/", {"date": self.today.isoformat(), "task": "stock", "data": '{"stock": 300}'},
                   format="multipart")
        self.assertEqual(r.status_code, 403)
        r = self.client_for(self.other).post("/api/duty/checkin/", {"date": self.today.isoformat(), "task": "sell",
                                                                    "data": "{}"}, format="multipart")
        self.assertEqual(r.status_code, 403)

    def test_stock_requires_number_and_boss_confirm(self):
        c = self.client_for(self.b)
        r = c.post("/api/duty/checkin/", {"date": self.today.isoformat(), "task": "stock", "data": "{}"},
                   format="multipart")
        self.assertEqual(r.status_code, 400)
        r = c.post("/api/duty/checkin/", {"date": self.today.isoformat(), "task": "stock", "data": '{"stock": 210}'},
                   format="multipart")
        self.assertEqual(r.status_code, 200)
        r = c.post("/api/duty/confirm/", {"date": self.today.isoformat(), "task": "stock"}, format="json")
        self.assertEqual(r.status_code, 403)
        r = self.client_for(self.boss).post("/api/duty/confirm/", {"date": self.today.isoformat(), "task": "stock"},
                                            format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["confirmed"])
        st = self.client_for(self.boss).get("/api/duty/state/").json()
        self.assertTrue(st["me"]["manager"])
        self.assertIn(f"{self.today.isoformat()}|stock", st["records"])
        self.assertEqual(self.client_for(self.a).get("/api/duty/state/").json()["me"]["role"], "a")

    def test_undo_only_today(self):
        DutyRecord.objects.create(date=self.today - timedelta(days=1), task="sell", done_by=self.a,
                                  done_at=timezone.now())
        r = self.client_for(self.a).post("/api/duty/undo/", {"date": (self.today - timedelta(days=1)).isoformat(),
                                                             "task": "sell"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(DutyRecord.objects.count(), 1)

    def test_settings_only_manager(self):
        r = self.client_for(self.a).put("/api/duty/settings/", {"config": {"stockEnd": 600}}, format="json")
        self.assertEqual(r.status_code, 403)
        r = self.client_for(self.boss).put("/api/duty/settings/", {"config": {"stockEnd": 600, "stockOverride":
                                                                              {"2026-11-10": 999}}}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        cfg = duty.load_config()
        self.assertEqual(cfg["stockEnd"], 600)
        self.assertEqual(duty.stock_target(date(2026, 11, 10), cfg), 999)


@override_settings(MEDIA_ROOT="/tmp/xh-duty-test-media")
class DutyLeaveTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.a = U.objects.create_user("lin", password="x", is_staff=True)
        self.b = U.objects.create_user("jie", password="x", is_staff=True)
        self.boss = U.objects.create_user("boss", password="x", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.today = timezone.localdate()
        DutySettings.objects.create(config={"a_user": self.a.id, "b_user": self.b.id, "rotStart": self.today.isoformat(),
                                            "rotFirst": "a"})

    def c(self, u):
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_apply_approve_and_cover(self):
        r = self.c(self.a).post("/api/duty/leave/", {"start": self.today.isoformat(), "end": self.today.isoformat(),
                                                     "reason": "看病"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["status"], "pending")
        # 没批准之前，今天还是 A 销卡
        self.assertEqual({t["task"]: t["who"] for t in duty.tasks_for(self.today)}["sell"], "a")
        lid = r.json()["id"]
        self.assertEqual(self.c(self.b).post(f"/api/duty/leave/{lid}/approve/").status_code, 403)
        r = self.c(self.boss).post(f"/api/duty/leave/{lid}/approve/")
        self.assertEqual(r.json()["status"], "approved")
        t = {x["task"]: x for x in duty.tasks_for(self.today)}
        self.assertEqual(t["sell"]["who"], "b")
        self.assertEqual(t["sell"]["cover_for"], "a")
        # B 可以打 A 的销卡，A 不行了
        ok = self.c(self.b).post("/api/duty/checkin/", {"date": self.today.isoformat(), "task": "sell", "data": "{}"},
                                 format="multipart")
        self.assertEqual(ok.status_code, 200, ok.content)
        # 明天轮流照旧（不顺延）：明天本来就是 B 销卡
        self.assertEqual({x["task"]: x["who"] for x in duty.tasks_for(self.today + timedelta(days=1))}["sell"], "b")
        st = self.c(self.boss).get("/api/duty/state/").json()
        self.assertEqual(st["leaves"][0]["who"], "a")

    def test_both_on_leave_skips(self):
        for u in (self.a, self.b):
            self.c(self.boss).post("/api/duty/leave/", {"start": self.today.isoformat(), "who": "a" if u == self.a else "b"},
                                   format="json")
        t = duty.tasks_for(self.today)
        self.assertTrue(all(x["who"] is None and x.get("skip") for x in t))
        r = self.c(self.boss).post("/api/duty/checkin/", {"date": self.today.isoformat(), "task": "sell", "data": "{}"},
                                   format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_rules_for_employees(self):
        y = (self.today - timedelta(days=1)).isoformat()
        self.assertEqual(self.c(self.a).post("/api/duty/leave/", {"start": y}, format="json").status_code, 400)
        r = self.c(self.a).post("/api/duty/leave/", {"start": self.today.isoformat()}, format="json")
        self.assertEqual(self.c(self.a).post("/api/duty/leave/", {"start": self.today.isoformat()}, format="json").status_code,
                         400)  # 重复
        lid = r.json()["id"]
        self.assertEqual(self.c(self.a).post(f"/api/duty/leave/{lid}/cancel/").json()["status"], "cancelled")

    def test_swap_and_off_day(self):
        tomorrow = (self.today + timedelta(days=1)).isoformat()
        r = self.c(self.boss).put("/api/duty/settings/", {"config": {"swaps": {f"{self.today.isoformat()}|sell": "b"},
                                                                     "offDays": [tomorrow]}}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        t = {x["task"]: x for x in duty.tasks_for(self.today)}
        self.assertEqual(t["sell"]["who"], "b")
        self.assertTrue(t["sell"]["swapped"])
        self.assertEqual(duty.tasks_for(self.today + timedelta(days=1)), [])
