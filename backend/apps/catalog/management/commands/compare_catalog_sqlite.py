"""对比当前库与旧路径 SQLite 中 catalog 各表行数。用法（backend 目录）:
  python manage.py compare_catalog_sqlite
  python manage.py compare_catalog_sqlite --old /opt/xinhuo/xinhuo-app/backend/data/backend.sqlite3
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


# 职员端/后台共用的「内容类」表（不含订单、订阅；订单已单独合并过）
CONTENT_TABLES = (
    "catalog_tag",
    "catalog_platform",
    "catalog_platform_platform_tags",
    "catalog_business",
    "catalog_sku",
    "catalog_sku_channel_tags",
    "catalog_quickphrase",
    "catalog_phrasepool",
    "catalog_hallblock",
    "catalog_paymenttutorial",
    "catalog_tutorialpool",
    "catalog_platformaccount",
    "catalog_sharedappleidpage",
    "catalog_usdproxypricetier",
)


class Command(BaseCommand):
    help = "对比当前库与旧库 catalog 表行数，定位前端内容是否读错库。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--old",
            default="/opt/xinhuo/xinhuo-app/backend/data/backend.sqlite3",
            help="旧环境 SQLite 路径",
        )

    def handle(self, *args, **options):
        new_path = Path(settings.DATABASES["default"]["NAME"])
        old_path = Path(options["old"])
        if not old_path.is_file():
            self.stderr.write(self.style.ERROR(f"旧库不存在: {old_path}"))
            raise SystemExit(1)
        self.stdout.write(f"当前库: {new_path}")
        self.stdout.write(f"旧库:   {old_path}\n")
        self.stdout.write(f"{'表名':<42} {'当前':>8} {'旧库':>8} {'差(旧-当前)':>12}")
        self.stdout.write("-" * 74)
        need_sync = []
        for table in CONTENT_TABLES:
            nc = self._count(new_path, table)
            oc = self._count(old_path, table)
            diff = oc - nc
            flag = "  ← 建议从旧库同步" if diff > 0 else ""
            if diff > 0:
                need_sync.append(table)
            self.stdout.write(f"{table:<42} {nc:>8} {oc:>8} {diff:>+12}{flag}")
        self.stdout.write("")
        if need_sync:
            self.stdout.write(self.style.WARNING(f"共 {len(need_sync)} 张表旧库更多，可执行 sync_catalog_from_old_sqlite 合并。"))
        else:
            self.stdout.write(self.style.SUCCESS("内容表行数一致或当前库不少于旧库。"))

    def _count(self, db_path: Path, table: str) -> int:
        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()
                return int(row[0]) if row else 0
        except sqlite3.OperationalError:
            return -1
