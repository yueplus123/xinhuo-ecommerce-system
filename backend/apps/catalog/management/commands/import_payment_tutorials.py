"""从 dumpdata 的 JSON 合并「支付教程」到当前库（按 名称+详情链接 唯一合并）。"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from backend.apps.catalog.models import PaymentTutorial


def _is_payment_tutorial_row(model: str) -> bool:
    m = (model or "").lower()
    return m.endswith("paymenttutorial")


class Command(BaseCommand):
    help = (
        "读取 dumpdata 导出的 JSON（含 catalog.paymenttutorial 或旧站 business.paymenttutorial 等），"
        "按 name + detail_url 做 update_or_create。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="",
            help="JSON 路径；留空则使用 apps/catalog/fixtures/payment_tutorials.json",
        )

    def handle(self, *args, **options):
        raw = (options["path"] or "").strip()
        if raw:
            path = Path(raw).expanduser().resolve()
        else:
            catalog = Path(__file__).resolve().parent.parent.parent
            path = catalog / "fixtures" / "payment_tutorials.json"
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"找不到文件：{path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        n = 0
        for row in data:
            if not _is_payment_tutorial_row(row.get("model", "")):
                continue
            f = row["fields"]
            name = (f.get("name") or "").strip()
            detail_url = (f.get("detail_url") or "").strip()
            if not name or not detail_url:
                self.stderr.write(
                    self.style.WARNING(f"跳过一条缺少 name 或 detail_url 的记录：pk={row.get('pk')}")
                )
                continue

            defaults = {
                "sort_order": int(f.get("sort_order") or 0),
            }
            PaymentTutorial.objects.update_or_create(
                name=name,
                detail_url=detail_url,
                defaults=defaults,
            )
            n += 1

        self.stdout.write(self.style.SUCCESS(f"已合并支付教程 {n} 条。"))
