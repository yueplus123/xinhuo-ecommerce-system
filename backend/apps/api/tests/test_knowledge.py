"""教程+话术（知识库）：接口权限 / 校验，以及从商品导入的命令。"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from backend.apps.catalog.models import SKU, Business, KnowledgeEntry, PhrasePool, Platform, QuickPhrase, TutorialPool
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


class SeedKnowledgeTests(TestCase):
    def setUp(self):
        p = Platform.objects.create(name="apple")
        b1 = Business.objects.create(platform=p, name="苹果id")
        b2 = Business.objects.create(platform=p, name="共享苹果id")
        s1 = SKU.objects.create(business=b1, name="美区", tutorial_text="苹果登录教程 / 改密码教程")
        s2 = SKU.objects.create(business=b1, name="日区", tutorial_text="苹果登录教程")
        s3 = SKU.objects.create(business=b2, name="共享", tutorial_text="没有链接的教程")
        text = "1️⃣尽量不要换ip登录 2️⃣尽快登录核对 苹果登录教程 🔗https://a.example/login?x=1 改密码教程 🔗 https://a.example/pw"
        for s in (s1, s2, s3):
            QuickPhrase.objects.create(sku=s, content=text)
        QuickPhrase.objects.create(sku=s1, content="美区专属提醒，设置页 https://appleid.apple.com/ 可以改")
        QuickPhrase.objects.create(sku=s2, content="日区提醒 新教程 🔗https://b.example.feishu.cn/docx/abc")
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

    def test_apply_splits_dedupes_and_is_idempotent(self):
        self.run_cmd("--apply")
        tu = KnowledgeEntry.objects.filter(kind="tutorial")
        self.assertEqual(set(tu.filter(platform__name="apple").values_list("title", flat=True)),
                         {"苹果登录教程", "改密码教程", "新教程"})
        self.assertEqual(tu.get(title="没人用的教程").platform, None)  # 没被用到的放「通用」
        ph = KnowledgeEntry.objects.filter(kind="phrase")
        self.assertEqual(ph.count(), 3)  # 三个档位相同的话术只放一条
        shared = ph.get(title__startswith="账号交付注意")
        self.assertIn("苹果id、共享苹果id", shared.title)
        self.assertEqual(shared.content, "1️⃣尽量不要换ip登录\n2️⃣尽快登录核对")  # 教程链接拆出去了，分点换行
        self.assertEqual(sorted(KnowledgeEntry.objects.get(pk=i).title for i in shared.tutorials), ["改密码教程", "苹果登录教程"])
        other = ph.get(content__startswith="美区专属")
        self.assertIn("https://appleid.apple.com/", other.content)  # 普通链接留在话术里
        self.assertEqual(other.tutorials, [])
        self.assertEqual(SKU.objects.get(name="美区").quick_phrases.count(), 2)  # 原数据不动
        n = KnowledgeEntry.objects.count()
        self.run_cmd("--apply")
        self.assertEqual(KnowledgeEntry.objects.count(), n)  # 再跑一次不会重复


class SeedKnowledgeNamingTests(TestCase):
    """教程名用教程池里的；同一平台同名不同链接的教程只放一条。"""

    def test_pool_name_and_same_name_dedupe(self):
        p = Platform.objects.create(name="chatgpt")
        b = Business.objects.create(platform=p, name="开visa卡付GPT")
        s = SKU.objects.create(business=b, name="独享卡", tutorial_text="独享卡支付教程")
        TutorialPool.objects.create(name="独享卡支付教程", detail_url="https://x.feishu.cn/docx/AAA")
        TutorialPool.objects.create(name="下载教程", detail_url="https://x.feishu.cn/docx/DL")
        QuickPhrase.objects.create(sku=s, content="1️⃣请按教程操作 独享卡支付教程 🔗https://x.feishu.cn/docx/BBB")
        QuickPhrase.objects.create(sku=s, content="商品已经发到您的邮箱 请查收下载教程 https://x.feishu.cn/docx/DL")
        call_command("seed_knowledge_base", "--apply", stdout=StringIO())
        tu = KnowledgeEntry.objects.filter(kind="tutorial", platform=p)
        self.assertEqual(sorted(tu.values_list("title", flat=True)), ["下载教程", "独享卡支付教程"])
        self.assertEqual(tu.get(title="独享卡支付教程").url, "https://x.feishu.cn/docx/AAA")  # 用档位引用的那个链接
        ph = KnowledgeEntry.objects.get(kind="phrase", content__startswith="1️⃣")
        self.assertEqual(ph.tutorials, [tu.get(title="独享卡支付教程").id])


class SeedPhrasePoolTests(TestCase):
    def test_phrase_pool_goes_to_matching_platform(self):
        tg = Platform.objects.create(name="telegram")
        g = Platform.objects.create(name="google")
        b = Business.objects.create(platform=tg, name="telegram账号")
        sku = SKU.objects.create(business=b, name="成品号", tutorial_text="改中文教程")
        TutorialPool.objects.create(name="改中文教程", detail_url="https://x.feishu.cn/docx/ZH")
        QuickPhrase.objects.create(sku=sku, content="1️⃣尽快改密码 改中文教程 🔗https://x.feishu.cn/docx/ZH")
        PhrasePool.objects.create(name="telegram账号", content="1️⃣尽快改密码 改中文教程 🔗https://x.feishu.cn/docx/ZH")  # 和已有的一样
        PhrasePool.objects.create(name="telegram新号提醒", content="新号先养几天 改中文教程 🔗https://x.feishu.cn/docx/ZH")
        PhrasePool.objects.create(name="谷歌邮箱换绑", content="请换绑成自己的邮箱")
        PhrasePool.objects.create(name="欢迎语", content="您好，在的～")
        PhrasePool.objects.create(name="欢迎语2", content="您好，在的～")  # 内容相同只放一条
        call_command("seed_knowledge_base", "--apply", stdout=StringIO())
        ph = KnowledgeEntry.objects.filter(kind="phrase")
        self.assertEqual(ph.filter(platform=tg).count(), 2)  # SKU 话术 1 条 + 话术池新的 1 条（重复的跳过）
        new = ph.get(title="telegram新号提醒")
        self.assertEqual(new.platform, tg)
        tut = KnowledgeEntry.objects.filter(kind="tutorial", title="改中文教程")
        self.assertEqual(tut.count(), 1)  # 不会在「通用」里再建一篇
        self.assertEqual(new.tutorials, [tut.get().id])
        self.assertEqual(ph.get(title="谷歌邮箱换绑").platform, g)
        self.assertEqual(list(ph.filter(platform=None).values_list("title", flat=True)), ["欢迎语"])
        n = KnowledgeEntry.objects.count()
        call_command("seed_knowledge_base", "--apply", stdout=StringIO())
        self.assertEqual(KnowledgeEntry.objects.count(), n)


class SkuSaveKeepsOldPhrasesTests(TestCase):
    """管理后台 SKU 编辑页不再提交话术 / 教程：保存时原来的数据不能被清空。"""

    def test_save_without_phrase_fields_keeps_them(self):
        U = get_user_model()
        admin = U.objects.create_user("su", password="x", is_staff=True, is_superuser=True)
        p = Platform.objects.create(name="apple")
        b = Business.objects.create(platform=p, name="苹果id")
        s = SKU.objects.create(business=b, name="美区", tutorial_text="登录教程")
        QuickPhrase.objects.create(sku=s, content="旧话术")
        c = APIClient()
        c.force_authenticate(admin)
        r = c.put(f"/api/manage/sku-editor/{s.id}/",
                  {"name": "美区2", "status": "on_sale", "price_items": "[]", "channel_tag_ids": "[]"}, format="multipart")
        self.assertEqual(r.status_code, 200, getattr(r, "data", r))
        s.refresh_from_db()
        self.assertEqual(s.name, "美区2")
        self.assertEqual(s.tutorial_text, "登录教程")
        self.assertEqual(list(s.quick_phrases.values_list("content", flat=True)), ["旧话术"])
