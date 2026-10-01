"""订单记录列表、导出等共用逻辑。"""
from io import BytesIO

from django.db.models import Max
from django.http import HttpResponse
from django.utils import timezone

from .forms import PaymentRecordFilterForm
from .models import PaymentRecord, PaymentRecordImage

PAYMENT_RECORD_PAGE_SIZE = 30


def filtered_payment_records_qs(get_params, *, prefetch_images=False):
    """按 GET 参数筛选；默认不 prefetch 截图（列表页对当前页再 prefetch）。"""
    qs = PaymentRecord.objects.select_related("user").all()
    if prefetch_images:
        qs = qs.prefetch_related("extra_images")
    filter_form = PaymentRecordFilterForm(get_params or None)
    if filter_form.is_valid():
        cd = filter_form.cleaned_data
        if cd.get("user"):
            qs = qs.filter(user=cd["user"])
        ch = cd.get("channel")
        if ch:
            qs = qs.filter(channel=ch)
        if cd.get("date_from"):
            qs = qs.filter(record_date__gte=cd["date_from"])
        if cd.get("date_to"):
            qs = qs.filter(record_date__lte=cd["date_to"])
    return qs.order_by("-created_at"), filter_form


def filtered_payment_records_api_qs(request, *, prefetch_images=False):
    """职员端 API 筛选（user_id / platform 参数名）。"""
    qs = PaymentRecord.objects.select_related("user").all()
    if prefetch_images:
        qs = qs.prefetch_related("extra_images")
    if not request.user.is_superuser:
        qs = qs.filter(user=request.user)
    else:
        user_id = (request.GET.get("user_id") or "").strip()
        if user_id:
            qs = qs.filter(user_id=user_id)
    channel = (request.GET.get("platform") or request.GET.get("channel") or "").strip()
    if channel:
        qs = qs.filter(channel=channel)
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    if date_from:
        qs = qs.filter(record_date__gte=date_from)
    if date_to:
        qs = qs.filter(record_date__lte=date_to)
    return qs.order_by("-created_at")


def prefetch_payment_record_images(records):
    """为已取出的记录批量 prefetch 附图，并保持原顺序。"""
    if not records:
        return []
    pks = [r.pk for r in records]
    prefetched = (
        PaymentRecord.objects.filter(pk__in=pks)
        .select_related("user")
        .prefetch_related("extra_images")
    )
    by_pk = {r.pk: r for r in prefetched}
    return [by_pk[pk] for pk in pks if pk in by_pk]


def handle_payment_record_images(request, record):
    """编辑页：删除/上传截图（主图 + 附图）。"""
    if request.POST.get("delete_main_screenshot") == "on" and record.screenshot:
        record.screenshot.delete(save=False)
        record.screenshot = None
        record.save(update_fields=["screenshot"])

    delete_ids = request.POST.getlist("delete_extra_image_ids")
    if delete_ids:
        PaymentRecordImage.objects.filter(payment_record=record, pk__in=delete_ids).delete()

    files = request.FILES.getlist("payment_images")
    if not files:
        return

    remaining = list(files)
    if not record.screenshot and remaining:
        record.screenshot = remaining.pop(0)
        record.save(update_fields=["screenshot"])

    if remaining:
        max_order = record.extra_images.aggregate(m=Max("sort_order"))["m"]
        if max_order is None:
            max_order = -1
        for f in remaining:
            max_order += 1
            PaymentRecordImage.objects.create(
                payment_record=record, image=f, sort_order=max_order
            )


def payment_records_xlsx_response(queryset):
    """导出 Excel（无图片列）。"""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "订单记录"
    ws.append(["收款渠道", "订单数", "金额", "备注", "人员", "订单时间", "填写时间"])

    qs = queryset.select_related("user").iterator(chunk_size=500)
    for r in qs:
        created_local = timezone.localtime(r.created_at).strftime("%Y-%m-%d %H:%M:%S")
        ws.append(
            [
                r.get_channel_display(),
                r.order_count,
                float(r.amount),
                r.note or "",
                r.user.username,
                r.record_date.isoformat() if r.record_date else "",
                created_local,
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="payment_records.xlsx"'
    return response
