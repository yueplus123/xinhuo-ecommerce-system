"""从旧路径 SQLite 覆盖同步「内容类」catalog 表到当前库（保留订单、订阅、用户账号）。

用法（先备份！）:
  python manage.py sync_catalog_from_old_sqlite --dry-run
  python manage.py sync_catalog_from_old_sqlite
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

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

DELETE_ORDER = list(reversed(CONTENT_TABLES))
INSERT_ORDER = list(CONTENT_TABLES)


class Command(BaseCommand):
    help = "从旧库同步大厅/平台/SKU/教程/共享苹果ID/平台账号等内容表。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--old",
            default="/opt/xinhuo/xinhuo-app/backend/data/backend.sqlite3",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        new_path = Path(settings.DATABASES["default"]["NAME"]).resolve()
        old_path = Path(options["old"]).resolve()
        dry = options["dry_run"]
        if not old_path.is_file():
            self.stderr.write(self.style.ERROR(f"旧库不存在: {old_path}"))
            raise SystemExit(1)
        self.stdout.write(f"当前库: {new_path}")
        self.stdout.write(f"旧库:   {old_path}")
        if dry:
            self.stdout.write(self.style.WARNING("[dry-run] 仅预览，不写库。"))

        with sqlite3.connect(new_path) as conn:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("ATTACH DATABASE ? AS old_db", (str(old_path),))
            try:
                for table in CONTENT_TABLES:
                    n = self._count(conn, "main", table)
                    o = self._count(conn, "old_db", table)
                    self.stdout.write(f"  {table}: 当前 {n} → 旧库 {o}")
                if dry:
                    return
                for table in DELETE_ORDER:
                    conn.execute(f"DELETE FROM main.[{table}]")
                for table in INSERT_ORDER:
                    if self._count(conn, "old_db", table) == 0:
                        continue
                    cols = self._columns(conn, "old_db", table)
                    if not cols:
                        continue
                    col_list = ", ".join(f"[{c}]" for c in cols)
                    conn.execute(
                        f"INSERT INTO main.[{table}] ({col_list}) "
                        f"SELECT {col_list} FROM old_db.[{table}]"
                    )
                    if "id" in cols:
                        max_id = conn.execute(
                            f"SELECT COALESCE(MAX(id), 0) FROM main.[{table}]"
                        ).fetchone()[0]
                        conn.execute(
                            "INSERT INTO main.sqlite_sequence(name, seq) VALUES (?, ?) "
                            "ON CONFLICT(name) DO UPDATE SET seq = excluded.seq",
                            (table, max_id),
                        )
                conn.commit()
            finally:
                conn.execute("DETACH old_db")
                conn.execute("PRAGMA foreign_keys=ON")

        self.stdout.write(
            self.style.SUCCESS(
                "内容表已同步。请执行: rsync 旧 media/hall/ 等目录，并重启 Gunicorn。"
            )
        )

    def _count(self, conn, schema: str, table: str) -> int:
        try:
            return int(
                conn.execute(f"SELECT COUNT(*) FROM {schema}.[{table}]").fetchone()[0]
            )
        except sqlite3.OperationalError:
            return 0

    def _columns(self, conn, schema: str, table: str) -> list[str]:
        rows = conn.execute(f"PRAGMA {schema}.table_info([{table}])").fetchall()
        return [r[1] for r in rows]
