"""日元充值汇率接口。

GET   /api/card-fx/            职员可看（游客 403）；职员端大厅顶部用
GET   /api/card-fx/settings/?factor=…  预览（不保存），仅超级管理员
PATCH /api/card-fx/settings/   改系数，仅超级管理员（管理后台「日元充值汇率」页）
"""

from __future__ import annotations

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog import card_fx

from .views import StaffOnlyPermission


class _SuperuserOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_superuser)


class CardFxAPIView(APIView):
    permission_classes = [StaffOnlyPermission]

    def get(self, request):
        return Response(card_fx.build_payload())


class CardFxSettingsAPIView(APIView):
    """GET ?factor=1.028 只预览不保存；PATCH {"factor": "1.028"} 保存。"""

    permission_classes = [_SuperuserOnly]

    def get(self, request):
        raw = request.query_params.get("factor")
        if raw in (None, ""):
            return Response(card_fx.build_payload())
        try:
            f = card_fx.parse_factor(raw)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(card_fx.build_payload(factor=f))

    def patch(self, request):
        try:
            card_fx.set_factor((request.data or {}).get("factor"), request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(card_fx.build_payload())
