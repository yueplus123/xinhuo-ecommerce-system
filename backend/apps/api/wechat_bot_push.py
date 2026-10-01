"""微信机器人 → 薪火「微信BOT数据」：接收推送 + 职员端按业务列表。不含普通记账。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from backend.apps.catalog.models import WechatBotRecord

TABLE_TYPES = {c.value for c in WechatBotRecord.TableType}
TT = WechatBotRecord.TableType

# 机器人 book / 中文名 / 别名 → table_type（不含 ledger 普通记账）
_TABLE_ALIASES = {
    "pixivcoban": TT.PIXIVCOBAN,
    "充币": TT.PIXIVCOBAN,
    "recharge": TT.PIXIVCOBAN,
    "pixiv": TT.PIXIVCOBAN,
    "coban": TT.PIXIVCOBAN,
    "once_card": TT.ONCE_CARD,
    "一次卡": TT.ONCE_CARD,
    "once": TT.ONCE_CARD,
    "shared": TT.SHARED,
    "共享": TT.SHARED,
    "share": TT.SHARED,
    "package": TT.PACKAGE,
    "打包": TT.PACKAGE,
    "pack": TT.PACKAGE,
    "openrouter": TT.OPENROUTER,
    "op": TT.OPENROUTER,
    "patreon": TT.PATREON,
    "pat": TT.PATREON,
    "commission": TT.COMMISSION,
    "约稿": TT.COMMISSION,
    "booth": TT.BOOTH,
    "pictspace": TT.PICTSPACE,
    "pict": TT.PICTSPACE,
    "premium": TT.PREMIUM,
    "高级会员": TT.PREMIUM,
    "vip": TT.PREMIUM,
    "mega": TT.MEGA,
    "chatgpt": TT.CHATGPT,
    "gpt": TT.CHATGPT,
    "gpt_recharge": TT.CHATGPT,
    "chatgptplus": TT.CHATGPT,
    "plus": TT.CHATGPT,
    "usdt": TT.USDT,
    "usdt充值": TT.USDT,
}


def _api_key_ok(request) -> bool:
    expected = (getattr(settings, "EXTERNAL_PUSH_API_KEY", "") or "").strip()
    if not expected:
        return False
    got = (
        (request.headers.get("X-Api-Key") or "")
        or (request.META.get("HTTP_X_API_KEY") or "")
        or ""
    ).strip()
    if not got:
        auth = (request.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
    return bool(got) and got == expected


def _parse_amount(raw, field="amount") -> Decimal:
    try:
        d = Decimal(str(raw if raw is not None else "0").strip() or "0")
    except (InvalidOperation, AttributeError, TypeError):
        raise ValueError(f"{field} 无效")
    return d.quantize(Decimal("0.01"))


def _parse_quantity(raw, *, direction: str = "", amount=None) -> int:
    """数量：优先用 quantity；否则由 amount + direction 推导（EXPENSE → 负）。"""
    if raw is not None and str(raw).strip() != "":
        try:
            return int(Decimal(str(raw).strip()))
        except (InvalidOperation, AttributeError, TypeError, ValueError):
            raise ValueError("quantity 无效")
    if amount is None or str(amount).strip() == "":
        return 0
    try:
        n = int(Decimal(str(amount).strip()))
    except (InvalidOperation, AttributeError, TypeError, ValueError):
        return 0
    d = str(direction or "").strip().upper()
    if d in {"EXPENSE", "OUT", "DEBIT", "-"}:
        return -abs(n) if n else 0
    return n


def _normalize_clear_status(raw) -> str:
    """统一为空：ACTIVE=未清空；PROCESSED/CLEARED=已清空。"""
    s = str(raw or "").strip()
    if not s:
        return "ACTIVE"
    u = s.upper()
    if s in {"未清空", "未清", "有效"} or u in {"ACTIVE", "OPEN", "UNCLEARED"}:
        return "ACTIVE"
    if s in {"已清空", "已清", "清空"} or u in {"PROCESSED", "CLEARED", "CLEAR", "DONE"}:
        return "PROCESSED"
    if u == "REVERSED" or s in {"已撤销"}:
        return "REVERSED"
    return u[:16]


def clear_status_label(status: str) -> str:
    u = str(status or "").strip().upper()
    if u in {"PROCESSED", "CLEARED", "CLEAR", "DONE"}:
        return "已清空"
    if u == "REVERSED":
        return "已撤销"
    return "未清空"


def quantity_label(qty: int) -> str:
    q = int(qty or 0)
    if q > 0:
        return f"+{q}"
    return str(q)


def _parse_dt(raw):
    if not raw:
        return None
    s = str(raw).strip()
    dt = parse_datetime(s)
    if dt is None:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("occurred_at 无法解析，请用 ISO8601")
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _normalize_table_type(raw: str, book: str = "", business_name: str = "") -> str:
    t = str(raw or "").strip().lower()
    if t in TABLE_TYPES:
        return t
    b = str(book or "").strip().lower()
    biz = str(business_name or "").strip()
    biz_l = biz.lower()

    for key in (t, b, biz, biz_l):
        if key in _TABLE_ALIASES:
            return _TABLE_ALIASES[key]

    # ledger 仅当业务名指向 gpt 时归入 gpt 表；普通记账不入库
    if b == "ledger" and ("gpt" in biz_l or "chatgpt" in biz_l or "代充" in biz):
        return TT.CHATGPT

    allowed = " / ".join(sorted(TABLE_TYPES))
    raise ValueError(
        f"table_type 无效：{raw!r}（允许：{allowed}；"
        f"或传 book=recharge|usdt|gpt_recharge|once_card|…；普通记账不接入本页）"
    )


def ingest_wechat_bot_item(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("记录必须是 JSON 对象")

    action = str(raw.get("action") or "").strip().lower()
    if action == "status":
        return _update_wechat_bot_status(raw)
    if action == "delete":
        return _delete_wechat_bot_by_event(raw)

    event_id = str(raw.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("event_id 必填")
    if len(event_id) > 128:
        raise ValueError("event_id 最长 128")

    book = str(raw.get("book") or "").strip()
    business_name = str(raw.get("business_name") or "")[:128]
    table_type = _normalize_table_type(raw.get("table_type") or "", book, business_name)

    existing = WechatBotRecord.objects.filter(external_id=event_id).only("id", "table_type").first()
    if existing:
        return {
            "status": "duplicate",
            "id": existing.id,
            "event_id": event_id,
            "table_type": existing.table_type,
        }

    direction = str(raw.get("direction") or "")[:16]
    # USDT：人民币数 / 美金数；其它表：数量 ±1
    amount_cny_raw = raw.get("amount_cny")
    if amount_cny_raw is None:
        amount_cny_raw = raw.get("amount")
    if amount_cny_raw is None:
        amount_cny_raw = raw.get("receive_amount")
    amount_usd_raw = raw.get("amount_usd")
    if amount_usd_raw is None:
        amount_usd_raw = raw.get("usd_amount")

    qty_raw = raw.get("quantity")
    if qty_raw is None:
        qty_raw = raw.get("qty")
    if qty_raw is None:
        qty_raw = raw.get("delta")

    clear_raw = raw.get("clear_status")
    if clear_raw is None or str(clear_raw).strip() == "":
        clear_raw = raw.get("status")

    data = {
        "table_type": table_type,
        "external_id": event_id,
        "record_no": str(raw.get("record_no") or "")[:64],
        "book": book[:32],
        "direction": direction,
        "quantity": _parse_quantity(qty_raw, direction=direction, amount=raw.get("amount")),
        "amount": _parse_amount(amount_cny_raw, "amount"),
        "amount_usd": _parse_amount(amount_usd_raw, "amount_usd"),
        "currency": str(raw.get("currency") or ("USD" if table_type == TT.USDT else "CNY"))[:8],
        "business_name": business_name,
        "amount_to_you": _parse_amount(raw.get("amount_to_you"), "amount_to_you"),
        "amount_to_me": _parse_amount(raw.get("amount_to_me"), "amount_to_me"),
        "profit_amount": _parse_amount(raw.get("profit_amount"), "profit_amount"),
        "employee_name": str(raw.get("employee_name") or "")[:128],
        "chat_name": str(raw.get("chat_name") or "")[:128],
        "raw_text": str(raw.get("raw_text") or "")[:500],
        "remark": str(raw.get("remark") or "")[:200],
        "status": _normalize_clear_status(clear_raw),
        "occurred_at": _parse_dt(raw.get("occurred_at")),
    }

    try:
        with transaction.atomic():
            rec = WechatBotRecord.objects.create(**data)
    except IntegrityError:
        existing = WechatBotRecord.objects.filter(external_id=event_id).only("id", "table_type").first()
        if existing:
            return {
                "status": "duplicate",
                "id": existing.id,
                "event_id": event_id,
                "table_type": existing.table_type,
            }
        raise

    return {
        "status": "created",
        "id": rec.id,
        "event_id": event_id,
        "table_type": rec.table_type,
    }


def _update_wechat_bot_status(raw: dict) -> dict:
    """机器人清空/已转账后：按 event_id 更新清空状态。"""
    event_id = str(raw.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("event_id 必填")
    status = _normalize_clear_status(raw.get("status") or raw.get("clear_status"))
    rec = WechatBotRecord.objects.filter(external_id=event_id).first()
    if not rec:
        return {
            "status": "missing",
            "event_id": event_id,
            "table_type": "",
        }
    rec.status = status
    rec.save(update_fields=["status", "updated_at"])
    return {
        "status": "updated",
        "id": rec.id,
        "event_id": event_id,
        "table_type": rec.table_type,
        "clear_status": clear_status_label(status),
    }


def _delete_wechat_bot_by_event(raw: dict) -> dict:
    event_id = str(raw.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("event_id 必填")
    deleted, _ = WechatBotRecord.objects.filter(external_id=event_id).delete()
    return {
        "status": "deleted" if deleted else "missing",
        "event_id": event_id,
        "deleted": int(deleted),
    }


def ingest_wechat_bot_pull(raw: dict) -> dict:
    """拉取微信BOT数据（与记账 pull 对齐）。

    可选过滤：status / employee_name / business_name / table_type / book
    status 默认 ACTIVE（未清空）；传 * / ALL / 空且 want_all 时不按状态过滤——
    这里约定：未传 status 默认 ACTIVE；status=* 表示全部。
    """
    if not isinstance(raw, dict):
        raise ValueError("记录必须是 JSON 对象")
    status_raw = str(raw.get("status") or "ACTIVE").strip()
    status_u = status_raw.upper()
    employee_name = str(raw.get("employee_name") or "").strip()
    business_name = str(
        raw.get("business_name") or raw.get("book") or ""
    ).strip()
    table_type = str(raw.get("table_type") or "").strip()

    qs = WechatBotRecord.objects.all().order_by("occurred_at", "id")
    if status_u and status_u not in {"*", "ALL", "__ALL__"}:
        # 已清空兼容 PROCESSED / CLEARED
        if status_u in {"PROCESSED", "CLEARED", "CLEAR", "DONE"}:
            qs = qs.filter(status__in=["PROCESSED", "CLEARED"])
        else:
            qs = qs.filter(status=status_u)
    if employee_name:
        qs = qs.filter(employee_name=employee_name)
    if business_name:
        # book 或 business_name 任一匹配；也支持中文别名落到 table_type
        mapped = _TABLE_ALIASES.get(business_name) or _TABLE_ALIASES.get(
            business_name.lower()
        )
        if mapped is not None:
            tt_val = getattr(mapped, "value", None) or str(mapped)
            qs = qs.filter(
                Q(table_type=tt_val)
                | Q(business_name=business_name)
                | Q(book=business_name)
            )
        else:
            qs = qs.filter(Q(business_name=business_name) | Q(book=business_name))
    if table_type:
        if table_type not in TABLE_TYPES:
            # 允许中文
            mapped = _TABLE_ALIASES.get(table_type) or _TABLE_ALIASES.get(
                table_type.lower()
            )
            if mapped is None:
                raise ValueError(f"table_type 无效：{table_type}")
            table_type = getattr(mapped, "value", None) or str(mapped)
        qs = qs.filter(table_type=table_type)

    records = []
    for row in qs.iterator():
        item = serialize_wechat_bot_record(row)
        item["event_id"] = (row.external_id or "").strip() or f"manual-{row.id}"
        records.append(item)
    return {
        "count": len(records),
        "records": records,
        "status": status_raw or "ACTIVE",
        "employee_name": employee_name,
        "business_name": business_name,
        "table_type": table_type,
    }


def ingest_wechat_bot_payload(body) -> dict:
    if not isinstance(body, dict):
        raise ValueError("请求体必须是 JSON 对象")
    action = str(body.get("action") or "").strip().lower()
    if action in {"pull", "sync", "list"}:
        r = ingest_wechat_bot_pull(body)
        return {"ok": True, "mode": "pull", **r}
    # 顶层 action=status/delete：单条生命周期
    if action in {"status", "delete"} and "items" not in body:
        if action == "status":
            r = _update_wechat_bot_status(body)
        else:
            r = _delete_wechat_bot_by_event(body)
        return {"ok": True, "mode": "single", **r}
    if "items" in body:
        items = body.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("items 必须是非空数组")
        if len(items) > 100:
            raise ValueError("单次最多 100 条")
        results = []
        created = duplicate = updated = 0
        for idx, it in enumerate(items):
            try:
                r = ingest_wechat_bot_item(it)
            except ValueError as e:
                raise ValueError(f"items[{idx}]: {e}") from e
            results.append(r)
            st = r.get("status")
            if st == "created":
                created += 1
            elif st == "updated":
                updated += 1
            else:
                duplicate += 1
        return {
            "ok": True,
            "mode": "batch",
            "created": created,
            "duplicate": duplicate,
            "updated": updated,
            "results": results,
        }
    if not body.get("event_id"):
        raise ValueError("缺少 event_id；批量请用 {\"items\":[...]}")
    r = ingest_wechat_bot_item(body)
    return {"ok": True, "mode": "single", **r}


def serialize_wechat_bot_record(obj: WechatBotRecord) -> dict:
    qty = int(obj.quantity or 0)
    return {
        "id": obj.id,
        "table_type": obj.table_type,
        "external_id": obj.external_id,
        "record_no": obj.record_no,
        "book": obj.book,
        "direction": obj.direction,
        "quantity": qty,
        "quantity_label": quantity_label(qty),
        "amount": str(obj.amount),
        "amount_cny": str(obj.amount),
        "amount_usd": str(obj.amount_usd),
        "currency": obj.currency,
        "business_name": obj.business_name,
        "amount_to_you": str(obj.amount_to_you),
        "amount_to_me": str(obj.amount_to_me),
        "profit_amount": str(obj.profit_amount),
        "employee_name": obj.employee_name,
        "chat_name": obj.chat_name,
        "raw_text": obj.raw_text,
        "remark": obj.remark,
        "status": obj.status,
        "clear_status": clear_status_label(obj.status),
        "occurred_at": obj.occurred_at.isoformat() if obj.occurred_at else "",
        "created_at": obj.created_at.isoformat() if obj.created_at else "",
    }


def list_wechat_bot_employees(*, table_type: str = "") -> list[str]:
    """去重员工名；可按业务表过滤，供页内人员筛选。"""
    qs = WechatBotRecord.objects.exclude(employee_name="")
    table_type = (table_type or "").strip()
    if table_type:
        if table_type not in TABLE_TYPES:
            raise ValueError(f"table 参数无效：{table_type}")
        qs = qs.filter(table_type=table_type)
    names = qs.values_list("employee_name", flat=True).distinct().order_by("employee_name")
    return [str(n).strip() for n in names if str(n).strip()]


def list_wechat_bot_records(
    *,
    table_type: str = "",
    employee_name: str = "",
    q: str = "",
    page: int = 1,
    page_size: int = 30,
):
    qs = WechatBotRecord.objects.all()
    table_type = (table_type or "").strip()
    employee_name = (employee_name or "").strip()
    if table_type:
        if table_type not in TABLE_TYPES:
            raise ValueError(f"table 参数无效：{table_type}")
        qs = qs.filter(table_type=table_type)
    if employee_name:
        qs = qs.filter(employee_name=employee_name)
    q = (q or "").strip()
    if q:
        qs = qs.filter(
            Q(employee_name__icontains=q)
            | Q(chat_name__icontains=q)
            | Q(raw_text__icontains=q)
            | Q(remark__icontains=q)
            | Q(business_name__icontains=q)
            | Q(record_no__icontains=q)
            | Q(external_id__icontains=q)
        )
    qs = qs.order_by("-occurred_at", "-id")
    total = qs.count()
    page = max(1, int(page or 1))
    page_size = min(100, max(1, int(page_size or 30)))
    start = (page - 1) * page_size
    rows = [serialize_wechat_bot_record(o) for o in qs[start : start + page_size]]
    return {"count": total, "page": page, "page_size": page_size, "results": rows}


def create_manual_wechat_bot_record(raw: dict) -> dict:
    """职员端手工录入（自动生成 event_id）。"""
    if not isinstance(raw, dict):
        raise ValueError("请求体必须是 JSON 对象")
    table_type = _normalize_table_type(
        raw.get("table_type") or "",
        str(raw.get("book") or ""),
        str(raw.get("business_name") or ""),
    )
    import uuid

    payload = dict(raw)
    payload["table_type"] = table_type
    payload["event_id"] = str(raw.get("event_id") or f"manual-{uuid.uuid4().hex}")[:128]
    if not payload.get("book"):
        payload["book"] = "manual"
    result = ingest_wechat_bot_item(payload)
    if result.get("status") == "duplicate":
        # 极低概率撞 id，再试一次
        payload["event_id"] = f"manual-{uuid.uuid4().hex}"[:128]
        result = ingest_wechat_bot_item(payload)
    obj = WechatBotRecord.objects.filter(pk=result.get("id")).first()
    if not obj:
        raise ValueError("创建失败")
    return {"ok": True, "record": serialize_wechat_bot_record(obj)}


def delete_wechat_bot_record(pk: int) -> None:
    deleted, _ = WechatBotRecord.objects.filter(pk=pk).delete()
    if not deleted:
        raise LookupError("记录不存在")


def delete_wechat_bot_records(ids) -> dict:
    """职员端批量删除。"""
    if not isinstance(ids, (list, tuple)):
        raise ValueError("ids 必须是数组")
    cleaned: list[int] = []
    for x in ids:
        try:
            cleaned.append(int(x))
        except (TypeError, ValueError) as e:
            raise ValueError(f"无效 id：{x}") from e
    cleaned = list(dict.fromkeys(cleaned))
    if not cleaned:
        raise ValueError("请选择要删除的记录")
    if len(cleaned) > 200:
        raise ValueError("单次最多删除 200 条")
    deleted, _ = WechatBotRecord.objects.filter(pk__in=cleaned).delete()
    return {"ok": True, "deleted": int(deleted), "requested": len(cleaned)}


def update_wechat_bot_record(pk: int, raw: dict) -> dict:
    """职员端编辑单条记录（不改 table_type / external_id）。"""
    if not isinstance(raw, dict):
        raise ValueError("请求体必须是 JSON 对象")
    obj = WechatBotRecord.objects.filter(pk=pk).first()
    if not obj:
        raise LookupError("记录不存在")

    if "occurred_at" in raw and raw.get("occurred_at"):
        obj.occurred_at = _parse_dt(raw.get("occurred_at"))

    if "employee_name" in raw:
        emp = str(raw.get("employee_name") or "").strip()
        if not emp:
            raise ValueError("请填写人员")
        obj.employee_name = emp[:100]

    if "remark" in raw:
        obj.remark = str(raw.get("remark") or "").strip()[:500]

    if "clear_status" in raw or "status" in raw:
        obj.status = _normalize_clear_status(raw.get("clear_status") or raw.get("status"))

    if "business_name" in raw:
        obj.business_name = str(raw.get("business_name") or "").strip()[:200]

    if "quantity" in raw and raw.get("quantity") is not None and str(raw.get("quantity")) != "":
        try:
            obj.quantity = int(raw.get("quantity"))
        except (TypeError, ValueError) as e:
            raise ValueError("数量无效") from e

    if "amount_cny" in raw or "amount" in raw:
        from decimal import Decimal, InvalidOperation

        try:
            obj.amount = Decimal(str(raw.get("amount_cny") if raw.get("amount_cny") is not None else raw.get("amount") or "0"))
        except (InvalidOperation, TypeError, ValueError) as e:
            raise ValueError("人民币金额无效") from e

    if "amount_usd" in raw:
        from decimal import Decimal, InvalidOperation

        try:
            obj.amount_usd = Decimal(str(raw.get("amount_usd") or "0"))
        except (InvalidOperation, TypeError, ValueError) as e:
            raise ValueError("美金金额无效") from e

    obj.save()
    return {"ok": True, "record": serialize_wechat_bot_record(obj)}


def seed_wechat_bot_demo(*, per_table: int = 10, replace: bool = True) -> dict:
    """为每个业务表写入演示数据，便于看表效果。"""
    from datetime import timedelta
    from decimal import Decimal

    demo_prefix = "demo-wbot-"
    if replace:
        WechatBotRecord.objects.filter(external_id__startswith=demo_prefix).delete()

    employees = ["张越", "李冬梅", "王芳", "陈晨", "刘洋"]
    sku_map = {
        TT.PREMIUM: ["一个月", "三个月", "六个月", "一年", "终身"],
        TT.MEGA: [
            "pro1一个月",
            "pro1三个月",
            "pro1六个月",
            "pro1一年",
            "pro3一个月",
            "pro3三个月",
        ],
        TT.CHATGPT: ["pro100刀", "pro200刀", "plus", "plus一个月", "team"],
    }
    remarks = ["演示数据", "测试备注", "群内记单", "补录", ""]
    now = timezone.localtime()
    created = 0

    for table in WechatBotRecord.TableType:
        for i in range(per_table):
            emp = employees[i % len(employees)]
            occurred = now - timedelta(hours=i * 3 + (hash(table.value) % 5))
            cleared = i % 4 == 0
            qty = 1 if i % 3 != 2 else -1
            biz = ""
            if table.value in sku_map:
                biz = sku_map[table.value][i % len(sku_map[table.value])]
            amount = Decimal("0")
            amount_usd = Decimal("0")
            if table == TT.USDT:
                amount = Decimal(str(500 + i * 120))
                amount_usd = Decimal(str(100 + i * 50))
                qty = 0
            WechatBotRecord.objects.create(
                table_type=table.value,
                external_id=f"{demo_prefix}{table.value}-{i+1:02d}",
                book="demo",
                direction="INCOME" if qty >= 0 else "EXPENSE",
                quantity=qty,
                amount=amount,
                amount_usd=amount_usd,
                currency="USD" if table == TT.USDT else "CNY",
                business_name=biz,
                employee_name=emp,
                remark=remarks[i % len(remarks)],
                status="PROCESSED" if cleared else "ACTIVE",
                occurred_at=occurred,
                raw_text=f"demo {table.label} #{i+1}",
            )
            created += 1

    return {"ok": True, "created": created, "per_table": per_table, "tables": len(TABLE_TYPES)}
