from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.messages import get_messages
from django.core.paginator import Paginator
from django.db.models import Max, Q, Prefetch, Count
import json

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .forms import (
    BusinessForm,
    ChannelTagPoolForm,
    ChannelTagPoolQuickForm,
    HallBlockForm,
    PlatformAccountForm,
    PaymentRecordAdminForm,
    PaymentRecordFilterForm,
    PaymentTutorialForm,
    PhrasePoolForm,
    PlatformListFilterForm,
    PlatformForm,
    PlatformTagPoolForm,
    PlatformTagPoolQuickForm,
    QuickPhraseForm,
    QuickPhraseEditorFormSet,
    SKUEditorForm,
    SKUPriceItemFormSet,
    SharedAppleIDPageForm,
    PictCartPageForm,
    FanboxStatsPageForm,
    ServiceMonitorPageForm,
    SKUForm,
    StaffUserForm,
    SubscriptionReminderAdminForm,
    SubscriptionReminderFilterForm,
    TutorialPoolForm,
    UsdProxyPriceTierForm,
)
from .payment_records import (
    PAYMENT_RECORD_PAGE_SIZE,
    filtered_payment_records_qs,
    handle_payment_record_images,
    payment_records_xlsx_response,
    prefetch_payment_record_images,
)
from .models import (
    Business,
    ChannelTagPool,
    HallBlock,
    HallBlockImage,
    PaymentTutorial,
    PhrasePool,
    Platform,
    PlatformAccount,
    PlatformTagPool,
    PaymentRecord,
    PaymentRecordImage,
    QuickPhrase,
    SharedAppleIDPage,
    PictCartPage,
    FanboxStatsPage,
    ServiceMonitorPage,
    SKU,
    SKUImage,
    SubscriptionPlatformOption,
    SubscriptionReminder,
    Tag,
    TutorialPool,
    UsdProxyPriceTier,
)
from .roles import is_boss, is_ceo, is_guest


def home(request):
    if request.user.is_authenticated:
        return redirect("backoffice:backoffice_home")
    return HttpResponseRedirect(reverse("login"))


def superuser_required(view_func):
    return login_required(user_passes_test(lambda u: u.is_superuser)(view_func))


PRODUCT_SECTION_VIEWS = frozenset(
    {
        "backoffice:platform_list",
        "backoffice:platform_workbench",
        "backoffice:platform_add",
        "backoffice:platform_edit",
        "backoffice:platform_delete",
        "backoffice:platform_reorder",
        "backoffice:business_list",
        "backoffice:business_add",
        "backoffice:business_edit",
        "backoffice:business_delete",
        "backoffice:sku_list",
        "backoffice:sku_editor",
        "backoffice:sku_editor_add",
        "backoffice:sku_add",
        "backoffice:sku_edit",
        "backoffice:sku_delete",
    }
)

PRODUCT_TABS = (
    ("backoffice:platform_list", "平台管理"),
)

RESOURCE_POOL_SECTION_VIEWS = frozenset(
    {
        "backoffice:phrase_pool_list",
        "backoffice:phrase_pool_add",
        "backoffice:phrase_pool_edit",
        "backoffice:phrase_pool_delete",
        "backoffice:tutorial_pool_list",
        "backoffice:tutorial_pool_add",
        "backoffice:tutorial_pool_edit",
        "backoffice:tutorial_pool_delete",
        "backoffice:platform_tag_pool_list",
        "backoffice:platform_tag_pool_add",
        "backoffice:platform_tag_pool_edit",
        "backoffice:platform_tag_pool_delete",
        "backoffice:channel_tag_pool_list",
        "backoffice:channel_tag_pool_add",
        "backoffice:channel_tag_pool_edit",
        "backoffice:channel_tag_pool_delete",
        "backoffice:usd_proxy_price_pool_list",
        "backoffice:usd_proxy_price_pool_add",
        "backoffice:usd_proxy_price_pool_edit",
        "backoffice:usd_proxy_price_pool_delete",
    }
)

RESOURCE_POOL_TABS = (
    ("backoffice:tutorial_pool_list", "教程池"),
    ("backoffice:phrase_pool_list", "话术池"),
    ("backoffice:platform_tag_pool_list", "标签池"),
    ("backoffice:channel_tag_pool_list", "渠道池"),
    ("backoffice:usd_proxy_price_pool_list", "美金代付价格池"),
)

# 兼容旧常量名
TUTORIAL_PHRASE_SECTION_VIEWS = RESOURCE_POOL_SECTION_VIEWS
TUTORIAL_PHRASE_TABS = RESOURCE_POOL_TABS


def _product_tab_for_view(view_name: str) -> str:
    if not view_name or not view_name.startswith("backoffice:"):
        return ""
    part = view_name.split(":", 1)[1]
    if part.startswith("platform_") and not part.startswith("platform_account"):
        return "backoffice:platform_list"
    if part.startswith("business_"):
        return "backoffice:platform_list"
    if part.startswith("sku_"):
        return "backoffice:platform_list"
    if part == "platform_workbench":
        return "backoffice:platform_list"
    return ""


def _resource_pool_tab_for_view(view_name: str) -> str:
    if view_name in RESOURCE_POOL_SECTION_VIEWS:
        if view_name.startswith("backoffice:tutorial_pool"):
            return "backoffice:tutorial_pool_list"
        if view_name.startswith("backoffice:phrase_pool"):
            return "backoffice:phrase_pool_list"
        if view_name.startswith("backoffice:platform_tag_pool"):
            return "backoffice:platform_tag_pool_list"
        if view_name.startswith("backoffice:channel_tag_pool"):
            return "backoffice:channel_tag_pool_list"
        if view_name.startswith("backoffice:usd_proxy_price_pool"):
            return "backoffice:usd_proxy_price_pool_list"
        return view_name
    return ""


BACKOFFICE_SECTIONS = {
    "product": {
        "aria_label": "商品管理",
        "views": PRODUCT_SECTION_VIEWS,
        "tabs": PRODUCT_TABS,
        "tab_for_view": _product_tab_for_view,
    },
    "tutorial_phrase": {
        "aria_label": "资源池",
        "views": RESOURCE_POOL_SECTION_VIEWS,
        "tabs": RESOURCE_POOL_TABS,
        "tab_for_view": _resource_pool_tab_for_view,
    },
}


def backoffice_context(request):
    active = request.resolver_match.view_name if request.resolver_match else ""

    active_section = ""
    for section_key, section in BACKOFFICE_SECTIONS.items():
        if active in section["views"]:
            active_section = section_key
            break

    nav = [
        ("backoffice:hall_block_list", "大厅内容管理", "🏛️"),
        ("backoffice:platform_list", "商品管理", "📦", "product"),
        ("backoffice:tutorial_pool_list", "资源池", "💬", "tutorial_phrase"),
        ("backoffice:shared_apple_id_page_list", "共享苹果ID分享页管理", "🍎"),
        ("backoffice:pict_cart_page_list", "pict加购物车页面管理", "🛒"),
        ("backoffice:fanbox_stats_page_list", "fanbox投稿作品统计管理", "🖼"),
        ("backoffice:service_monitor_page_list", "服务监控页面管理", "📡"),
        ("backoffice:payment_record_list", "订单记录管理", "📋"),
        ("backoffice:subscription_reminder_list", "订阅提醒管理", "🔔"),
        ("backoffice:platform_account_list", "平台账号密码管理", "🔐"),
        ("backoffice:payment_tutorial_list", "AAA图文远程", "📔"),
        ("backoffice:user_list", "前端用户管理", "👥"),
    ]
    sidebar = []
    active_key = ""
    for entry in nav:
        if len(entry) == 4:
            name, label, icon, group_key = entry
            is_active = active_section == group_key
            if is_active:
                active_key = group_key
            sidebar.append(
                {
                    "key": group_key,
                    "label": label,
                    "icon": icon,
                    "url": reverse(name),
                    "active": is_active,
                }
            )
        else:
            name, label, icon = entry
            is_active = active == name
            if is_active:
                active_key = name
            sidebar.append(
                {
                    "key": name,
                    "label": label,
                    "icon": icon,
                    "url": reverse(name),
                    "active": is_active,
                }
            )

    section_nav = None
    if active_section:
        section = BACKOFFICE_SECTIONS[active_section]
        tab_active = section["tab_for_view"](active)
        section_nav = {
            "aria_label": section["aria_label"],
            "tabs": [
                {
                    "label": label,
                    "url": reverse(name),
                    "active": tab_active == name,
                    "name": name,
                }
                for name, label in section["tabs"]
            ],
        }
        if len(section["tabs"]) <= 1:
            section_nav = None

    flash_messages = [
        {"level": m.level_tag, "text": str(m.message)}
        for m in get_messages(request)
    ]
    boot = {
        "nav": [
            {"key": i["key"], "label": i["label"], "url": i["url"], "icon": i.get("icon") or ""}
            for i in sidebar
        ],
        "activeKey": active_key,
        "sectionNav": section_nav,
        "username": request.user.get_username() if getattr(request.user, "is_authenticated", False) else "",
        "logoutUrl": reverse("logout"),
        "messages": flash_messages,
    }

    return {
        "backoffice_nav": sidebar,
        "backoffice_section_nav": section_nav,
        "backoffice_nav_active": active_key,
        "backoffice_boot": boot,
    }


def render_b(request, template_name, context):
    return render(request, template_name, context)


def _redirect_editor_anchor(next_url, *, pick_channel=None, anchor=""):
    """跳转回 SKU 编辑器并保留锚点，避免刷新后滚到页顶。"""
    parts = urlsplit(next_url or "")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "pick_channel"]
    if pick_channel is not None:
        query.append(("pick_channel", str(pick_channel)))
    return HttpResponseRedirect(
        urlunsplit(("", "", parts.path, urlencode(query), anchor or parts.fragment))
    )


def _redirect_platform_edit(next_url, *, pick_platform_tag=None):
    parts = urlsplit(next_url or "")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "pick_platform_tag"]
    if pick_platform_tag is not None:
        query.append(("pick_platform_tag", str(pick_platform_tag)))
    return HttpResponseRedirect(urlunsplit(("", "", parts.path, urlencode(query), parts.fragment)))


def _platform_tag_selection(request, obj=None):
    if request.method == "POST":
        return {int(x) for x in request.POST.getlist("platform_tags") if str(x).isdigit()}
    selected = set()
    if obj:
        selected = set(obj.platform_tags.values_list("pk", flat=True))
    raw = (request.GET.get("pick_platform_tag") or "").strip()
    if raw.isdigit():
        selected.add(int(raw))
    return selected


def render_platform_form(request, title, subtitle, form, cancel_url, delete_url=None, extra_context=None):
    obj = (extra_context or {}).get("object")
    ctx = {
        "title": title,
        "subtitle": subtitle,
        "form": form,
        "cancel_url": cancel_url,
        "delete_url": delete_url,
        "platform_tags_all": PlatformTagPool.objects.order_by("order", "id"),
        "selected_platform_tag_ids": _platform_tag_selection(request, obj),
        "editor_return_url": request.get_full_path(),
    }
    if extra_context:
        ctx.update(extra_context)
    return render_b(request, "backoffice/platform_form.html", ctx)


def platform_action_links(obj_id):
    return format_html(
        '<div class="bb-table-actions">'
        '<a class="bb-btn bb-btn-primary bb-btn--xs" href="{}">工作台</a>'
        '<a class="bb-btn bb-btn--xs" href="{}">编辑</a>'
        '<a class="bb-btn bb-btn-danger bb-btn--xs" href="{}">删除</a>'
        "</div>",
        reverse("backoffice:platform_workbench", args=[obj_id]),
        reverse("backoffice:platform_edit", args=[obj_id]),
        reverse("backoffice:platform_delete", args=[obj_id]),
    )


TAG_PILL_COLOR_PAIRS = (
    ("#ffe4e6", "#be123c"),
    ("#ffedd5", "#c2410c"),
    ("#fef3c7", "#b45309"),
    ("#dcfce7", "#15803d"),
    ("#cffafe", "#0f766e"),
    ("#dbeafe", "#1d4ed8"),
    ("#e0e7ff", "#4338ca"),
    ("#f3e8ff", "#7e22ce"),
)


def _tag_pill_color_pair(tag):
    key = str(getattr(tag, "pk", None) or getattr(tag, "name", "") or "")
    h = 0
    for ch in key:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return TAG_PILL_COLOR_PAIRS[h % len(TAG_PILL_COLOR_PAIRS)]


def platform_tags_cell(platform):
    tags = list(platform.platform_tags.all())
    if not tags:
        return mark_safe("—")
    pills = []
    for tag in tags:
        bg, color = _tag_pill_color_pair(tag)
        pills.append(
            format_html(
                '<span class="bb-tag-pill" style="background-color:{};color:{};border-color:{}33;">{}</span>',
                bg,
                color,
                color,
                escape(tag.name),
            )
        )
    return format_html('<span class="bb-tag-pill-list">{}</span>', mark_safe("".join(str(p) for p in pills)))


def _workbench_url_for_platform(platform_id):
    return reverse("backoffice:platform_workbench", args=[platform_id])


def _workbench_url_for_business(business):
    return _workbench_url_for_platform(business.platform_id)


def _workbench_url_for_sku(sku):
    return _workbench_url_for_platform(sku.business.platform_id)


def _sync_legacy_price(sku):
    first = sku.price_items.order_by("sort_order", "id").first()
    sku.price = first.rmb_amount if first else None
    sku.save(update_fields=["price"])


def _handle_member_images(request, sku):
    delete_ids = request.POST.getlist("delete_member_image_ids")
    if delete_ids:
        SKUImage.objects.filter(sku=sku, pk__in=delete_ids).delete()
    files = request.FILES.getlist("member_images")
    if not files:
        if sku.member_images.exists() and not sku.image:
            first_img = sku.member_images.order_by("sort_order", "id").first()
            if first_img:
                sku.image = first_img.image
                sku.save(update_fields=["image"])
        return
    max_order = sku.member_images.aggregate(m=Max("sort_order"))["m"]
    if max_order is None:
        max_order = -1
    for uploaded in files:
        max_order += 1
        SKUImage.objects.create(sku=sku, image=uploaded, sort_order=max_order)
    first_img = sku.member_images.order_by("sort_order", "id").first()
    if first_img:
        sku.image = first_img.image
        sku.save(update_fields=["image"])


def _render_sku_editor(request, sku, *, is_create=False):
    workbench_url = ""
    if sku.pk and sku.business_id:
        workbench_url = _workbench_url_for_sku(sku)
    elif request.GET.get("business_id"):
        try:
            biz = Business.objects.select_related("platform").get(pk=int(request.GET.get("business_id")))
            workbench_url = _workbench_url_for_platform(biz.platform_id)
        except (Business.DoesNotExist, TypeError, ValueError):
            pass

    if request.method == "POST":
        form = SKUEditorForm(request.POST, request.FILES, instance=sku)
        if form.is_valid():
            with transaction.atomic():
                sku = form.save()
                price_formset = SKUPriceItemFormSet(request.POST, instance=sku)
                phrase_formset = QuickPhraseEditorFormSet(request.POST, instance=sku)
                if price_formset.is_valid() and phrase_formset.is_valid():
                    price_formset.save()
                    phrase_formset.save()
                    _handle_member_images(request, sku)
                    _sync_legacy_price(sku)
                    messages.success(request, "SKU 已保存。")
                    return redirect("backoffice:sku_editor", pk=sku.pk)
        price_formset = SKUPriceItemFormSet(request.POST, instance=sku)
        phrase_formset = QuickPhraseEditorFormSet(request.POST, instance=sku)
    else:
        initial = {}
        business_id = (request.GET.get("business_id") or "").strip()
        if business_id and not sku.pk:
            initial["business"] = business_id
        form = SKUEditorForm(instance=sku, initial=initial)
        price_formset = SKUPriceItemFormSet(instance=sku)
        phrase_formset = QuickPhraseEditorFormSet(instance=sku)

    member_images = list(sku.member_images.all()) if sku.pk else []
    channel_tags_all = Tag.objects.filter(type=Tag.TYPE_CHANNEL).order_by("order", "id")
    if request.method == "POST":
        selected_channel_ids = {int(x) for x in request.POST.getlist("channel_tags") if str(x).isdigit()}
    elif sku.pk:
        selected_channel_ids = set(sku.channel_tags.values_list("pk", flat=True))
    else:
        selected_channel_ids = set()
    pick_channel = (request.GET.get("pick_channel") or "").strip()
    if pick_channel.isdigit():
        selected_channel_ids.add(int(pick_channel))

    if sku.pk:
        editor_return_url = reverse("backoffice:sku_editor", args=[sku.pk])
    else:
        business_id = (request.GET.get("business_id") or "").strip()
        editor_return_url = reverse("backoffice:sku_editor_add")
        if business_id:
            editor_return_url = f"{editor_return_url}?business_id={business_id}"

    phrase_pool_data = [
        {"id": p.pk, "name": p.name, "content": p.content}
        for p in PhrasePool.objects.all().order_by("sort_order", "id")
    ]
    tutorial_pool_data = [
        {"id": t.pk, "name": t.name, "detail_url": t.detail_url}
        for t in TutorialPool.objects.all().order_by("sort_order", "id")
    ]
    if request.method == "POST":
        selected_tutorial_ids = [int(x) for x in request.POST.getlist("tutorial_pool") if str(x).isdigit()]
    elif sku.pk:
        names = [n.strip() for n in (sku.tutorial_text or "").split(" / ") if n.strip()]
        selected_tutorial_ids = list(
            TutorialPool.objects.filter(name__in=names).values_list("pk", flat=True)
        )
    else:
        selected_tutorial_ids = []

    tutorial_by_id = {t["id"]: t for t in tutorial_pool_data}
    selected_tutorials = [
        tutorial_by_id[i] for i in selected_tutorial_ids if i in tutorial_by_id
    ]

    return render_b(
        request,
        "backoffice/sku_editor.html",
        {
            "form": form,
            "price_formset": price_formset,
            "phrase_formset": phrase_formset,
            "sku": sku,
            "is_create": is_create,
            "member_images": member_images,
            "workbench_url": workbench_url,
            "delete_url": reverse("backoffice:sku_delete", args=[sku.pk]) if sku.pk else None,
            "channel_tags_all": channel_tags_all,
            "selected_channel_ids": selected_channel_ids,
            "editor_return_url": editor_return_url,
            "phrase_pool_data": phrase_pool_data,
            "tutorial_pool_data": tutorial_pool_data,
            "selected_tutorial_ids": selected_tutorial_ids,
            "selected_tutorials": selected_tutorials,
            "phrase_formset_prefix": phrase_formset.prefix,
        },
    )


def action_links(edit_name, delete_name, obj_id):
    return format_html(
        '<a class="bb-btn" href="{}">编辑</a> <a class="bb-btn bb-btn-danger" href="{}">删除</a>',
        reverse(edit_name, args=[obj_id]),
        reverse(delete_name, args=[obj_id]),
    )


def delete_action_link(delete_name, obj_id):
    return format_html(
        '<a class="bb-btn bb-btn-danger" href="{}">删除</a>',
        reverse(delete_name, args=[obj_id]),
    )


def render_list(request, title, subtitle, headers, rows, create_url=None, create_label=None, **extra):
    ctx = {
        "title": title,
        "subtitle": subtitle,
        "headers": headers,
        "rows": rows,
        "create_url": create_url,
        "create_label": create_label,
    }
    ctx.update(extra)
    return render_b(request, "backoffice/manage_list.html", ctx)


def _sync_hall_block_legacy_image(block):
    first = block.images.order_by("sort_order", "id").first()
    block.image = first.image if first else None
    block.save(update_fields=["image"])


def _handle_hall_block_images(request, block):
    delete_ids = request.POST.getlist("delete_member_image_ids")
    if delete_ids:
        HallBlockImage.objects.filter(block=block, pk__in=delete_ids).delete()
    files = request.FILES.getlist("member_images")
    if files:
        max_order = block.images.aggregate(m=Max("sort_order"))["m"]
        if max_order is None:
            max_order = -1
        for uploaded in files:
            max_order += 1
            HallBlockImage.objects.create(block=block, image=uploaded, sort_order=max_order)
    _sync_hall_block_legacy_image(block)


def _render_hall_block_form(request, *, block=None, title, subtitle, cancel_url, delete_url=None):
    is_edit = block is not None and block.pk
    if request.method == "POST":
        form = HallBlockForm(request.POST, request.FILES, instance=block)
        if form.is_valid():
            with transaction.atomic():
                obj = form.save()
                _handle_hall_block_images(request, obj)
            messages.success(request, "大厅板块已保存。" if is_edit else "大厅板块已创建，可在列表中继续编辑或删除。")
            return redirect("backoffice:hall_block_edit", pk=obj.pk)
    else:
        form = HallBlockForm(instance=block)

    hall_images = list(block.images.all()) if is_edit else []
    return render_b(
        request,
        "backoffice/hall_block_form.html",
        {
            "title": title,
            "subtitle": subtitle,
            "form": form,
            "cancel_url": cancel_url,
            "delete_url": delete_url,
            "hall_images": hall_images,
        },
    )


def render_form(request, title, subtitle, form, cancel_url, delete_url=None, wide_fields=None, checklist_fields=None, extra_context=None):
    ctx = {
        "title": title,
        "subtitle": subtitle,
        "form": form,
        "cancel_url": cancel_url,
        "delete_url": delete_url,
        "wide_fields": wide_fields or [],
        "checklist_fields": checklist_fields or [],
    }
    if extra_context:
        ctx.update(extra_context)
    return render_b(request, "backoffice/manage_form.html", ctx)


def render_delete(request, title, object_label, cancel_url):
    return render_b(
        request,
        "backoffice/confirm_delete.html",
        {"title": title, "object_label": object_label, "cancel_url": cancel_url},
    )


@superuser_required
def platform_list(request):
    filter_form = PlatformListFilterForm(request.GET or None)
    platform_id = (request.GET.get("platform") or "").strip()
    q = (request.GET.get("q") or "").strip()
    has_filters = bool(platform_id or q)

    qs = Platform.objects.prefetch_related("platform_tags").all()
    if platform_id:
        try:
            qs = qs.filter(pk=int(platform_id))
        except (TypeError, ValueError):
            qs = qs.none()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(url__icontains=q) | Q(note__icontains=q) | Q(platform_tags__name__icontains=q)).distinct()

    rows = []
    drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
    for obj in qs.order_by("sort_order", "id"):
        rows.append(
            {
                "sort_id": obj.pk,
                "cells": [
                    drag,
                    escape(obj.name),
                    obj.get_status_display(),
                    escape(obj.url or "—"),
                    platform_tags_cell(obj),
                    str(obj.businesses.count()),
                    platform_action_links(obj.pk),
                ],
            }
        )
    return render_list(
        request,
        "平台管理",
        "独立维护平台并继续关联业务。拖动左侧「⋮⋮」可调整顺序；点击「工作台」进入树形管理。",
        ["排序", "平台名称", "状态", "网址", "平台标签", "业务数", "操作"],
        rows,
        create_url=reverse("backoffice:platform_add"),
        create_label="新增平台",
        sortable_reorder_url=None if has_filters else reverse("backoffice:platform_reorder"),
        filter_form=filter_form,
        reset_list_url=reverse("backoffice:platform_list"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_add(request):
    form = PlatformForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        max_o = Platform.objects.exclude(pk=obj.pk).aggregate(m=Max("sort_order"))["m"] or 0
        obj.sort_order = max_o + 1
        obj.save(update_fields=["sort_order"])
        messages.success(request, "平台已创建。")
        return redirect("backoffice:platform_edit", pk=obj.pk)
    return render_platform_form(
        request, "新增平台", "填写平台基础信息。", form, reverse("backoffice:platform_list")
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_edit(request, pk):
    obj = get_object_or_404(Platform.objects.prefetch_related("businesses"), pk=pk)
    form = PlatformForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "平台已更新。")
        return redirect("backoffice:platform_edit", pk=obj.pk)
    return render_platform_form(
        request,
        "编辑平台",
        "保存后可继续维护该平台下的业务。",
        form,
        reverse("backoffice:platform_list"),
        delete_url=reverse("backoffice:platform_delete", args=[obj.pk]),
        extra_context={"object": obj, "related_template": "backoffice/platform_related.html"},
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_delete(request, pk):
    obj = get_object_or_404(Platform, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "平台已删除。")
        return redirect("backoffice:platform_list")
    return render_delete(request, "平台", obj.name, reverse("backoffice:platform_list"))


@superuser_required
def platform_workbench(request, pk):
    platform = get_object_or_404(
        Platform.objects.prefetch_related("platform_tags"),
        pk=pk,
    )
    businesses = (
        Business.objects.filter(platform=platform)
        .prefetch_related(Prefetch("skus", queryset=SKU.objects.prefetch_related("quick_phrases").order_by("id")))
        .order_by("id")
    )
    return render_b(
        request,
        "backoffice/platform_workbench.html",
        {
            "platform": platform,
            "businesses": businesses,
            "platform_tags_html": platform_tags_cell(platform),
        },
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def sku_editor(request, pk):
    sku = get_object_or_404(
        SKU.objects.select_related("business", "business__platform").prefetch_related(
            "channel_tags", "price_items", "quick_phrases", "member_images"
        ),
        pk=pk,
    )
    return _render_sku_editor(request, sku, is_create=False)


@superuser_required
@require_http_methods(["GET", "POST"])
def sku_editor_add(request):
    return _render_sku_editor(request, SKU(), is_create=True)


def _reorder_by_sort_ids(request, model, field="sort_order"):
    """Parse JSON ``{order: [id, ...]}`` and set ``model.<field>`` by index (0-based)."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "无效的 JSON"}, status=400)
    order = payload.get("order")
    if not isinstance(order, list) or not order:
        return JsonResponse({"ok": False, "error": "缺少排序列表"}, status=400)
    ids = []
    for x in order:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "无效的 ID"}, status=400)
    existing = set(model.objects.values_list("id", flat=True))
    if set(ids) != existing or len(ids) != len(existing):
        return JsonResponse({"ok": False, "error": "列表与服务器不一致，请刷新页面"}, status=400)
    with transaction.atomic():
        for i, pk in enumerate(ids):
            model.objects.filter(pk=pk).update(**{field: i})
    return JsonResponse({"ok": True})


@superuser_required
@require_http_methods(["POST"])
def platform_reorder(request):
    return _reorder_by_sort_ids(request, Platform)


@superuser_required
@require_http_methods(["POST"])
def payment_tutorial_reorder(request):
    return _reorder_by_sort_ids(request, PaymentTutorial)


@superuser_required
@require_http_methods(["POST"])
def platform_account_reorder(request):
    return _reorder_by_sort_ids(request, PlatformAccount)


@superuser_required
def business_list(request):
    return redirect("backoffice:platform_list")


@superuser_required
@require_http_methods(["GET", "POST"])
def business_add(request):
    initial = {}
    platform_id = (request.GET.get("platform_id") or "").strip()
    if platform_id:
        initial["platform"] = platform_id
    form = BusinessForm(request.POST or None, initial=initial)
    if platform_id:
        try:
            cancel_url = _workbench_url_for_platform(int(platform_id))
        except (TypeError, ValueError):
            cancel_url = reverse("backoffice:platform_list")
    else:
        cancel_url = reverse("backoffice:platform_list")
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, "业务已创建。")
        return redirect(_workbench_url_for_business(obj))
    return render_form(request, "新增业务", "选择所属平台。", form, cancel_url)


@superuser_required
@require_http_methods(["GET", "POST"])
def business_edit(request, pk):
    obj = get_object_or_404(Business.objects.prefetch_related("skus"), pk=pk)
    form = BusinessForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "业务已更新。")
        return redirect(_workbench_url_for_business(obj))
    return render_form(
        request,
        "编辑业务",
        "修改业务名称与状态。",
        form,
        _workbench_url_for_business(obj),
        delete_url=reverse("backoffice:business_delete", args=[obj.pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def business_delete(request, pk):
    obj = get_object_or_404(Business, pk=pk)
    workbench_url = _workbench_url_for_business(obj)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "业务已删除。")
        return redirect(workbench_url)
    return render_delete(request, "业务", obj.name, workbench_url)


@superuser_required
def sku_list(request):
    return redirect("backoffice:platform_list")


@superuser_required
def sku_add(request):
    url = reverse("backoffice:sku_editor_add")
    if request.GET:
        url = f"{url}?{request.GET.urlencode()}"
    return redirect(url)


@superuser_required
@require_http_methods(["GET", "POST"])
def sku_edit(request, pk):
    return redirect("backoffice:sku_editor", pk=pk)


@superuser_required
@require_http_methods(["GET", "POST"])
def sku_delete(request, pk):
    obj = get_object_or_404(SKU.objects.select_related("business"), pk=pk)
    workbench_url = _workbench_url_for_sku(obj)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "SKU已删除。")
        return redirect(workbench_url)
    return render_delete(request, "SKU", obj.name, workbench_url)


@superuser_required
def phrase_list(request):
    rows = []
    for obj in QuickPhrase.objects.select_related("sku").all():
        rows.append(
            {"cells": [escape(obj.sku.name), str(obj.order), escape(obj.content), action_links("backoffice:phrase_edit", "backoffice:phrase_delete", obj.pk)]}
        )
    return render_list(request, "快捷语管理", "快捷语挂在 SKU 下。", ["SKU", "排序", "内容", "操作"], rows, reverse("backoffice:phrase_add"), "新增快捷语")


@superuser_required
@require_http_methods(["GET", "POST"])
def phrase_add(request):
    initial = {}
    if request.GET.get("sku_id"):
        initial["sku"] = request.GET.get("sku_id")
    form = QuickPhraseForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, "快捷语已创建。")
        return redirect("backoffice:phrase_edit", pk=obj.pk)
    return render_form(request, "新增快捷语", "维护快捷语内容和排序。", form, reverse("backoffice:phrase_list"), wide_fields=["content"])


@superuser_required
@require_http_methods(["GET", "POST"])
def phrase_edit(request, pk):
    obj = get_object_or_404(QuickPhrase, pk=pk)
    form = QuickPhraseForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "快捷语已更新。")
        return redirect("backoffice:phrase_edit", pk=obj.pk)
    return render_form(request, "编辑快捷语", "维护内容。", form, reverse("backoffice:phrase_list"), delete_url=reverse("backoffice:phrase_delete", args=[obj.pk]), wide_fields=["content"])


@superuser_required
@require_http_methods(["GET", "POST"])
def phrase_delete(request, pk):
    obj = get_object_or_404(QuickPhrase, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "快捷语已删除。")
        return redirect("backoffice:phrase_list")
    return render_delete(request, "快捷语", obj.content[:20], reverse("backoffice:phrase_list"))


@ensure_csrf_cookie
@superuser_required
def payment_tutorial_list(request):
    rows = []
    drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
    for obj in PaymentTutorial.objects.all().order_by("sort_order", "id"):
        rows.append(
            {
                "sort_id": obj.pk,
                "cells": [
                    drag,
                    escape(obj.name),
                    format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', obj.detail_url, escape(obj.detail_url)),
                    action_links("backoffice:payment_tutorial_edit", "backoffice:payment_tutorial_delete", obj.pk),
                ],
            }
        )
    return render_list(
        request,
        "AAA图文远程",
        "维护 AAA 图文远程链接的名称与地址；拖动左侧「⋮⋮」调整顺序。与「教程池」互相独立。",
        ["排序", "名称", "详情链接", "操作"],
        rows,
        create_url=reverse("backoffice:payment_tutorial_add"),
        create_label="新增教程",
        sortable_reorder_url=reverse("backoffice:payment_tutorial_reorder"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def payment_tutorial_add(request):
    form = PaymentTutorialForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        max_o = PaymentTutorial.objects.exclude(pk=obj.pk).aggregate(m=Max("sort_order"))["m"] or 0
        obj.sort_order = max_o + 1
        obj.save(update_fields=["sort_order"])
        messages.success(request, "AAA图文远程条目已创建。")
        return redirect("backoffice:payment_tutorial_edit", pk=obj.pk)
    return render_form(
        request,
        "新增AAA图文远程",
        "填写名称与详情页链接。",
        form,
        reverse("backoffice:payment_tutorial_list"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def payment_tutorial_edit(request, pk):
    obj = get_object_or_404(PaymentTutorial, pk=pk)
    form = PaymentTutorialForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "AAA图文远程条目已更新。")
        return redirect("backoffice:payment_tutorial_edit", pk=obj.pk)
    return render_form(
        request,
        "编辑AAA图文远程",
        "保存后职员端列表将显示最新内容。",
        form,
        reverse("backoffice:payment_tutorial_list"),
        delete_url=reverse("backoffice:payment_tutorial_delete", args=[obj.pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def payment_tutorial_delete(request, pk):
    obj = get_object_or_404(PaymentTutorial, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "AAA图文远程条目已删除。")
        return redirect("backoffice:payment_tutorial_list")
    return render_delete(request, "AAA图文远程", obj.name, reverse("backoffice:payment_tutorial_list"))


def _make_link_page_views(*, prefix, model, form_class, noun, list_title, list_subtitle, link_header,
                          create_label, add_title, add_subtitle, edit_title, edit_subtitle):
    """同构的「名称 + 外链 + 启用 + 拖动排序」后台页面：生成 list/add/edit/delete/reorder 五个视图。"""

    def url(action, *args):
        return reverse(f"backoffice:{prefix}_{action}", args=args or None)

    @ensure_csrf_cookie
    @superuser_required
    def list_view(request):
        rows = []
        drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
        for obj in model.objects.all().order_by("sort_order", "id"):
            rows.append(
                {
                    "sort_id": obj.pk,
                    "cells": [
                        drag,
                        escape(obj.name),
                        format_html(
                            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                            obj.share_url,
                            escape(obj.share_url),
                        ),
                        "启用" if obj.is_active else "停用",
                        action_links(f"backoffice:{prefix}_edit", f"backoffice:{prefix}_delete", obj.pk),
                    ],
                }
            )
        return render_list(
            request,
            list_title,
            list_subtitle,
            ["排序", "页面名称", link_header, "状态", "操作"],
            rows,
            create_url=url("add"),
            create_label=create_label,
            sortable_reorder_url=url("reorder"),
        )

    @superuser_required
    @require_http_methods(["GET", "POST"])
    def add_view(request):
        form = form_class(request.POST or None)
        if request.method == "POST" and form.is_valid():
            obj = form.save()
            max_o = model.objects.exclude(pk=obj.pk).aggregate(m=Max("sort_order"))["m"] or 0
            obj.sort_order = max_o + 1
            obj.save(update_fields=["sort_order"])
            messages.success(request, f"{noun}已创建。")
            return redirect(f"backoffice:{prefix}_edit", pk=obj.pk)
        return render_form(request, add_title, add_subtitle, form, url("list"))

    @superuser_required
    @require_http_methods(["GET", "POST"])
    def edit_view(request, pk):
        obj = get_object_or_404(model, pk=pk)
        form = form_class(request.POST or None, instance=obj)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, f"{noun}已更新。")
            return redirect(f"backoffice:{prefix}_edit", pk=obj.pk)
        return render_form(
            request, edit_title, edit_subtitle, form, url("list"), delete_url=url("delete", obj.pk)
        )

    @superuser_required
    @require_http_methods(["GET", "POST"])
    def delete_view(request, pk):
        obj = get_object_or_404(model, pk=pk)
        if request.method == "POST":
            obj.delete()
            messages.success(request, f"{noun}已删除。")
            return redirect(f"backoffice:{prefix}_list")
        return render_delete(request, noun, obj.name, url("list"))

    @superuser_required
    @require_http_methods(["POST"])
    def reorder_view(request):
        return _reorder_by_sort_ids(request, model)

    for action, fn in (
        ("list", list_view), ("add", add_view), ("edit", edit_view),
        ("delete", delete_view), ("reorder", reorder_view),
    ):
        fn.__name__ = fn.__qualname__ = f"{prefix}_{action}"
    return list_view, add_view, edit_view, delete_view, reorder_view


(
    shared_apple_id_page_list,
    shared_apple_id_page_add,
    shared_apple_id_page_edit,
    shared_apple_id_page_delete,
    shared_apple_id_page_reorder,
) = _make_link_page_views(
    prefix="shared_apple_id_page",
    model=SharedAppleIDPage,
    form_class=SharedAppleIDPageForm,
    noun="共享苹果ID分享页",
    list_title="共享苹果ID分享页管理",
    list_subtitle="维护前端「共享苹果ID」页展示的分享链接；拖动左侧「⋮⋮」可调整展示顺序。",
    link_header="分享页链接",
    create_label="新增分享页",
    add_title="新增共享苹果ID分享页",
    add_subtitle="填写页面名称和分享页链接。",
    edit_title="编辑共享苹果ID分享页",
    edit_subtitle="保存后前端「共享苹果ID」页将显示最新链接。",
)

(
    pict_cart_page_list,
    pict_cart_page_add,
    pict_cart_page_edit,
    pict_cart_page_delete,
    pict_cart_page_reorder,
) = _make_link_page_views(
    prefix="pict_cart_page",
    model=PictCartPage,
    form_class=PictCartPageForm,
    noun="pict加购物车页面",
    list_title="pict加购物车页面管理",
    list_subtitle="维护前端「pict加购物车」页展示的外链；拖动左侧「⋮⋮」可调整展示顺序。",
    link_header="页面链接",
    create_label="新增页面",
    add_title="新增 pict加购物车页面",
    add_subtitle="填写页面名称和链接，前端将以嵌入方式展示。",
    edit_title="编辑 pict加购物车页面",
    edit_subtitle="保存后前端「pict加购物车」页将显示最新链接。",
)

(
    fanbox_stats_page_list,
    fanbox_stats_page_add,
    fanbox_stats_page_edit,
    fanbox_stats_page_delete,
    fanbox_stats_page_reorder,
) = _make_link_page_views(
    prefix="fanbox_stats_page",
    model=FanboxStatsPage,
    form_class=FanboxStatsPageForm,
    noun="fanbox投稿作品统计页面",
    list_title="fanbox投稿作品统计管理",
    list_subtitle="维护前端「fanbox投稿作品统计」页展示的外链；拖动左侧「⋮⋮」可调整展示顺序。",
    link_header="页面链接",
    create_label="新增页面",
    add_title="新增 fanbox投稿作品统计页面",
    add_subtitle="填写页面名称和链接，前端将以嵌入方式展示。",
    edit_title="编辑 fanbox投稿作品统计页面",
    edit_subtitle="保存后前端「fanbox投稿作品统计」页将显示最新链接。",
)

(
    service_monitor_page_list,
    service_monitor_page_add,
    service_monitor_page_edit,
    service_monitor_page_delete,
    service_monitor_page_reorder,
) = _make_link_page_views(
    prefix="service_monitor_page",
    model=ServiceMonitorPage,
    form_class=ServiceMonitorPageForm,
    noun="服务监控页面",
    list_title="服务监控页面管理",
    list_subtitle="维护前端「服务监控」页嵌入的 Uptime Kuma / 状态页链接；拖动左侧「⋮⋮」可调整展示顺序。",
    link_header="页面链接",
    create_label="新增页面",
    add_title="新增服务监控页面",
    add_subtitle="填写页面名称和 Uptime Kuma 访问链接，前端将以嵌入方式展示。",
    edit_title="编辑服务监控页面",
    edit_subtitle="保存后前端「服务监控」页将显示最新链接。",
)


@ensure_csrf_cookie
@superuser_required
def tutorial_pool_list(request):
    rows = []
    drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
    for obj in TutorialPool.objects.all().order_by("sort_order", "id"):
        rows.append(
            {
                "sort_id": obj.pk,
                "cells": [
                    drag,
                    escape(obj.name),
                    format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', obj.detail_url, escape(obj.detail_url)),
                    action_links("backoffice:tutorial_pool_edit", "backoffice:tutorial_pool_delete", obj.pk),
                ],
            }
        )
    return render_list(
        request,
        "教程池",
        "维护可复用的顾客教程；在 SKU 编辑器中从本池选取，不再批量发送到 SKU。",
        ["排序", "名称", "详情链接", "操作"],
        rows,
        create_url=reverse("backoffice:tutorial_pool_add"),
        create_label="新增教程",
        sortable_reorder_url=reverse("backoffice:tutorial_pool_reorder"),
    )


@superuser_required
@require_http_methods(["POST"])
def tutorial_pool_reorder(request):
    return _reorder_by_sort_ids(request, TutorialPool)


@superuser_required
@require_http_methods(["GET", "POST"])
def tutorial_pool_add(request):
    form = TutorialPoolForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        max_o = TutorialPool.objects.exclude(pk=obj.pk).aggregate(m=Max("sort_order"))["m"] or 0
        obj.sort_order = max_o + 1
        obj.save(update_fields=["sort_order"])
        messages.success(request, "教程已加入教程池。")
        return redirect("backoffice:tutorial_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "新增教程",
        "填写教程名称与详情页链接。",
        form,
        reverse("backoffice:tutorial_pool_list"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def tutorial_pool_edit(request, pk):
    obj = get_object_or_404(TutorialPool, pk=pk)
    form = TutorialPoolForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "教程已更新。")
        return redirect("backoffice:tutorial_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "编辑教程",
        "保存后职员端可通过 SKU 关联展示最新链接。",
        form,
        reverse("backoffice:tutorial_pool_list"),
        delete_url=reverse("backoffice:tutorial_pool_delete", args=[obj.pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def tutorial_pool_delete(request, pk):
    obj = get_object_or_404(TutorialPool, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "教程已从教程池删除。")
        return redirect("backoffice:tutorial_pool_list")
    return render_delete(request, "教程", obj.name, reverse("backoffice:tutorial_pool_list"))


@ensure_csrf_cookie
@superuser_required
def phrase_pool_list(request):
    rows = []
    drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
    for obj in PhrasePool.objects.all().order_by("sort_order", "id"):
        preview = (obj.content or "").replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:80] + "…"
        rows.append(
            {
                "sort_id": obj.pk,
                "cells": [
                    drag,
                    escape(obj.name),
                    escape(preview or "—"),
                    action_links("backoffice:phrase_pool_edit", "backoffice:phrase_pool_delete", obj.pk),
                ],
            }
        )
    return render_list(
        request,
        "话术池",
        "维护可复用的客服话术；在 SKU 编辑器中从本池选取，不再批量发送到 SKU。",
        ["排序", "名称", "内容预览", "操作"],
        rows,
        create_url=reverse("backoffice:phrase_pool_add"),
        create_label="新增话术",
        sortable_reorder_url=reverse("backoffice:phrase_pool_reorder"),
    )


@superuser_required
@require_http_methods(["POST"])
def phrase_pool_reorder(request):
    return _reorder_by_sort_ids(request, PhrasePool)


@superuser_required
@require_http_methods(["GET", "POST"])
def phrase_pool_add(request):
    form = PhrasePoolForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        max_o = PhrasePool.objects.exclude(pk=obj.pk).aggregate(m=Max("sort_order"))["m"] or 0
        obj.sort_order = max_o + 1
        obj.save(update_fields=["sort_order"])
        messages.success(request, "话术已加入话术池。")
        return redirect("backoffice:phrase_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "新增话术",
        "填写话术名称与完整内容。",
        form,
        reverse("backoffice:phrase_pool_list"),
        wide_fields=["content"],
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def phrase_pool_edit(request, pk):
    obj = get_object_or_404(PhrasePool, pk=pk)
    form = PhrasePoolForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "话术已更新。")
        return redirect("backoffice:phrase_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "编辑话术",
        "保存后可在 SKU 编辑器中选取本话术。",
        form,
        reverse("backoffice:phrase_pool_list"),
        delete_url=reverse("backoffice:phrase_pool_delete", args=[obj.pk]),
        wide_fields=["content"],
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def phrase_pool_delete(request, pk):
    obj = get_object_or_404(PhrasePool, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "话术已从话术池删除。")
        return redirect("backoffice:phrase_pool_list")
    return render_delete(request, "话术", obj.name, reverse("backoffice:phrase_pool_list"))


@ensure_csrf_cookie
@superuser_required
def platform_tag_pool_list(request):
    rows = []
    drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
    for obj in PlatformTagPool.objects.all().order_by("order", "id"):
        rows.append(
            {
                "sort_id": obj.pk,
                "cells": [
                    drag,
                    escape(obj.name),
                    action_links("backoffice:platform_tag_pool_edit", "backoffice:platform_tag_pool_delete", obj.pk),
                ],
            }
        )
    return render_list(
        request,
        "标签池",
        "维护平台标签；在平台编辑器中从本池选取。",
        ["排序", "名称", "操作"],
        rows,
        create_url=reverse("backoffice:platform_tag_pool_add"),
        create_label="新增标签",
        sortable_reorder_url=reverse("backoffice:platform_tag_pool_reorder"),
    )


@superuser_required
@require_http_methods(["POST"])
def platform_tag_pool_reorder(request):
    return _reorder_by_sort_ids(request, PlatformTagPool, "order")


@superuser_required
@require_http_methods(["POST"])
def platform_tag_pool_quick_add(request):
    """平台编辑页内快速向标签池追加标签。"""
    form = PlatformTagPoolQuickForm(request.POST)
    next_url = (request.POST.get("next") or "").strip() or reverse("backoffice:platform_tag_pool_list")
    if form.is_valid():
        obj = form.save()
        max_o = PlatformTagPool.objects.exclude(pk=obj.pk).aggregate(m=Max("order"))["m"] or 0
        obj.order = max_o + 1
        obj.save(update_fields=["order"])
        messages.success(request, f"标签「{obj.name}」已加入标签池。")
        return _redirect_platform_edit(next_url, pick_platform_tag=obj.pk)
    err = "；".join(
        f"{fields}: {', '.join(errors)}" for fields, errors in form.errors.items()
    ) or "请检查名称是否重复"
    messages.error(request, f"添加标签失败：{err}")
    return redirect(next_url)


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_tag_pool_add(request):
    form = PlatformTagPoolForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        max_o = PlatformTagPool.objects.exclude(pk=obj.pk).aggregate(m=Max("order"))["m"] or 0
        obj.order = max_o + 1
        obj.save(update_fields=["order"])
        messages.success(request, "标签已加入标签池。")
        return redirect("backoffice:platform_tag_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "新增平台标签",
        "填写标签名称；排序可在列表页拖拽调整。",
        form,
        reverse("backoffice:platform_tag_pool_list"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_tag_pool_edit(request, pk):
    obj = get_object_or_404(PlatformTagPool, pk=pk)
    form = PlatformTagPoolForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "标签已更新。")
        return redirect("backoffice:platform_tag_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "编辑平台标签",
        "保存后关联的平台将显示最新标签名。",
        form,
        reverse("backoffice:platform_tag_pool_list"),
        delete_url=reverse("backoffice:platform_tag_pool_delete", args=[obj.pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_tag_pool_delete(request, pk):
    obj = get_object_or_404(PlatformTagPool, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "标签已从标签池删除。")
        return redirect("backoffice:platform_tag_pool_list")
    return render_delete(request, "平台标签", obj.name, reverse("backoffice:platform_tag_pool_list"))


@ensure_csrf_cookie
@superuser_required
def channel_tag_pool_list(request):
    rows = []
    drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
    for obj in ChannelTagPool.objects.all().order_by("order", "id"):
        rows.append(
            {
                "sort_id": obj.pk,
                "cells": [
                    drag,
                    escape(obj.name),
                    action_links("backoffice:channel_tag_pool_edit", "backoffice:channel_tag_pool_delete", obj.pk),
                ],
            }
        )
    return render_list(
        request,
        "渠道池",
        "维护渠道标签；在 SKU 编辑器中从本池选取。",
        ["排序", "名称", "操作"],
        rows,
        create_url=reverse("backoffice:channel_tag_pool_add"),
        create_label="新增渠道",
        sortable_reorder_url=reverse("backoffice:channel_tag_pool_reorder"),
    )


@superuser_required
@require_http_methods(["POST"])
def channel_tag_pool_reorder(request):
    return _reorder_by_sort_ids(request, ChannelTagPool, "order")


@superuser_required
@require_http_methods(["POST"])
def channel_tag_pool_quick_add(request):
    """SKU 编辑器内快速向渠道池追加标签。"""
    form = ChannelTagPoolQuickForm(request.POST)
    next_url = (request.POST.get("next") or "").strip() or reverse("backoffice:channel_tag_pool_list")
    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if form.is_valid():
        obj = form.save()
        max_o = ChannelTagPool.objects.exclude(pk=obj.pk).aggregate(m=Max("order"))["m"] or 0
        obj.order = max_o + 1
        obj.save(update_fields=["order"])
        msg = f"渠道「{obj.name}」已加入渠道池。"
        if wants_json:
            return JsonResponse({"ok": True, "id": obj.pk, "name": obj.name, "message": msg})
        messages.success(request, msg)
        return _redirect_editor_anchor(next_url, pick_channel=obj.pk)
    err = "；".join(
        f"{fields}: {', '.join(errors)}" for fields, errors in form.errors.items()
    ) or "请检查名称是否重复"
    if wants_json:
        return JsonResponse({"ok": False, "error": err}, status=400)
    messages.error(request, f"添加渠道失败：{err}")
    return redirect(next_url)


@superuser_required
@require_http_methods(["GET", "POST"])
def channel_tag_pool_add(request):
    form = ChannelTagPoolForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        max_o = ChannelTagPool.objects.exclude(pk=obj.pk).aggregate(m=Max("order"))["m"] or 0
        obj.order = max_o + 1
        obj.save(update_fields=["order"])
        messages.success(request, "渠道已加入渠道池。")
        return redirect("backoffice:channel_tag_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "新增渠道标签",
        "填写渠道名称；排序可在列表页拖拽调整。",
        form,
        reverse("backoffice:channel_tag_pool_list"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def channel_tag_pool_edit(request, pk):
    obj = get_object_or_404(ChannelTagPool, pk=pk)
    form = ChannelTagPoolForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "渠道已更新。")
        return redirect("backoffice:channel_tag_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "编辑渠道标签",
        "保存后关联的 SKU 将显示最新渠道名。",
        form,
        reverse("backoffice:channel_tag_pool_list"),
        delete_url=reverse("backoffice:channel_tag_pool_delete", args=[obj.pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def channel_tag_pool_delete(request, pk):
    obj = get_object_or_404(ChannelTagPool, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "渠道已从渠道池删除。")
        return redirect("backoffice:channel_tag_pool_list")
    return render_delete(request, "渠道标签", obj.name, reverse("backoffice:channel_tag_pool_list"))


@ensure_csrf_cookie
@superuser_required
def usd_proxy_price_pool_list(request):
    rows = []
    drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
    for obj in UsdProxyPriceTier.objects.all().order_by("sort_order", "id"):
        rows.append(
            {
                "sort_id": obj.pk,
                "cells": [
                    drag,
                    escape(obj.usd_range),
                    format_html("{}%", obj.rate_percent),
                    action_links(
                        "backoffice:usd_proxy_price_pool_edit",
                        "backoffice:usd_proxy_price_pool_delete",
                        obj.pk,
                    ),
                ],
            }
        )
    return render_list(
        request,
        "美金代付价格池",
        "维护按美金代付的费率表；SKU 选择「按美金代付收费」时将引用本表。",
        ["排序", "美金", "费率", "操作"],
        rows,
        create_url=reverse("backoffice:usd_proxy_price_pool_add"),
        create_label="新增档位",
        sortable_reorder_url=reverse("backoffice:usd_proxy_price_pool_reorder"),
    )


@superuser_required
@require_http_methods(["POST"])
def usd_proxy_price_pool_reorder(request):
    return _reorder_by_sort_ids(request, UsdProxyPriceTier)


@superuser_required
@require_http_methods(["GET", "POST"])
def usd_proxy_price_pool_add(request):
    form = UsdProxyPriceTierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        max_o = UsdProxyPriceTier.objects.exclude(pk=obj.pk).aggregate(m=Max("sort_order"))["m"] or 0
        obj.sort_order = max_o + 1
        obj.save(update_fields=["sort_order"])
        messages.success(request, "档位已加入美金代付价格池。")
        return redirect("backoffice:usd_proxy_price_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "新增美金代付档位",
        "填写美金区间与对应费率百分比。",
        form,
        reverse("backoffice:usd_proxy_price_pool_list"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def usd_proxy_price_pool_edit(request, pk):
    obj = get_object_or_404(UsdProxyPriceTier, pk=pk)
    form = UsdProxyPriceTierForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "美金代付档位已保存。")
        return redirect("backoffice:usd_proxy_price_pool_edit", pk=obj.pk)
    return render_form(
        request,
        "编辑美金代付档位",
        "修改美金区间或费率。",
        form,
        reverse("backoffice:usd_proxy_price_pool_list"),
        delete_url=reverse("backoffice:usd_proxy_price_pool_delete", args=[obj.pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def usd_proxy_price_pool_delete(request, pk):
    obj = get_object_or_404(UsdProxyPriceTier, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "美金代付档位已删除。")
        return redirect("backoffice:usd_proxy_price_pool_list")
    return render_delete(
        request,
        "美金代付档位",
        f"{obj.usd_range}（{obj.rate_percent}%）",
        reverse("backoffice:usd_proxy_price_pool_list"),
    )


@ensure_csrf_cookie
@superuser_required
def platform_account_list(request):
    rows = []
    drag = mark_safe('<span class="bb-drag-handle" title="拖动排序">⋮⋮</span>')
    for obj in PlatformAccount.objects.all().order_by("sort_order", "id"):
        rows.append(
            {
                "sort_id": obj.pk,
                "cells": [
                    drag,
                    escape(obj.name),
                    escape(obj.account),
                    escape(obj.password),
                    escape(obj.url or "—"),
                    escape(obj.note or "—"),
                    action_links("backoffice:platform_account_edit", "backoffice:platform_account_delete", obj.pk),
                ],
            }
        )
    return render_list(
        request,
        "平台账号密码管理",
        "维护前端「平台账号密码」页的数据来源。拖动左侧「⋮⋮」调整表格展示顺序。",
        ["排序", "平台", "账号", "密码", "网址链接", "备注", "操作"],
        rows,
        create_url=reverse("backoffice:platform_account_add"),
        create_label="新增平台账号",
        sortable_reorder_url=reverse("backoffice:platform_account_reorder"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_account_add(request):
    form = PlatformAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        max_o = PlatformAccount.objects.exclude(pk=obj.pk).aggregate(m=Max("sort_order"))["m"] or 0
        obj.sort_order = max_o + 1
        obj.save(update_fields=["sort_order"])
        messages.success(request, "平台账号已创建。")
        return redirect("backoffice:platform_account_edit", pk=obj.pk)
    return render_form(
        request,
        "新增平台账号",
        "填写平台、账号、密码与链接。",
        form,
        reverse("backoffice:platform_account_list"),
        wide_fields=["note"],
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_account_edit(request, pk):
    obj = get_object_or_404(PlatformAccount, pk=pk)
    form = PlatformAccountForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "平台账号已更新。")
        return redirect("backoffice:platform_account_edit", pk=obj.pk)
    return render_form(
        request,
        "编辑平台账号",
        "可更新账号、密码、链接和备注。",
        form,
        reverse("backoffice:platform_account_list"),
        delete_url=reverse("backoffice:platform_account_delete", args=[obj.pk]),
        wide_fields=["note"],
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def platform_account_delete(request, pk):
    obj = get_object_or_404(PlatformAccount, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "平台账号已删除。")
        return redirect("backoffice:platform_account_list")
    return render_delete(request, "平台账号", obj.name, reverse("backoffice:platform_account_list"))


@superuser_required
def user_list(request):
    User = get_user_model()
    rows = []
    for obj in User.objects.filter(is_staff=True).select_related("staff_login_meta").order_by("id"):
        if obj.is_superuser:
            role = "管理员"
        elif is_boss(obj):
            role = "老板"
        elif is_ceo(obj):
            role = "CEO"
        elif is_guest(obj):
            role = "游客/访客"
        else:
            role = "员工"
        active = "启用" if obj.is_active else "停用"
        if obj.last_login:
            last_login = timezone.localtime(obj.last_login).strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_login = "—"
        meta = getattr(obj, "staff_login_meta", None)
        last_ip = (meta.last_login_ip if meta else "") or "—"
        rows.append(
            {
                "cells": [
                    escape(obj.username),
                    role,
                    active,
                    last_login,
                    escape(last_ip),
                    action_links("backoffice:user_edit", "backoffice:user_delete", obj.pk),
                ]
            }
        )
    return render_list(
        request,
        "前端用户管理",
        "维护职员端登录账号：可新增员工、CEO、管理员、老板与游客/访客，并分配权限等级。",
        ["用户名", "权限等级", "状态", "最近登录", "最近IP", "操作"],
        rows,
        create_url=reverse("backoffice:user_add"),
        create_label="新增用户",
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def user_add(request):
    form = StaffUserForm(request.POST or None, require_password=True)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"用户「{obj.username}」已创建。")
        return redirect("backoffice:user_edit", pk=obj.pk)
    return render_form(
        request,
        "新增用户",
        "可创建员工或管理员账号。",
        form,
        reverse("backoffice:user_list"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def user_edit(request, pk):
    User = get_user_model()
    obj = get_object_or_404(User, pk=pk, is_staff=True)
    form = StaffUserForm(request.POST or None, instance=obj, require_password=False)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"用户「{obj.username}」已更新。")
        return redirect("backoffice:user_edit", pk=obj.pk)
    return render_form(
        request,
        "编辑用户",
        "可调整权限等级、启用状态和密码。",
        form,
        reverse("backoffice:user_list"),
        delete_url=reverse("backoffice:user_delete", args=[obj.pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def user_delete(request, pk):
    User = get_user_model()
    obj = get_object_or_404(User, pk=pk, is_staff=True)
    if request.method == "POST":
        if obj.pk == request.user.pk:
            messages.error(request, "不能删除当前登录账号。")
            return redirect("backoffice:user_list")
        if obj.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
            messages.error(request, "至少需要保留一个启用中的管理员。")
            return redirect("backoffice:user_list")
        obj.delete()
        messages.success(request, "用户已删除。")
        return redirect("backoffice:user_list")
    return render_delete(request, "用户", obj.username, reverse("backoffice:user_list"))


def _payment_page_query(request, page_number):
    q = request.GET.copy()
    if page_number:
        q["page"] = str(page_number)
    elif "page" in q:
        del q["page"]
    return q.urlencode()


def _payment_record_screenshot_cell(obj):
    urls = []
    if obj.screenshot:
        urls.append(obj.screenshot.url)
    for ei in obj.extra_images.all():
        try:
            urls.append(ei.image.url)
        except ValueError:
            continue
    if not urls:
        return "—"
    chunks = []
    for i, url in enumerate(urls):
        if obj.screenshot and i == 0:
            label = "主图"
        elif obj.screenshot:
            label = f"附{i}"
        else:
            label = f"附{i + 1}"
        chunks.append(
            format_html(
                (
                    '<a class="js-bb-payment-img bb-payment-img-item" href="{}" data-bb-idx="{}" '
                    'title="点击查看大图：{}" aria-label="点击查看大图：{}">'
                    '<img class="bb-payment-img-thumb" src="{}" alt="{}缩略图" loading="lazy" decoding="async" />'
                    '<span class="bb-payment-img-tag">{}</span>'
                    "</a>"
                ),
                url,
                i,
                label,
                label,
                url,
                label,
                label,
            )
        )
    # 图集由前端从同容器内所有 .js-bb-payment-img 的 href 收集，避免 data-bb-gallery JSON 在属性里被截断/解析失败
    return format_html('<span class="bb-payment-imgs">{}</span>', mark_safe(" ".join(chunks)))


@superuser_required
def payment_record_list(request):
    qs, filter_form = filtered_payment_records_qs(request.GET)
    paginator = Paginator(qs, PAYMENT_RECORD_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    records = prefetch_payment_record_images(page_obj.object_list)

    rows = []
    for obj in records:
        note = (obj.note or "").strip()
        if len(note) > 48:
            note = note[:47] + "…"
        created_local = timezone.localtime(obj.created_at).strftime("%Y-%m-%d %H:%M:%S")
        rows.append(
            {
                "cells": [
                    escape(obj.get_channel_display()),
                    str(obj.order_count),
                    str(obj.amount),
                    escape(obj.user.username),
                    obj.record_date.isoformat(),
                    created_local,
                    escape(note) if note else "—",
                    _payment_record_screenshot_cell(obj),
                    action_links(
                        "backoffice:payment_record_edit",
                        "backoffice:payment_record_delete",
                        obj.pk,
                    ),
                ]
            }
        )
    return render_b(
        request,
        "backoffice/payment_record_list.html",
        {
            "title": "订单记录管理",
            "subtitle": "与职员端「收款统计」同源数据；仅超级管理员可在此增删改查。",
            "headers": ["渠道", "订单数", "金额", "填写人", "订单时间", "填写时间", "备注", "截图", "操作"],
            "rows": rows,
            "create_url": reverse("backoffice:payment_record_add"),
            "create_label": "新增记录",
            "filter_form": filter_form,
            "reset_list_url": reverse("backoffice:payment_record_list"),
            "page_obj": page_obj,
            "pagination_query": _payment_page_query(request, None),
        },
    )


@superuser_required
def payment_record_export(request):
    """导出当前 GET 筛选条件下的订单记录（Excel，无图片）。"""
    qs, _ = filtered_payment_records_qs(request.GET)
    return payment_records_xlsx_response(qs)


@superuser_required
@require_http_methods(["GET", "POST"])
def payment_record_add(request):
    form = PaymentRecordAdminForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"已创建一条订单记录（{obj.get_channel_display()}）。")
        return redirect("backoffice:payment_record_edit", pk=obj.pk)
    return render_form(
        request,
        "新增订单记录",
        "可代员工录入或修正渠道、订单数、金额与主截图。",
        form,
        reverse("backoffice:payment_record_list"),
        wide_fields=["note"],
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def payment_record_edit(request, pk):
    obj = get_object_or_404(PaymentRecord.objects.prefetch_related("extra_images"), pk=pk)
    if request.method == "POST":
        form = PaymentRecordAdminForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            with transaction.atomic():
                record = form.save()
                handle_payment_record_images(request, record)
            messages.success(request, "订单记录已更新。")
            return redirect("backoffice:payment_record_edit", pk=obj.pk)
    else:
        form = PaymentRecordAdminForm(instance=obj)

    payment_images = []
    if obj.screenshot:
        payment_images.append({"kind": "main", "id": None, "url": obj.screenshot.url})
    for img in obj.extra_images.all():
        try:
            payment_images.append({"kind": "extra", "id": img.pk, "url": img.image.url})
        except ValueError:
            continue

    return render_b(
        request,
        "backoffice/payment_record_edit.html",
        {
            "form": form,
            "record": obj,
            "payment_images": payment_images,
            "cancel_url": reverse("backoffice:payment_record_list"),
            "delete_url": reverse("backoffice:payment_record_delete", args=[obj.pk]),
        },
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def payment_record_delete(request, pk):
    obj = get_object_or_404(PaymentRecord, pk=pk)
    if request.method == "POST":
        label = f"{obj.get_channel_display()} / {obj.amount}"
        obj.delete()
        messages.success(request, f"已删除：{label}")
        return redirect("backoffice:payment_record_list")
    return render_delete(
        request,
        "订单记录",
        f"{obj.get_channel_display()} · {obj.amount} · {obj.user.username}",
        reverse("backoffice:payment_record_list"),
    )


def _hall_body_preview(obj, limit=72):
    t = (obj.body or "").replace("\r", " ").replace("\n", " ").strip()
    if len(t) > limit:
        return escape(t[: limit - 1] + "…")
    return escape(t) if t else "—"


@superuser_required
def hall_block_list(request):
    rows = []
    for obj in HallBlock.objects.prefetch_related("images").all().order_by("-is_pinned", "sort_order", "id"):
        img_count = obj.images.count()
        if not img_count and obj.image:
            img_count = 1
        rows.append(
            {
                "cells": [
                    escape(obj.title),
                    "置顶" if obj.is_pinned else "普通",
                    str(obj.sort_order),
                    _hall_body_preview(obj),
                    str(img_count) if img_count else "—",
                    action_links("backoffice:hall_block_edit", "backoffice:hall_block_delete", obj.pk),
                ]
            }
        )
    return render_list(
        request,
        "大厅内容管理",
        "此处维护的板块会出现在前端「大厅」页；置顶项始终排在最前（同置顶内按排序数字）。",
        ["标题", "置顶", "排序", "正文摘要", "配图数", "操作"],
        rows,
        create_url=reverse("backoffice:hall_block_add"),
        create_label="新增板块",
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def hall_block_add(request):
    return _render_hall_block_form(
        request,
        block=None,
        title="新增大厅板块",
        subtitle="填写标题与正文；配图可上传多张缩略图管理。排序数字越小越靠前。",
        cancel_url=reverse("backoffice:hall_block_list"),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def hall_block_edit(request, pk):
    obj = HallBlock.objects.filter(pk=pk).prefetch_related("images").first()
    if obj is None:
        messages.warning(request, "该大厅板块不存在或已被删除，请从列表重新操作。")
        return redirect("backoffice:hall_block_list")
    return _render_hall_block_form(
        request,
        block=obj,
        title="编辑大厅板块",
        subtitle="保存后立即对前端大厅生效；置顶板块排在列表最前。",
        cancel_url=reverse("backoffice:hall_block_list"),
        delete_url=reverse("backoffice:hall_block_delete", args=[obj.pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def hall_block_delete(request, pk):
    obj = HallBlock.objects.filter(pk=pk).first()
    if obj is None:
        messages.warning(request, "该大厅板块不存在或已被删除。")
        return redirect("backoffice:hall_block_list")
    if request.method == "POST":
        obj.delete()
        messages.success(request, "大厅板块已删除。")
        return redirect("backoffice:hall_block_list")
    return render_delete(request, "大厅板块", obj.title, reverse("backoffice:hall_block_list"))


@superuser_required
def tag_list(request):
    return redirect("backoffice:platform_tag_pool_list")


@superuser_required
def tag_add(request):
    return redirect("backoffice:platform_tag_pool_add")


@superuser_required
@require_http_methods(["GET", "POST"])
def tag_delete(request, pk):
    obj = get_object_or_404(Tag, pk=pk)
    back = "backoffice:platform_tag_pool_list"
    if obj.type == Tag.TYPE_CHANNEL:
        back = "backoffice:channel_tag_pool_list"
    if request.method == "POST":
        obj.delete()
        messages.success(request, "已删除。")
        return redirect(back)
    return render_delete(request, "标签", obj.name, reverse(back))


SUBSCRIPTION_REMINDER_PAGE_SIZE = 30


def _subscription_page_query(request):
    q = request.GET.copy()
    if "page" in q:
        del q["page"]
    return q.urlencode()


def _subscription_reminder_list_qs(request):
    qs = SubscriptionReminder.objects.select_related("user", "platform_option").all()
    filter_form = SubscriptionReminderFilterForm(request.GET or None)
    if filter_form.is_valid():
        cd = filter_form.cleaned_data
        if cd.get("user"):
            qs = qs.filter(user=cd["user"])
        q = (cd.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(wechat_label__icontains=q)
                | Q(platform_option__name__icontains=q)
                | Q(remark__icontains=q)
            )
    return qs.order_by("next_reminder_at", "id"), filter_form


def _subscription_reminder_is_modal(request):
    return request.headers.get("X-BB-Modal") == "1"


def _subscription_reminder_modal_fragment(request, *, title, subtitle, form, form_post_url, delete_url=None, status=200):
    return render(
        request,
        "backoffice/subscription_reminder_modal_form.html",
        {
            "title": title,
            "subtitle": subtitle,
            "form": form,
            "form_post_url": form_post_url,
            "delete_url": delete_url,
            "platform_datalist_options": SubscriptionPlatformOption.objects.order_by("sort_order", "id"),
        },
        status=status,
    )


@superuser_required
def subscription_reminder_list(request):
    total_all = SubscriptionReminder.objects.count()
    qs, filter_form = _subscription_reminder_list_qs(request)
    total_filtered = qs.count()
    paginator = Paginator(qs, SUBSCRIPTION_REMINDER_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    rows = []
    today = timezone.localdate()
    for obj in page_obj.object_list:
        nxt = obj.next_reminder_at
        if nxt is None:
            status_html = "未设日期"
        elif nxt < today:
            status_html = "已逾期"
        elif nxt == today:
            status_html = "今日待跟进"
        else:
            status_html = "待提醒"
        renewed = "—"
        if obj.last_renewed_at:
            renewed = timezone.localtime(obj.last_renewed_at).strftime("%Y-%m-%d %H:%M")
        pname = getattr(obj.platform_option, "name", "") or "—"
        staff_cell = format_html(
            '<span class="bb-sub-staff"><span class="bb-sub-staff__name">{}</span>'
            '<span class="bb-sub-staff__meta">用户编号 {}</span></span>',
            obj.user.username,
            obj.user.pk,
        )
        remark_cell = escape((obj.remark or "").strip() or "—")
        rows.append(
            {
                "cells": [
                    staff_cell,
                    escape(obj.wechat_label),
                    escape(pname),
                    remark_cell,
                    escape(nxt.strftime("%Y-%m-%d") if nxt else "—"),
                    escape(renewed),
                    escape(status_html),
                    format_html(
                        '<button type="button" class="bb-btn bb-sub-rem-open-edit" data-modal-url="{}">编辑</button> {}',
                        reverse("backoffice:subscription_reminder_modal_edit", args=[obj.pk]),
                        delete_action_link("backoffice:subscription_reminder_delete", obj.pk),
                    ),
                ]
            }
        )
    auto_open_modal_url = None
    if (request.GET.get("open_add") or "") == "1":
        auto_open_modal_url = reverse("backoffice:subscription_reminder_modal_add")
    else:
        raw_edit = (request.GET.get("edit") or "").strip()
        if raw_edit.isdigit():
            if SubscriptionReminder.objects.filter(pk=int(raw_edit)).exists():
                auto_open_modal_url = reverse("backoffice:subscription_reminder_modal_edit", args=[int(raw_edit)])
    return render_b(
        request,
        "backoffice/subscription_reminder_list.html",
        {
            "title": "订阅提醒管理",
            "subtitle": "查看全员订阅到期记录（与职员端同源）。首列为所属员工（职员登录账号及用户编号）。下方统计为全部条数与当前筛选条数。",
            "headers": [
                "所属员工",
                "微信名/微信号",
                "订阅平台",
                "备注",
                "下次提醒日期",
                "上次续费登记",
                "状态",
                "操作",
            ],
            "rows": rows,
            "filter_form": filter_form,
            "reset_list_url": reverse("backoffice:subscription_reminder_list"),
            "total_all": total_all,
            "total_filtered": total_filtered,
            "modal_add_url": reverse("backoffice:subscription_reminder_modal_add"),
            "auto_open_modal_url": auto_open_modal_url,
            "page_obj": page_obj,
            "pagination_query": _subscription_page_query(request),
        },
    )


@superuser_required
@require_http_methods(["GET"])
def subscription_reminder_modal_add(request):
    form = SubscriptionReminderAdminForm()
    return _subscription_reminder_modal_fragment(
        request,
        title="新增订阅提醒",
        subtitle="可代员工录入；负责人决定该条在谁的前端列表中可见、可改。",
        form=form,
        form_post_url=reverse("backoffice:subscription_reminder_add"),
        delete_url=None,
    )


@superuser_required
@require_http_methods(["GET"])
def subscription_reminder_modal_edit(request, pk):
    obj = get_object_or_404(SubscriptionReminder.objects.select_related("user", "platform_option"), pk=pk)
    form = SubscriptionReminderAdminForm(instance=obj)
    return _subscription_reminder_modal_fragment(
        request,
        title="编辑订阅提醒",
        subtitle="修改后职员端列表与续费登记展示会同步更新。",
        form=form,
        form_post_url=reverse("backoffice:subscription_reminder_edit", args=[pk]),
        delete_url=reverse("backoffice:subscription_reminder_delete", args=[pk]),
    )


@superuser_required
@require_http_methods(["GET", "POST"])
def subscription_reminder_add(request):
    if request.method == "GET":
        return redirect(f"{reverse('backoffice:subscription_reminder_list')}?open_add=1")
    form = SubscriptionReminderAdminForm(request.POST)
    modal = _subscription_reminder_is_modal(request)
    if form.is_valid():
        obj = form.save()
        messages.success(request, f"已创建订阅提醒：{obj.wechat_label}。")
        if modal:
            return JsonResponse({"ok": True, "redirect": reverse("backoffice:subscription_reminder_list")})
        return redirect("backoffice:subscription_reminder_list")
    if modal:
        return _subscription_reminder_modal_fragment(
            request,
            title="新增订阅提醒",
            subtitle="可代员工录入；负责人决定该条在谁的前端列表中可见、可改。",
            form=form,
            form_post_url=reverse("backoffice:subscription_reminder_add"),
            delete_url=None,
            status=422,
        )
    return redirect(f"{reverse('backoffice:subscription_reminder_list')}?open_add=1")


@superuser_required
@require_http_methods(["GET", "POST"])
def subscription_reminder_edit(request, pk):
    obj = get_object_or_404(SubscriptionReminder.objects.select_related("user", "platform_option"), pk=pk)
    if request.method == "GET":
        return redirect(f"{reverse('backoffice:subscription_reminder_list')}?edit={pk}")
    form = SubscriptionReminderAdminForm(request.POST, instance=obj)
    modal = _subscription_reminder_is_modal(request)
    if form.is_valid():
        form.save()
        messages.success(request, "订阅提醒已更新。")
        if modal:
            return JsonResponse({"ok": True, "redirect": reverse("backoffice:subscription_reminder_list")})
        return redirect("backoffice:subscription_reminder_list")
    if modal:
        return _subscription_reminder_modal_fragment(
            request,
            title="编辑订阅提醒",
            subtitle="修改后职员端列表与续费登记展示会同步更新。",
            form=form,
            form_post_url=reverse("backoffice:subscription_reminder_edit", args=[pk]),
            delete_url=reverse("backoffice:subscription_reminder_delete", args=[pk]),
            status=422,
        )
    return redirect(f"{reverse('backoffice:subscription_reminder_list')}?edit={pk}")


@superuser_required
@require_http_methods(["GET", "POST"])
def subscription_reminder_delete(request, pk):
    obj = get_object_or_404(SubscriptionReminder.objects.select_related("platform_option"), pk=pk)
    pname = getattr(obj.platform_option, "name", "") or "—"
    if request.method == "POST":
        label = f"{obj.wechat_label} / {pname}"
        obj.delete()
        messages.success(request, f"已删除：{label}")
        return redirect("backoffice:subscription_reminder_list")
    return render_delete(
        request,
        "订阅提醒",
        f"{obj.wechat_label} · {pname} · {obj.user.username}",
        reverse("backoffice:subscription_reminder_list"),
    )
