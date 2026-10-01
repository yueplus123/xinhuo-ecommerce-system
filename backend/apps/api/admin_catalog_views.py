from django.db import transaction
from django.db.models import Count, Prefetch, Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog.models import Business, Platform, QuickPhrase, SKU

from .admin_catalog_serializers import (
    AdminBusinessTreeSerializer,
    AdminBusinessWriteSerializer,
    AdminPlatformReorderSerializer,
    AdminPlatformWorkbenchSerializer,
    AdminPlatformWriteSerializer,
    AdminSkuTreeSerializer,
    AdminSkuWriteSerializer,
)
from .serializers import PlatformListSerializer


class AdminCatalogPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


def _platform_workbench_queryset():
    sku_qs = SKU.objects.annotate(quick_phrase_count=Count("quick_phrases")).order_by("id")
    business_qs = Business.objects.annotate(sku_count=Count("skus")).prefetch_related(
        Prefetch("skus", queryset=sku_qs)
    ).order_by("id")
    return Platform.objects.prefetch_related("platform_tags").annotate(
        business_count=Count("businesses", distinct=True),
        sku_count=Count("businesses__skus", distinct=True),
    ).prefetch_related(Prefetch("businesses", queryset=business_qs))


class AdminPlatformListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [AdminCatalogPermission]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminPlatformWriteSerializer
        return PlatformListSerializer

    def get_queryset(self):
        qs = Platform.objects.prefetch_related("platform_tags").annotate(
            business_count=Count("businesses", distinct=True),
            sku_count=Count("businesses__skus", distinct=True),
            sku_on_sale_count=Count(
                "businesses__skus",
                filter=Q(businesses__skus__status=Platform.STATUS_ON_SALE),
                distinct=True,
            ),
            sku_off_sale_count=Count(
                "businesses__skus",
                filter=Q(businesses__skus__status=Platform.STATUS_OFF_SALE),
                distinct=True,
            ),
            sku_pending_test_count=Count(
                "businesses__skus",
                filter=Q(businesses__skus__status=Platform.STATUS_PENDING_TEST),
                distinct=True,
            ),
        )
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(url__icontains=q)
                | Q(note__icontains=q)
                | Q(platform_tags__name__icontains=q)
            ).distinct()
        return qs.order_by("sort_order", "id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        platform = serializer.save()
        platform = _platform_workbench_queryset().get(pk=platform.pk)
        out = AdminPlatformWorkbenchSerializer(platform, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)


class AdminPlatformWorkbenchAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AdminCatalogPermission]
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return _platform_workbench_queryset()

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return AdminPlatformWriteSerializer
        return AdminPlatformWorkbenchSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = AdminPlatformWriteSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        instance = _platform_workbench_queryset().get(pk=instance.pk)
        return Response(AdminPlatformWorkbenchSerializer(instance, context={"request": request}).data)


class AdminPlatformReorderAPIView(APIView):
    permission_classes = [AdminCatalogPermission]

    def post(self, request):
        ser = AdminPlatformReorderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        order = ser.validated_data["order"]
        existing = set(Platform.objects.values_list("id", flat=True))
        if set(order) != existing or len(order) != len(existing):
            return Response({"detail": "排序列表与服务器不一致，请刷新后重试。"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            for i, pk in enumerate(order):
                Platform.objects.filter(pk=pk).update(sort_order=i)
        return Response({"ok": True})


class AdminBusinessCreateAPIView(generics.CreateAPIView):
    permission_classes = [AdminCatalogPermission]
    serializer_class = AdminBusinessWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = serializer.save()
        business = Business.objects.annotate(sku_count=Count("skus")).prefetch_related(
            Prefetch("skus", queryset=SKU.objects.annotate(quick_phrase_count=Count("quick_phrases")).order_by("id"))
        ).get(pk=business.pk)
        return Response(AdminBusinessTreeSerializer(business).data, status=status.HTTP_201_CREATED)


class AdminBusinessDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AdminCatalogPermission]
    serializer_class = AdminBusinessWriteSerializer
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return Business.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        business = Business.objects.annotate(sku_count=Count("skus")).prefetch_related(
            Prefetch("skus", queryset=SKU.objects.annotate(quick_phrase_count=Count("quick_phrases")).order_by("id"))
        ).get(pk=instance.pk)
        return Response(AdminBusinessTreeSerializer(business).data)


class AdminSkuCreateAPIView(generics.CreateAPIView):
    permission_classes = [AdminCatalogPermission]
    serializer_class = AdminSkuWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku = serializer.save()
        sku = SKU.objects.annotate(quick_phrase_count=Count("quick_phrases")).get(pk=sku.pk)
        return Response(AdminSkuTreeSerializer(sku).data, status=status.HTTP_201_CREATED)


class AdminSkuDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AdminCatalogPermission]
    serializer_class = AdminSkuWriteSerializer
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return SKU.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        sku = SKU.objects.annotate(quick_phrase_count=Count("quick_phrases")).get(pk=instance.pk)
        return Response(AdminSkuTreeSerializer(sku).data)


class AdminSkuDuplicateAPIView(APIView):
    permission_classes = [AdminCatalogPermission]

    def post(self, request, pk):
        source = SKU.objects.filter(pk=pk).prefetch_related("channel_tags", "quick_phrases").first()
        if source is None:
            return Response({"detail": "SKU 不存在。"}, status=status.HTTP_404_NOT_FOUND)
        base_name = (source.name or "SKU").strip() or "SKU"
        copy_name = f"{base_name}-副本"
        n = 2
        while SKU.objects.filter(business=source.business, name=copy_name).exists():
            copy_name = f"{base_name}-副本{n}"
            n += 1
        sku = SKU.objects.create(
            business=source.business,
            name=copy_name,
            status=source.status,
            price=source.price,
            price_type=source.price_type,
            price_notice=source.price_notice,
            note=source.note,
            tutorial_text=source.tutorial_text,
        )
        sku.channel_tags.set(source.channel_tags.all())
        for qp in source.quick_phrases.all():
            QuickPhrase.objects.create(sku=sku, content=qp.content, order=qp.order)
        sku = SKU.objects.annotate(quick_phrase_count=Count("quick_phrases")).get(pk=sku.pk)
        return Response(AdminSkuTreeSerializer(sku).data, status=status.HTTP_201_CREATED)
