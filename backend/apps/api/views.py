from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .api_key import api_key_ok, configured_api_key
from backend.apps.catalog.payment_records import (
    filtered_payment_records_api_qs,
    payment_records_xlsx_response,
)
from backend.apps.catalog.roles import is_guest
from backend.apps.catalog.models import (
    PAYMENT_CHANNELS,
    HallBlock,
    PaymentBatchSubmitKey,
    PaymentRecord,
    PaymentRecordImage,
    PaymentTutorial,
    PhrasePool,
    ChannelTagPool,
    Platform,
    PlatformTagPool,
    PlatformAccount,
    SharedAppleIDPage,
    PictCartPage,
    FanboxStatsPage,
    ServiceMonitorPage,
    Business,
    SKU,
    SubscriptionPlatformOption,
    SubscriptionReminder,
    MaterialRenewal,
    CommonCard,
    CommonAccount,
    StaffLoginLog,
    StaffLoginMeta,
    TutorialPool,
    UsdProxyPriceTier,
)

from .data_screen import build_data_screen_payload
from .jwt_serializers import StaffTokenObtainPairSerializer, StaffTokenRefreshSerializer
from .serializers import (
    HallBlockSerializer,
    PaymentRecordSerializer,
    PaymentTutorialSerializer,
    PhrasePoolSerializer,
    ChannelTagPoolSerializer,
    PlatformAccountSerializer,
    PlatformDetailSerializer,
    PlatformListSerializer,
    PlatformTagPoolSerializer,
    SharedAppleIDPageSerializer,
    PictCartPageSerializer,
    FanboxStatsPageSerializer,
    ServiceMonitorPageSerializer,
    SubscriptionPlatformOptionSerializer,
    SubscriptionReminderSerializer,
    MaterialRenewalSerializer,
    CommonCardSerializer,
    CommonAccountSerializer,
    TutorialPoolSerializer,
    UsdProxyPriceTierSerializer,
    UserSerializer,
    StaffLoginLogSerializer,
)


class StaffOnlyPermission(IsAuthenticated):
    """职员可访问；游客仅可访问标记了 guest_allowed=True 的视图。"""

    def has_permission(self, request, view):
        if not (super().has_permission(request, view) and bool(request.user and request.user.is_staff)):
            return False
        if is_guest(request.user) and not getattr(view, "guest_allowed", False):
            return False
        return True


def _parse_next_reminder_at(raw):
    """解析 YYYY-MM-DD（或旧版带时间的字符串）为「提醒日期」（按项目时区落到日历日）。"""
    raw = (raw or "").strip()
    if not raw:
        return None
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        day_part = raw[:10]
        try:
            return datetime.strptime(day_part, "%Y-%m-%d").date()
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return timezone.localtime(dt).date()


class SubscriptionPlatformOptionViewSet(viewsets.ModelViewSet):
    """订阅平台下拉项：职员可增删改；删除时若仍被订阅提醒引用则拒绝。"""

    permission_classes = [StaffOnlyPermission]
    serializer_class = SubscriptionPlatformOptionSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return SubscriptionPlatformOption.objects.all().order_by("sort_order", "id")

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "该平台选项仍被订阅提醒引用，请先修改或删除相关提醒后再删除此选项。"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SubscriptionReminderAccessPermission(permissions.BasePermission):
    """职员仅能访问自己的记录；超级管理员可访问全部（便于以后扩展，日常以后台「订阅提醒管理」为主）。"""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_staff and not is_guest(u))

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj.user_id == request.user.pk


class SubscriptionReminderPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = None


class SubscriptionReminderViewSet(viewsets.ModelViewSet):
    permission_classes = [SubscriptionReminderAccessPermission]
    serializer_class = SubscriptionReminderSerializer
    pagination_class = SubscriptionReminderPagination
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = SubscriptionReminder.objects.select_related("user", "platform_option").all()
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(wechat_label__icontains=q)
                | Q(platform_option__name__icontains=q)
                | Q(remark__icontains=q)
            )
        return qs.order_by("next_reminder_at", "id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="mark-renewed")
    def mark_renewed(self, request, pk=None):
        """客户续费后：指定下一次提醒时间，并记录登记时间。"""
        obj = self.get_object()
        raw = (request.data.get("next_reminder_at") or request.data.get("next_reminder_date") or "").strip()
        parsed = _parse_next_reminder_at(raw)
        if not parsed:
            return Response(
                {"detail": "请提供 next_reminder_at（格式 YYYY-MM-DD，仅日期）。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.next_reminder_at = parsed
        obj.last_renewed_at = timezone.now()
        obj.save()
        return Response(SubscriptionReminderSerializer(obj).data)


def _add_months(d, months: int):
    import calendar
    from datetime import date

    m0 = d.month - 1 + months
    y = d.year + m0 // 12
    m = m0 % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def _advance_due_date(obj: MaterialRenewal, from_date=None):
    from datetime import timedelta

    base = from_date or obj.next_due_at
    if obj.cycle_type == MaterialRenewal.CYCLE_MONTHLY:
        return _add_months(base, 1)
    if obj.cycle_type == MaterialRenewal.CYCLE_YEARLY:
        return _add_months(base, 12)
    days = int(obj.cycle_days or 0)
    if days < 1:
        raise ValueError("自定义天数无效")
    return base + timedelta(days=days)


class MaterialRenewalPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = None


class MaterialRenewalViewSet(viewsets.ModelViewSet):
    """公司物料续费台账：全体职员共享读写（非游客）。"""

    permission_classes = [StaffOnlyPermission]
    serializer_class = MaterialRenewalSerializer
    pagination_class = MaterialRenewalPagination
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = MaterialRenewal.objects.all()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(category__icontains=q) | Q(remark__icontains=q))
        active = (self.request.GET.get("active") or "").strip().lower()
        if active in ("1", "true", "yes"):
            qs = qs.filter(is_active=True)
        elif active in ("0", "false", "no"):
            qs = qs.filter(is_active=False)
        return qs.order_by("next_due_at", "id")

    @action(detail=True, methods=["post"], url_path="mark-renewed")
    def mark_renewed(self, request, pk=None):
        """登记续费：可手填下次到期日，否则按周期自动顺延。"""
        obj = self.get_object()
        raw = (request.data.get("next_due_at") or "").strip()
        if raw:
            parsed = _parse_next_reminder_at(raw)
            if not parsed:
                return Response(
                    {"detail": "请提供 next_due_at（格式 YYYY-MM-DD）。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            obj.next_due_at = parsed
        else:
            try:
                obj.next_due_at = _advance_due_date(obj)
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        obj.last_renewed_at = timezone.now()
        obj.save(update_fields=["next_due_at", "last_renewed_at", "updated_at"])
        return Response(MaterialRenewalSerializer(obj).data)


class CommonCardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class CommonCardViewSet(viewsets.ModelViewSet):
    """常用卡：全体职员（含游客）共享增删改查。"""

    permission_classes = [StaffOnlyPermission]
    guest_allowed = True
    serializer_class = CommonCardSerializer
    pagination_class = CommonCardPagination
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = CommonCard.objects.all()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(platform__icontains=q)
                | Q(card_number__icontains=q)
                | Q(expiry__icontains=q)
                | Q(remark__icontains=q)
            )
        return qs.order_by("-updated_at", "id")


class CommonAccountPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CommonAccountViewSet(viewsets.ModelViewSet):
    """常用卡页内账号密码小表：全体职员（含游客）共享增删改查。"""

    permission_classes = [StaffOnlyPermission]
    guest_allowed = True
    serializer_class = CommonAccountSerializer
    pagination_class = CommonAccountPagination
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = CommonAccount.objects.all()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(platform__icontains=q)
                | Q(account__icontains=q)
                | Q(password__icontains=q)
                | Q(remark__icontains=q)
            )
        return qs.order_by("-updated_at", "id")


class ApiTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = StaffTokenObtainPairSerializer


class ApiTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    serializer_class = StaffTokenRefreshSerializer


class MeAPIView(APIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True

    def get(self, request):
        # 最近登录 IP/市 仅在签发 token、刷新 token 与 Django 会话登录时写入，避免前端轮询 /me/ 误刷记录与地理接口。
        u = (
            get_user_model()
            .objects.select_related("staff_login_meta")
            .get(pk=request.user.pk)
        )
        return Response(UserSerializer(u, context={"request": request}).data)


class MeAvatarAPIView(APIView):
    """上传/清除当前职员头像。支持 multipart file 或 JSON base64。"""

    permission_classes = [StaffOnlyPermission]
    guest_allowed = True

    def post(self, request):
        import base64
        import uuid

        from django.core.files.base import ContentFile

        meta, _ = StaffLoginMeta.objects.get_or_create(user_id=request.user.pk)
        uploaded = request.FILES.get("avatar") or request.FILES.get("file")
        if uploaded:
            if uploaded.size > 2 * 1024 * 1024:
                return Response({"detail": "头像不能超过 2MB"}, status=status.HTTP_400_BAD_REQUEST)
            if meta.avatar:
                meta.avatar.delete(save=False)
            meta.avatar.save(uploaded.name, uploaded, save=True)
        else:
            raw = request.data.get("avatar") or request.data.get("image") or ""
            if not isinstance(raw, str) or not raw.startswith("data:image"):
                return Response(
                    {"detail": "请上传图片文件或 base64 图片"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                header, b64 = raw.split(",", 1)
                ext = "png"
                if "jpeg" in header or "jpg" in header:
                    ext = "jpg"
                elif "webp" in header:
                    ext = "webp"
                data = base64.b64decode(b64)
            except Exception:
                return Response({"detail": "图片数据无效"}, status=status.HTTP_400_BAD_REQUEST)
            if len(data) > 2 * 1024 * 1024:
                return Response({"detail": "头像不能超过 2MB"}, status=status.HTTP_400_BAD_REQUEST)
            if meta.avatar:
                meta.avatar.delete(save=False)
            meta.avatar.save(f"{uuid.uuid4().hex}.{ext}", ContentFile(data), save=True)

        u = get_user_model().objects.select_related("staff_login_meta").get(pk=request.user.pk)
        return Response(UserSerializer(u, context={"request": request}).data)

    def delete(self, request):
        meta = StaffLoginMeta.objects.filter(user_id=request.user.pk).first()
        if meta and meta.avatar:
            meta.avatar.delete(save=False)
            meta.avatar = None
            meta.save(update_fields=["avatar"])
        u = get_user_model().objects.select_related("staff_login_meta").get(pk=request.user.pk)
        return Response(UserSerializer(u, context={"request": request}).data)


class MeLoginLogsAPIView(APIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True

    def get(self, request):
        since = timezone.now() - timedelta(days=30)
        logs = (
            StaffLoginLog.objects.filter(user=request.user, logged_at__gte=since)
            .order_by("-logged_at", "-id")[:200]
        )
        return Response(StaffLoginLogSerializer(logs, many=True).data)


class PlatformListAPIView(generics.ListAPIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True
    serializer_class = PlatformListSerializer

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
        status_val = (self.request.GET.get("status") or "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(url__icontains=q)
                | Q(platform_tags__name__icontains=q)
                | Q(businesses__name__icontains=q)
                | Q(businesses__skus__name__icontains=q)
                | Q(businesses__skus__note__icontains=q)
                | Q(businesses__skus__tutorial_text__icontains=q)
                | Q(businesses__skus__quick_phrases__content__icontains=q)
            ).distinct()
        return qs.order_by("sort_order", "id")


def _platforms_filtered_queryset(request):
    """与平台列表相同的关键词 / 状态筛选。"""
    qs = Platform.objects.all()
    q = (request.GET.get("q") or "").strip()
    status_val = (request.GET.get("status") or "").strip()
    if status_val:
        qs = qs.filter(status=status_val)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(url__icontains=q)
            | Q(platform_tags__name__icontains=q)
            | Q(businesses__name__icontains=q)
            | Q(businesses__skus__name__icontains=q)
            | Q(businesses__skus__note__icontains=q)
            | Q(businesses__skus__tutorial_text__icontains=q)
            | Q(businesses__skus__quick_phrases__content__icontains=q)
        ).distinct()
    return qs.order_by("sort_order", "id")


class PlatformBusinessExportAPIView(APIView):
    """导出当前筛选下的在售业务：每行「平台名----业务名」；禁售/待测试不导出。"""

    permission_classes = [StaffOnlyPermission]
    guest_allowed = True

    def get(self, request):
        from django.http import HttpResponse
        from urllib.parse import quote

        # 仅在售业务；禁售 / 待测试（测试）一律不导出
        on_sale_businesses = Business.objects.filter(status=Business.STATUS_ON_SALE).order_by("id")
        platforms = _platforms_filtered_queryset(request).prefetch_related(
            Prefetch("businesses", queryset=on_sale_businesses)
        )
        lines = []
        for p in platforms:
            # 平台本身非在售时跳过（与业务规则一致）
            if getattr(p, "status", None) != Platform.STATUS_ON_SALE:
                continue
            pname = (p.name or "").strip()
            for b in p.businesses.all():
                bname = (b.name or "").strip()
                if not pname and not bname:
                    continue
                lines.append(f"{pname}----{bname}")
        body = "\n".join(lines)
        if body:
            body += "\n"
        filename = "薪火business.txt"
        resp = HttpResponse(body.encode("utf-8"), content_type="text/plain; charset=utf-8")
        # ASCII fallback + RFC 5987 for Chinese filename
        resp["Content-Disposition"] = (
            f"attachment; filename=\"xinhuo-business.txt\"; filename*=UTF-8''{quote(filename)}"
        )
        return resp


class PlatformDetailAPIView(generics.RetrieveAPIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True
    serializer_class = PlatformDetailSerializer

    def get_queryset(self):
        return Platform.objects.prefetch_related(
            "platform_tags",
            Prefetch(
                "businesses",
                queryset=Business.objects.prefetch_related(
                    "skus__quick_phrases",
                    "skus__channel_tags",
                    "skus__price_items",
                    "skus__member_images",
                ).order_by("id"),
            ),
        )


def _payment_order_datetime(month_day: str):
    """
    解析批量录入的订单日期（MM-DD）。
    年份与时分秒取提交当下的本地时间。
    """
    now = timezone.localtime(timezone.now())
    raw = (month_day or "").strip()
    if not raw:
        return now.replace(microsecond=0)
    try:
        month_s, day_s = raw.split("-", 1)
        month, day = int(month_s), int(day_s)
        return now.replace(month=month, day=day, microsecond=0)
    except (ValueError, TypeError, OverflowError):
        return now.replace(microsecond=0)


class PaymentRecordPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class PaymentRecordListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [StaffOnlyPermission]
    serializer_class = PaymentRecordSerializer
    pagination_class = PaymentRecordPagination

    def get_queryset(self):
        return filtered_payment_records_api_qs(self.request, prefetch_images=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentBatchSubmitAPIView(APIView):
    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        batch_id = (request.POST.get("batch_id") or "").strip()[:64]
        if batch_id:
            try:
                PaymentBatchSubmitKey.objects.create(user=request.user, batch_id=batch_id)
            except IntegrityError:
                return Response(
                    {"created": 0, "duplicate": True, "detail": "该批次已提交，请勿重复点击"},
                    status=status.HTTP_409_CONFLICT,
                )

        created = 0
        channels = request.POST.getlist("channels")
        for idx, channel in enumerate(channels):
            try:
                order_count = int(request.POST.get(f"order_count_{idx}", "0") or "0")
            except (TypeError, ValueError):
                order_count = 0
            amount_raw = request.POST.get(f"amount_{idx}", "0") or "0"
            try:
                amount_val = float(amount_raw)
            except (TypeError, ValueError):
                amount_val = 0.0
            note = request.POST.get(f"note_{idx}", "")[:500]
            if order_count <= 0 and amount_val <= 0:
                continue
            order_md = request.POST.get(f"order_md_{idx}", "")
            order_at = _payment_order_datetime(order_md)
            submit_at = timezone.now()
            rec = PaymentRecord.objects.create(
                channel=channel,
                order_count=order_count,
                amount=amount_val,
                note=note,
                user=request.user,
                record_date=order_at.date(),
                created_at=submit_at,
            )
            files = request.FILES.getlist(f"screenshots_{idx}")
            if files:
                rec.screenshot = files[0]
                rec.save(update_fields=["screenshot"])
                for i, f in enumerate(files[1:], start=1):
                    PaymentRecordImage.objects.create(payment_record=rec, image=f, sort_order=i)
            created += 1
        return Response({"created": created, "duplicate": False})


class PaymentRecordExportAPIView(APIView):
    permission_classes = [StaffOnlyPermission]

    def get(self, request):
        qs = filtered_payment_records_api_qs(request, prefetch_images=False)
        return payment_records_xlsx_response(qs)


class PaymentMetaAPIView(APIView):
    permission_classes = [StaffOnlyPermission]

    def get(self, request):
        return Response({"channels": PAYMENT_CHANNELS})


class ExternalPaymentPushAPIView(APIView):
    """外部系统实时推送收款：API Key 鉴权，event_id 幂等。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not api_key_ok(request):
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"ok": True, "service": "external-payment-push"})

    def post(self, request):
        from .external_payment_push import ingest_push_payload

        if not api_key_ok(request):
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            result = ingest_push_payload(request.data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # 单条新建用 201；重复或批量统一 200
        if result.get("mode") == "single" and result.get("status") == "created":
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_200_OK)


class ExternalBotProductQueryAPIView(APIView):
    """微信机器人查商品：API Key 鉴权；仅返回平台名 + 商品名。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        from .bot_product_query import format_bot_product_reply, query_bot_products

        if not api_key_ok(request):
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)

        q = (request.GET.get("q") or request.GET.get("keyword") or "").strip()
        platform = (request.GET.get("platform") or "").strip()
        # 勿用 format=：DRF 会当成内容协商导致 404
        fmt = (request.GET.get("as") or request.GET.get("reply") or "").strip().lower()
        on_sale = (request.GET.get("on_sale") or "1").strip() not in {"0", "false", "no"}
        try:
            limit = int(request.GET.get("limit") or 50)
        except (TypeError, ValueError):
            return Response({"detail": "limit 无效"}, status=status.HTTP_400_BAD_REQUEST)

        data = query_bot_products(q=q, platform=platform, limit=limit, on_sale_only=on_sale)
        if fmt in {"text", "plain", "reply", "1", "true"}:
            return Response(
                {"ok": True, "text": format_bot_product_reply(data), "count": data["count"]}
            )
        return Response(data)

    def post(self, request):
        """兼容 BOT 用 POST body：{"q":"关键词"}。"""
        from .bot_product_query import format_bot_product_reply, query_bot_products

        if not api_key_ok(request):
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)

        body = request.data if isinstance(request.data, dict) else {}
        q = str(body.get("q") or body.get("keyword") or request.GET.get("q") or "").strip()
        platform = str(body.get("platform") or request.GET.get("platform") or "").strip()
        fmt = str(
            body.get("as")
            or body.get("reply")
            or request.GET.get("as")
            or request.GET.get("reply")
            or ""
        ).strip().lower()
        on_sale_raw = body.get("on_sale", request.GET.get("on_sale", "1"))
        on_sale = str(on_sale_raw).strip().lower() not in {"0", "false", "no"}
        try:
            limit = int(body.get("limit") or request.GET.get("limit") or 50)
        except (TypeError, ValueError):
            return Response({"detail": "limit 无效"}, status=status.HTTP_400_BAD_REQUEST)

        data = query_bot_products(q=q, platform=platform, limit=limit, on_sale_only=on_sale)
        if fmt in {"text", "plain", "reply", "1", "true"}:
            return Response(
                {"ok": True, "text": format_bot_product_reply(data), "count": data["count"]}
            )
        return Response(data)


class ExternalBridgeHealthAPIView(APIView):
    """xinhuo-bridge 健康检查：列出对外能力与鉴权是否就绪。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        key_ok = api_key_ok(request)
        if not key_ok:
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)

        capabilities = [
            {
                "name": "product_query",
                "method": "GET",
                "path": "/api/external/wechat-bot/products/",
            },
            {
                "name": "bot_record_push",
                "method": "POST",
                "path": "/api/external/wechat-bot/push/",
            },
            {
                "name": "ledger_push",
                "method": "POST",
                "path": "/api/external/ledger/push/",
            },
            {
                "name": "bridge_health",
                "method": "GET",
                "path": "/api/external/bridge/health/",
            },
        ]
        return Response(
            {
                "ok": True,
                "service": "xinhuo",
                "bridge": "xinhuo-bridge",
                "api_key_configured": bool(configured_api_key()),
                "capabilities": capabilities,
            }
        )


class ExternalWechatBotPushAPIView(APIView):
    """微信机器人推送 → 微信BOT三表：API Key 鉴权，event_id 幂等。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not api_key_ok(request):
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"ok": True, "service": "external-wechat-bot-push"})

    def post(self, request):
        from .wechat_bot_push import ingest_wechat_bot_payload

        if not api_key_ok(request):
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            result = ingest_wechat_bot_payload(request.data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if result.get("mode") == "single" and result.get("status") == "created":
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_200_OK)


class ExternalLedgerPushAPIView(APIView):
    """微信机器人推送 → 记账表 LedgerRecord：API Key 鉴权，event_id 幂等。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not api_key_ok(request):
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"ok": True, "service": "external-ledger-push"})

    def post(self, request):
        from .ledger_push import ingest_ledger_push_payload

        if not api_key_ok(request):
            return Response({"detail": "未授权"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            result = ingest_ledger_push_payload(request.data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if result.get("mode") == "single" and result.get("status") == "created":
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_200_OK)


class WechatBotRecordListAPIView(APIView):
    """职员端：微信BOT记录列表 / 手工添加。"""

    permission_classes = [StaffOnlyPermission]

    def get(self, request):
        from .wechat_bot_push import list_wechat_bot_records

        table = (request.GET.get("table") or "").strip()
        employee = (request.GET.get("employee") or request.GET.get("employee_name") or "").strip()
        q = (request.GET.get("q") or "").strip()
        try:
            page = int(request.GET.get("page") or 1)
            page_size = int(request.GET.get("page_size") or 30)
        except (TypeError, ValueError):
            return Response({"detail": "page / page_size 无效"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = list_wechat_bot_records(
                table_type=table,
                employee_name=employee,
                q=q,
                page=page,
                page_size=page_size,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)

    def post(self, request):
        from .wechat_bot_push import create_manual_wechat_bot_record

        try:
            data = create_manual_wechat_bot_record(request.data if isinstance(request.data, dict) else {})
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data, status=status.HTTP_201_CREATED)


class WechatBotRecordDetailAPIView(APIView):
    """职员端：编辑 / 删除单条微信BOT记录。"""

    permission_classes = [StaffOnlyPermission]

    def patch(self, request, pk: int):
        from .wechat_bot_push import update_wechat_bot_record

        try:
            data = update_wechat_bot_record(int(pk), request.data if isinstance(request.data, dict) else {})
        except (TypeError, ValueError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except LookupError:
            return Response({"detail": "记录不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)

    def put(self, request, pk: int):
        return self.patch(request, pk)

    def delete(self, request, pk: int):
        from .wechat_bot_push import delete_wechat_bot_record

        try:
            delete_wechat_bot_record(int(pk))
        except (TypeError, ValueError):
            return Response({"detail": "无效 id"}, status=status.HTTP_400_BAD_REQUEST)
        except LookupError:
            return Response({"detail": "记录不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WechatBotRecordBatchDeleteAPIView(APIView):
    """职员端：批量删除微信BOT记录。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        from .wechat_bot_push import delete_wechat_bot_records

        raw = request.data if isinstance(request.data, dict) else {}
        try:
            data = delete_wechat_bot_records(raw.get("ids") or [])
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)


class WechatBotEmployeeListAPIView(APIView):
    """职员端：某业务表（或全部）下出现过的员工名，供页内人员筛选。"""

    permission_classes = [StaffOnlyPermission]

    def get(self, request):
        from .wechat_bot_push import list_wechat_bot_employees

        table = (request.GET.get("table") or "").strip()
        try:
            employees = list_wechat_bot_employees(table_type=table)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"employees": employees})


class StaffUsersListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response([], status=status.HTTP_200_OK)
        qs = (
            get_user_model()
            .objects.filter(is_active=True, is_staff=True)
            .select_related("staff_login_meta")
            .order_by("username")
        )
        return Response(UserSerializer(qs, many=True).data)


class PaymentTutorialListAPIView(generics.ListAPIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True
    serializer_class = PaymentTutorialSerializer

    def get_queryset(self):
        qs = PaymentTutorial.objects.all().order_by("sort_order", "id")
        name = (self.request.GET.get("name") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class PlatformAccountListAPIView(generics.ListAPIView):
    permission_classes = [StaffOnlyPermission]
    serializer_class = PlatformAccountSerializer

    def get_queryset(self):
        return PlatformAccount.objects.order_by("sort_order", "id")


class SharedAppleIDPageListAPIView(generics.ListAPIView):
    permission_classes = [StaffOnlyPermission]
    serializer_class = SharedAppleIDPageSerializer

    def get_queryset(self):
        qs = SharedAppleIDPage.objects.filter(is_active=True).order_by("sort_order", "id")
        name = (self.request.GET.get("name") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class PictCartPageListAPIView(generics.ListAPIView):
    permission_classes = [StaffOnlyPermission]
    serializer_class = PictCartPageSerializer

    def get_queryset(self):
        qs = PictCartPage.objects.filter(is_active=True).order_by("sort_order", "id")
        name = (self.request.GET.get("name") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class FanboxStatsPageListAPIView(generics.ListAPIView):
    """游客也可读（前端 fanbox 页对游客开放）。"""

    permission_classes = [StaffOnlyPermission]
    serializer_class = FanboxStatsPageSerializer
    guest_allowed = True

    def get_queryset(self):
        qs = FanboxStatsPage.objects.filter(is_active=True).order_by("sort_order", "id")
        name = (self.request.GET.get("name") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class ServiceMonitorPageListAPIView(generics.ListAPIView):
    permission_classes = [StaffOnlyPermission]
    serializer_class = ServiceMonitorPageSerializer

    def get_queryset(self):
        qs = ServiceMonitorPage.objects.filter(is_active=True).order_by("sort_order", "id")
        name = (self.request.GET.get("name") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class PlatformTagPoolListAPIView(generics.ListAPIView):
    permission_classes = [StaffOnlyPermission]
    serializer_class = PlatformTagPoolSerializer

    def get_queryset(self):
        qs = PlatformTagPool.objects.all().order_by("order", "id")
        name = (self.request.GET.get("name") or self.request.GET.get("q") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class ChannelTagPoolListAPIView(generics.ListAPIView):
    permission_classes = [StaffOnlyPermission]
    serializer_class = ChannelTagPoolSerializer

    def get_queryset(self):
        qs = ChannelTagPool.objects.all().order_by("order", "id")
        name = (self.request.GET.get("name") or self.request.GET.get("q") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class TutorialPoolListAPIView(generics.ListAPIView):
    """教程池列表（职员端浏览 / 后续 SKU 选取）。"""

    permission_classes = [StaffOnlyPermission]
    serializer_class = TutorialPoolSerializer

    def get_queryset(self):
        qs = TutorialPool.objects.all().order_by("sort_order", "id")
        name = (self.request.GET.get("name") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)
        return qs


class PhrasePoolListAPIView(generics.ListAPIView):
    """话术池列表（后续 SKU 选取）。"""

    permission_classes = [StaffOnlyPermission]
    serializer_class = PhrasePoolSerializer

    def get_queryset(self):
        qs = PhrasePool.objects.all().order_by("sort_order", "id")
        q = (self.request.GET.get("q") or self.request.GET.get("name") or "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(content__icontains=q))
        return qs


class UsdProxyPriceTierListAPIView(generics.ListAPIView):
    """美金代付价格池（职员端 SKU 价格展示）。"""

    permission_classes = [StaffOnlyPermission]
    guest_allowed = True
    serializer_class = UsdProxyPriceTierSerializer

    def get_queryset(self):
        return UsdProxyPriceTier.objects.all().order_by("sort_order", "id")


def _tutorial_platform_tags_by_name():
    """从 SKU.tutorial_text 统计各教程关联的平台标签（过渡期，待 SKU 关联表上线后替换）。"""
    deployed = {}
    sku_qs = (
        SKU.objects.select_related("business__platform")
        .prefetch_related("business__platform__platform_tags")
        .exclude(tutorial_text="")
        .order_by("id")
    )
    for sku in sku_qs:
        platform = getattr(getattr(sku, "business", None), "platform", None)
        if platform is None:
            continue
        labels = [x for x in platform.platform_tags.values_list("name", flat=True) if x] or [platform.name]
        titles = [x.strip() for x in str(sku.tutorial_text or "").split("/") if x.strip()]
        for title in titles:
            bag = deployed.setdefault(title, set())
            for lb in labels:
                bag.add(lb)
    return deployed


class NannyTutorialListAPIView(APIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True

    def get(self, request):
        name_kw = (request.GET.get("name") or "").strip().lower()
        tag_kw = (request.GET.get("tag") or "").strip()
        tag_kw_lower = tag_kw.lower() if tag_kw else ""

        tags_by_name = _tutorial_platform_tags_by_name()
        all_tag_names = set()
        for tags in tags_by_name.values():
            all_tag_names.update(tags)

        rows = []
        for t in TutorialPool.objects.all().order_by("sort_order", "id"):
            title = (t.name or "").strip()
            if not title:
                continue
            if name_kw and name_kw not in title.lower():
                continue
            tags = sorted(tags_by_name.get(title, []))
            if tag_kw_lower and not any(tag_kw_lower == x.lower() for x in tags):
                continue
            all_tag_names.update(tags)
            rows.append(
                {
                    "id": t.id,
                    "name": title,
                    "detail_url": t.detail_url,
                    "sort_order": t.sort_order,
                    "platform_tags": tags,
                }
            )

        return Response(
            {
                "results": rows,
                "platform_tag_options": sorted(all_tag_names, key=lambda x: (x.lower(), x)),
            }
        )


class DataScreenAPIView(APIView):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True

    def get(self, request):
        return Response(build_data_screen_payload(user=request.user))


class HallBlockViewSet(viewsets.ModelViewSet):
    permission_classes = [StaffOnlyPermission]
    guest_allowed = True
    serializer_class = HallBlockSerializer

    def get_queryset(self):
        # 职员与超管使用同一套大厅数据；不在列表层按 is_active 过滤，避免后台新增后因未勾选「显示」
        # 或历史脏数据导致前端长期空白。是否展示可由前端根据 is_active 控制样式。
        return HallBlock.objects.prefetch_related("images").order_by("-is_pinned", "sort_order", "id")

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [StaffOnlyPermission()]
