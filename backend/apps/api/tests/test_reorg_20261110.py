"""一次性整理脚本 reorg_catalog_20261110：试运行不改数据；正式执行按清单挪档位、停用空业务；数据对不上就放弃。"""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from backend.apps.catalog.models import SKU, Business, Platform


class ReorgTests(TestCase):
    def setUp(self):
        P = {23: "Fanbox", 24: "Pixiv", 25: "booth"}
        for pid, n in P.items():
            Platform.objects.create(id=pid, name=n)
        B = [(163, 23, "fanbox代赞助"), (164, 23, "fanbox独享visa卡"), (165, 23, "fanbox账号"), (166, 23, "打包下载"),
             (167, 23, "充值pixivcoban币"), (168, 24, "pixiv高级会员"), (170, 24, "一个月高级会员"), (171, 24, "pixiv画师约稿"),
             (172, 25, "代购booth商品"), (173, 25, "充值pixivcoban币"), (174, 25, "代开visa卡订阅支付booth")]
        for bid, pid, n in B:
            Business.objects.create(id=bid, platform_id=pid, name=n)
        S = [(2403, 163, "一次性卡"), (2412, 163, "共享fanbox号"), (2411, 164, "赞助卡"), (2404, 165, "独享fanbox账号--支持改密码"),
             (2410, 166, "fanbox作品下载"), (2405, 167, "1000日元"), (2406, 167, "2000日元"), (2407, 167, "3000日元"),
             (2408, 167, "5000日元"), (2409, 167, "10000日元"), (2414, 168, "3个月高级会员"), (2417, 170, "1个月会员"),
             (2418, 171, "约稿金额≤10000 日元"), (2421, 172, "代购booth商品(任意金额)"), (2422, 173, "1000日元")]
        for sid, bid, n in S:
            SKU.objects.create(id=sid, business_id=bid, name=n)

    def run_cmd(self, *a):
        out = StringIO()
        call_command("reorg_catalog_20261110", *a, stdout=out)
        return out.getvalue()

    def test_dry_run_changes_nothing(self):
        out = self.run_cmd()
        self.assertIn("试运行", out)
        self.assertEqual(SKU.objects.get(pk=2411).business_id, 164)
        self.assertEqual(Business.objects.get(pk=164).status, "on_sale")

    def test_apply(self):
        self.run_cmd("--apply", "--no-backup")
        self.assertEqual(set(SKU.objects.filter(business_id=163).values_list("id", flat=True)),
                         {2403, 2412, 2411, 2410, 2405, 2406, 2407, 2408, 2409})
        self.assertEqual(SKU.objects.get(pk=2417).business_id, 168)
        for bid in (164, 166, 167, 170):
            self.assertEqual(Business.objects.get(pk=bid).status, "off_sale")
        self.assertEqual(Business.objects.get(pk=171).name, "pixiv画师约稿")  # 没加 --rename 不改名
        self.assertEqual(SKU.objects.get(pk=2422).business_id, 173)  # booth 不动
        # 再跑一次：已经整理过，安全检查拦下来
        with self.assertRaises(CommandError):
            self.run_cmd("--apply", "--no-backup")

    def test_rename(self):
        self.run_cmd("--apply", "--no-backup", "--rename")
        self.assertEqual(Business.objects.get(pk=171).name, "pixiv画师赞助")
        self.assertEqual(Business.objects.get(pk=174).name, "代开visa订阅booth")

    def test_mismatch_aborts(self):
        SKU.objects.create(id=2999, business_id=164, name="清单外的档位")
        with self.assertRaises(CommandError):
            self.run_cmd("--apply", "--no-backup")
        self.assertEqual(SKU.objects.get(pk=2411).business_id, 164)
