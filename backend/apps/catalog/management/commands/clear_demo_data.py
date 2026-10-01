"""
清除「演示 / 假数据」，便于只保留真实业务数据。

针对：
  - `seed_demo_data`：seed_emp_* 用户、Seed平台 * 平台树（级联业务/SKU/快捷语）、
    备注为 seed_demo_data 的收款记录
  - `seed_platform_channel_tags`：名称形如「平台标签 + 两位数字」「渠道标签 + 两位数字」的标签
  - `seed_demo_data` 写入的支付教程：detail_url 含 example.com/tutorial（可用 --keep-example-tutorials 保留）
  - 职员端「平台账号密码」表：链接含 example.com/platform/ 或备注为「批量演示数据」的演示行

用法（在 backend 目录）:
  python manage.py clear_demo_data --dry-run
  python manage.py clear_demo_data
  python manage.py clear_demo_data --keep-example-tutorials
"""

import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from backend.apps.catalog.models import PaymentRecord, PaymentTutorial, Platform, PlatformAccount, Tag

SEED_USER_PREFIX = "seed_emp_"
SEED_PLATFORM_PREFIX = "Seed平台 "
SEED_PAYMENT_NOTE = "seed_demo_data"
# 与历史批量写入的「平台账号密码」演示行一致（非 seed_demo_data 命令写入）
SEED_PLATFORM_ACCOUNT_DEMO_NOTE = "批量演示数据"
SEED_PLATFORM_ACCOUNT_DEMO_URL = "example.com/platform/"

_TAG_PLATFORM_DEMO = re.compile(r"^平台标签\d{2}$")
_TAG_CHANNEL_DEMO = re.compile(r"^渠道标签\d{2}$")


def _demo_tags(tag_type: str, prefix: str, pattern: re.Pattern):
    qs = Tag.objects.filter(type=tag_type, name__startswith=prefix)
    return [t for t in qs if pattern.match(t.name)]


class Command(BaseCommand):
    help = "清除 seed_demo_data / seed_platform_channel_tags 等产生的演示数据。"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="只统计数量，不执行删除")
        parser.add_argument(
            "--keep-example-tutorials",
            action="store_true",
            help="保留支付教程中 detail_url 含 example.com/tutorial 的记录",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        keep_tutorials = options["keep_example_tutorials"]

        User = get_user_model()

        pay_qs = PaymentRecord.objects.filter(
            Q(user__username__startswith=SEED_USER_PREFIX) | Q(note=SEED_PAYMENT_NOTE)
        )
        user_qs = User.objects.filter(username__startswith=SEED_USER_PREFIX)
        plat_qs = Platform.objects.filter(name__startswith=SEED_PLATFORM_PREFIX)

        demo_tags = _demo_tags(Tag.TYPE_PLATFORM, "平台标签", _TAG_PLATFORM_DEMO) + _demo_tags(
            Tag.TYPE_CHANNEL, "渠道标签", _TAG_CHANNEL_DEMO
        )

        tut_qs = PaymentTutorial.objects.none()
        if not keep_tutorials:
            tut_qs = PaymentTutorial.objects.filter(detail_url__icontains="example.com/tutorial")

        pa_qs = PlatformAccount.objects.filter(
            Q(url__icontains=SEED_PLATFORM_ACCOUNT_DEMO_URL) | Q(note=SEED_PLATFORM_ACCOUNT_DEMO_NOTE)
        )

        n_pay = pay_qs.count()
        n_user = user_qs.count()
        n_plat = plat_qs.count()
        n_tag = len(demo_tags)
        n_tut = tut_qs.count()
        n_pa = pa_qs.count()

        self.stdout.write(
            "将处理：收款记录 {} 条，演示用户 {} 个，演示平台 {} 个，"
            "演示标签 {} 个，支付教程 {} 条（{}），平台账号密码演示行 {} 条。".format(
                n_pay,
                n_user,
                n_plat,
                n_tag,
                n_tut,
                "保留 example 教程" if keep_tutorials else "含 example.com/tutorial",
                n_pa,
            )
        )

        if dry:
            self.stdout.write(self.style.WARNING("已指定 --dry-run，未修改数据库。"))
            return

        with transaction.atomic():
            d_pay, _ = pay_qs.delete()
            d_user, _ = user_qs.delete()
            d_plat, _ = plat_qs.delete()
            for t in demo_tags:
                t.delete()
            d_tag = len(demo_tags)
            if keep_tutorials:
                d_tut = 0
            else:
                d_tut, _ = tut_qs.delete()
            d_pa, _ = pa_qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"已删除：收款相关 {d_pay} 行，用户 {d_user} 行，平台级联 {d_plat} 行，"
                f"标签 {d_tag} 个，支付教程 {d_tut} 行，平台账号密码 {d_pa} 行。"
            )
        )
        self.stdout.write("提示：管理员账号、自建平台/大厅板块等未匹配上述规则的，不会被删除。")
