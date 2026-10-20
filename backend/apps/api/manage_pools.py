"""管理后台 API：话术池 / 教程池 / 平台标签池 / 渠道池 / 美金代付价格池 / SKU 快捷语。

替代 /backoffice 中对应的 HTML 页面（全部仅超级用户可用，与旧 superuser_required 一致）。
校验直接复用旧的 Django ModelForm，保证与旧后台规则一致。
机器人使用的只读接口（/api/tutorial-pool/ 等）不在此处，保持不变。
"""

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.http import Http404
from django.urls import path
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog.forms import (
    ChannelTagPoolForm,
    ChannelTagPoolQuickForm,
    PhrasePoolForm,
    PlatformTagPoolForm,
    PlatformTagPoolQuickForm,
    QuickPhraseForm,
    TutorialPoolForm,
    UsdProxyPriceTierForm,
)
from backend.apps.catalog.models import (
    SKU,
    ChannelTagPool,
    PhrasePool,
    PlatformTagPool,
    QuickPhrase,
    Tag,
    TutorialPool,
    UsdProxyPriceTier,
)


class SuperuserOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


# order_field：排序字段；append：新增时排到末尾（旧后台行为）；reorderable：支持拖动排序
POOLS = {
    "phrase-pool": {
        "model": PhrasePool,
        "form": PhrasePoolForm,
        "order_field": "sort_order",
        "append": True,
        "reorderable": True,
        "fields": ("name", "content", "sort_order"),
    },
    "tutorial-pool": {
        "model": TutorialPool,
        "form": TutorialPoolForm,
        "order_field": "sort_order",
        "append": True,
        "reorderable": True,
        "fields": ("name", "detail_url", "sort_order"),
    },
    "platform-tag-pool": {
        "model": PlatformTagPool,
        "form": PlatformTagPoolForm,
        "quick_form": PlatformTagPoolQuickForm,
        "order_field": "order",
        "append": True,
        "reorderable": True,
        "tag_type": Tag.TYPE_PLATFORM,
        "fields": ("name", "order"),
    },
    "channel-tag-pool": {
        "model": ChannelTagPool,
        "form": ChannelTagPoolForm,
        "quick_form": ChannelTagPoolQuickForm,
        "order_field": "order",
        "append": True,
        "reorderable": True,
        "tag_type": Tag.TYPE_CHANNEL,
        "fields": ("name", "order"),
    },
    "usd-proxy-price-pool": {
        "model": UsdProxyPriceTier,
        "form": UsdProxyPriceTierForm,
        "order_field": "sort_order",
        "append": True,
        "reorderable": True,
        "fields": ("usd_range", "rate_percent", "sort_order"),
    },
    "quick-phrases": {
        "model": QuickPhrase,
        "form": QuickPhraseForm,
        "order_field": "order",
        "append": False,
        "reorderable": False,
        "fields": ("sku", "content", "order"),
    },
}


def _cfg(key):
    cfg = POOLS.get(key)
    if cfg is None:
        raise Http404
    return cfg


def _value(obj, field):
    if field == "sku":
        return obj.sku_id
    val = getattr(obj, field)
    return float(val) if field == "rate_percent" else val


def _row(cfg, obj):
    data = {"id": obj.pk}
    for f in cfg["fields"]:
        data[f] = _value(obj, f)
    if cfg["model"] is QuickPhrase:
        sku = obj.sku
        data["sku_name"] = sku.name
        data["business_name"] = sku.business.name
        data["platform_name"] = sku.business.platform.name
        data["sku_label"] = f"{sku.business.platform.name} / {sku.business.name} / {sku.name}"
    return data


def _queryset(cfg):
    qs = cfg["model"].objects.all()
    if cfg["model"] is QuickPhrase:
        qs = qs.select_related("sku__business__platform")
    return qs.order_by(cfg["order_field"], "id")


def _form_error(form):
    parts = []
    for name, errors in form.errors.items():
        label = form.fields[name].label if name in form.fields and form.fields[name].label else name
        msg = "，".join(str(e) for e in errors)
        parts.append(msg if name == "__all__" else f"{label}：{msg}")
    return Response(
        {"detail": "；".join(parts) or "提交内容有误", "errors": form.errors.get_json_data()},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _bad(msg, code=status.HTTP_400_BAD_REQUEST):
    return Response({"detail": msg}, status=code)


def _form_data(cfg, payload, obj=None):
    """表单字段缺省值：编辑取当前值，新增取模型默认值，使局部提交也能通过校验。"""
    form_fields = cfg["form"].base_fields.keys()
    data = {}
    for f in form_fields:
        if f in payload:
            data[f] = payload[f]
        elif obj is not None:
            val = _value(obj, f)
            data[f] = val
        elif f == cfg["order_field"]:
            data[f] = 0
    return data


def _name_taken(cfg, name, exclude_pk=None):
    qs = Tag.objects.filter(type=cfg["tag_type"], name=name)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def _append_order(cfg, obj):
    field = cfg["order_field"]
    top = cfg["model"].objects.exclude(pk=obj.pk).aggregate(m=Max(field))["m"] or 0
    setattr(obj, field, top + 1)
    obj.save(update_fields=[field])


def _save_form(cfg, form, creating):
    """保存并处理标签池重名（旧后台此处会触发数据库错误，这里改为明确提示）。"""
    if "tag_type" in cfg:
        name = form.cleaned_data["name"]
        if _name_taken(cfg, name, None if creating else form.instance.pk):
            return None, _bad("名称已存在，请换一个")
    try:
        with transaction.atomic():
            obj = form.save()
            if creating and cfg["append"]:
                _append_order(cfg, obj)
    except IntegrityError:
        return None, _bad("保存失败：名称重复")
    return obj, None


class PoolListCreateView(APIView):
    permission_classes = [SuperuserOnly]

    def get(self, request, key):
        cfg = _cfg(key)
        qs = _queryset(cfg)
        if cfg["model"] is QuickPhrase:
            sku_id = request.query_params.get("sku")
            if sku_id and sku_id.isdigit():
                qs = qs.filter(sku_id=int(sku_id))
        rows = [_row(cfg, o) for o in qs]
        return Response({"count": len(rows), "results": rows, "reorderable": cfg["reorderable"]})

    def post(self, request, key):
        cfg = _cfg(key)
        form = cfg["form"](_form_data(cfg, request.data))
        if not form.is_valid():
            return _form_error(form)
        obj, err = _save_form(cfg, form, creating=True)
        if err:
            return err
        obj = _queryset(cfg).get(pk=obj.pk)
        return Response(_row(cfg, obj), status=status.HTTP_201_CREATED)


class PoolDetailView(APIView):
    permission_classes = [SuperuserOnly]

    def _get(self, cfg, pk):
        try:
            return _queryset(cfg).get(pk=pk)
        except cfg["model"].DoesNotExist:
            raise Http404

    def get(self, request, key, pk):
        cfg = _cfg(key)
        return Response(_row(cfg, self._get(cfg, pk)))

    def put(self, request, key, pk):
        cfg = _cfg(key)
        obj = self._get(cfg, pk)
        form = cfg["form"](_form_data(cfg, request.data, obj), instance=obj)
        if not form.is_valid():
            return _form_error(form)
        saved, err = _save_form(cfg, form, creating=False)
        if err:
            return err
        return Response(_row(cfg, self._get(cfg, saved.pk)))

    patch = put

    def delete(self, request, key, pk):
        cfg = _cfg(key)
        self._get(cfg, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PoolReorderView(APIView):
    """请求体 ``{"order": [id, ...]}``，必须恰好包含全部条目；按下标写入排序字段（0 起）。"""

    permission_classes = [SuperuserOnly]

    def post(self, request, key):
        cfg = _cfg(key)
        if not cfg["reorderable"]:
            raise Http404
        order = request.data.get("order") if hasattr(request.data, "get") else None
        if not isinstance(order, list) or not order:
            return _bad("缺少排序列表")
        try:
            ids = [int(x) for x in order]
        except (TypeError, ValueError):
            return _bad("无效的 ID")
        model = cfg["model"]
        existing = set(model.objects.values_list("id", flat=True))
        if set(ids) != existing or len(ids) != len(existing):
            return _bad("列表与服务器不一致，请刷新页面")
        with transaction.atomic():
            for i, pk in enumerate(ids):
                model.objects.filter(pk=pk).update(**{cfg["order_field"]: i})
        return Response({"ok": True})


class PoolQuickAddView(APIView):
    """向标签池快速追加一个标签（只填名称），对应旧的 quick-add。"""

    permission_classes = [SuperuserOnly]

    def post(self, request, key):
        cfg = _cfg(key)
        if "quick_form" not in cfg:
            raise Http404
        form = cfg["quick_form"](request.data)
        if not form.is_valid():
            return _form_error(form)
        obj, err = _save_form(cfg, form, creating=True)
        if err:
            return err
        return Response(
            {"id": obj.pk, "name": obj.name, "message": f"「{obj.name}」已加入"},
            status=status.HTTP_201_CREATED,
        )


class QuickPhraseSkuOptionsView(APIView):
    permission_classes = [SuperuserOnly]

    def get(self, request):
        skus = SKU.objects.select_related("business__platform").order_by("business__platform__name", "business__name", "name")
        return Response(
            [
                {"id": s.pk, "label": f"{s.business.platform.name} / {s.business.name} / {s.name}"}
                for s in skus
            ]
        )


urlpatterns = [
    path("manage/pools/quick-phrases/sku-options/", QuickPhraseSkuOptionsView.as_view(), name="manage-pools-sku-options"),
    path("manage/pools/<str:key>/", PoolListCreateView.as_view(), name="manage-pool-list"),
    path("manage/pools/<str:key>/reorder/", PoolReorderView.as_view(), name="manage-pool-reorder"),
    path("manage/pools/<str:key>/quick-add/", PoolQuickAddView.as_view(), name="manage-pool-quick-add"),
    path("manage/pools/<str:key>/<int:pk>/", PoolDetailView.as_view(), name="manage-pool-detail"),
]
