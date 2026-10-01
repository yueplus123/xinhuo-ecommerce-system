"""把 catalog_sku.price 同步到 catalog_skupriceitem（迁移遗漏或历史数据补全）。

用法（backend 目录或设置 PYTHONPATH 后）:
  python manage.py backfill_sku_price_items --dry-run
  python manage.py backfill_sku_price_items
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q

from django.core.management.base import BaseCommand

from backend.apps.catalog.models import SKU, SKUPriceItem


class Command(BaseCommand):
    help = "为 price 有值但无 price_items 的 SKU 补建价格档；并输出全库价格数据统计。"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="仅统计，不写库")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        stats = self._print_stats("补全前")

        qs = (
            SKU.objects.filter(price__isnull=False)
            .annotate(item_count=Count("price_items"))
            .filter(item_count=0)
            .order_by("id")
        )
        to_fix = list(qs)
        self.stdout.write(f"\n待补全 price_items 的 SKU 数: {len(to_fix)}")
        for sku in to_fix[:10]:
            self.stdout.write(f"  id={sku.pk} price={sku.price} name={sku.name[:40]}")
        if len(to_fix) > 10:
            self.stdout.write(f"  ... 另有 {len(to_fix) - 10} 条")

        if dry:
            self.stdout.write(self.style.WARNING("\n[dry-run] 未写入数据库。"))
            return

        created = 0
        with transaction.atomic():
            for sku in to_fix:
                SKUPriceItem.objects.create(
                    sku=sku,
                    label="",
                    rmb_amount=sku.price,
                    notice="",
                    sort_order=10,
                )
                if not sku.price_type:
                    sku.price_type = SKU.PRICE_TYPE_CNY_SINGLE
                    sku.save(update_fields=["price_type"])
                created += 1

        self.stdout.write(self.style.SUCCESS(f"\n已补全 {created} 条 SKU 的 price_items。"))
        self._print_stats("补全后")

    def _print_stats(self, label: str) -> dict:
        total = SKU.objects.count()
        with_price_col = SKU.objects.filter(price__isnull=False).count()
        with_type = SKU.objects.exclude(price_type="").count()
        with_items = SKU.objects.annotate(c=Count("price_items")).filter(c__gt=0).count()
        no_price = SKU.objects.filter(
            Q(price__isnull=True) | Q(price=Decimal("0")),
        ).annotate(c=Count("price_items")).filter(c=0, price_type="").count()
        # 真正无任何价格信息
        empty = (
            SKU.objects.filter(price__isnull=True, price_type="")
            .annotate(c=Count("price_items"))
            .filter(c=0)
            .count()
        )
        item_rows = SKUPriceItem.objects.count()

        self.stdout.write(f"\n========== {label} ==========")
        self.stdout.write(f"SKU 总数:              {total}")
        self.stdout.write(f"price 字段有值:        {with_price_col}")
        self.stdout.write(f"price_type 已设置:     {with_type}")
        self.stdout.write(f"有 price_items 的 SKU: {with_items}")
        self.stdout.write(f"price_items 行数:      {item_rows}")
        self.stdout.write(f"完全无价格信息 SKU:    {empty}")

        return {
            "total": total,
            "with_price_col": with_price_col,
            "with_items": with_items,
            "empty": empty,
        }
