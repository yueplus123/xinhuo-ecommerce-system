"""从 dumpdata 的 JSON 合并「平台账号密码」到当前库（按 平台名称+账号 唯一合并）。"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from backend.apps.catalog.models import PlatformAccount


def _is_platform_account_row(model: str) -> bool:
    m = (model or "").lower()
    return m.endswith("platformaccount")


class Command(BaseCommand):
    help = (
        "读取 dumpdata 导出的 JSON（含 catalog.platformaccount 或旧站 business.platformaccount 等），"
        "按 name + account 做 update_or_create。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="",
            help="JSON 路径；留空则使用 apps/catalog/fixtures/platform_accounts.json",
        )

    def handle(self, *args, **options):
        raw = (options["path"] or "").strip()
        if raw:
            path = Path(raw).expanduser().resolve()
        else:
            catalog = Path(__file__).resolve().parent.parent.parent
            path = catalog / "fixtures" / "platform_accounts.json"
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"找不到文件：{path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        n = 0
        for row in data:
            if not _is_platform_account_row(row.get("model", "")):
                continue
            f = row["fields"]
            name = (f.get("name") or "").strip()
            account = (f.get("account") or "").strip()
            if not name:
                self.stderr.write(self.style.WARNING(f"跳过一条缺少 name 的记录：{row.get('pk')}"))
                continue

            defaults = {
                "password": f.get("password") or "",
                "url": f.get("url") or "",
                "note": f.get("note") or "",
                "sort_order": int(f.get("sort_order") or 0),
            }
            PlatformAccount.objects.update_or_create(
                name=name,
                account=account,
                defaults=defaults,
            )
            n += 1

        self.stdout.write(self.style.SUCCESS(f"已合并平台账号密码 {n} 条。"))
