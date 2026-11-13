"""教程+话术（知识库）：接口权限 / 校验，以及从商品导入的命令。"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from backend.apps.catalog.models import SKU, Business, KnowledgeEntry, Platform, QuickPhrase, TutorialPool
from backend.apps.catalog.roles import GUEST_GROUP_NAME, ensure_boss_group


class KnowledgeApiTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.staff = U.objects.create_user("s", password="x", is_staff=True)
        self.boss = U.objects.create_user("boss", password="x", is_staff=True)
        self.boss.groups.add(ensure_boss_group())
        self.guest = U.objects.create_user("g", password="x", is_staff=True)
        self.guest.groups.add(Group.objects.get_or_create(name=GUEST_GROUP_NAME)[0])
        self.p = Platform.objects.create(name="Fanbox")

    def c(self, u):
        c = APIClient()
        c.force_authenticate(u)
        return c

    def test_crud(self):
        r = self.c(self.staff).post("/api/knowledge/", {"platform_id": self.p.id, "kind": "faq", "title": "币多久过期？",
                                                         "content": "180 天"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        eid = r.data["id"]
        r = self.c(self.staff).get("/api/knowledge/")
        self.assertEqual(len(r.data["entries"]), 1)
        self.assertTrue(r.data["can_edit"])
        self.assertFalse(r.data["can_delete"])
        self.assertEqual(r.data["platforms"][0]["name"], "Fanbox")
        r = self.c(self.staff).patch(f"/api/knowledge/{eid}/", {"content": "180 天（6 个月）"}, format="json")
        self.assertEqual(r.data["content"], "180 天（6 个月）")
        self.assertEqual(self.c(self.staff).delete(f"/api/knowledge/{eid}/").status_code, 403)
        self.assertEqual(self.c(self.boss).delete(f"/api/knowledge/{eid}/").status_code, 204)
        self.assertFalse(KnowledgeEntry.objects.exists())

    def test_validation(self):
        c = self.c(self.staff)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "tutorial", "title": "x"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "tutorial", "title": "x", "url": "javascript:alert(1)"},
                                format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "faq", "title": "问题"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "bad", "title": "x"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "faq", "title": "x", "content": "y", "platform_id": 999},
                                format="json").status_code, 400)
        r = c.post("/api/knowledge/", {"kind": "phrase", "content": "请尽快登录核对"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["title"], "请尽快登录核对")  # 快捷语没写标题就用内容开头
        self.assertIsNone(r.data["platform_id"])  # 通用

    def test_guest_read_only(self):
        self.assertEqual(self.c(self.guest).get("/api/knowledge/").status_code, 200)
        self.assertFalse(self.c(self.guest).get("/api/knowledge/").data["can_edit"])
        r = self.c(self.guest).post("/api/knowledge/", {"kind": "faq", "title": "x", "content": "y"}, format="json")
        self.assertEqual(r.status_code, 403)


class SeedKnowledgeTests(TestCase):
    def setUp(self):
        p = Platform.objects.create(name="apple")
        b1 = Business.objects.create(platform=p, name="苹果id")
        b2 = Business.objects.create(platform=p, name="共享苹果id")
        s1 = SKU.objects.create(business=b1, name="美区", tutorial_text="苹果登录教程 / 改密码教程")
        s2 = SKU.objects.create(business=b1, name="日区", tutorial_text="苹果登录教程")
        s3 = SKU.objects.create(business=b2, name="共享", tutorial_text="没有链接的教程")
        for s in (s1, s2, s3):
            QuickPhrase.objects.create(sku=s, content="1️⃣尽量不要换ip登录\n2️⃣尽快改密码")
        QuickPhrase.objects.create(sku=s1, content="美区专属提醒")
        TutorialPool.objects.create(name="苹果登录教程", detail_url="https://a.example/login")
        TutorialPool.objects.create(name="改密码教程", detail_url="https://a.example/pw")
        TutorialPool.objects.create(name="没人用的教程", detail_url="https://a.example/unused")

    def run_cmd(self, *a):
        out = StringIO()
        call_command("seed_knowledge_base", *a, stdout=out)
        return out.getvalue()

    def test_dry_run_writes_nothing(self):
        out = self.run_cmd()
        self.assertIn("试运行", out)
        self.assertIn("没有链接的教程", out)
        self.assertFalse(KnowledgeEntry.objects.exists())

    def test_apply_dedupes_and_is_idempotent(self):
        self.run_cmd("--apply")
        ph = KnowledgeEntry.objects.filter(kind="phrase")
        self.assertEqual(ph.count(), 2)  # 三个档位相同的话术只放一条
        self.assertTrue(ph.filter(title__contains="苹果id、共享苹果id").exists())
        tu = KnowledgeEntry.objects.filter(kind="tutorial")
        self.assertEqual(set(tu.filter(platform__name="apple").values_list("title", flat=True)), {"苹果登录教程", "改密码教程"})
        self.assertEqual(tu.get(title="没人用的教程").platform, None)  # 没被用到的放「通用」
        self.assertEqual(SKU.objects.get(name="美区").quick_phrases.count(), 2)  # 原数据不动
        n = KnowledgeEntry.objects.count()
        self.run_cmd("--apply")
        self.assertEqual(KnowledgeEntry.objects.count(), n)  # 再跑一次不会重复
