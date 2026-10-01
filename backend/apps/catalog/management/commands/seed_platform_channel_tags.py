import random

from django.core.management.base import BaseCommand
from django.db import transaction

from backend.apps.catalog.models import Platform, SKU, Tag


class Command(BaseCommand):
    help = "生成平台标签和渠道标签，并分配到 Platform/SKU。"

    def add_arguments(self, parser):
        parser.add_argument("--platform-count", type=int, default=20, help="平台标签数量，默认 20")
        parser.add_argument("--channel-count", type=int, default=25, help="渠道标签数量，默认 25")
        parser.add_argument("--seed", type=int, default=20260417, help="随机种子，默认 20260417")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(options["seed"])
        platform_count = max(1, int(options["platform_count"]))
        channel_count = max(1, int(options["channel_count"]))

        platform_tags = self._ensure_tags(Tag.TYPE_PLATFORM, "平台标签", platform_count)
        channel_tags = self._ensure_tags(Tag.TYPE_CHANNEL, "渠道标签", channel_count)

        platform_assigned = self._assign_platform_tags(platform_tags)
        sku_assigned = self._assign_sku_tags(channel_tags)

        self.stdout.write(
            self.style.SUCCESS(
                f"完成：平台标签 {len(platform_tags)} 个，渠道标签 {len(channel_tags)} 个；"
                f"已分配平台 {platform_assigned} 个，已分配 SKU {sku_assigned} 个。"
            )
        )

    def _ensure_tags(self, tag_type: str, prefix: str, count: int):
        tags = []
        for i in range(1, count + 1):
            name = f"{prefix}{i:02d}"
            tag, _ = Tag.objects.get_or_create(
                type=tag_type,
                name=name,
                defaults={"order": i * 10},
            )
            tags.append(tag)
        return tags

    def _assign_platform_tags(self, tags):
        if not tags:
            return 0
        platforms = list(Platform.objects.order_by("id"))
        for idx, platform in enumerate(platforms):
            # 每个平台绑定 2~4 个标签，并保证有一个按序轮转的主标签
            base_tag = tags[idx % len(tags)]
            pick_size = random.randint(2, min(4, len(tags)))
            picked = random.sample(tags, k=pick_size)
            if base_tag not in picked:
                picked[0] = base_tag
            platform.platform_tags.set(picked)
        return len(platforms)

    def _assign_sku_tags(self, tags):
        if not tags:
            return 0
        skus = list(SKU.objects.order_by("id"))
        for idx, sku in enumerate(skus):
            # 每个 SKU 绑定 1~3 个渠道标签，并按序保证覆盖全部渠道标签
            base_tag = tags[idx % len(tags)]
            pick_size = random.randint(1, min(3, len(tags)))
            picked = random.sample(tags, k=pick_size)
            if base_tag not in picked:
                picked[0] = base_tag
            sku.channel_tags.set(picked)
        return len(skus)
