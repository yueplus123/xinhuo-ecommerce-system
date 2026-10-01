"""从 dumpdata 的 JSON 合并「收款记录」及附属截图行（PaymentRecordImage）。"""

import json
from datetime import datetime, time as time_min
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from backend.apps.catalog.models import PAYMENT_CHANNELS, PaymentRecord, PaymentRecordImage

_VALID_CHANNEL = {c[0] for c in PAYMENT_CHANNELS}
# 旧数据若存的是展示名，尽量映射到当前库存储值（choices 第一项）
_CHANNEL_ALIASES = {
    "淘宝": "千牛",
    "闲鱼/得物": "咸鱼/得物",
    "闲鱼": "咸鱼/得物",
}


def _is_payment_record_row(model: str) -> bool:
    m = (model or "").lower()
    return m.endswith("paymentrecord") and not m.endswith("paymentrecordimage")


def _is_payment_record_image_row(model: str) -> bool:
    return (model or "").lower().endswith("paymentrecordimage")


def _resolve_user(raw):
    User = get_user_model()
    if raw is None:
        return None
    if isinstance(raw, int):
        return User.objects.filter(pk=raw).first()
    if isinstance(raw, (list, tuple)) and len(raw) >= 1:
        return User.objects.filter(username=str(raw[-1])).first()
    return None


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, str) and "T" in val:
        dt = parse_datetime(val)
        return dt.date() if dt else None
    if isinstance(val, str):
        return parse_date(val)
    return val


def _parse_dt(val):
    if not val:
        return None
    if not isinstance(val, str):
        return val
    dt = parse_datetime(val)
    if dt is not None and timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _normalize_channel(ch: str) -> str:
    s = (ch or "").strip()
    if s in _VALID_CHANNEL:
        return s
    return _CHANNEL_ALIASES.get(s, s)


class Command(BaseCommand):
    help = (
        "读取 dumpdata 导出的 JSON（business.paymentrecord / catalog.paymentrecord 等）。"
        "建议服务器导出时使用 --natural-foreign --natural-primary，以便 user 按用户名解析。"
        "合并策略：按 fixture 里的 pk 做 update_or_create（本地同 pk 会被覆盖）。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="",
            help="JSON 路径；留空则使用 apps/catalog/fixtures/payment_records.json",
        )

    def handle(self, *args, **options):
        raw = (options["path"] or "").strip()
        if raw:
            path = Path(raw).expanduser().resolve()
        else:
            catalog = Path(__file__).resolve().parent.parent.parent
            path = catalog / "fixtures" / "payment_records.json"
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"找不到文件：{path}"))
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        n_rec = 0
        n_img = 0
        skipped = 0

        for row in data:
            if not _is_payment_record_row(row.get("model", "")):
                continue
            pk = row.get("pk")
            f = row["fields"]
            user = _resolve_user(f.get("user"))
            if user is None:
                self.stderr.write(
                    self.style.WARNING(
                        f"跳过收款记录 pk={pk}：无法解析用户 {f.get('user')!r}（请用带 --natural-foreign 的导出，或先导入用户且保证 pk 一致）。"
                    )
                )
                skipped += 1
                continue

            ch = _normalize_channel(f.get("channel") or "")
            if ch not in _VALID_CHANNEL:
                self.stderr.write(
                    self.style.WARNING(f"跳过收款记录 pk={pk}：未知渠道 {f.get('channel')!r}，请先在 models 增加或手工改 JSON。")
                )
                skipped += 1
                continue

            try:
                amount = Decimal(str(f.get("amount") or "0"))
            except (InvalidOperation, TypeError):
                amount = Decimal("0")

            order_count = int(f.get("order_count") or 0)
            note = (f.get("note") or "")[:500]
            screenshot = f.get("screenshot") or ""
            if isinstance(screenshot, str) and not screenshot.strip():
                screenshot = ""

            rd = _parse_date(f.get("record_date"))
            ca = _parse_dt(f.get("created_at"))
            if rd is None:
                from datetime import date

                rd = date.today()
            if ca is None:
                ca = timezone.make_aware(
                    datetime.combine(rd, time_min.min),
                    timezone.get_current_timezone(),
                )

            defaults = {
                "user": user,
                "channel": ch,
                "order_count": order_count,
                "amount": amount,
                "note": note,
                "record_date": rd,
                "created_at": ca,
            }
            if screenshot:
                defaults["screenshot"] = screenshot

            PaymentRecord.objects.update_or_create(pk=pk, defaults=defaults)
            # 直接 UPDATE，避免历史上 auto_now_add 在 INSERT 时忽略 fixture 里的时间
            PaymentRecord.objects.filter(pk=pk).update(record_date=rd, created_at=ca)
            n_rec += 1

        for row in data:
            if not _is_payment_record_image_row(row.get("model", "")):
                continue
            pk = row.get("pk")
            f = row["fields"]
            pr_id = f.get("payment_record")
            if not PaymentRecord.objects.filter(pk=pr_id).exists():
                self.stderr.write(self.style.WARNING(f"跳过附属图 pk={pk}：无 payment_record_id={pr_id}"))
                skipped += 1
                continue
            img = (f.get("image") or "").strip()
            if not img:
                skipped += 1
                continue
            defaults = {
                "payment_record_id": pr_id,
                "image": img,
                "sort_order": int(f.get("sort_order") or 0),
            }
            PaymentRecordImage.objects.update_or_create(pk=pk, defaults=defaults)
            n_img += 1

        self.stdout.write(self.style.SUCCESS(f"已合并收款记录 {n_rec} 条，附属截图行 {n_img} 条。"))
        if n_rec and not n_img:
            self.stdout.write(
                self.style.WARNING(
                    "未导入任何 PaymentRecordImage。若线上有多张「附属截图」，请在服务器用一条命令同时导出：\n"
                    "  dumpdata business.PaymentRecord business.PaymentRecordImage --natural-foreign --natural-primary\n"
                    "勿再用仅 PaymentRecord 的导出覆盖该 JSON，否则附属图会丢失。"
                )
            )
        if skipped:
            self.stdout.write(self.style.WARNING(f"跳过 / 警告累计 {skipped} 次（见上）。"))
