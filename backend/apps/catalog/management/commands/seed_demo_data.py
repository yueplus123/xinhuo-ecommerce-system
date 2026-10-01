"""
开发/演示用：批量写入平台-业务-SKU 树，以及员工收款记录（本月每日 + 上月部分）。

用法（在 backend 目录下）:
  python manage.py seed_demo_data
  python manage.py seed_demo_data --purge   # 先删除本命令写入过的数据再重建
  python manage.py clear_demo_data           # 只清演示数据、不重建（录入真数据前用）
  python manage.py clear_demo_data --dry-run

默认会创建:
  - 5 个职员账号 seed_emp_01 … seed_emp_05（密码见 --password 或环境变量 SEED_DEMO_PASSWORD）
  - 20 个平台「Seed平台 01」…，每平台 8 业务，每业务 15 SKU
  - 每个员工：本月从 1 号到今天每天若干条 PaymentRecord；上月整月每天 1～2 条
"""

import os
import random
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from backend.apps.catalog.models import (
    PAYMENT_CHANNELS,
    Business,
    PaymentRecord,
    PaymentTutorial,
    Platform,
    PlatformAccount,
    QuickPhrase,
    SKU,
    Tag,
)

SEED_USER_PREFIX = "seed_emp_"
SEED_PLATFORM_PREFIX = "Seed平台 "
SEED_PAYMENT_NOTE = "seed_demo_data"
SEED_PLATFORM_ACCOUNT_DEMO_NOTE = "批量演示数据"
SEED_PLATFORM_ACCOUNT_DEMO_URL = "example.com/platform/"


class Command(BaseCommand):
    help = "写入演示员工、平台/业务/SKU 树、以及本月/上月收款记录。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge",
            action="store_true",
            help="删除此前由本命令创建的用户、平台（级联业务/SKU）及收款记录后重新生成。",
        )
        parser.add_argument(
            "--password",
            default=None,
            help="演示员工密码；默认读环境变量 SEED_DEMO_PASSWORD，否则 Seed@demo1",
        )
        parser.add_argument("--seed", type=int, default=42, help="随机种子，默认 42。")

    def handle(self, *args, **options):
        random.seed(options["seed"])
        pwd = options["password"] or os.environ.get("SEED_DEMO_PASSWORD") or "Seed@demo1"

        if options["purge"]:
            self._purge()

        with transaction.atomic():
            users = self._ensure_users(5, pwd)
            if Platform.objects.filter(name__startswith=SEED_PLATFORM_PREFIX).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"已存在名称以「{SEED_PLATFORM_PREFIX}」开头的平台，本次跳过平台/业务/SKU基础结构创建，改为补充渠道/教程/快捷语。"
                    )
                )
                n_plat = Platform.objects.filter(name__startswith=SEED_PLATFORM_PREFIX).count()
                n_biz = Business.objects.filter(platform__name__startswith=SEED_PLATFORM_PREFIX).count()
                n_sku = SKU.objects.filter(business__platform__name__startswith=SEED_PLATFORM_PREFIX).count()
            else:
                n_plat, n_biz, n_sku = self._seed_catalog(20, 8, 15)
            n_channel_tags, n_tutorials, n_quick_phrases = self._seed_sku_extras()
            n_pay = self._seed_payments(users)

        self.stdout.write(
            self.style.SUCCESS(
                f"完成：用户 {len(users)}，平台 {n_plat}，业务 {n_biz}，SKU {n_sku}，"
                f"渠道标签 {n_channel_tags}，支付教程 {n_tutorials}，快捷语 {n_quick_phrases}，收款记录 {n_pay}。"
            )
        )

    def _purge(self):
        User = get_user_model()
        qs_users = User.objects.filter(username__startswith=SEED_USER_PREFIX)
        deleted_pay, _ = PaymentRecord.objects.filter(
            Q(user__username__startswith=SEED_USER_PREFIX) | Q(note=SEED_PAYMENT_NOTE)
        ).delete()
        deleted_users, _ = qs_users.delete()
        deleted_plat, _ = Platform.objects.filter(name__startswith=SEED_PLATFORM_PREFIX).delete()
        deleted_pa, _ = PlatformAccount.objects.filter(
            Q(url__icontains=SEED_PLATFORM_ACCOUNT_DEMO_URL) | Q(note=SEED_PLATFORM_ACCOUNT_DEMO_NOTE)
        ).delete()
        self.stdout.write(
            self.style.WARNING(
                f"已清理：收款记录 {deleted_pay} 条，用户 {deleted_users} 个，平台 {deleted_plat} 个（级联业务/SKU），"
                f"平台账号密码演示行 {deleted_pa} 条。"
            )
        )

    def _ensure_users(self, count: int, password: str):
        User = get_user_model()
        users = []
        for i in range(1, count + 1):
            username = f"{SEED_USER_PREFIX}{i:02d}"
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.invalid",
                    "is_staff": True,
                    "is_active": True,
                    "is_superuser": False,
                },
            )
            if created or not u.has_usable_password():
                u.set_password(password)
                u.is_staff = True
                u.is_active = True
                u.save()
            users.append(u)
            self.stdout.write(f"  用户 {'新建' if created else '已存在'}：{username}")
        return users

    def _seed_catalog(self, n_platforms: int, businesses_each: int, skus_each: int):
        platforms = []
        for i in range(1, n_platforms + 1):
            platforms.append(
                Platform(
                    name=f"{SEED_PLATFORM_PREFIX}{i:02d}",
                    url=f"https://example.com/seed-platform/{i:02d}",
                    status=Platform.STATUS_ON_SALE,
                    note="seed_demo_data",
                    sort_order=i - 1,
                )
            )
        Platform.objects.bulk_create(platforms)
        platforms = list(Platform.objects.filter(name__startswith=SEED_PLATFORM_PREFIX).order_by("id"))

        businesses = []
        for p in platforms:
            for b in range(1, businesses_each + 1):
                businesses.append(
                    Business(
                        platform_id=p.id,
                        name=f"业务{p.name[-2:]}-{b:02d}",
                        status=Platform.STATUS_ON_SALE,
                    )
                )
        Business.objects.bulk_create(businesses)
        pid_list = [p.id for p in platforms]
        businesses = list(Business.objects.filter(platform_id__in=pid_list).order_by("platform_id", "id"))

        skus = []
        for biz in businesses:
            p_short = biz.platform.name[-2:]
            for s in range(1, skus_each + 1):
                skus.append(
                    SKU(
                        business_id=biz.id,
                        name=f"SKU-{p_short}-{biz.name.split('-')[-1]}-{s:02d}",
                        status=Platform.STATUS_ON_SALE,
                        price=Decimal(str(round(random.uniform(9.9, 999.99), 2))),
                        note="seed",
                    )
                )
        for i in range(0, len(skus), 400):
            SKU.objects.bulk_create(skus[i : i + 400])

        n_sku = SKU.objects.filter(business_id__in=[b.id for b in businesses]).count()
        return len(platforms), len(businesses), n_sku

    def _pick_channel(self):
        codes = [c[0] for c in PAYMENT_CHANNELS]
        weights = [3 if c != "退款项" else 1 for c in codes]
        return random.choices(codes, weights=weights, k=1)[0]

    def _seed_sku_extras(self):
        channel_names = [
            "站内",
            "淘宝",
            "闲鱼",
            "Discord",
            "Telegram",
            "工单",
            "企业微信",
            "其他渠道",
        ]
        channel_tags = []
        for idx, name in enumerate(channel_names, start=1):
            tag, _ = Tag.objects.get_or_create(
                type=Tag.TYPE_CHANNEL,
                name=name,
                defaults={"order": idx * 10},
            )
            channel_tags.append(tag)

        tutorials = [
            ("Pixiv购买流程", "https://example.com/tutorial/pixiv"),
            ("Fanbox开通指南", "https://example.com/tutorial/fanbox"),
            ("Patreon支付排错", "https://example.com/tutorial/patreon"),
            ("Onlyfans订阅说明", "https://example.com/tutorial/onlyfans"),
            ("Discord发货规范", "https://example.com/tutorial/discord"),
            ("售后与退款处理", "https://example.com/tutorial/refund"),
            ("订阅周期说明", "https://example.com/tutorial/renew"),
            ("订单补发处理", "https://example.com/tutorial/resend"),
            ("账号异常排查", "https://example.com/tutorial/account-check"),
            ("渠道切换说明", "https://example.com/tutorial/channel-switch"),
            ("跨区支付说明", "https://example.com/tutorial/cross-region"),
            ("开票与对账流程", "https://example.com/tutorial/invoice"),
        ]
        tutorial_count = 0
        for i, (name, url) in enumerate(tutorials):
            _, created = PaymentTutorial.objects.get_or_create(
                name=name,
                defaults={"detail_url": url, "sort_order": i},
            )
            if created:
                tutorial_count += 1

        sku_qs = SKU.objects.filter(business__platform__name__startswith=SEED_PLATFORM_PREFIX).order_by("id")
        phrase_templates = [
            "您好，订单已收到，正在处理。",
            "支付成功后请截图回传，方便核验。",
            "教程已发您，请按步骤操作。",
            "如需售后支持，请在24小时内联系。",
            "本SKU发货完成后可在记录页查看。",
            "请确认邮箱与账号信息一致，避免延迟。",
            "当前高峰期预计15-30分钟处理完成。",
            "若支付失败，请优先更换浏览器重试。",
            "如出现风控提示，请截图给客服。",
            "请勿重复下单，避免重复扣费。",
            "订单已进入复核流程，请稍候。",
            "发货完成后会自动推送通知。",
            "如需改绑账号，请先提交工单。",
            "退款申请已登记，按规则审核。",
            "教程第三步需要开启代理后操作。",
            "已为您预留库存，请尽快完成付款。",
            "若链接失效，请联系人工补发。",
        ]
        phrase_count = 0
        for sku in sku_qs:
            tutorial_pick = random.sample(tutorials, k=5)
            tutorial_names = [t[0] for t in tutorial_pick]
            sku.tutorial_text = " / ".join(tutorial_names)
            if not sku.note:
                sku.note = "seed"
            sku.save(update_fields=["tutorial_text", "note"])

            if channel_tags:
                pick_num = random.randint(1, min(2, len(channel_tags)))
                sku.channel_tags.set(random.sample(channel_tags, pick_num))

            sku.quick_phrases.all().delete()
            for i, content in enumerate(random.sample(phrase_templates, k=8), start=1):
                QuickPhrase.objects.create(sku=sku, order=i * 10, content=content)
                phrase_count += 1

        return len(channel_tags), tutorial_count, phrase_count

    def _seed_payments(self, users):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        prev_last = month_start - timedelta(days=1)
        prev_start = prev_last.replace(day=1)
        _, dim = monthrange(prev_start.year, prev_start.month)

        n = 0
        channels_positive = [c[0] for c in PAYMENT_CHANNELS if c[0] != "退款项"]

        def add_records(user, d: date, lo: int, hi: int):
            nonlocal n
            k = random.randint(lo, hi)
            for _ in range(k):
                ch = self._pick_channel()
                sign = -1 if ch == "退款项" else 1
                base = random.uniform(50, 2000)
                amt = Decimal(str(round(sign * base, 2)))
                oc = random.randint(0, 20) if ch != "退款项" else random.randint(0, 5)
                pr = PaymentRecord.objects.create(
                    user=user,
                    channel=ch,
                    order_count=oc,
                    amount=amt,
                    note=SEED_PAYMENT_NOTE,
                )
                PaymentRecord.objects.filter(pk=pr.pk).update(record_date=d)
                n += 1

        for user in users:
            d = month_start
            while d <= today:
                add_records(user, d, 1, 3)
                d += timedelta(days=1)

            for day in range(1, dim + 1):
                d = date(prev_start.year, prev_start.month, day)
                add_records(user, d, 1, 2)

            for _ in range(8):
                ch = random.choice(channels_positive)
                extra_day = prev_start + timedelta(days=random.randint(0, dim - 1))
                pr = PaymentRecord.objects.create(
                    user=user,
                    channel=ch,
                    order_count=random.randint(1, 15),
                    amount=Decimal(str(round(random.uniform(30, 800), 2))),
                    note=SEED_PAYMENT_NOTE,
                )
                PaymentRecord.objects.filter(pk=pr.pk).update(record_date=extra_day)
                n += 1

        return n
