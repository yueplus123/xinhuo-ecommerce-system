"""记账 API（原 Node 3001），并入 Django，仅 CEO 可访问。"""

from __future__ import annotations

import re

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog.ledger_models import (
    LedgerBusiness,
    LedgerBusinessOption,
    LedgerRecord,
    LedgerWalletRecord,
)
from backend.apps.catalog.ledger_utils import (
    build_stats_payload,
    business_to_json,
    decimal_num,
    format_beijing_datetime,
    ledger_record_to_json,
    new_uuid,
    parse_money_input,
    resolve_ledger_option,
    sync_ledger_status_fields,
    wallet_record_to_json,
)
from backend.apps.catalog.roles import is_ceo


class CeoOnlyPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_ceo(request.user))


def _err(msg: str, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": msg}, status=code)


class LedgerHealthAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def get(self, request):
        return Response({"ok": True})


class LedgerCatalogAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def get(self, request):
        businesses = LedgerBusiness.objects.prefetch_related("options").order_by("name", "id")
        return Response({"businesses": [business_to_json(b) for b in businesses]})

    def post(self, request):
        name = request.data.get("name")
        if not name or not isinstance(name, str):
            return _err("缺少业务名称")
        b = LedgerBusiness.objects.create(id=new_uuid(), name=name.strip())
        return Response(business_to_json(b))


class LedgerCatalogBusinessDetailAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def put(self, request, pk):
        b = LedgerBusiness.objects.filter(pk=pk).first()
        if not b:
            return _err("未找到业务", status.HTTP_404_NOT_FOUND)
        name = request.data.get("name")
        if name is not None and isinstance(name, str):
            b.name = name.strip()
            b.save(update_fields=["name"])
        return Response(business_to_json(LedgerBusiness.objects.prefetch_related("options").get(pk=pk)))

    def delete(self, request, pk):
        b = LedgerBusiness.objects.filter(pk=pk).first()
        if not b:
            return _err("未找到业务", status.HTTP_404_NOT_FOUND)
        b.delete()
        return Response({"ok": True})


class LedgerCatalogOptionAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def post(self, request, bid):
        label = request.data.get("label")
        if not label or not isinstance(label, str):
            return _err("缺少二级选项文案")
        b = LedgerBusiness.objects.filter(pk=bid).first()
        if not b:
            return _err("未找到业务", status.HTTP_404_NOT_FOUND)
        o = LedgerBusinessOption.objects.create(id=new_uuid(), business=b, label=label.strip())
        return Response({"id": o.id, "label": o.label})

    def put(self, request, bid, oid):
        label = request.data.get("label")
        if not label or not isinstance(label, str):
            return _err("缺少二级选项文案")
        o = LedgerBusinessOption.objects.filter(pk=oid, business_id=bid).first()
        if not o:
            return _err("未找到选项", status.HTTP_404_NOT_FOUND)
        o.label = label.strip()
        o.save(update_fields=["label"])
        return Response({"id": o.id, "label": o.label})

    def delete(self, request, bid, oid):
        o = LedgerBusinessOption.objects.filter(pk=oid, business_id=bid).first()
        if not o:
            return _err("未找到选项", status.HTTP_404_NOT_FOUND)
        o.delete()
        return Response({"ok": True})


def _ensure_flat_business_for_import(name: str) -> LedgerBusiness:
    raw = (name or "").strip() or "未命名"
    b = LedgerBusiness.objects.filter(name=raw).prefetch_related("options").first()
    if b and not b.options.exists():
        return b
    if b and b.options.exists():
        for i in range(1, 500):
            alt = f"{raw}（导入{i}）"
            c = LedgerBusiness.objects.filter(name=alt).prefetch_related("options").first()
            if c and not c.options.exists():
                return c
            if not c:
                return LedgerBusiness.objects.create(id=new_uuid(), name=alt)
    if not b:
        return LedgerBusiness.objects.create(id=new_uuid(), name=raw)
    return LedgerBusiness.objects.create(
        id=new_uuid(),
        name=f"{raw}·{new_uuid()[:8]}",
    )


class LedgerListAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def get(self, request):
        from django.db.models import Q

        # 后台「删除」改为软删除(REVERSED)，列表默认不展示，避免机器人查询仍读到旧数据时对不上
        qs = (
            LedgerRecord.objects.select_related("business")
            .exclude(status=LedgerRecord.Status.REVERSED)
            .order_by("-record_at", "-id")
        )
        q = (request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(business_name__icontains=q)
                | Q(option_label__icontains=q)
                | Q(employee_name__icontains=q)
                | Q(chat_name__icontains=q)
                | Q(record_no__icontains=q)
                | Q(record_at__icontains=q)
            )
        return Response([ledger_record_to_json(r) for r in qs])

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        project = str(data.get("businessName") or data.get("projectName") or "").strip()
        business_id = data.get("businessId")

        if project:
            b = _ensure_flat_business_for_import(project)
            resolved = {"option_id": None, "option_label": ""}
            business_name = project
        elif business_id:
            b = LedgerBusiness.objects.filter(pk=business_id).prefetch_related("options").first()
            if not b:
                return _err("业务不存在")
            resolved = resolve_ledger_option(b, data.get("optionId"))
            if resolved.get("error"):
                return _err(resolved["error"])
            business_name = b.name
        else:
            return _err("请填写项目名")

        record_at = str(data.get("recordAt") or format_beijing_datetime())
        record_no = str(data.get("recordNo") or record_at)[:64]
        employee_name = str(data.get("employeeName") or "")[:128]
        chat_name = str(data.get("chatName") or "")[:128]
        if not employee_name or not chat_name:
            return _err("请选择提交人与群")

        row = LedgerRecord.objects.create(
            id=new_uuid(),
            record_at=record_at,
            record_no=record_no,
            business=b,
            business_name=business_name,
            option_id=resolved["option_id"],
            option_label=resolved["option_label"],
            amount=decimal_num(data.get("amount")),
            give_amount=decimal_num(data.get("giveAmount")),
            take_amount=decimal_num(data.get("takeAmount")),
            profit=decimal_num(data.get("profit")),
            employee_name=employee_name,
            chat_name=chat_name,
            status=LedgerRecord.Status.ACTIVE,
            settled_at=None,
        )
        return Response(ledger_record_to_json(row))


class LedgerDetailAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def put(self, request, pk):
        row = LedgerRecord.objects.filter(pk=pk).select_related("business").first()
        if not row:
            return _err("未找到记录", status.HTTP_404_NOT_FOUND)
        data = request.data if isinstance(request.data, dict) else {}
        project = str(data.get("businessName") or data.get("projectName") or "").strip()
        business_id = data.get("businessId")

        if project:
            b = _ensure_flat_business_for_import(project)
            resolved = {"option_id": None, "option_label": ""}
            business_name = project
        elif business_id:
            b = LedgerBusiness.objects.filter(pk=business_id).prefetch_related("options").first()
            if not b:
                return _err("业务不存在")
            resolved = resolve_ledger_option(b, data.get("optionId"))
            if resolved.get("error"):
                return _err(resolved["error"])
            business_name = b.name
        else:
            b = row.business
            resolved = {"option_id": row.option_id, "option_label": row.option_label or ""}
            business_name = row.business_name

        row.record_at = str(data.get("recordAt", row.record_at))
        if data.get("recordNo") is not None:
            row.record_no = str(data.get("recordNo") or row.record_at)[:64]
        row.business = b
        row.business_name = business_name
        row.option_id = resolved["option_id"]
        row.option_label = resolved["option_label"]
        row.amount = decimal_num(data.get("amount"))
        row.give_amount = decimal_num(data.get("giveAmount"))
        row.take_amount = decimal_num(data.get("takeAmount"))
        row.profit = decimal_num(data.get("profit"))
        if data.get("employeeName") is not None:
            row.employee_name = str(data.get("employeeName") or "")[:128]
        if data.get("chatName") is not None:
            row.chat_name = str(data.get("chatName") or "")[:128]
        row.save()
        return Response(ledger_record_to_json(row))

    def delete(self, request, pk):
        row = LedgerRecord.objects.filter(pk=pk).first()
        if not row:
            return _err("未找到记录", status.HTTP_404_NOT_FOUND)
        # 软删除：保留 external_id，机器人查询前 pull 可同步为 REVERSED
        sync_ledger_status_fields(row, LedgerRecord.Status.REVERSED)
        row.save(update_fields=["status", "settled_at"])
        return Response({"ok": True, "status": LedgerRecord.Status.REVERSED, "externalId": row.external_id})


class LedgerSettleAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def patch(self, request, pk):
        row = LedgerRecord.objects.filter(pk=pk).first()
        if not row:
            return _err("未找到记录", status.HTTP_404_NOT_FOUND)
        t = request.data.get("settledAt")
        row.settled_at = str(t) if t is not None else format_beijing_datetime()
        sync_ledger_status_fields(row, LedgerRecord.Status.PROCESSED)
        row.save(update_fields=["settled_at", "status"])
        return Response(ledger_record_to_json(row))


class LedgerStatusAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def patch(self, request, pk):
        row = LedgerRecord.objects.filter(pk=pk).first()
        if not row:
            return _err("未找到记录", status.HTTP_404_NOT_FOUND)
        status_raw = str(request.data.get("status") or "").strip().upper()
        allowed = {c.value for c in LedgerRecord.Status}
        if status_raw not in allowed:
            return _err(f"status 无效，允许：{', '.join(sorted(allowed))}")
        sync_ledger_status_fields(row, status_raw)
        row.save(update_fields=["status", "settled_at"])
        return Response(ledger_record_to_json(row))


class LedgerBulkStatusAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        ids = data.get("ids")
        status_raw = str(data.get("status") or "").strip().upper()
        allowed = {c.value for c in LedgerRecord.Status}
        if status_raw not in allowed:
            return _err(f"status 无效，允许：{', '.join(sorted(allowed))}")
        if not isinstance(ids, list) or not ids:
            return _err("ids 须为非空数组")
        updated = 0
        for pk in ids[:500]:
            row = LedgerRecord.objects.filter(pk=str(pk)).first()
            if not row:
                continue
            sync_ledger_status_fields(row, status_raw)
            row.save(update_fields=["status", "settled_at"])
            updated += 1
        return Response({"ok": True, "updated": updated})


class LedgerMetaAPIView(APIView):
    """提交人 / 群 下拉建议（来自历史记录）。"""

    permission_classes = [CeoOnlyPermission]

    def get(self, request):
        employees = (
            LedgerRecord.objects.exclude(employee_name="")
            .values_list("employee_name", flat=True)
            .distinct()
            .order_by("employee_name")[:200]
        )
        chats = (
            LedgerRecord.objects.exclude(chat_name="")
            .values_list("chat_name", flat=True)
            .distinct()
            .order_by("chat_name")[:200]
        )
        return Response({"employees": list(employees), "chats": list(chats)})


def _normalize_legacy_record_at(s: str) -> str:
    t = (s or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", t):
        return t
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?", t)
    if m:
        pad = lambda x: str(x).zfill(2)
        sec = pad(m.group(6)) if m.group(6) else "00"
        return f"{m.group(1)}-{pad(m.group(2))}-{pad(m.group(3))} {pad(m.group(4))}:{m.group(5)}:{sec}"
    return t


class LedgerBatchImportAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def post(self, request):
        rows = request.data.get("rows")
        if not isinstance(rows, list):
            return _err("rows 须为数组")
        if len(rows) > 12000:
            return _err("单次最多 12000 条")
        count = 0
        skipped = 0
        warnings: list[str] = []
        to_create: list[LedgerRecord] = []
        for raw in rows:
            if not raw or not isinstance(raw, dict):
                skipped += 1
                continue
            item = str(raw.get("businessName") or raw.get("item") or "").strip()
            record_at_raw = str(raw.get("recordAt") or raw.get("time") or "").strip()
            if not item or not record_at_raw:
                skipped += 1
                continue
            record_at = _normalize_legacy_record_at(record_at_raw)
            if not record_at:
                skipped += 1
                continue
            b = _ensure_flat_business_for_import(item)
            settled_at = None
            if raw.get("settled") is True:
                settled_at = record_at
            elif raw.get("settledAt") not in (None, False, True, ""):
                settled_at = str(raw.get("settledAt"))
            elif "清算" in str(raw.get("status") or ""):
                settled_at = record_at
            to_create.append(
                LedgerRecord(
                    id=new_uuid(),
                    record_at=record_at,
                    business=b,
                    business_name=b.name,
                    option_id=None,
                    option_label="",
                    amount=parse_money_input(raw.get("amount")),
                    give_amount=parse_money_input(raw.get("giveAmount") or raw.get("give")),
                    take_amount=parse_money_input(raw.get("takeAmount") or raw.get("take")),
                    profit=parse_money_input(raw.get("profit")),
                    settled_at=settled_at,
                )
            )
            count += 1
        if to_create:
            LedgerRecord.objects.bulk_create(to_create, batch_size=500)
        return Response({"ok": True, "count": count, "skipped": skipped, "warnings": warnings})


class WalletListAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def get(self, request):
        rows = LedgerWalletRecord.objects.order_by("record_at", "id")
        return Response([wallet_record_to_json(r) for r in rows])

    def post(self, request):
        data = request.data
        w = decimal_num(data.get("wechat"))
        a = decimal_num(data.get("alipay"))
        c = decimal_num(data.get("card"))
        p = decimal_num(data.get("pocket"))
        row = LedgerWalletRecord.objects.create(
            id=new_uuid(),
            record_at=str(data.get("recordAt") or ""),
            wechat=w,
            alipay=a,
            card=c,
            pocket=p,
            total=w + a + c + p,
        )
        return Response(wallet_record_to_json(row))


class WalletDetailAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def put(self, request, pk):
        row = LedgerWalletRecord.objects.filter(pk=pk).first()
        if not row:
            return _err("未找到记录", status.HTTP_404_NOT_FOUND)
        data = request.data
        w = decimal_num(data.get("wechat"))
        a = decimal_num(data.get("alipay"))
        c = decimal_num(data.get("card"))
        p = decimal_num(data.get("pocket"))
        row.record_at = str(data.get("recordAt", row.record_at))
        row.wechat = w
        row.alipay = a
        row.card = c
        row.pocket = p
        row.total = w + a + c + p
        row.save()
        return Response(wallet_record_to_json(row))

    def delete(self, request, pk):
        row = LedgerWalletRecord.objects.filter(pk=pk).first()
        if not row:
            return _err("未找到记录", status.HTTP_404_NOT_FOUND)
        row.delete()
        return Response({"ok": True})


class LedgerStatsAPIView(APIView):
    permission_classes = [CeoOnlyPermission]

    def get(self, request):
        return Response(build_stats_payload())
