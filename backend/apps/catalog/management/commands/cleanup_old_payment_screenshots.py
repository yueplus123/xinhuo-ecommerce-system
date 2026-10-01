"""清理超过保留天数的订单截图文件（不删除订单记录）。"""

from datetime import timedelta

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from backend.apps.catalog.models import PaymentRecord, PaymentRecordImage


def _is_path_still_referenced(path: str, *, exclude_record_id=None, exclude_image_id=None) -> bool:
    if not path:
        return False
    q_rec = PaymentRecord.objects.filter(screenshot=path)
    if exclude_record_id is not None:
        q_rec = q_rec.exclude(pk=exclude_record_id)
    if q_rec.exists():
        return True

    q_img = PaymentRecordImage.objects.filter(image=path)
    if exclude_image_id is not None:
        q_img = q_img.exclude(pk=exclude_image_id)
    return q_img.exists()


class Command(BaseCommand):
    help = "清理超过 N 天的订单截图（主截图置空、附图行删除），订单记录保留不删。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="截图保留天数，默认 90 天。",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="演练模式：只输出将处理数量，不改数据库和文件。",
        )

    def handle(self, *args, **options):
        days = max(1, int(options["days"] or 90))
        dry_run = bool(options["dry_run"])
        cutoff = timezone.localdate() - timedelta(days=days)

        old_records = PaymentRecord.objects.filter(
            record_date__lt=cutoff
        ).exclude(Q(screenshot="") | Q(screenshot__isnull=True))
        old_images = PaymentRecordImage.objects.filter(payment_record__record_date__lt=cutoff).exclude(
            Q(image="") | Q(image__isnull=True)
        )

        n_record_rows = 0
        n_image_rows = 0
        n_files_deleted = 0
        n_files_missing = 0

        for rec in old_records.iterator():
            path = (rec.screenshot.name or "").strip()
            if not path:
                continue
            n_record_rows += 1
            should_delete_file = not _is_path_still_referenced(path, exclude_record_id=rec.pk)
            if not dry_run:
                rec.screenshot = ""
                rec.save(update_fields=["screenshot"])
                if should_delete_file:
                    if default_storage.exists(path):
                        default_storage.delete(path)
                        n_files_deleted += 1
                    else:
                        n_files_missing += 1

        for img in old_images.iterator():
            path = (img.image.name or "").strip()
            if not path:
                continue
            n_image_rows += 1
            should_delete_file = not _is_path_still_referenced(path, exclude_image_id=img.pk)
            if not dry_run:
                img.delete()
                if should_delete_file:
                    if default_storage.exists(path):
                        default_storage.delete(path)
                        n_files_deleted += 1
                    else:
                        n_files_missing += 1

        mode = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}已处理主截图字段 {n_record_rows} 条、附图行 {n_image_rows} 条；"
                f"删除文件 {n_files_deleted} 个，文件不存在 {n_files_missing} 个。"
            )
        )
        self.stdout.write(self.style.WARNING(f"清理阈值：record_date < {cutoff}（保留最近 {days} 天）。"))
