"""SKU 详细编辑 API（替代 /backoffice 的 SKU 编辑器）：仅超级管理员。

GET  /api/manage/sku-editor/<id>/   读取完整详情 + 编辑所需的选项（标签 / 教程池 / 话术池）
POST /api/manage/sku-editor/        新建（必须带 business）
PUT  /api/manage/sku-editor/<id>/   保存（multipart：可同时上传 / 删除会员截图）
价格档与快捷话术以「整表替换」方式提交（JSON 字符串字段 price_items / quick_phrases）。
"""

import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.urls import path
from rest_framework import permissions, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog.models import (
    SKU,
    Business,
    PhrasePool,
    QuickPhrase,
    SKUImage,
    SKUPriceItem,
    Tag,
    TutorialPool,
    UsdProxyPriceTier,
)

from .upload_utils import sniff_image_ext

MAX_PRICE_ITEMS = 50
MAX_PHRASES = 100
MAX_IMAGES_PER_SKU = 20
_MONEY_MAX = Decimal("1e10")
_TUTORIAL_SEP = " / "


class IsSuperuser(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_superuser)


def _loads_list(raw, field):
    """前端以 JSON 字符串提交列表字段；也兼容直接传数组（JSON 请求）。"""
    if raw in (None, ""):
        return []
    if isinstance(raw, (list, tuple)):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            raise serializers.ValidationError({field: "格式错误"})
    if not isinstance(data, list):
        raise serializers.ValidationError({field: "必须是数组"})
    return data


def _money(v, field):
    try:
        d = Decimal(str(v).strip())
    except (InvalidOperation, AttributeError, TypeError):
        raise serializers.ValidationError({field: "金额格式错误"})
    if not d.is_finite() or d < 0 or d >= _MONEY_MAX:
        raise serializers.ValidationError({field: "金额需为 0 到 100 亿之间的数字"})
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clean_price_items(rows):
    if len(rows) > MAX_PRICE_ITEMS:
        raise serializers.ValidationError({"price_items": f"价格档最多 {MAX_PRICE_ITEMS} 条"})
    out = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise serializers.ValidationError({"price_items": "格式错误"})
        out.append(
            {
                "label": str(r.get("label") or "").strip()[:100],
                "rmb_amount": _money(r.get("rmb_amount"), "price_items"),
                "notice": str(r.get("notice") or "").strip(),
                "sort_order": i,
            }
        )
    return out


def _clean_phrases(rows):
    if len(rows) > MAX_PHRASES:
        raise serializers.ValidationError({"quick_phrases": f"快捷话术最多 {MAX_PHRASES} 条"})
    out = []
    for r in rows:
        content = str((r.get("content") if isinstance(r, dict) else r) or "").strip()
        if content:  # 空白条目直接忽略
            out.append({"content": content, "order": len(out)})
    return out


def _int_list(raw, field):
    ids = []
    for x in _loads_list(raw, field):
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            raise serializers.ValidationError({field: "ID 无效"})
    return ids


def _detail(sku, request=None):
    sku = (
        SKU.objects.select_related("business__platform")
        .prefetch_related("price_items", "quick_phrases", "channel_tags", "member_images")
        .get(pk=sku.pk)
    )
    names = [n.strip() for n in (sku.tutorial_text or "").split(_TUTORIAL_SEP) if n.strip()]
    tutorial_ids = list(TutorialPool.objects.filter(name__in=names).values_list("pk", flat=True))
    return {
        "id": sku.pk,
        "business": sku.business_id,
        "business_name": sku.business.name,
        "platform": sku.business.platform_id,
        "platform_name": sku.business.platform.name,
        "name": sku.name,
        "status": sku.status,
        "precaution": sku.precaution,
        "price_type": sku.price_type,
        "price_notice": sku.price_notice,
        "channel_tag_ids": [t.pk for t in sku.channel_tags.all()],
        "tutorial_ids": tutorial_ids,
        "price_items": [
            {"id": p.pk, "label": p.label, "rmb_amount": str(p.rmb_amount), "notice": p.notice}
            for p in sku.price_items.all()
        ],
        "quick_phrases": [{"id": q.pk, "content": q.content} for q in sku.quick_phrases.all()],
        "images": [{"id": im.pk, "url": im.image.url if im.image else ""} for im in sku.member_images.all()],
    }


def _options():
    return {
        "channel_tags": [
            {"id": t.pk, "name": t.name}
            for t in Tag.objects.filter(type=Tag.TYPE_CHANNEL).order_by("order", "id")
        ],
        "tutorials": [
            {"id": t.pk, "name": t.name} for t in TutorialPool.objects.all().order_by("sort_order", "id")
        ],
        "phrases": [
            {"id": p.pk, "name": p.name, "content": p.content}
            for p in PhrasePool.objects.all().order_by("sort_order", "id")
        ],
        "price_types": [{"value": v, "label": l} for v, l in SKU.PRICE_TYPE_CHOICES],
        "statuses": [{"value": v, "label": l} for v, l in SKU.STATUS_CHOICES],
        "usd_tiers": [
            {"id": t.pk, "usd_range": t.usd_range, "rate_percent": str(t.rate_percent)}
            for t in UsdProxyPriceTier.objects.all().order_by("sort_order", "id")
        ],
    }


def _save(request, sku):
    """校验并写入（调用方需放在 transaction.atomic 内）。sku 为 None 表示新建。"""
    data = request.data
    name = str(data.get("name") or "").strip()
    if not name:
        raise serializers.ValidationError({"name": "请填写 SKU 名称"})
    status_v = str(data.get("status") or SKU.STATUS_ON_SALE)
    if status_v not in dict(SKU.STATUS_CHOICES):
        raise serializers.ValidationError({"status": "状态无效"})
    price_type = str(data.get("price_type") or "")
    if price_type and price_type not in dict(SKU.PRICE_TYPE_CHOICES):
        raise serializers.ValidationError({"price_type": "价格类型无效"})

    if sku is None:
        try:
            business = Business.objects.get(pk=int(data.get("business")))
        except (TypeError, ValueError, Business.DoesNotExist):
            raise serializers.ValidationError({"business": "业务不存在"})
        sku = SKU(business=business)
    elif data.get("business") not in (None, ""):
        try:
            sku.business = Business.objects.get(pk=int(data.get("business")))
        except (TypeError, ValueError, Business.DoesNotExist):
            raise serializers.ValidationError({"business": "业务不存在"})

    prices = _clean_price_items(_loads_list(data.get("price_items"), "price_items"))
    phrases = _clean_phrases(_loads_list(data.get("quick_phrases"), "quick_phrases"))
    tag_ids = _int_list(data.get("channel_tag_ids"), "channel_tag_ids")
    tut_ids = _int_list(data.get("tutorial_ids"), "tutorial_ids")
    del_img_ids = _int_list(data.get("delete_image_ids"), "delete_image_ids")

    tags = list(Tag.objects.filter(pk__in=tag_ids, type=Tag.TYPE_CHANNEL))
    if len(tags) != len(set(tag_ids)):
        raise serializers.ValidationError({"channel_tag_ids": "包含无效的渠道标签"})
    tutorials = {t.pk: t for t in TutorialPool.objects.filter(pk__in=tut_ids)}
    if len(tutorials) != len(set(tut_ids)):
        raise serializers.ValidationError({"tutorial_ids": "包含无效的教程"})

    files = request.FILES.getlist("images") if hasattr(request, "FILES") else []
    keep = SKUImage.objects.filter(sku=sku).exclude(pk__in=del_img_ids).count() if sku.pk else 0
    if keep + len(files) > MAX_IMAGES_PER_SKU:
        raise serializers.ValidationError({"images": f"每个 SKU 最多 {MAX_IMAGES_PER_SKU} 张截图"})
    for f in files:
        try:
            sniff_image_ext(f)
        except ValueError as e:
            raise serializers.ValidationError({"images": str(e)})

    sku.name = name[:200]
    sku.status = status_v
    sku.precaution = str(data.get("precaution") or "")
    sku.price_type = price_type
    sku.price_notice = str(data.get("price_notice") or "")
    # 教程名称按选择顺序拼接，与旧编辑器的存储格式一致
    sku.tutorial_text = _TUTORIAL_SEP.join(tutorials[i].name for i in tut_ids if i in tutorials)[:500]
    sku.price = prices[0]["rmb_amount"] if prices else None  # 旧字段：取第一档
    sku.save()
    sku.channel_tags.set(tags)

    sku.price_items.all().delete()
    SKUPriceItem.objects.bulk_create([SKUPriceItem(sku=sku, **p) for p in prices])
    sku.quick_phrases.all().delete()
    QuickPhrase.objects.bulk_create([QuickPhrase(sku=sku, **q) for q in phrases])

    if del_img_ids:
        SKUImage.objects.filter(sku=sku, pk__in=del_img_ids).delete()
    top = sku.member_images.aggregate(m=Max("sort_order"))["m"]
    n = -1 if top is None else top
    for f in files:
        n += 1
        SKUImage.objects.create(sku=sku, image=f, sort_order=n)
    first = sku.member_images.order_by("sort_order", "id").first()
    sku.image = first.image if first else None
    sku.save(update_fields=["image"])
    return sku


class SkuEditorCreateView(APIView):
    permission_classes = [IsSuperuser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        with transaction.atomic():
            sku = _save(request, None)
        return Response({**_detail(sku), "options": _options()}, status=status.HTTP_201_CREATED)


class SkuEditorDetailView(APIView):
    permission_classes = [IsSuperuser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get(self, pk):
        try:
            return SKU.objects.get(pk=pk)
        except SKU.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        return Response({**_detail(self._get(pk)), "options": _options()})

    def put(self, request, pk):
        sku = self._get(pk)
        with transaction.atomic():
            sku = _save(request, sku)
        return Response({**_detail(sku), "options": _options()})

    patch = put


class SkuEditorOptionsView(APIView):
    """新建 SKU 时（还没有 id）获取选项。"""

    permission_classes = [IsSuperuser]

    def get(self, request):
        return Response(_options())


urlpatterns = [
    path("manage/sku-editor/options/", SkuEditorOptionsView.as_view(), name="manage-sku-editor-options"),
    path("manage/sku-editor/", SkuEditorCreateView.as_view(), name="manage-sku-editor-create"),
    path("manage/sku-editor/<int:pk>/", SkuEditorDetailView.as_view(), name="manage-sku-editor-detail"),
]
