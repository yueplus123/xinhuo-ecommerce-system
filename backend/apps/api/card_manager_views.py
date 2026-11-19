"""薪火卡管家（汇通卡 Chrome 插件）权限接口。

GET  /api/card-manager/me/                  插件登录后调用：我是谁、能看哪些备注关键词（游客 403）
GET  /api/card-manager/scopes/              管理后台「卡管家权限」页：所有职员及关键词（仅超级管理员）
PUT  /api/card-manager/scopes/<user_id>/    保存某个职员的关键词 {"keywords": ["冬", "苏橘"]}（仅超级管理员）

插件用的是职员端同一套账号：POST /api/auth/token/ 拿 access/refresh。
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog import card_manager
from backend.apps.catalog.roles import is_guest

from .views import StaffOnlyPermission


class _SuperuserOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_superuser)


class CardManagerMeAPIView(APIView):
    permission_classes = [StaffOnlyPermission]

    def get(self, request):
        return Response(card_manager.me_payload(request.user))


class CardManagerScopeListAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def get(self, request):
        return Response({"results": card_manager.staff_rows()})


class CardManagerScopeDetailAPIView(APIView):
    permission_classes = [_SuperuserOnly]

    def put(self, request, user_id: int):
        user = get_user_model().objects.filter(pk=user_id, is_active=True, is_staff=True).first()
        if not user or is_guest(user):
            return Response({"detail": "职员不存在或已停用"}, status=404)
        try:
            kws = card_manager.set_keywords(user, (request.data or {}).get("keywords"), request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        row = next((r for r in card_manager.staff_rows() if r["id"] == user.pk), None)
        return Response(row or {"id": user.pk, "username": user.username, "keywords": kws})
