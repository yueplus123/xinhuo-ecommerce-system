"""外部系统实时推送收款记录（对方 POST → 我方入库）。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from backend.apps.catalog.models import PAYMENT_CHANNELS, PaymentRecord

_CHANNEL_CODES = {c[0] for c in PAYMENT_CHANNELS}
_CHANNEL_ALIASES = {
    "淘宝": "千牛",
    "闲鱼/得物": "咸鱼/得物",
    "咸鱼": "咸鱼/得物",
    "闲鱼": "咸鱼/得物",
    "得物": "咸鱼/得物",
    "微信": "普通微信",
    "企业微信收款": "企业微信",
    "b站": "Bilibili(B站)",
    "bilibili": "Bilibili(B站)",
    "退款": "退款项",
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


def _normalize_channel(raw) -> str | None:
    s = str(raw or "").strip()
    if not s:
        return None
    if s in _CHANNEL_CODES:
        return s
    alias = _CHANNEL_ALIASES.get(s) or _CHANNEL_ALIASES.get(s.lower())
    if alias and alias in _CHANNEL_CODES:
        return alias
    return None


def _parse_amount(raw) -> Decimal:
    try:
        d = Decimal(str(raw).strip())
    except (InvalidOperation, AttributeError, TypeError):
        raise ValueError("amount 无效，需为数字字符串，单位：元，最多两位小数")
    if d.copy_abs().as_tuple().exponent < -2:
        raise ValueError("amount 最多两位小数")
    return d.quantize(Decimal("0.01"))


def _parse_order_count(raw) -> int:
    if raw is None or raw == "":
        return 1
    try:
        n = int(raw)
    except (TypeError, ValueError):
        raise ValueError("order_count 需为非负整数")
    if n < 0:
        raise ValueError("order_count 不能为负数")
    return n


def _parse_record_date(occurred_at, record_date) -> date:
    if record_date:
        s = str(record_date).strip()[:10]
        try:
            return date.fromisoformat(s)
        except ValueError:
            raise ValueError("record_date 格式应为 YYYY-MM-DD")
    if occurred_at:
        s = str(occurred_at).strip()
        dt = parse_datetime(s)
        if dt is None:
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("occurred_at 无法解析，请用 ISO8601，如 2026-07-30T13:00:00+08:00")
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return timezone.localtime(dt).date()
    return timezone.localdate()


def _resolve_owner(owner_username: str | None):
    User = get_user_model()
    username = (owner_username or "").strip()
    if not username:
        username = (getattr(settings, "EXTERNAL_PUSH_DEFAULT_USERNAME", "") or "").strip()
    if not username:
        raise ValueError(
            "未提供 owner_username，且服务端未配置 EXTERNAL_PUSH_DEFAULT_USERNAME"
        )
    user = User.objects.filter(username=username, is_active=True).first()
    if not user:
        raise ValueError(f"owner_username 对应用户不存在或未启用：{username}")
    if not user.is_staff:
        raise ValueError(f"owner_username 必须是职员账号：{username}")
    return user


def _item_from_payload(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("每条记录必须是 JSON 对象")
    event_id = str(raw.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("event_id 必填（对方系统内全局唯一，用于幂等）")
    if len(event_id) > 128:
        raise ValueError("event_id 最长 128 字符")

    channel = _normalize_channel(raw.get("channel"))
    if not channel:
        raise ValueError(
            f"channel 无效。允许值：{', '.join(sorted(_CHANNEL_CODES))}"
        )

    amount = _parse_amount(raw.get("amount"))
    order_count = _parse_order_count(raw.get("order_count"))
    if channel != "退款项" and amount < 0:
        raise ValueError("非退款项金额不能为负")
    if channel == "退款项" and amount < 0:
        amount = abs(amount)

    note = str(raw.get("note") or "")[:500]
    record_date = _parse_record_date(raw.get("occurred_at"), raw.get("record_date"))
    owner = _resolve_owner(raw.get("owner_username"))

    return {
        "external_id": event_id,
        "channel": channel,
        "amount": amount,
        "order_count": order_count,
        "note": note,
        "record_date": record_date,
        "user": owner,
    }


def ingest_payment_item(raw: dict) -> dict:
    """
    写入一条收款。返回:
      {"status": "created"|"duplicate", "id": int, "event_id": str}
    """
    data = _item_from_payload(raw)
    event_id = data["external_id"]

    existing = PaymentRecord.objects.filter(external_id=event_id).only("id").first()
    if existing:
        return {"status": "duplicate", "id": existing.id, "event_id": event_id}

    try:
        with transaction.atomic():
            rec = PaymentRecord.objects.create(
                external_id=event_id,
                channel=data["channel"],
                amount=data["amount"],
                order_count=data["order_count"],
                note=data["note"],
                record_date=data["record_date"],
                user=data["user"],
                created_at=timezone.now(),
            )
    except IntegrityError:
        existing = PaymentRecord.objects.filter(external_id=event_id).only("id").first()
        if existing:
            return {"status": "duplicate", "id": existing.id, "event_id": event_id}
        raise

    return {"status": "created", "id": rec.id, "event_id": event_id}


def ingest_push_payload(body) -> dict:
    """
    支持单条对象，或 {"items": [ ... ]} 批量（单次最多 100 条）。
    """
    if not isinstance(body, dict):
        raise ValueError("请求体必须是 JSON 对象")

    if "items" in body:
        items = body.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("items 必须是非空数组")
        if len(items) > 100:
            raise ValueError("单次最多推送 100 条")
        results = []
        created = duplicate = 0
        for idx, it in enumerate(items):
            try:
                r = ingest_payment_item(it)
            except ValueError as e:
                raise ValueError(f"items[{idx}]: {e}") from e
            results.append(r)
            if r["status"] == "created":
                created += 1
            else:
                duplicate += 1
        return {
            "ok": True,
            "mode": "batch",
            "created": created,
            "duplicate": duplicate,
            "results": results,
        }

    # 单条：顶层即业务字段
    if not body.get("event_id"):
        raise ValueError("缺少 event_id；批量请用 {\"items\":[...]}")
    r = ingest_payment_item(body)
    return {"ok": True, "mode": "single", **r}
