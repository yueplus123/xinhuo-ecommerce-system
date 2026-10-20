"""管理后台 API（替代 /backoffice 的 HTML 页面）：职员账号、收款记录、订阅提醒。

全部仅超级管理员可用（与旧 backoffice 的 superuser_required 一致）。
表单校验直接复用旧 backoffice 的 Form，保证规则等价。
"""
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog.forms import (
    PaymentRecordAdminForm,
    StaffUserForm,
    SubscriptionReminderAdminForm,
    SubscriptionReminderFilterForm,
)
from backend.apps.catalog.models import (
    PAYMENT_CHANNELS,
    PaymentRecord,
    SubscriptionPlatformOption,
    SubscriptionReminder,
)
from backend.apps.catalog.payment_records import (
    PAYMENT_RECORD_PAGE_SIZE,
    filtered_payment_records_qs,
    handle_payment_record_images,
    payment_records_xlsx_response,
    prefetch_payment_record_images,
)
from backend.apps.catalog.roles import is_boss, is_ceo, is_guest

SUBSCRIPTION_REMINDER_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100

ROLE_LABELS = dict(StaffUserForm.ROLE_CHOICES)


class IsActiveSuperuser(BasePermission):
    """仅超级管理员（旧后台 superuser_required 的等价物）。"""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.is_superuser)


class ManageAPIView(APIView):
    permission_classes = [IsActiveSuperuser]


def _page_size(request, default):
    try:
        n = int(request.query_params.get("page_size") or default)
    except (TypeError, ValueError):
        n = default
    return max(1, min(n, MAX_PAGE_SIZE))


def _form_error_response(form):
    data = {}
    for field, errs in form.errors.get_json_data().items():
        key = "non_field_errors" if field == "__all__" else field
        data[key] = [e["message"] for e in errs]
    return Response(data, status=status.HTTP_400_BAD_REQUEST)


def _data_dict(request):
    """把 JSON / multipart 请求体转成可喂给 Django Form 的普通 dict（单值）。"""
    src = request.data
    out = {}
    for k in src.keys():
        v = src.get(k)
        if v is not None:
            out[k] = v
    return out


def _iso_local(dt):
    return timezone.localtime(dt).isoformat() if dt else None


# ───────────────────────── 职员账号 ─────────────────────────


def _user_role(obj):
    if obj.is_superuser:
        return StaffUserForm.ROLE_ADMIN
    if is_boss(obj):
        return StaffUserForm.ROLE_BOSS
    if is_ceo(obj):
        return StaffUserForm.ROLE_CEO
    if is_guest(obj):
        return StaffUserForm.ROLE_GUEST
    return StaffUserForm.ROLE_EMPLOYEE


def _user_payload(obj):
    meta = getattr(obj, "staff_login_meta", None)
    role = _user_role(obj)
    return {
        "id": obj.pk,
        "username": obj.username,
        "role": role,
        "role_label": ROLE_LABELS.get(role, role),
        "is_active": obj.is_active,
        "last_login": _iso_local(obj.last_login),
        "last_login_ip": (meta.last_login_ip if meta else "") or "",
    }


def _staff_users_qs():
    return get_user_model().objects.filter(is_staff=True).select_related("staff_login_meta").order_by("id")


class UserListCreateView(ManageAPIView):
    def get(self, request):
        return Response([_user_payload(u) for u in _staff_users_qs()])

    def post(self, request):
        data = _data_dict(request)
        data.setdefault("role", StaffUserForm.ROLE_EMPLOYEE)
        data.setdefault("is_active", True)
        form = StaffUserForm(data, require_password=True)
        if not form.is_valid():
            return _form_error_response(form)
        obj = form.save()
        return Response(_user_payload(_staff_users_qs().get(pk=obj.pk)), status=status.HTTP_201_CREATED)


class UserDetailView(ManageAPIView):
    def _get(self, pk):
        return get_object_or_404(_staff_users_qs(), pk=pk)

    def get(self, request, pk):
        return Response(_user_payload(self._get(pk)))

    def patch(self, request, pk):
        obj = self._get(pk)
        data = {"username": obj.username, "is_active": obj.is_active, "role": _user_role(obj)}
        data.update(_data_dict(request))
        form = StaffUserForm(data, instance=obj, require_password=False)
        if not form.is_valid():
            return _form_error_response(form)
        form.save()
        return Response(_user_payload(self._get(pk)))

    def delete(self, request, pk):
        User = get_user_model()
        obj = self._get(pk)
        if obj.pk == request.user.pk:
            return Response({"detail": "不能删除当前登录账号。"}, status=status.HTTP_400_BAD_REQUEST)
        if obj.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
            return Response({"detail": "至少需要保留一个启用中的管理员。"}, status=status.HTTP_400_BAD_REQUEST)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────────────────────── 收款记录 ─────────────────────────


def _payment_payload(obj, request):
    images = []
    if obj.screenshot:
        try:
            images.append({"kind": "main", "id": None, "url": request.build_absolute_uri(obj.screenshot.url)})
        except ValueError:
            pass
    for img in obj.extra_images.all():
        try:
            images.append({"kind": "extra", "id": img.pk, "url": request.build_absolute_uri(img.image.url)})
        except ValueError:
            continue
    return {
        "id": obj.pk,
        "user": obj.user_id,
        "user_name": obj.user.username,
        "channel": obj.channel,
        "channel_label": obj.get_channel_display(),
        "order_count": obj.order_count,
        "amount": str(obj.amount),
        "note": obj.note,
        "record_date": obj.record_date.isoformat() if obj.record_date else None,
        "created_at": _iso_local(obj.created_at),
        "images": images,
    }


def _payment_with_images(pk):
    return get_object_or_404(PaymentRecord.objects.select_related("user").prefetch_related("extra_images"), pk=pk)


class PaymentRecordListCreateView(ManageAPIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        qs, _ = filtered_payment_records_qs(request.query_params)
        paginator = Paginator(qs, _page_size(request, PAYMENT_RECORD_PAGE_SIZE))
        page_obj = paginator.get_page(request.query_params.get("page"))
        records = prefetch_payment_record_images(list(page_obj.object_list))
        return Response(
            {
                "count": paginator.count,
                "page": page_obj.number,
                "page_size": paginator.per_page,
                "results": [_payment_payload(r, request) for r in records],
            }
        )

    def post(self, request):
        form = PaymentRecordAdminForm(_data_dict(request))
        if not form.is_valid():
            return _form_error_response(form)
        with transaction.atomic():
            record = form.save()
            handle_payment_record_images(request, record)
        return Response(_payment_payload(_payment_with_images(record.pk), request), status=status.HTTP_201_CREATED)


class PaymentRecordDetailView(ManageAPIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, pk):
        return Response(_payment_payload(_payment_with_images(pk), request))

    def patch(self, request, pk):
        obj = _payment_with_images(pk)
        data = {
            "user": obj.user_id,
            "channel": obj.channel,
            "order_count": obj.order_count,
            "amount": str(obj.amount),
            "note": obj.note,
            "record_date": obj.record_date.isoformat() if obj.record_date else "",
        }
        data.update(_data_dict(request))
        form = PaymentRecordAdminForm(data, instance=obj)
        if not form.is_valid():
            return _form_error_response(form)
        with transaction.atomic():
            record = form.save()
            handle_payment_record_images(request, record)
        return Response(_payment_payload(_payment_with_images(pk), request))

    def delete(self, request, pk):
        get_object_or_404(PaymentRecord, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentRecordExportView(ManageAPIView):
    def get(self, request):
        qs, _ = filtered_payment_records_qs(request.query_params)
        return payment_records_xlsx_response(qs)


# ───────────────────────── 订阅提醒 ─────────────────────────


def _reminder_status(nxt, today):
    if nxt is None:
        return "none", "未设日期"
    if nxt < today:
        return "overdue", "已逾期"
    if nxt == today:
        return "today", "今日待跟进"
    return "pending", "待提醒"


def _reminder_payload(obj, today):
    code, text = _reminder_status(obj.next_reminder_at, today)
    return {
        "id": obj.pk,
        "user": obj.user_id,
        "user_name": obj.user.username,
        "wechat_label": obj.wechat_label,
        "platform_name": getattr(obj.platform_option, "name", "") or "",
        "remark": obj.remark or "",
        "next_reminder_at": obj.next_reminder_at.isoformat() if obj.next_reminder_at else None,
        "last_renewed_at": _iso_local(obj.last_renewed_at),
        "status": code,
        "status_text": text,
    }


def _reminder_qs():
    return SubscriptionReminder.objects.select_related("user", "platform_option")


class SubscriptionReminderListCreateView(ManageAPIView):
    def get(self, request):
        qs = _reminder_qs().all()
        filter_form = SubscriptionReminderFilterForm(request.query_params or None)
        if filter_form.is_valid():
            cd = filter_form.cleaned_data
            if cd.get("user"):
                qs = qs.filter(user=cd["user"])
            q = (cd.get("q") or "").strip()
            if q:
                qs = qs.filter(
                    Q(wechat_label__icontains=q) | Q(platform_option__name__icontains=q) | Q(remark__icontains=q)
                )
        qs = qs.order_by("next_reminder_at", "id")
        total_all = SubscriptionReminder.objects.count()
        paginator = Paginator(qs, _page_size(request, SUBSCRIPTION_REMINDER_PAGE_SIZE))
        page_obj = paginator.get_page(request.query_params.get("page"))
        today = timezone.localdate()
        return Response(
            {
                "count": paginator.count,
                "total_all": total_all,
                "total_filtered": paginator.count,
                "page": page_obj.number,
                "page_size": paginator.per_page,
                "results": [_reminder_payload(r, today) for r in page_obj.object_list],
            }
        )

    def post(self, request):
        form = SubscriptionReminderAdminForm(_data_dict(request))
        if not form.is_valid():
            return _form_error_response(form)
        obj = form.save()
        return Response(
            _reminder_payload(_reminder_qs().get(pk=obj.pk), timezone.localdate()), status=status.HTTP_201_CREATED
        )


class SubscriptionReminderDetailView(ManageAPIView):
    def patch(self, request, pk):
        obj = get_object_or_404(_reminder_qs(), pk=pk)
        data = {
            "user": obj.user_id,
            "wechat_label": obj.wechat_label,
            "platform_display": getattr(obj.platform_option, "name", ""),
            "remark": obj.remark or "",
            "next_reminder_at": obj.next_reminder_at.isoformat() if obj.next_reminder_at else "",
        }
        data.update(_data_dict(request))
        form = SubscriptionReminderAdminForm(data, instance=obj)
        if not form.is_valid():
            return _form_error_response(form)
        form.save()
        return Response(_reminder_payload(_reminder_qs().get(pk=pk), timezone.localdate()))

    def delete(self, request, pk):
        get_object_or_404(SubscriptionReminder, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────────────────────── 下拉选项 ─────────────────────────


class AccountsOptionsView(ManageAPIView):
    def get(self, request):
        User = get_user_model()
        staff = list(User.objects.filter(is_staff=True).order_by("username").values("id", "username", "is_active"))
        return Response(
            {
                "staff_users": [u for u in staff if u["is_active"]],
                "all_staff_users": staff,
                "channels": [{"value": v, "label": l} for v, l in PAYMENT_CHANNELS],
                "roles": [{"value": v, "label": l} for v, l in StaffUserForm.ROLE_CHOICES],
                "platform_options": list(
                    SubscriptionPlatformOption.objects.order_by("sort_order", "id").values_list("name", flat=True)
                ),
            }
        )


urlpatterns = [
    path("manage/accounts/options/", AccountsOptionsView.as_view(), name="manage-accounts-options"),
    path("manage/accounts/users/", UserListCreateView.as_view(), name="manage-accounts-users"),
    path("manage/accounts/users/<int:pk>/", UserDetailView.as_view(), name="manage-accounts-user-detail"),
    path(
        "manage/accounts/payment-records/",
        PaymentRecordListCreateView.as_view(),
        name="manage-accounts-payment-records",
    ),
    path(
        "manage/accounts/payment-records/export/",
        PaymentRecordExportView.as_view(),
        name="manage-accounts-payment-records-export",
    ),
    path(
        "manage/accounts/payment-records/<int:pk>/",
        PaymentRecordDetailView.as_view(),
        name="manage-accounts-payment-record-detail",
    ),
    path(
        "manage/accounts/subscription-reminders/",
        SubscriptionReminderListCreateView.as_view(),
        name="manage-accounts-subscription-reminders",
    ),
    path(
        "manage/accounts/subscription-reminders/<int:pk>/",
        SubscriptionReminderDetailView.as_view(),
        name="manage-accounts-subscription-reminder-detail",
    ),
]
