"""值班打卡：事务频率与分配、只能当天打卡、员工只看自己的、请假代班、调班 / 全员休息、企业微信推送。"""

from datetime import date, timedelta
from io import BytesIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from backend.apps.catalog import duty
from backend.apps.catalog.models import DutyRecord, DutyTask
from backend.apps.catalog.roles import ensure_boss_group


def _png():
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (10, 10), (0, 112, 74)).save(buf, "PNG")
    return SimpleUploadedFile("s.png", buf.getvalue(), content_type="image/png")


def _task(**kw):
    base = dict(key=kw.pop("key", "t"), name=kw.pop("name", "事务"), start_date=kw.pop("start_date", date(2026, 11, 1)))
    base.update(kw)
    return DutyTask(**base)


class EngineTests(TestCase):
    """排班算法（不碰数据库）。"""

    def test_frequencies(self):
        wk = _task(freq_type="weekly", freq_weekdays=[0, 2])  # 周一、周三
        self.assertTrue(duty.occurs(wk, date(2026, 11, 2)))  # 周一
        self.assertFalse(duty.occurs(wk, date(2026, 11, 3)))
        mo = _task(freq_type="monthly", freq_monthdays=[1, -1])
        self.assertTrue(duty.occurs(mo, date(2026, 11, 30)))
        self.assertTrue(duty.occurs(mo, date(2026, 12, 1)))
        self.assertFalse(duty.occurs(mo, date(2026, 11, 29)))
        iv = _task(freq_type="interval", freq_interval=3)
        self.assertEqual([d for d in range(1, 11) if duty.occurs(iv, date(2026, 11, d))], [1, 4, 7, 10])
        once = _task(freq_type="once", start_date=date(2026, 11, 5))
        self.assertTrue(duty.occurs(once, date(2026, 11, 5)))
        self.assertFalse(duty.occurs(once, date(2026, 11, 6)))
        ended = _task(freq_type="daily", end_date=date(2026, 11, 3))
        self.assertFalse(duty.occurs(ended, date(2026, 11, 4)))

    def test_rotation_with_weight_and_leave(self):
        t = _task(freq_type="daily", assign_mode="rotate", assignees=[1, 1, 2])  # 1 号做两次、2 号做一次
        cfg = {"swaps": {}, "offDays": []}
        who = [duty.assignments_on(date(2026, 11, d), [t], cfg, set())[0]["user"] for d in range(1, 7)]
        self.assertEqual(who, [1, 1, 2, 1, 1, 2])
        a = duty.assignments_on(date(2026, 11, 1), [t], cfg, {1})[0]
        self.assertEqual((a["user"], a["cover_for"]), (2, 1))
        a = duty.assignments_on(date(2026, 11, 1), [t], cfg, {1, 2})[0]
        self.assertTrue(a["skip"])

    def test_weekly_rotation_index(self):
        t = _task(freq_type="weekly", freq_weekdays=[0, 4], assign_mode="rotate", assignees=[1, 2, 3])  # 周一、周五
        cfg = {"swaps": {}, "offDays": []}
        days = [d for d in range(1, 22) if duty.occurs(t, date(2026, 11, d))]
        who = [duty.assignments_on(date(2026, 11, d), [t], cfg, set())[0]["user"] for d in days]
        self.assertEqual(who, [1, 2, 3, 1, 2, 3][:len(days)])

    def test_all_mode_swap_off_and_targets(self):
        t = _task(key="x", freq_type="daily", assign_mode="all", assignees=[1, 2, 3], target_mode="ramp",
                  target_start=200, target_end=500)
        cfg = {"swaps": {}, "offDays": ["2026-11-02"]}
        a = duty.assignments_on(date(2026, 11, 1), [t], cfg, {2})
        self.assertEqual([x["user"] for x in a], [1, None, 3])
        self.assertEqual(a[0]["target"], 200)
        self.assertEqual(duty.assignments_on(date(2026, 11, 2), [t], cfg, set()), [])
        self.assertEqual(duty.target_for(t, date(2026, 11, 30)), 500)
        f = _task(key="f", freq_type="daily", assign_mode="fixed", assignees=[1, 2])
        a = duty.assignments_on(date(2026, 11, 3), [f], {"swaps": {"2026-11-03|f": 3}, "offDays": []}, set())[0]
        self.assertEqual((a["user"], a["swapped"]), (3, True))
        a = duty.assignments_on(date(2026, 11, 4), [f], {"swaps": {}, "offDays": []}, {1})[0]
        self.assertEqual(a["user"], 2)  # 固定的人请假，列表里下一个人代做


@override_settings(MEDIA_ROOT="/tmp/xh-duty-test-media", STAFF_FRONTEND_BASE_URL="https://staff.example")
class DutyApiTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.u1 = U.objects.create_user("u1", password="x", is_staff=True)
        self.u2 = U.objects.create_user("u2", password="x", is_staff=True)
        self.u3 = U.objects.create_user("u3", password="x", is_staff=True)
        self.boss = U.objects.create_user("boss", password="x", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.today = timezone.localdate()
        self.A = DutyTask.objects.create(key="A", name="事务A", start_date=self.today, freq_type="daily",
                                         assign_mode="rotate", assignees=[self.u1.id, self.u2.id],
                                         qty_enabled=True, qty_label="数量", qty_unit="个", qty_required=True,
                                         target_mode="fixed", target_start=10)
        self.B = DutyTask.objects.create(key="B", name="事务B", start_date=self.today, freq_type="daily",
                                         assign_mode="fixed", assignees=[self.u3.id], checklist=["第一步", "第二步"])

    def c(self, u):
        c = APIClient()
        c.force_authenticate(u)
        return c

    def checkin(self, u, task, data="{}", **extra):
        return self.c(u).post("/api/duty/checkin/", {"date": self.today.isoformat(), "task": task, "data": data, **extra},
                              format="multipart")

    def test_employee_sees_only_own(self):
        st = self.c(self.u3).get("/api/duty/state/").json()
        today = st["schedule"][self.today.isoformat()]
        self.assertEqual([(a["task"], a["user"]) for a in today], [("B", self.u3.id)])
        self.assertFalse(st["me"]["manager"])
        boss = self.c(self.boss).get("/api/duty/state/").json()
        self.assertEqual(len(boss["schedule"][self.today.isoformat()]), 2)
        self.assertTrue(boss["me"]["manager"])

    @mock.patch("backend.apps.catalog.duty_notify.webhook_url", return_value="https://hook")
    @mock.patch("backend.apps.catalog.duty_notify.send_markdown")
    def test_checkin_rules_and_push(self, send, _url):
        self.assertEqual(self.checkin(self.u2, "A", '{"qty": 3}').status_code, 403)  # 今天轮到 u1
        self.assertEqual(self.checkin(self.u1, "A", "{}").status_code, 400)  # 数量必填
        with self.captureOnCommitCallbacks(execute=True):
            r = self.checkin(self.u1, "A", '{"qty": 7, "note": "ok"}', image=_png())
        self.assertEqual(r.status_code, 200, r.content)
        import time
        for _ in range(50):
            if send.called:
                break
            time.sleep(0.02)
        md = send.call_args[0][1]
        self.assertIn("已打卡 · 📌 事务A", md)
        self.assertIn("u1", md)
        self.assertIn("还差 3", md)
        self.assertIn("https://staff.example/media/duty/", md)
        self.assertIn("今日进度：**1/2**", md)
        self.assertIn("事务B @u3", md)
        # 清单没勾完不行
        self.assertEqual(self.checkin(self.u3, "B", '{"checks": {"0": true}}').status_code, 400)
        self.assertEqual(self.checkin(self.u3, "B", '{"checks": {"0": true, "1": true}}').status_code, 200)
        # 过去的日子不能补
        r = self.c(self.u1).post("/api/duty/checkin/", {"date": (self.today - timedelta(days=1)).isoformat(),
                                                        "task": "A", "data": "{}"}, format="multipart")
        self.assertEqual(r.status_code, 400)

    def test_manager_checkin_for_and_confirm(self):
        r = self.checkin(self.boss, "B", '{"checks": {"0": true, "1": true}}', user=self.u3.id)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["by_manager"])
        r = self.c(self.boss).post("/api/duty/confirm/", {"date": self.today.isoformat(), "task": "B",
                                                          "user": self.u3.id}, format="json")
        self.assertTrue(r.json()["confirmed"])
        self.assertEqual(self.c(self.u1).post("/api/duty/confirm/", {}, format="json").status_code, 403)

    def test_task_crud_and_preview(self):
        body = {"name": "事务C", "freq_type": "weekly", "freq_weekdays": [0, 3], "start_date": self.today.isoformat(),
                "assign_mode": "rotate", "assignees": [self.u1.id, self.u1.id, self.u2.id], "push_wecom": True}
        self.assertEqual(self.c(self.u1).post("/api/duty/tasks/", body, format="json").status_code, 403)
        r = self.c(self.boss).post("/api/duty/tasks/preview/", body, format="json")
        self.assertEqual(len(r.json()["items"]), 10)
        r = self.c(self.boss).post("/api/duty/tasks/", body, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        tid, key = r.json()["id"], r.json()["key"]
        self.assertEqual(key, f"t{tid}")
        self.assertEqual(r.json()["assignees"], [self.u1.id, self.u1.id, self.u2.id])
        r = self.c(self.boss).put(f"/api/duty/tasks/{tid}/", {"freq_type": "weekly", "freq_weekdays": []}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c(self.boss).put(f"/api/duty/tasks/{tid}/", {"name": "事务C2"}, format="json")
        self.assertEqual(r.json()["name"], "事务C2")
        self.assertEqual(self.c(self.boss).delete(f"/api/duty/tasks/{tid}/").status_code, 204)
        # 有记录的只停用
        self.checkin(self.u3, "B", '{"checks": {"0": true, "1": true}}')
        r = self.c(self.boss).delete(f"/api/duty/tasks/{self.B.id}/")
        self.assertTrue(r.json()["archived"])
        self.assertFalse(DutyTask.objects.get(pk=self.B.id).is_active)

    def test_one_click_checkin_without_fields(self):
        """一键打卡：事务不要求数量 / 清单 / 截图时，空反馈直接打卡成功。"""
        DutyTask.objects.update(qty_enabled=False, qty_required=False, target_mode="none", checklist=[], image_mode="none")
        self.assertEqual(self.checkin(self.u1, "A").status_code, 200)
        self.assertEqual(self.checkin(self.u3, "B").status_code, 200)

    def test_leave_no_longer_changes_schedule(self):
        from backend.apps.catalog.models import DutyLeave

        DutyLeave.objects.create(user=self.u1, start_date=self.today, end_date=self.today, status="approved")
        a = [x for x in duty.assignments_for(self.today) if x["task"] == "A"][0]
        self.assertEqual(a["user"], self.u1.id)

    def test_swap_and_off_day(self):
        tomorrow = (self.today + timedelta(days=1)).isoformat()
        r = self.c(self.boss).put("/api/duty/settings/", {"config": {"swaps": {f"{self.today.isoformat()}|B": self.u1.id},
                                                                     "offDays": [tomorrow]}}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        b = [x for x in duty.assignments_for(self.today) if x["task"] == "B"][0]
        self.assertEqual(b["user"], self.u1.id)
        self.assertEqual(duty.assignments_for(self.today + timedelta(days=1)), [])


class LegacyMigrationTests(TestCase):
    def test_convert_old_config(self):
        from importlib import import_module

        from django.apps import apps

        from backend.apps.catalog.models import DutySettings

        U = get_user_model()
        a = U.objects.create_user("a", password="x")
        b = U.objects.create_user("b", password="x")
        DutySettings.objects.create(config={"a_user": a.id, "b_user": b.id, "rotStart": "2026-11-01", "rotFirst": "a",
                                            "stockStart": 200, "stockEnd": 500, "swaps": {"2026-11-09|sell": "b"},
                                            "offDays": ["2026-11-20"]})
        old = DutyRecord.objects.create(date=date(2026, 11, 2), task="stock", assignee=a, done_by=a,
                                        done_at=timezone.now(), data={"stock": 230, "qty": 40})
        cl = DutyRecord.objects.create(date=date(2026, 10, 31), task="clean", assignee=a, done_by=a,
                                       done_at=timezone.now(), data={"checks": {"clean": True, "notify": True}})
        mod = import_module("backend.apps.catalog.migrations.0076_duty_tasks")
        mod.convert_old_duty_config(apps, None)
        sell = DutyTask.objects.get(key="sell")
        stock = DutyTask.objects.get(key="stock")
        self.assertEqual(sell.assignees, [a.id, b.id])
        self.assertEqual(stock.assignees, [b.id, a.id])
        self.assertEqual(duty.target_for(stock, date(2026, 11, 30)), 500)
        self.assertEqual(duty.load_config()["swaps"], {"2026-11-09|sell": b.id})
        cfg = duty.load_config()
        who = {x["task"]: x["user"] for x in duty.assignments_on(date(2026, 11, 2), duty.active_tasks(), cfg, set())}
        self.assertEqual((who["sell"], who["stock"]), (b.id, a.id))
        old.refresh_from_db()
        cl.refresh_from_db()
        self.assertEqual(old.data, {"qty": 230, "added": 40})
        self.assertEqual(cl.data["checks"], {"0": True, "1": True})
