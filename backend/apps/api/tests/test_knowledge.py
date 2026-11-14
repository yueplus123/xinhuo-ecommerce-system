"""教程+话术（知识库）：接口权限 / 校验；SKU 编辑保存不再涉及话术 / 教程。"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from backend.apps.catalog.models import SKU, Business, KnowledgeEntry, Platform
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

    def test_staff_read_only_manager_edits(self):
        self.assertEqual(self.c(self.staff).post("/api/knowledge/", {"kind": "faq", "title": "x", "content": "y"},
                                                 format="json").status_code, 403)
        r = self.c(self.staff).get("/api/knowledge/")
        self.assertFalse(r.data["can_edit"])
        c = self.c(self.boss)
        t = c.post("/api/knowledge/", {"platform_id": self.p.id, "kind": "tutorial", "title": "取消扣款教程",
                                        "url": "https://a.example/t", "content": "不想续费的客户"}, format="json")
        self.assertEqual(t.status_code, 201, t.data)
        r = c.post("/api/knowledge/", {"platform_id": self.p.id, "kind": "faq", "title": "怎么取消扣款？",
                                        "content": "按教程操作：", "tutorials": [t.data["id"]]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["tutorials"], [t.data["id"]])
        eid = r.data["id"]
        self.assertTrue(c.get("/api/knowledge/").data["can_edit"])
        r = c.patch(f"/api/knowledge/{eid}/", {"content": "按下面的教程操作："}, format="json")
        self.assertEqual(r.data["content"], "按下面的教程操作：")
        self.assertEqual(self.c(self.staff).patch(f"/api/knowledge/{eid}/", {"content": "z"}, format="json").status_code, 403)
        self.assertEqual(self.c(self.staff).delete(f"/api/knowledge/{eid}/").status_code, 403)
        # 删掉教程：带着它的问答里的引用也一起去掉
        self.assertEqual(c.delete(f"/api/knowledge/{t.data['id']}/").status_code, 204)
        self.assertEqual(KnowledgeEntry.objects.get(pk=eid).tutorials, [])
        self.assertEqual(c.delete(f"/api/knowledge/{eid}/").status_code, 204)
        self.assertFalse(KnowledgeEntry.objects.exists())

    def test_validation(self):
        c = self.c(self.boss)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "tutorial", "title": "x"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "tutorial", "title": "x", "url": "javascript:alert(1)"},
                                format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "faq", "title": "问题"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "bad", "title": "x"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "faq", "title": "x", "content": "y", "platform_id": 999},
                                format="json").status_code, 400)
        self.assertEqual(c.post("/api/knowledge/", {"kind": "faq", "title": "x", "content": "y", "tutorials": [999]},
                                format="json").status_code, 400)
        r = c.post("/api/knowledge/", {"kind": "phrase", "content": "请尽快登录核对"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["title"], "请尽快登录核对")  # 快捷语没写标题就用内容开头
        self.assertIsNone(r.data["platform_id"])  # 通用
        # 附带教程只能选教程
        self.assertEqual(c.post("/api/knowledge/", {"kind": "faq", "title": "x", "content": "y",
                                                     "tutorials": [r.data["id"]]}, format="json").status_code, 400)

    def test_guest_read_only(self):
        self.assertEqual(self.c(self.guest).get("/api/knowledge/").status_code, 200)
        self.assertFalse(self.c(self.guest).get("/api/knowledge/").data["can_edit"])
        r = self.c(self.guest).post("/api/knowledge/", {"kind": "faq", "title": "x", "content": "y"}, format="json")
        self.assertEqual(r.status_code, 403)


class SkuEditorSaveTests(TestCase):
    """管理后台 SKU 编辑页保存：只保存价格、渠道等，不再有话术 / 教程字段。"""

    def test_save_sku(self):
        U = get_user_model()
        admin = U.objects.create_user("su", password="x", is_staff=True, is_superuser=True)
        p = Platform.objects.create(name="apple")
        b = Business.objects.create(platform=p, name="苹果id")
        s = SKU.objects.create(business=b, name="美区")
        c = APIClient()
        c.force_authenticate(admin)
        r = c.put(f"/api/manage/sku-editor/{s.id}/",
                  {"name": "美区2", "status": "on_sale", "price_items": "[]", "channel_tag_ids": "[]"}, format="multipart")
        self.assertEqual(r.status_code, 200, getattr(r, "data", r))
        self.assertNotIn("quick_phrases", r.data)
        self.assertNotIn("tutorials", r.data["options"])
        s.refresh_from_db()
        self.assertEqual(s.name, "美区2")
