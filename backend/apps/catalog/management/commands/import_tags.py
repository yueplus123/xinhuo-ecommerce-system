"""从 dumpdata 的 JSON 合并「平台标签 / 渠道标签」（按 type + name，与模型 unique_together 一致）。"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from backend.apps.catalog.models import Tag


def _is_tag_row(model: str) -> bool:
    m = (model or "").lower()
    return m == "catalog.tag" or m.endswith(".tag")


class Command(BaseCommand):
    help = (
        "读取 dumpdata 导出的 Tag（catalog.tag 或 business.tag 等），"
        "按 type + name 做 update_or_create，更新 order；不按线上 pk 新建，以免打乱本机 M2M。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="",
            help="JSON 路径；留空则使用 apps/catalog/fixtures/tags.json",
        )

    def handle(self, *args, **options):
        raw = (options["path"] or "").strip()
        if raw:
            path = Path(raw).expanduser().resolve()
        else:
            catalog = Path(__file__).resolve().parent.parent.parent
            path = catalog / "fixtures" / "tags.json"
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"找不到文件：{path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        valid_types = {Tag.TYPE_PLATFORM, Tag.TYPE_CHANNEL}
        n = 0
        skipped = 0
        for row in data:
            if not _is_tag_row(row.get("model", "")):
                continue
            f = row.get("fields") or {}
            t = (f.get("type") or "").strip()
            name = (f.get("name") or "").strip()
            if not t or not name:
                skipped += 1
                continue
            if t not in valid_types:
                self.stderr.write(self.style.WARNING(f"跳过未知 type={t!r} 的标签：{name!r}"))
                skipped += 1
                continue
            order = int(f.get("order") or 0)
            Tag.objects.update_or_create(type=t, name=name, defaults={"order": order})
            n += 1

        self.stdout.write(self.style.SUCCESS(f"已合并标签 {n} 条（平台 + 渠道）。"))
        if skipped:
            self.stdout.write(self.style.WARNING(f"跳过 {skipped} 条。"))
