"""教程+话术（知识库）接口，给职员端 public/knowledge.html 使用。

GET    /api/knowledge/        全部平台 + 全部条目（游客也可看）
POST   /api/knowledge/        新增（职员）
PATCH  /api/knowledge/<id>/   修改（职员）
DELETE /api/knowledge/<id>/   删除（超级管理员 / 老板 / CEO）
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog.models import KnowledgeEntry, Platform
from backend.apps.catalog.roles import is_guest

from .duty_views import is_manager
from .views import StaffOnlyPermission

KINDS = {k for k, _ in KnowledgeEntry.KIND_CHOICES}


def _name(user) -> str:
    if not user:
        return ""
    return (user.get_full_name() or "").strip() or user.username


def _entry(e: KnowledgeEntry) -> dict:
    return {
        "id": e.id,
        "platform_id": e.platform_id,
        "kind": e.kind,
        "title": e.title,
        "content": e.content,
        "url": e.url,
        "sort_order": e.sort_order,
        "updated_at": int(e.updated_at.timestamp() * 1000) if e.updated_at else None,
        "updated_by": _name(e.updated_by),
    }


def _clean(data: dict, entry: KnowledgeEntry | None = None) -> tuple[dict, str | None]:
    """校验并整理提交的字段；返回 (字段, 错误信息)。"""
    out: dict = {}
    if entry is None or "kind" in data:
        kind = str(data.get("kind") or "").strip()
        if kind not in KINDS:
            return {}, "类型只能是 问答 / 教程 / 快捷语"
        out["kind"] = kind
    if entry is None or "platform_id" in data:
        pid = data.get("platform_id")
        if pid in (None, "", 0, "0"):
            out["platform"] = None
        else:
            try:
                out["platform"] = Platform.objects.get(pk=int(pid))
            except (Platform.DoesNotExist, TypeError, ValueError):
                return {}, "平台不存在"
    for f, limit in (("title", 300), ("content", 20000), ("url", 1000)):
        if entry is None or f in data:
            v = str(data.get(f) or "").strip()
            if len(v) > limit:
                return {}, f"内容太长（最多 {limit} 字）"
            out[f] = v
    if "sort_order" in data:
        try:
            out["sort_order"] = max(0, int(data.get("sort_order") or 0))
        except (TypeError, ValueError):
            return {}, "排序必须是数字"

    kind = out.get("kind", entry.kind if entry else "")
    title = out.get("title", entry.title if entry else "")
    content = out.get("content", entry.content if entry else "")
    url = out.get("url", entry.url if entry else "")
    if kind == KnowledgeEntry.KIND_PHRASE and not title and content:
        title = out["title"] = content.replace("\n", " ")[:20]
    if not title:
        return {}, {"faq": "请填写客户的问题", "tutorial": "请填写教程名称", "phrase": "请填写快捷语"}[kind]
    if kind == KnowledgeEntry.KIND_TUTORIAL:
        if not url:
            return {}, "请填写教程链接"
        try:
            URLValidator(schemes=["http", "https"])(url)
        except ValidationError:
            return {}, "链接格式不对，要以 http:// 或 https:// 开头"
    elif url:
        try:
            URLValidator(schemes=["http", "https"])(url)
        except ValidationError:
            return {}, "链接格式不对，要以 http:// 或 https:// 开头"
    if kind in (KnowledgeEntry.KIND_FAQ, KnowledgeEntry.KIND_PHRASE) and not content:
        return {}, "请填写答案" if kind == KnowledgeEntry.KIND_FAQ else "请填写快捷语内容"
    return out, None


def _can_edit(user) -> bool:
    return bool(user and user.is_authenticated and user.is_staff and not is_guest(user))


class KnowledgeListAPIView(APIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True  # 与「业务+价格」一致，游客只读

    def get(self, request):
        platforms = [
            {"id": p.id, "name": p.name, "status": p.status}
            for p in Platform.objects.order_by("sort_order", "id")
        ]
        entries = [_entry(e) for e in KnowledgeEntry.objects.select_related("updated_by")]
        return Response({
            "platforms": platforms,
            "entries": entries,
            "can_edit": _can_edit(request.user),
            "can_delete": is_manager(request.user),
        })

    def post(self, request):
        if not _can_edit(request.user):
            return Response({"detail": "游客不能修改"}, status=status.HTTP_403_FORBIDDEN)
        fields, err = _clean(request.data or {})
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        e = KnowledgeEntry.objects.create(updated_by=request.user, **fields)
        return Response(_entry(e), status=status.HTTP_201_CREATED)


class KnowledgeDetailAPIView(APIView):
    permission_classes = [StaffOnlyPermission]

    def _get(self, pk):
        return KnowledgeEntry.objects.select_related("updated_by").filter(pk=pk).first()

    def patch(self, request, pk):
        if not _can_edit(request.user):
            return Response({"detail": "游客不能修改"}, status=status.HTTP_403_FORBIDDEN)
        e = self._get(pk)
        if not e:
            return Response({"detail": "这条内容已经不存在了"}, status=status.HTTP_404_NOT_FOUND)
        fields, err = _clean(request.data or {}, e)
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        for k, v in fields.items():
            setattr(e, k, v)
        e.updated_by = request.user
        e.save()
        return Response(_entry(e))

    def delete(self, request, pk):
        if not is_manager(request.user):
            return Response({"detail": "只有老板 / CEO / 管理员可以删除"}, status=status.HTTP_403_FORBIDDEN)
        e = self._get(pk)
        if not e:
            return Response(status=status.HTTP_204_NO_CONTENT)
        e.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
