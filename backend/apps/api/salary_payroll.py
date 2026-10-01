"""工资核算：业绩汇总、底薪、三类提成计算。"""

import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.utils import timezone

from backend.apps.catalog.models import (
    PAYMENT_CHANNELS,
    PaymentRecord,
    StaffSalaryMonthEntry,
    StaffSalaryProfile,
)
from backend.apps.catalog.roles import BOSS_GROUP_NAME, CEO_GROUP_NAME

from .data_screen import _money_two_decimals

_REFUND_CHANNEL = "退款项"
_RATE_GMV_EX = Decimal("0.02")
_RATE_SHILEI = Decimal("0.10")
_RATE_YINLI_NET = Decimal("0.005")  # 实发工资公式：引力币 × 0.5%
_Q = Decimal("0.01")


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _parse_year_month(request) -> tuple[int, int]:
    now = timezone.localdate()
    raw = (request.GET.get("month") or request.data.get("month") or "").strip()
    if raw and len(raw) >= 7 and raw[4] == "-":
        try:
            y, m = int(raw[:4]), int(raw[5:7])
            if 1 <= m <= 12:
                return y, m
        except ValueError:
            pass
    return now.year, now.month


def _payroll_personnel_queryset():
    User = get_user_model()
    return (
        User.objects.filter(is_staff=True, is_active=True, is_superuser=False)
        .exclude(groups__name=BOSS_GROUP_NAME)
        .order_by("username")
    )


def _ceo_user_ids() -> set[int]:
    User = get_user_model()
    return set(User.objects.filter(groups__name=CEO_GROUP_NAME).values_list("pk", flat=True))


def _payroll_user_ids() -> list[int]:
    return list(_payroll_personnel_queryset().values_list("pk", flat=True))


def _dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _money(v: Decimal) -> float:
    return float(v.quantize(_Q, rounding=ROUND_HALF_UP))


def _aggregate_summary(qs) -> dict:
    gmv = _money_two_decimals(
        qs.aggregate(
            s=Sum(
                Case(
                    When(channel=_REFUND_CHANNEL, then=-F("amount")),
                    default=F("amount"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["s"]
    )
    shilei = _money_two_decimals(qs.filter(channel="十类收款").aggregate(s=Sum("amount"))["s"])
    order_count = qs.exclude(channel=_REFUND_CHANNEL).aggregate(c=Sum("order_count"))["c"] or 0
    refund = _money_two_decimals(qs.filter(channel=_REFUND_CHANNEL).aggregate(s=Sum("amount"))["s"])
    gmv_ex = _money_two_decimals(
        qs.aggregate(
            s=Sum(
                Case(
                    When(channel=_REFUND_CHANNEL, then=-F("amount")),
                    When(channel="十类收款", then=Value(0)),
                    default=F("amount"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["s"]
    )
    return {
        "gmv": gmv,
        "shilei": shilei,
        "gmv_ex_shilei": gmv_ex,
        "order_count": int(order_count),
        "refund": refund,
    }


def _user_summary(qs, user_id: int) -> dict:
    return _aggregate_summary(qs.filter(user_id=user_id))


def _channel_lines_from_qs(qs) -> list[dict]:
    lines = []
    for code, label in PAYMENT_CHANNELS:
        if code == _REFUND_CHANNEL:
            continue
        ch_qs = qs.filter(channel=code)
        order_count = ch_qs.aggregate(c=Sum("order_count"))["c"] or 0
        amount = _money_two_decimals(ch_qs.aggregate(s=Sum("amount"))["s"])
        if not order_count and not amount:
            continue
        lines.append(
            {
                "channel": code,
                "channel_label": label,
                "order_count": int(order_count),
                "amount": amount,
            }
        )
    return lines


def _channel_lines(qs, user_id: int) -> list[dict]:
    return _channel_lines_from_qs(qs.filter(user_id=user_id))


def _resolve_month_sales(summary: dict, month_entry) -> tuple[Decimal, Decimal]:
    """返回 (十类销售额, 二类销售额)；未手动保存时沿用收款统计汇总。"""
    auto_shilei = _dec(summary.get("shilei") or 0).quantize(_Q, rounding=ROUND_HALF_UP)
    auto_tier2 = _dec(summary.get("gmv_ex_shilei") or 0).quantize(_Q, rounding=ROUND_HALF_UP)
    if not month_entry:
        return auto_shilei, auto_tier2
    shilei = (
        _dec(month_entry.shilei_sales_amount).quantize(_Q, rounding=ROUND_HALF_UP)
        if month_entry.shilei_sales_amount is not None
        else auto_shilei
    )
    tier2 = (
        _dec(month_entry.tier2_sales_amount).quantize(_Q, rounding=ROUND_HALF_UP)
        if month_entry.tier2_sales_amount is not None
        else auto_tier2
    )
    return shilei, tier2


def _resolve_refund_amount(summary: dict, month_entry) -> Decimal:
    auto_refund = _dec(summary.get("refund") or 0).quantize(_Q, rounding=ROUND_HALF_UP)
    if not month_entry or month_entry.refund_amount is None:
        return auto_refund
    return _dec(month_entry.refund_amount).quantize(_Q, rounding=ROUND_HALF_UP)


def _resolve_social_insurance(month_entry, profile) -> Decimal:
    if month_entry is not None:
        return _dec(month_entry.social_insurance_amount).quantize(_Q, rounding=ROUND_HALF_UP)
    if profile and profile.has_social_insurance:
        return _dec(profile.social_insurance_amount or 0).quantize(_Q, rounding=ROUND_HALF_UP)
    return Decimal("0")


def _member_gmv(summary: dict) -> Decimal:
    """与数据大屏「各成员 GMV」一致：收款净额（退款项扣减）。"""
    return _dec(summary.get("gmv") or 0).quantize(_Q, rounding=ROUND_HALF_UP)


def compute_payroll(
    base_salary,
    shilei_sales,
    tier2_sales,
    refund_amount,
    yinli_sales_amount,
    social_insurance_amount=0,
    yinli_separate=False,
) -> dict:
    """实发工资 = 基本工资 + 十类×10% + (二类−退款项)×2% + 引力币×0.5% − 社保。"""
    base = _dec(base_salary).quantize(_Q, rounding=ROUND_HALF_UP)
    shilei = _dec(shilei_sales).quantize(_Q, rounding=ROUND_HALF_UP)
    tier2 = _dec(tier2_sales).quantize(_Q, rounding=ROUND_HALF_UP)
    refund = _dec(refund_amount).quantize(_Q, rounding=ROUND_HALF_UP)
    yinli = _dec(yinli_sales_amount if yinli_separate else 0).quantize(_Q, rounding=ROUND_HALF_UP)
    social = _dec(social_insurance_amount).quantize(_Q, rounding=ROUND_HALF_UP)

    tier2_net = max(Decimal("0"), tier2 - refund).quantize(_Q, rounding=ROUND_HALF_UP)
    commission_shilei = (shilei * _RATE_SHILEI).quantize(_Q, rounding=ROUND_HALF_UP)
    commission_tier2 = (tier2_net * _RATE_GMV_EX).quantize(_Q, rounding=ROUND_HALF_UP)
    commission_yinli = (
        (yinli * _RATE_YINLI_NET).quantize(_Q, rounding=ROUND_HALF_UP) if yinli_separate else Decimal("0")
    )
    net_pay = (base + commission_shilei + commission_tier2 + commission_yinli - social).quantize(
        _Q, rounding=ROUND_HALF_UP
    )

    return {
        "base_salary": _money(base),
        "shilei_base": _money(shilei),
        "tier2_base": _money(tier2),
        "tier2_net_base": _money(tier2_net),
        "refund_amount": _money(refund),
        "yinli_sales_amount": _money(yinli),
        "commission_shilei": _money(commission_shilei),
        "commission_gmv_ex": _money(commission_tier2),
        "commission_yinli": _money(commission_yinli),
        "social_insurance_amount": _money(social),
        "net_pay": _money(net_pay),
        "yinli_rate_percent": "0.5%",
    }


def _load_profiles(user_ids: list[int]) -> dict[int, StaffSalaryProfile]:
    return {p.user_id: p for p in StaffSalaryProfile.objects.filter(user_id__in=user_ids)}


def _load_month_entries(user_ids: list[int], year: int, month: int) -> dict[int, StaffSalaryMonthEntry]:
    return {
        e.user_id: e
        for e in StaffSalaryMonthEntry.objects.filter(user_id__in=user_ids, year=year, month=month)
    }


def commission_rules_payload() -> dict:
    return {
        "gmv_ex_shilei_label": "销售额（除十类）",
        "gmv_ex_shilei_rate": _money(_RATE_GMV_EX),
        "gmv_ex_shilei_rate_percent": "2%",
        "shilei_label": "十类收款",
        "shilei_rate": _money(_RATE_SHILEI),
        "shilei_rate_percent": "10%",
        "yinli_label": "引力币",
        "yinli_rate": _money(_RATE_YINLI_NET),
        "yinli_rate_percent": "0.5%",
        "yinli_manual": True,
        "net_pay_formula": "基本工资 + 十类×10% + (二类−退款项)×2% + 引力币×0.5% − 社保",
    }


def build_salary_payroll_payload(request) -> dict:
    year, month = _parse_year_month(request)
    date_from, date_to = _month_bounds(year, month)
    personnel = list(_payroll_personnel_queryset().values("id", "username"))
    user_ids = [p["id"] for p in personnel]
    ceo_ids = _ceo_user_ids()
    profiles = _load_profiles(user_ids)
    month_entries = _load_month_entries(user_ids, year, month)
    base_qs = PaymentRecord.objects.filter(record_date__gte=date_from, record_date__lte=date_to)

    slips = []
    for person in personnel:
        uid = person["id"]
        is_ceo_row = uid in ceo_ids
        if is_ceo_row:
            summary = _aggregate_summary(base_qs)
            channels = _channel_lines_from_qs(base_qs)
            role = "ceo"
            role_label = "CEO"
        else:
            summary = _user_summary(base_qs, uid)
            channels = _channel_lines(base_qs, uid)
            role = "employee"
            role_label = "员工"

        profile = profiles.get(uid)
        month_entry = month_entries.get(uid)
        base_salary = profile.base_salary if profile else Decimal("0")
        yinli_sales = month_entry.yinli_sales_amount if month_entry else Decimal("0")
        yinli_separate = bool(profile and profile.yinli_separate)
        yinli_sales_for_calc = yinli_sales if yinli_separate else Decimal("0")
        shilei_sales, tier2_sales = _resolve_month_sales(summary, month_entry)
        member_gmv = _member_gmv(summary)
        refund_amount = _resolve_refund_amount(summary, month_entry)
        social_insurance = _resolve_social_insurance(month_entry, profile)
        payroll = compute_payroll(
            base_salary,
            shilei_sales,
            tier2_sales,
            refund_amount,
            yinli_sales_for_calc,
            social_insurance,
            yinli_separate=yinli_separate,
        )

        slip_data = {
                "id": uid,
                "username": person["username"],
                "role": role,
                "role_label": role_label,
                "is_ceo": is_ceo_row,
                "base_salary": _money(_dec(base_salary)),
                "yinli_separate": yinli_separate,
                "yinli_commission_rate_percent": (
                    _money(_dec(profile.yinli_commission_rate_percent))
                    if profile and yinli_separate and profile.yinli_commission_rate_percent is not None
                    else None
                ),
                "yinli_sales_amount": _money(_dec(yinli_sales if yinli_separate else 0)),
                "shilei_sales_amount": _money(shilei_sales),
                "tier2_sales_amount": _money(tier2_sales),
                "member_gmv": _money(member_gmv),
                "total_sales_amount": _money(member_gmv),
                "refund_amount": _money(refund_amount),
                "social_insurance_amount": _money(social_insurance),
                "summary": summary,
                "channels": channels,
                "payroll": payroll,
            }
        slips.append(slip_data)

    slips.sort(key=lambda x: (0 if x["is_ceo"] else 1, x["username"] or ""))

    return {
        "period": {
            "year": year,
            "month": month,
            "month_key": f"{year:04d}-{month:02d}",
            "label": f"{year}年{month}月",
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
        "commission_rules": commission_rules_payload(),
        "employees": slips,
        "employee_count": len(slips),
    }


def save_salary_payroll_settings(request) -> dict:
    year, month = _parse_year_month(request)
    allowed_ids = set(_payroll_user_ids())
    profiles = _load_profiles(list(allowed_ids))
    items = request.data.get("items") or []
    if not isinstance(items, list):
        raise ValueError("items 须为数组")

    for raw in items:
        try:
            uid = int(raw.get("user_id"))
        except (TypeError, ValueError):
            continue
        if uid not in allowed_ids:
            continue
        base_raw = raw.get("base_salary")
        yinli_raw = raw.get("yinli_sales_amount")
        shilei_raw = raw.get("shilei_sales_amount")
        tier2_raw = raw.get("tier2_sales_amount")
        social_raw = raw.get("social_insurance_amount")
        refund_raw = raw.get("refund_amount")
        base_salary = _dec(base_raw if base_raw is not None else 0).quantize(_Q, rounding=ROUND_HALF_UP)
        profile = profiles.get(uid)
        yinli_separate = bool(profile and profile.yinli_separate)
        yinli_sales = (
            _dec(yinli_raw if yinli_raw is not None else 0).quantize(_Q, rounding=ROUND_HALF_UP)
            if yinli_separate
            else Decimal("0")
        )
        shilei_sales = _dec(shilei_raw if shilei_raw is not None else 0).quantize(_Q, rounding=ROUND_HALF_UP)
        tier2_sales = _dec(tier2_raw if tier2_raw is not None else 0).quantize(_Q, rounding=ROUND_HALF_UP)
        social_insurance = _dec(social_raw if social_raw is not None else 0).quantize(_Q, rounding=ROUND_HALF_UP)
        refund_amount = _dec(refund_raw if refund_raw is not None else 0).quantize(_Q, rounding=ROUND_HALF_UP)
        if (
            base_salary < 0
            or yinli_sales < 0
            or shilei_sales < 0
            or tier2_sales < 0
            or social_insurance < 0
            or refund_amount < 0
        ):
            continue
        StaffSalaryProfile.objects.update_or_create(user_id=uid, defaults={"base_salary": base_salary})
        entry_defaults = {
            "shilei_sales_amount": shilei_sales,
            "tier2_sales_amount": tier2_sales,
            "social_insurance_amount": social_insurance,
            "refund_amount": refund_amount,
        }
        if yinli_separate:
            entry_defaults["yinli_sales_amount"] = yinli_sales
        StaffSalaryMonthEntry.objects.update_or_create(
            user_id=uid,
            year=year,
            month=month,
            defaults=entry_defaults,
        )

    return build_salary_payroll_payload(request)
