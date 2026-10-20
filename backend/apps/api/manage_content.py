"""管理后台 API（内容类）：替代 /backoffice 中教程图文、信息页、平台账号、大厅板块的 HTML 页面。

全部仅超级管理员可用（与旧 backoffice 的 superuser_required 一致）。路径前缀：/api/manage/content/
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Max
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter

from .upload_utils import sniff_image_ext
from backend.apps.catalog.models import (
    FanboxStatsPage,
    HallBlock,
    HallBlockImage,
    PaymentTutorial,
    PictCartPage,
    PlatformAccount,
    ServiceMonitorPage,
    SharedAppleIDPage,
)


class IsSuperuser(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


def _normalize_url(value: str) -> str:
    value = (value or "").strip()
    if value and "://" not in value:
        return f"https://{value}"
    return value


def _clean_url(value, *, required: bool, required_msg: str, invalid_msg: str) -> str:
    value = _normalize_url(value)
    if not value:
        if required:
            raise serializers.ValidationError(required_msg)
        return value
    try:
        URLValidator()(value)
    except DjangoValidationError:
        raise serializers.ValidationError(invalid_msg)
    return value


# --------------------------------------------------------------------------- #
# 序列化器
# --------------------------------------------------------------------------- #
class _SortedSerializer(serializers.ModelSerializer):
    sort_order = serializers.IntegerField(read_only=True)


class PaymentTutorialManageSerializer(_SortedSerializer):
    detail_url = serializers.CharField(max_length=200)

    class Meta:
        model = PaymentTutorial
        fields = ("id", "name", "detail_url", "sort_order")

    def validate_detail_url(self, value):
        return _clean_url(value, required=True, required_msg="请输入详情链接。", invalid_msg="请输入有效的链接。")


def _link_page_serializer(model, *, required_msg):
    class Meta:
        fields = ("id", "name", "share_url", "is_active", "sort_order")

    Meta.model = model

    def validate_share_url(self, value):
        return _clean_url(value, required=True, required_msg=required_msg, invalid_msg="请输入有效的链接。")

    return type(
        f"{model.__name__}ManageSerializer",
        (_SortedSerializer,),
        {
            "share_url": serializers.CharField(max_length=200),
            "validate_share_url": validate_share_url,
            "Meta": Meta,
        },
    )


SharedAppleIDPageManageSerializer = _link_page_serializer(SharedAppleIDPage, required_msg="请输入分享页链接。")
PictCartPageManageSerializer = _link_page_serializer(PictCartPage, required_msg="请输入页面链接。")
FanboxStatsPageManageSerializer = _link_page_serializer(FanboxStatsPage, required_msg="请输入页面链接。")
ServiceMonitorPageManageSerializer = _link_page_serializer(ServiceMonitorPage, required_msg="请输入页面链接。")


class PlatformAccountManageSerializer(_SortedSerializer):
    url = serializers.CharField(max_length=200, required=False, allow_blank=True)

    class Meta:
        model = PlatformAccount
        fields = ("id", "name", "account", "password", "url", "note", "sort_order")

    def validate_url(self, value):
        return _clean_url(value, required=False, required_msg="", invalid_msg="请输入网址。")


# --------------------------------------------------------------------------- #
# 可排序资源的通用 ViewSet（列表 / 新增 / 编辑 / 删除 / 拖动排序）
# --------------------------------------------------------------------------- #
class SortableManageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsSuperuser]
    pagination_class = None
    queryset = None  # 子类设置
    serializer_class = None  # 子类设置

    def get_queryset(self):
        return self.queryset.model.objects.all().order_by("sort_order", "id")

    def perform_create(self, serializer):
        model = serializer.Meta.model
        with transaction.atomic():
            obj = serializer.save()
            max_order = model.objects.exclude(pk=obj.pk).aggregate(m=Max("sort_order"))["m"] or 0
            obj.sort_order = max_order + 1
            obj.save(update_fields=["sort_order"])

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        order = request.data.get("order")
        if not isinstance(order, list) or not order:
            return Response({"ok": False, "error": "缺少排序列表"}, status=status.HTTP_400_BAD_REQUEST)
        ids = []
        for x in order:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                return Response({"ok": False, "error": "无效的 ID"}, status=status.HTTP_400_BAD_REQUEST)
        model = self.queryset.model
        existing = set(model.objects.values_list("id", flat=True))
        if set(ids) != existing or len(ids) != len(existing):
            return Response(
                {"ok": False, "error": "列表与服务器不一致，请刷新页面"}, status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            for i, pk in enumerate(ids):
                model.objects.filter(pk=pk).update(sort_order=i)
        return Response({"ok": True})


def _sortable_viewset(model, serializer):
    return type(
        f"{model.__name__}ManageViewSet",
        (SortableManageViewSet,),
        {"queryset": model.objects.all(), "serializer_class": serializer},
    )


PaymentTutorialManageViewSet = _sortable_viewset(PaymentTutorial, PaymentTutorialManageSerializer)
SharedAppleIDPageManageViewSet = _sortable_viewset(SharedAppleIDPage, SharedAppleIDPageManageSerializer)
PictCartPageManageViewSet = _sortable_viewset(PictCartPage, PictCartPageManageSerializer)
FanboxStatsPageManageViewSet = _sortable_viewset(FanboxStatsPage, FanboxStatsPageManageSerializer)
ServiceMonitorPageManageViewSet = _sortable_viewset(ServiceMonitorPage, ServiceMonitorPageManageSerializer)
PlatformAccountManageViewSet = _sortable_viewset(PlatformAccount, PlatformAccountManageSerializer)


# --------------------------------------------------------------------------- #
# 大厅板块（含多图上传）
# --------------------------------------------------------------------------- #
class HallBlockImageManageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = HallBlockImage
        fields = ("id", "url", "sort_order")

    def get_url(self, obj):
        try:
            return obj.image.url
        except Exception:
            return ""


class HallBlockManageSerializer(serializers.ModelSerializer):
    images = HallBlockImageManageSerializer(many=True, read_only=True)
    image_count = serializers.SerializerMethodField()
    body_preview = serializers.SerializerMethodField()
    sort_order = serializers.IntegerField(min_value=0, required=False, default=0)
    is_pinned = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = HallBlock
        fields = ("id", "title", "body", "sort_order", "is_pinned", "images", "image_count", "body_preview")

    def get_image_count(self, obj):
        n = len(obj.images.all())
        if not n and obj.image:
            n = 1
        return n

    def get_body_preview(self, obj, limit=72):
        t = (obj.body or "").replace("\r", " ").replace("\n", " ").strip()
        return t[: limit - 1] + "…" if len(t) > limit else t


def _sync_legacy_image(block):
    first = block.images.order_by("sort_order", "id").first()
    block.image = first.image if first else None
    block.save(update_fields=["image"])


class HallBlockManageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsSuperuser]
    pagination_class = None
    serializer_class = HallBlockManageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return HallBlock.objects.prefetch_related("images").order_by("-is_pinned", "sort_order", "id")

    def _apply_images(self, request, block):
        delete_ids = [x for x in request.data.getlist("delete_member_image_ids")] if hasattr(
            request.data, "getlist"
        ) else list(request.data.get("delete_member_image_ids") or [])
        files = request.FILES.getlist("member_images")
        for f in files:
            try:
                sniff_image_ext(f)
            except ValueError as e:
                raise serializers.ValidationError({"member_images": str(e)})
        clean_ids = []
        for x in delete_ids:
            try:
                clean_ids.append(int(x))
            except (TypeError, ValueError):
                raise serializers.ValidationError({"delete_member_image_ids": "无效的图片 ID。"})
        if clean_ids:
            HallBlockImage.objects.filter(block=block, pk__in=clean_ids).delete()
        if files:
            max_order = block.images.aggregate(m=Max("sort_order"))["m"]
            max_order = -1 if max_order is None else max_order
            for uploaded in files:
                max_order += 1
                HallBlockImage.objects.create(block=block, image=uploaded, sort_order=max_order)
        _sync_legacy_image(block)

    def perform_create(self, serializer):
        with transaction.atomic():
            obj = serializer.save(is_active=True)
            self._apply_images(self.request, obj)

    def perform_update(self, serializer):
        with transaction.atomic():
            obj = serializer.save(is_active=True)
            self._apply_images(self.request, obj)

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        # 重新序列化以包含刚上传的配图
        obj = self.get_queryset().get(pk=resp.data["id"])
        resp.data = self.get_serializer(obj).data
        return resp

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        obj = self.get_queryset().get(pk=self.kwargs["pk"])
        resp.data = self.get_serializer(obj).data
        return resp


router = SimpleRouter()
router.register("manage/content/payment-tutorials", PaymentTutorialManageViewSet, basename="manage-payment-tutorial")
router.register(
    "manage/content/shared-apple-id-pages", SharedAppleIDPageManageViewSet, basename="manage-shared-apple-id-page"
)
router.register("manage/content/pict-cart-pages", PictCartPageManageViewSet, basename="manage-pict-cart-page")
router.register(
    "manage/content/fanbox-stats-pages", FanboxStatsPageManageViewSet, basename="manage-fanbox-stats-page"
)
router.register(
    "manage/content/service-monitor-pages",
    ServiceMonitorPageManageViewSet,
    basename="manage-service-monitor-page",
)
router.register("manage/content/platform-accounts", PlatformAccountManageViewSet, basename="manage-platform-account")
router.register("manage/content/hall-blocks", HallBlockManageViewSet, basename="manage-hall-block")

urlpatterns = router.urls
