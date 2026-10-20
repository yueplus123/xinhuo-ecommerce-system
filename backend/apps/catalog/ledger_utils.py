"""记账统计与工具（与 Node server/index.mjs 行为对齐）。"""

from __future__ import annotations

import re
import uuid
from decimal import Decimal
from typing import Any

from django.db.models import Sum

from .ledger_models import LedgerBusiness, LedgerRecord


def new_uuid() -> str:
    return str(uuid.uuid4())


_MAX_MONEY = Decimal("1e12")  # 与 DecimalField(max_digits=14, decimal_places=2) 对齐，防止溢出


def decimal_num(v: Any) -> Decimal:
    """宽松金额解析（允许负数，如负利润）：非数字 / NaN / Infinity / 超范围一律按 0，统一保留两位小数。"""
    if v is None or v == "":
        return Decimal("0")
    try:
        n = v if isinstance(v, Decimal) else Decimal(str(v).replace(",", "").strip())
    except Exception:
        return Decimal("0")
    if not n.is_finite() or abs(n) >= _MAX_MONEY:
        return Decimal("0")
    return n.quantize(Decimal("0.01"))


def parse_money_input(v: Any) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    if isinstance(v, (int, float)):
        n = Decimal(str(v))
        if n < 0:
            return Decimal("0")
        return n.quantize(Decimal("0.01"))
    s = str(v).replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")
    s = re.sub(r"[\uff10-\uff19]", lambda m: chr(ord(m.group(0)) - 0xFF10 + 0x30), s)
    s = s.replace("\uff0c", "").replace(",", "").strip()
    try:
        n = Decimal(s)
    except Exception:
        return Decimal("0")
    if n < 0:
        return Decimal("0")
    return n.quantize(Decimal("0.01"))


def beijing_year_month(d=None) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if d is None:
        d = datetime.now(ZoneInfo("Asia/Shanghai"))
    elif not hasattr(d, "tzinfo") or d.tzinfo is None:
        d = d.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    else:
        d = d.astimezone(ZoneInfo("Asia/Shanghai"))
    return f"{d.year}-{d.month:02d}"


def format_beijing_datetime(d=None) -> str:
    """北京时间 YYYY-MM-DD HH:mm:ss，24 小时制。"""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if d is None:
        d = datetime.now(ZoneInfo("Asia/Shanghai"))
    elif not hasattr(d, "tzinfo") or d.tzinfo is None:
        d = d.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    else:
        d = d.astimezone(ZoneInfo("Asia/Shanghai"))
    return d.strftime("%Y-%m-%d %H:%M:%S")


def year_month_add(ym: str, delta_months: int) -> str:
    y, mo = map(int, ym.split("-"))
    mo0 = mo - 1 + delta_months
    y2 = y + mo0 // 12
    m2 = mo0 % 12 + 1
    return f"{y2}-{m2:02d}"


def record_at_to_year_month(s: str | None) -> str | None:
    if not s or not isinstance(s, str):
        return None
    t = s.strip()
    m = re.match(r"^(\d{4})[-/](\d{1,2})\b", t)
    if not m:
        return None
    mo = int(m.group(2))
    if mo < 1 or mo > 12:
        return None
    return f"{m.group(1)}-{mo:02d}"


def ledger_project_name(r: LedgerRecord) -> str:
    line = " ".join(x for x in [r.business_name, r.option_label or ""] if x).strip()
    return line or r.business_name or "未命名"


def ledger_status_label(status: str | None, settled_at: str | None = None) -> str:
    s = (status or "").strip().upper()
    if s == LedgerRecord.Status.PROCESSED:
        return "已清账"
    if s == LedgerRecord.Status.REVERSED:
        return "已撤销"
    if s == LedgerRecord.Status.ACTIVE:
        return "未清账"
    if settled_at:
        return "已清账"
    return "未清账"


def sync_ledger_status_fields(row: LedgerRecord, status: str | None = None) -> None:
    s = (status or row.status or LedgerRecord.Status.ACTIVE).strip().upper()
    row.status = s
    if s == LedgerRecord.Status.PROCESSED:
        if not row.settled_at:
            row.settled_at = row.record_at or format_beijing_datetime()
    elif s == LedgerRecord.Status.ACTIVE:
        row.settled_at = None


def ledger_record_to_json(r: LedgerRecord) -> dict:
    return {
        "id": r.id,
        "recordAt": r.record_at,
        "recordNo": r.record_no or r.record_at,
        "businessId": r.business_id,
        "businessName": r.business_name,
        "projectName": ledger_project_name(r),
        "optionId": r.option_id,
        "optionLabel": r.option_label or "",
        "amount": float(r.amount),
        "giveAmount": float(r.give_amount),
        "takeAmount": float(r.take_amount),
        "profit": float(r.profit),
        "employeeName": r.employee_name or "",
        "chatName": r.chat_name or "",
        "status": r.status or LedgerRecord.Status.ACTIVE,
        "statusLabel": ledger_status_label(r.status, r.settled_at),
        "settledAt": r.settled_at,
        "externalId": r.external_id,
    }


def wallet_record_to_json(r) -> dict:
    return {
        "id": r.id,
        "recordAt": r.record_at,
        "wechat": float(r.wechat),
        "alipay": float(r.alipay),
        "card": float(r.card),
        "pocket": float(r.pocket),
        "total": float(r.total),
    }


def business_to_json(b: LedgerBusiness) -> dict:
    return {
        "id": b.id,
        "name": b.name,
        "options": [{"id": o.id, "label": o.label} for o in b.options.all()],
    }


def resolve_ledger_option(b: LedgerBusiness, option_id_raw) -> dict:
    empty = option_id_raw is None or option_id_raw == ""
    opts = list(b.options.all())
    if not empty:
        oid = str(option_id_raw)
        for o in opts:
            if o.id == oid:
                return {"option_id": o.id, "option_label": o.label}
        return {"error": "二级选项不存在"}
    if opts:
        return {"error": "请选择二级选项"}
    return {"option_id": None, "option_label": ""}


def build_stats_payload() -> dict:
    ledger = list(LedgerRecord.objects.select_related("business").order_by("record_at", "id"))

    sum_amount = sum(float(r.amount) for r in ledger)
    sum_give = sum(float(r.give_amount) for r in ledger)
    sum_take = sum(float(r.take_amount) for r in ledger)
    sum_profit = sum(float(r.profit) for r in ledger)
    unsettled_ledger = sum(
        1
        for r in ledger
        if (r.status or LedgerRecord.Status.ACTIVE) == LedgerRecord.Status.ACTIVE and not r.settled_at
    )

    by_biz: dict[str, float] = {}
    for r in ledger:
        k = r.business_name or "未分类"
        by_biz[k] = by_biz.get(k, 0) + float(r.profit)

    this_ym = beijing_year_month()
    last_ym = year_month_add(this_ym, -1)

    ledger_this_month_profit = 0.0
    ledger_this_month_amount = 0.0
    ledger_last_month_profit = 0.0
    ledger_last_month_amount = 0.0
    biz_freq_map: dict[str, int] = {}
    ledger_month_map: dict[str, dict] = {}

    for r in ledger:
        ym = record_at_to_year_month(r.record_at)
        amt = float(r.amount)
        prof = float(r.profit)
        if ym == this_ym:
            ledger_this_month_amount += amt
            ledger_this_month_profit += prof
        elif ym == last_ym:
            ledger_last_month_amount += amt
            ledger_last_month_profit += prof
        if ym:
            o = ledger_month_map.setdefault(ym, {"count": 0, "amount": 0.0, "profit": 0.0})
            o["count"] += 1
            o["amount"] += amt
            o["profit"] += prof
        line = " ".join(x for x in [r.business_name, r.option_label] if x) or "未分类"
        biz_freq_map[line] = biz_freq_map.get(line, 0) + 1

    ledger_by_month = [{"month": m, **v} for m, v in sorted(ledger_month_map.items())]
    biz_frequency = sorted(
        [{"label": k, "count": v} for k, v in biz_freq_map.items()],
        key=lambda x: (-x["count"], x["label"]),
    )

    return {
        "ledgerCount": len(ledger),
        "sumAmount": sum_amount,
        "sumGive": sum_give,
        "sumTake": sum_take,
        "sumProfit": sum_profit,
        "unsettledLedger": unsettled_ledger,
        "byBiz": by_biz,
        "recentLedger": [ledger_record_to_json(r) for r in ledger[-12:][::-1]],
        "ledgerThisMonthProfit": ledger_this_month_profit,
        "ledgerThisMonthAmount": ledger_this_month_amount,
        "ledgerLastMonthProfit": ledger_last_month_profit,
        "ledgerLastMonthAmount": ledger_last_month_amount,
        "ledgerByMonth": ledger_by_month,
        "bizFrequency": biz_frequency,
    }


def import_counts() -> dict:
    from .ledger_models import LedgerBusinessOption, LedgerWalletRecord

    return {
        "businesses": LedgerBusiness.objects.count(),
        "options": LedgerBusinessOption.objects.count(),
        "ledger": LedgerRecord.objects.count(),
        "wallet": LedgerWalletRecord.objects.count(),
    }
