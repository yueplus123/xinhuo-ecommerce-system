"""月度 GMV 目标（管理后台「资源池 → 月度目标」，仅超级管理员）。

GET   /api/admin/gmv-targets/   近 12 个月 + 下个月：目标、实际 GMV、完成度
PUT   /api/admin/gmv-targets/   {"month": "2026-12", "target": "150000"}；target 为空 = 删除该月目标
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog.models import MonthlyGmvTarget

from .data_screen import _history_month_gmv, _shift_months


class _SuperuserOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_superuser)


def _payload():
    today = timezone.localdate()
    this_month = today.replace(day=1)
    actual = {r["date"]: r["gmv"] for r in _history_month_gmv(12)}
    targets = {t.month: t for t in MonthlyGmvTarget.objects.all()}
    rows = []
    for i in range(-1, 12):  # 下个月 ~ 11 个月前
        m = _shift_months(today, -i)
        key = m.strftime("%Y-%m")
        t = targets.get(m)
        target = float(t.target) if t else None
        gmv = actual.get(key) if m <= this_month else None
        rows.append({
            "month": key,
            "is_current": m == this_month,
            "is_future": m > this_month,
            "target": target,
            "gmv": gmv,
            "done_pct": round(gmv / target * 100, 1) if (target and gmv is not None) else None,
            "updated_by": (t.updated_by.get_full_name() or t.updated_by.username) if (t and t.updated_by) else "",
        })
    return {"rows": rows}


class GmvTargetAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def get(self, request):
        return Response(_payload())

    def put(self, request):
        data = request.data or {}
        raw_month = str(data.get("month") or "").strip()
        try:
            y, m = raw_month.split("-")
            month = date(int(y), int(m), 1)
        except (ValueError, TypeError):
            return Response({"detail": "月份格式应为 YYYY-MM"}, status=400)
        raw = str(data.get("target") if data.get("target") is not None else "").strip().replace(",", "")
        if raw == "":
            MonthlyGmvTarget.objects.filter(month=month).delete()
            return Response(_payload())
        try:
            target = Decimal(raw)
        except InvalidOperation:
            return Response({"detail": "目标必须是数字"}, status=400)
        if not target.is_finite() or target <= 0 or target >= Decimal("1e12"):
            return Response({"detail": "目标必须大于 0"}, status=400)
        MonthlyGmvTarget.objects.update_or_create(
            month=month, defaults={"target": target.quantize(Decimal("0.01")), "updated_by": request.user}
        )
        return Response(_payload())
