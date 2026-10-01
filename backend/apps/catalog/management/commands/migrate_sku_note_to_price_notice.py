"""将 SKU 旧字段 note（备注）复制到 price_notice（价格整组注意事项）。

仅当 price_notice 为空且 note 有内容时写入，不删除原 note。

用法:
  python manage.py migrate_sku_note_to_price_notice --dry-run
  python manage.py migrate_sku_note_to_price_notice
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from backend.apps.catalog.models import SKU


class Command(BaseCommand):
    help = "把 catalog_sku.note 复制到 price_notice，供职员端价格弹层显示。"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        candidates = []
        for sku in SKU.objects.all().only("id", "name", "note", "price_notice").order_by("id"):
            note = (sku.note or "").strip()
            if not note:
                continue
            if (sku.price_notice or "").strip():
                continue
            candidates.append(sku)

        self.stdout.write(f"note 有内容且 price_notice 为空的 SKU: {len(candidates)}")
        for sku in candidates[:15]:
            preview = (sku.note or "").strip().replace("\n", " ")
            if len(preview) > 60:
                preview = preview[:60] + "…"
            self.stdout.write(f"  id={sku.pk} {sku.name[:30]!r} → {preview}")
        if len(candidates) > 15:
            self.stdout.write(f"  ... 另有 {len(candidates) - 15} 条")

        if dry:
            self.stdout.write(self.style.WARNING("\n[dry-run] 未写入。"))
            return

        updated = 0
        with transaction.atomic():
            for sku in candidates:
                SKU.objects.filter(pk=sku.pk).update(price_notice=(sku.note or "").strip())
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"\n已复制 {updated} 条 note → price_notice。"))
