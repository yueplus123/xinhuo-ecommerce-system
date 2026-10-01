"""
从记账 Node 的 store.json 安全导入到 Django SQLite。

用法（生产服务器）：
  cp /opt/ledger-app/server/data/store.json /tmp/store.json.bak
  PYTHONPATH=/var/www/xinhuo/app .venv/bin/python backend/manage.py import_ledger_store \\
    --file /opt/ledger-app/server/data/store.json --dry-run
  # 确认计数无误后：
  PYTHONPATH=/var/www/xinhuo/app .venv/bin/python backend/manage.py import_ledger_store \\
    --file /opt/ledger-app/server/data/store.json
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from backend.apps.catalog.ledger_models import (
    LedgerBusiness,
    LedgerBusinessOption,
    LedgerRecord,
    LedgerWalletRecord,
)
from backend.apps.catalog.ledger_utils import decimal_num, import_counts


class Command(BaseCommand):
    help = "从 store.json 导入记账数据到 Django（默认拒绝覆盖已有数据）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="store.json 路径，例如 /opt/ledger-app/server/data/store.json",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="只统计与校验，不写入数据库",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="若 Django 中已有记账数据，先清空再导入（危险，需先备份）",
        )
        parser.add_argument(
            "--backup-db",
            action="store_true",
            help="导入前复制 backend/data/backend.sqlite3 到 backups/",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.is_file():
            raise CommandError(f"文件不存在: {path}")

        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON 解析失败: {e}") from e

        businesses = data.get("businesses") or []
        ledger = data.get("ledger") or []
        wallet = data.get("wallet") or []

        self.stdout.write(
            f"store.json: businesses={len(businesses)} ledger={len(ledger)} wallet={len(wallet)}"
        )

        existing = import_counts()
        self.stdout.write(f"Django 当前: {existing}")

        if any(existing.values()) and not options["force"]:
            raise CommandError(
                "Django 中已有记账数据。若确认要导入，请先备份后加 --force；"
                "或仅用 --dry-run 查看。"
            )

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("dry-run 完成，未写入数据库。"))
            return

        if options["backup_db"]:
            from django.conf import settings

            db_path = Path(settings.DATABASES["default"]["NAME"])
            if db_path.is_file():
                dest_dir = db_path.parent.parent.parent / "backups"
                dest_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d-%H%M")
                dest = dest_dir / f"backend-sqlite-pre-ledger-import-{stamp}.sqlite3"
                shutil.copy2(db_path, dest)
                self.stdout.write(f"已备份数据库到 {dest}")

        store_backup = path.parent / f"store.json.bak-{datetime.now().strftime('%Y%m%d-%H%M')}"
        shutil.copy2(path, store_backup)
        self.stdout.write(f"已备份 store.json 到 {store_backup}")

        with transaction.atomic():
            if options["force"]:
                LedgerRecord.objects.all().delete()
                LedgerWalletRecord.objects.all().delete()
                LedgerBusinessOption.objects.all().delete()
                LedgerBusiness.objects.all().delete()

            biz_map: dict[str, LedgerBusiness] = {}
            for b in businesses:
                bid = str(b.get("id") or "")
                if not bid:
                    continue
                obj, _ = LedgerBusiness.objects.get_or_create(
                    id=bid,
                    defaults={"name": str(b.get("name") or "").strip() or "未命名"},
                )
                if obj.name != (b.get("name") or "").strip():
                    obj.name = str(b.get("name") or "").strip() or obj.name
                    obj.save(update_fields=["name"])
                biz_map[bid] = obj
                for o in b.get("options") or []:
                    oid = str(o.get("id") or "")
                    if not oid:
                        continue
                    LedgerBusinessOption.objects.update_or_create(
                        id=oid,
                        defaults={
                            "business": obj,
                            "label": str(o.get("label") or "").strip(),
                        },
                    )

            for r in ledger:
                rid = str(r.get("id") or "")
                bid = str(r.get("businessId") or "")
                if not rid or not bid:
                    continue
                bobj = biz_map.get(bid)
                if not bobj:
                    bobj, _ = LedgerBusiness.objects.get_or_create(
                        id=bid,
                        defaults={"name": str(r.get("businessName") or bid)},
                    )
                    biz_map[bid] = bobj
                LedgerRecord.objects.update_or_create(
                    id=rid,
                    defaults={
                        "record_at": str(r.get("recordAt") or ""),
                        "business": bobj,
                        "business_name": str(r.get("businessName") or bobj.name),
                        "option_id": r.get("optionId") or None,
                        "option_label": str(r.get("optionLabel") or ""),
                        "amount": decimal_num(r.get("amount")),
                        "give_amount": decimal_num(r.get("giveAmount")),
                        "take_amount": decimal_num(r.get("takeAmount")),
                        "profit": decimal_num(r.get("profit")),
                        "settled_at": r.get("settledAt") or None,
                    },
                )

            for r in wallet:
                rid = str(r.get("id") or "")
                if not rid:
                    continue
                w = decimal_num(r.get("wechat"))
                a = decimal_num(r.get("alipay"))
                c = decimal_num(r.get("card"))
                p = decimal_num(r.get("pocket"))
                total = decimal_num(r.get("total"))
                if total == 0:
                    total = w + a + c + p
                LedgerWalletRecord.objects.update_or_create(
                    id=rid,
                    defaults={
                        "record_at": str(r.get("recordAt") or ""),
                        "wechat": w,
                        "alipay": a,
                        "card": c,
                        "pocket": p,
                        "total": total,
                    },
                )

        after = import_counts()
        self.stdout.write(f"导入后 Django: {after}")
        self.stdout.write(self.style.SUCCESS("导入完成。"))
