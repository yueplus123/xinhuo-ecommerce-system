"""将 JSON 或 CSV 中的平台名称、网址等导入当前库（按平台名称合并首条记录）。"""

import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from backend.apps.catalog.models import Platform


def _is_dumpdata_platform_row(model: str) -> bool:
    m = (model or "").lower()
    return m.endswith("platform") and "business" not in m and "account" not in m


def _load_rows(path: Path) -> list[dict]:
    suf = path.suffix.lower()
    if suf == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            rows = []
            for row in r:
                rows.append(
                    {
                        "name": (row.get("name") or row.get("平台名称") or "").strip(),
                        "url": (row.get("url") or row.get("网址") or "").strip(),
                        "status": (row.get("status") or "").strip() or "on_sale",
                        "note": (row.get("note") or row.get("备注") or "").strip(),
                        "sort_order": int((row.get("sort_order") or row.get("排序") or 0) or 0),
                    }
                )
            return rows
    if suf == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list) and data and isinstance(data[0], dict) and "fields" in data[0]:
            out = []
            for row in data:
                if not _is_dumpdata_platform_row(row.get("model", "")):
                    continue
                f = row["fields"]
                out.append(
                    {
                        "name": (f.get("name") or "").strip(),
                        "url": (f.get("url") or "").strip(),
                        "status": (f.get("status") or "").strip() or "on_sale",
                        "note": (f.get("note") or "").strip(),
                        "sort_order": int(f.get("sort_order") or 0),
                    }
                )
            return out
        if isinstance(data, list):
            out = []
            for p in data:
                if not isinstance(p, dict):
                    continue
                out.append(
                    {
                        "name": (p.get("name") or "").strip(),
                        "url": (p.get("url") or "").strip(),
                        "status": (p.get("status") or "").strip() or "on_sale",
                        "note": (p.get("note") or "").strip(),
                        "sort_order": int(p.get("sort_order") or 0),
                    }
                )
            return out
    raise CommandError(f"不支持的文件类型：{path}（请使用 .json 或 .csv）")


class Command(BaseCommand):
    help = "从 pull_platforms_from_remote 生成的文件或手写 CSV 导入 Platform（按名称更新首条）。"

    def add_arguments(self, parser):
        parser.add_argument("path", help="JSON 或 CSV 路径")
        parser.add_argument("--dry-run", action="store_true", help="只打印将写入的条数，不写库")

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser().resolve()
        if not path.is_file():
            raise CommandError(f"找不到文件：{path}")

        rows = _load_rows(path)
        dry = options["dry_run"]
        n_create = 0
        n_update = 0
        for r in rows:
            name = r["name"]
            if not name:
                continue
            status = r["status"] if r["status"] in dict(Platform.STATUS_CHOICES) else Platform.STATUS_ON_SALE
            qs = Platform.objects.filter(name=name).order_by("id")
            first = qs.first()
            if first:
                if dry:
                    n_update += 1
                    continue
                first.url = r["url"] or first.url
                first.status = status
                first.note = r["note"] if r["note"] else first.note
                first.sort_order = r["sort_order"]
                first.save()
                n_update += 1
            else:
                if dry:
                    n_create += 1
                    continue
                Platform.objects.create(
                    name=name,
                    url=r["url"],
                    status=status,
                    note=r["note"],
                    sort_order=r["sort_order"],
                )
                n_create += 1

        if dry:
            self.stdout.write(self.style.WARNING(f"[dry-run] 将新建 {n_create} 条，更新 {n_update} 条。"))
        else:
            self.stdout.write(self.style.SUCCESS(f"已新建 {n_create} 条，更新 {n_update} 条平台。"))
