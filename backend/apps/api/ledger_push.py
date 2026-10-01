"""微信机器人 → 薪火记账表（LedgerRecord）推送接收。"""

from __future__ import annotations

from django.db import IntegrityError, transaction

from backend.apps.catalog.ledger_models import LedgerBusiness, LedgerRecord
from backend.apps.catalog.ledger_utils import (
    decimal_num,
    format_beijing_datetime,
    ledger_record_to_json,
    new_uuid,
    sync_ledger_status_fields,
)

from .api_key import api_key_ok
from .wechat_bot_push import _parse_dt


def _ensure_business_for_project(name: str) -> LedgerBusiness:
    raw = (name or "").strip() or "未命名"
    b = LedgerBusiness.objects.filter(name=raw).prefetch_related("options").first()
    if b and not b.options.exists():
        return b
    if not b:
        return LedgerBusiness.objects.create(id=new_uuid(), name=raw)
    return LedgerBusiness.objects.create(id=new_uuid(), name=f"{raw}·{new_uuid()[:8]}")


def ingest_ledger_settlement(raw: dict) -> dict:
    """按群名清账：将该群所有未清账记录标为已清账。"""
    if not isinstance(raw, dict):
        raise ValueError("记录必须是 JSON 对象")
    chat_name = str(raw.get("chat_name") or "").strip()
    if not chat_name:
        raise ValueError("chat_name 必填")

    occurred = _parse_dt(raw.get("occurred_at"))
    settled_at = format_beijing_datetime(occurred) if occurred else format_beijing_datetime()

    qs = LedgerRecord.objects.filter(
        chat_name=chat_name,
        status=LedgerRecord.Status.ACTIVE,
    )
    updated = 0
    with transaction.atomic():
        for row in qs.iterator():
            sync_ledger_status_fields(row, LedgerRecord.Status.PROCESSED)
            row.settled_at = settled_at
            row.save(update_fields=["status", "settled_at"])
            updated += 1

    return {
        "status": "settled",
        "chat_name": chat_name,
        "updated": updated,
        "settled_at": settled_at,
    }


def ingest_ledger_status_update(raw: dict) -> dict:
    """按 event_id 更新单条记录状态（撤销 / 恢复 / 标记已处理）。"""
    if not isinstance(raw, dict):
        raise ValueError("记录必须是 JSON 对象")
    event_id = str(raw.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("event_id 必填")
    status_raw = str(raw.get("status") or "").strip().upper()
    allowed = {c.value for c in LedgerRecord.Status}
    if status_raw not in allowed:
        raise ValueError(f"status 无效，允许：{', '.join(sorted(allowed))}")

    row = LedgerRecord.objects.filter(external_id=event_id).first()
    if not row:
        return {"status": "not_found", "event_id": event_id}

    sync_ledger_status_fields(row, status_raw)
    row.save(update_fields=["status", "settled_at"])
    return {
        "status": "updated",
        "event_id": event_id,
        "id": row.id,
        "record": ledger_record_to_json(row),
    }


def ingest_ledger_push_item(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("记录必须是 JSON 对象")

    event_id = str(raw.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("event_id 必填")
    if len(event_id) > 128:
        raise ValueError("event_id 最长 128")

    existing = LedgerRecord.objects.filter(external_id=event_id).select_related("business").first()
    if existing:
        status_raw = str(raw.get("status") or "").strip().upper()
        if status_raw and status_raw != existing.status:
            sync_ledger_status_fields(existing, status_raw)
            existing.save(update_fields=["status", "settled_at"])
            return {
                "status": "updated",
                "id": existing.id,
                "event_id": event_id,
                "record": ledger_record_to_json(existing),
            }
        return {
            "status": "duplicate",
            "id": existing.id,
            "event_id": event_id,
        }

    business_name = str(raw.get("business_name") or raw.get("project") or "").strip()
    if not business_name:
        raise ValueError("business_name（项目）必填")

    book = str(raw.get("book") or "").strip().lower()
    if book and book != "ledger":
        raise ValueError("仅接受 book=ledger 的记账推送")

    status_raw = str(raw.get("status") or LedgerRecord.Status.ACTIVE).strip().upper()
    if status_raw not in {c.value for c in LedgerRecord.Status}:
        status_raw = LedgerRecord.Status.ACTIVE

    occurred = _parse_dt(raw.get("occurred_at"))
    record_at = format_beijing_datetime(occurred) if occurred else format_beijing_datetime()
    record_no = str(raw.get("record_no") or record_at)[:64]

    amount = decimal_num(raw.get("receive_amount") if raw.get("receive_amount") is not None else raw.get("amount"))
    give_amount = decimal_num(raw.get("amount_to_you") if raw.get("amount_to_you") is not None else raw.get("giveAmount"))
    take_amount = decimal_num(raw.get("amount_to_me") if raw.get("amount_to_me") is not None else raw.get("takeAmount"))
    profit = decimal_num(raw.get("profit_amount") if raw.get("profit_amount") is not None else raw.get("profit"))

    b = _ensure_business_for_project(business_name)
    row = LedgerRecord(
        id=new_uuid(),
        external_id=event_id,
        record_at=record_at,
        record_no=record_no,
        business=b,
        business_name=business_name,
        option_id=None,
        option_label="",
        amount=amount,
        give_amount=give_amount,
        take_amount=take_amount,
        profit=profit,
        employee_name=str(raw.get("employee_name") or "")[:128],
        chat_name=str(raw.get("chat_name") or "")[:128],
        status=status_raw,
        settled_at=None,
    )
    sync_ledger_status_fields(row, status_raw)

    try:
        with transaction.atomic():
            row.save()
    except IntegrityError:
        existing = LedgerRecord.objects.filter(external_id=event_id).only("id").first()
        if existing:
            return {"status": "duplicate", "id": existing.id, "event_id": event_id}
        raise

    return {"status": "created", "id": row.id, "event_id": event_id, "record": ledger_record_to_json(row)}


def ingest_ledger_pull(raw: dict) -> dict:
    """拉取记账（含状态）。

    - chat_name 有值：只拉该群
    - chat_name 为空 / * / __all__：拉全部（与后台「未清账合计」对齐）
    - 含无 external_id 的手动补记（event_id=manual-{id}）
    - status=ACTIVE 时只返回未清账（可选）
    """
    if not isinstance(raw, dict):
        raise ValueError("记录必须是 JSON 对象")
    chat_name = str(raw.get("chat_name") or "").strip()
    status_filter = str(raw.get("status") or "").strip().upper()
    qs = LedgerRecord.objects.all().order_by("record_at", "id")
    if chat_name and chat_name not in {"*", "__all__", "ALL"}:
        qs = qs.filter(chat_name=chat_name)
    if status_filter in {c.value for c in LedgerRecord.Status}:
        qs = qs.filter(status=status_filter)

    records = []
    for row in qs.iterator():
        eid = (row.external_id or "").strip() or f"manual-{row.id}"
        records.append(
            {
                "event_id": eid,
                "status": row.status or LedgerRecord.Status.ACTIVE,
                "record_no": row.record_no or "",
                "business_name": row.business_name or "",
                "chat_name": row.chat_name or "",
                "receive_amount": str(row.amount or 0),
                "amount_to_you": str(row.give_amount or 0),
                "amount_to_me": str(row.take_amount or 0),
                "profit_amount": str(row.profit or 0),
                "occurred_at": row.record_at or "",
            }
        )
    return {
        "chat_name": chat_name or "*",
        "count": len(records),
        "records": records,
    }


def ingest_ledger_delete(raw: dict) -> dict:
    """按 event_id 软删除（标 REVERSED），避免硬删后机器人无法对账。"""
    if not isinstance(raw, dict):
        raise ValueError("记录必须是 JSON 对象")
    event_id = str(raw.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("event_id 必填")
    row = LedgerRecord.objects.filter(external_id=event_id).first()
    if not row:
        return {"status": "not_found", "event_id": event_id}
    sync_ledger_status_fields(row, LedgerRecord.Status.REVERSED)
    row.save(update_fields=["status", "settled_at"])
    return {
        "status": "deleted",
        "event_id": event_id,
        "id": row.id,
        "record": ledger_record_to_json(row),
    }


def ingest_ledger_push_payload(body) -> dict:
    if not isinstance(body, dict):
        raise ValueError("请求体必须是 JSON 对象")

    action = str(body.get("action") or "").strip().lower()
    if action == "settle":
        r = ingest_ledger_settlement(body)
        return {"ok": True, "mode": "settle", **r}
    if action in {"status", "status_update"}:
        r = ingest_ledger_status_update(body)
        return {"ok": True, "mode": "status", **r}
    if action in {"pull", "sync", "list"}:
        r = ingest_ledger_pull(body)
        return {"ok": True, "mode": "pull", **r}
    if action in {"delete", "remove"}:
        r = ingest_ledger_delete(body)
        return {"ok": True, "mode": "delete", **r}

    if "items" in body:
        items = body.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("items 必须是非空数组")
        if len(items) > 100:
            raise ValueError("单次最多 100 条")
        results = []
        created = duplicate = 0
        for idx, it in enumerate(items):
            try:
                r = ingest_ledger_push_item(it)
            except ValueError as e:
                raise ValueError(f"items[{idx}]: {e}") from e
            results.append(r)
            if r["status"] == "created":
                created += 1
            else:
                duplicate += 1
        return {"ok": True, "mode": "batch", "created": created, "duplicate": duplicate, "results": results}
    if not body.get("event_id"):
        raise ValueError("缺少 event_id；批量请用 {\"items\":[...]}")
    r = ingest_ledger_push_item(body)
    return {"ok": True, "mode": "single", **r}

