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


class SkuWarrantyTests(TestCase):
    """质保条件：管理后台商品编辑里填写，商品库接口返回给职员端显示（所有人一样）。"""

    def setUp(self):
        U = get_user_model()
        self.admin = U.objects.create_user("su2", password="x", is_staff=True, is_superuser=True)
        self.staff = U.objects.create_user("st2", password="x", is_staff=True)
        p = Platform.objects.create(name="chatgpt")
        b = Business.objects.create(platform=p, name="GPT号")
        self.sku = SKU.objects.create(business=b, name="普通号")

    def test_edit_and_show(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.get(f"/api/manage/sku-editor/{self.sku.id}/")
        self.assertIn("7 天", r.data["options"]["warranty_presets"])
        r = c.put(f"/api/manage/sku-editor/{self.sku.id}/",
                  {"name": "普通号", "status": "on_sale", "price_items": "[]", "channel_tag_ids": "[]",
                   "warranty": " 7 天 ", "warranty_note": "登录不上包换一次\n自己改密码后不保"}, format="multipart")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["warranty"], "7 天")
        # 保存时没带质保字段：原来的质保不动
        r = c.put(f"/api/manage/sku-editor/{self.sku.id}/",
                  {"name": "普通号2", "status": "on_sale", "price_items": "[]", "channel_tag_ids": "[]"}, format="multipart")
        self.sku.refresh_from_db()
        self.assertEqual((self.sku.warranty, self.sku.warranty_note), ("7 天", "登录不上包换一次\n自己改密码后不保"))
        # 职员端商品库：返回质保
        s = APIClient()
        s.force_authenticate(self.staff)
        lib = s.get("/api/catalog/library/").data
        sku = lib["platforms"][0]["businesses"][0]["skus"][0]
        self.assertEqual((sku["warranty"], sku["warranty_note"]), ("7 天", "登录不上包换一次\n自己改密码后不保"))
        # 复制商品：质保一起复制
        r = c.post(f"/api/admin/catalog/skus/{self.sku.id}/duplicate/")
        self.assertEqual(SKU.objects.get(pk=r.data["id"]).warranty, "7 天")

    def test_staff_cannot_edit(self):
        c = APIClient()
        c.force_authenticate(self.staff)
        r = c.put(f"/api/manage/sku-editor/{self.sku.id}/", {"name": "x", "warranty": "30 天"}, format="multipart")
        self.assertIn(r.status_code, (401, 403))
        self.sku.refresh_from_db()
        self.assertEqual(self.sku.warranty, "")
