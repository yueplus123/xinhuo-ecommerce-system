"""员工工资条分享链接：token 访问、自助填写十类/二类/引力币/退款项。"""

import secrets
from decimal import Decimal

from django.http import Http404
from django.utils import timezone

from backend.apps.catalog.models import (
    PaymentRecord,
    SalarySlipShareToken,
    StaffSalaryMonthEntry,
    StaffSalaryProfile,
)

from .salary_payroll import (
    _ceo_user_ids,
    _dec,
    _load_month_entries,
    _load_profiles,
    _member_gmv,
    _month_bounds,
    _money,
    _resolve_month_sales,
    _resolve_refund_amount,
    _resolve_social_insurance,
    _user_summary,
    commission_rules_payload,
    compute_payroll,
)

_Q = Decimal("0.01")


def _is_employee_user(user_id: int) -> bool:
    return user_id not in _ceo_user_ids()


def create_share_token(user_id: int, year: int, month: int) -> str:
    """每次生成新的分享 token（同一员工同月可有多条链接，各链接仅可提交一次）。"""
    if not _is_employee_user(user_id):
        raise ValueError("CEO 不提供工资条分享链接")
    token = secrets.token_urlsafe(32)
    while SalarySlipShareToken.objects.filter(token=token).exists():
        token = secrets.token_urlsafe(32)
    SalarySlipShareToken.objects.create(user_id=user_id, year=year, month=month, token=token)
    return token


def _get_share_record(token: str) -> SalarySlipShareToken:
    record = SalarySlipShareToken.objects.select_related("user").filter(token=token).first()
    if not record:
        raise Http404("分享链接无效或已失效")
    if not _is_employee_user(record.user_id):
        raise Http404("该链接不可用")
    return record


def _build_employee_slip(record: SalarySlipShareToken) -> dict:
    uid = record.user_id
    year, month = record.year, record.month
    submitted = record.submitted_at is not None
    date_from, date_to = _month_bounds(year, month)
    base_qs = PaymentRecord.objects.filter(record_date__gte=date_from, record_date__lte=date_to)
    summary = _user_summary(base_qs, uid)
    profiles = _load_profiles([uid])
    month_entries = _load_month_entries([uid], year, month)
    profile = profiles.get(uid)
    month_entry = month_entries.get(uid)

    base_salary = profile.base_salary if profile else Decimal("0")
    yinli_separate = bool(profile and profile.yinli_separate)
    yinli_sales = month_entry.yinli_sales_amount if month_entry else Decimal("0")
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

    editable_fields = ["shilei_sales_amount", "tier2_sales_amount", "refund_amount"]
    if yinli_separate:
        editable_fields.append("yinli_sales_amount")

    return {
        "username": record.user.username,
        "submitted": submitted,
        "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
        "read_only": submitted,
        "period": {
            "year": year,
            "month": month,
            "month_key": f"{year:04d}-{month:02d}",
            "label": f"{year}年{month}月",
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
        "commission_rules": commission_rules_payload(),
        "base_salary": _money(_dec(base_salary)),
        "yinli_separate": yinli_separate,
        "yinli_sales_amount": _money(_dec(yinli_sales if yinli_separate else 0)),
        "shilei_sales_amount": _money(shilei_sales),
        "tier2_sales_amount": _money(tier2_sales),
        "member_gmv": _money(member_gmv),
        "total_sales_amount": _money(member_gmv),
        "refund_amount": _money(refund_amount),
        "social_insurance_amount": _money(social_insurance),
        "has_social_insurance": bool(profile and profile.has_social_insurance),
        "payroll": payroll,
        "editable_fields": [] if submitted else editable_fields,
    }


def build_employee_slip_by_token(token: str) -> dict:
    record = _get_share_record(token)
    return _build_employee_slip(record)


def save_employee_slip_by_token(token: str, data: dict) -> dict:
    record = _get_share_record(token)
    if record.submitted_at is not None:
        raise ValueError("该链接已提交，不可再次修改")

    uid = record.user_id
    year, month = record.year, record.month
    profiles = _load_profiles([uid])
    profile = profiles.get(uid)
    yinli_separate = bool(profile and profile.yinli_separate)

    shilei_sales = _dec(data.get("shilei_sales_amount") if data.get("shilei_sales_amount") is not None else 0)
    tier2_sales = _dec(data.get("tier2_sales_amount") if data.get("tier2_sales_amount") is not None else 0)
    refund_amount = _dec(data.get("refund_amount") if data.get("refund_amount") is not None else 0)
    yinli_sales = (
        _dec(data.get("yinli_sales_amount") if data.get("yinli_sales_amount") is not None else 0)
        if yinli_separate
        else Decimal("0")
    )
    if shilei_sales < 0 or tier2_sales < 0 or yinli_sales < 0 or refund_amount < 0:
        raise ValueError("金额不能为负数")

    shilei_sales = shilei_sales.quantize(_Q)
    tier2_sales = tier2_sales.quantize(_Q)
    refund_amount = refund_amount.quantize(_Q)
    yinli_sales = yinli_sales.quantize(_Q)

    entry, _created = StaffSalaryMonthEntry.objects.get_or_create(
        user_id=uid,
        year=year,
        month=month,
        defaults={
            "shilei_sales_amount": shilei_sales,
            "tier2_sales_amount": tier2_sales,
            "refund_amount": refund_amount,
            "yinli_sales_amount": yinli_sales,
        },
    )
    if not _created:
        entry.shilei_sales_amount = shilei_sales
        entry.tier2_sales_amount = tier2_sales
        entry.refund_amount = refund_amount
        if yinli_separate:
            entry.yinli_sales_amount = yinli_sales
        entry.save(
            update_fields=[
                "shilei_sales_amount",
                "tier2_sales_amount",
                "refund_amount",
                * (["yinli_sales_amount"] if yinli_separate else []),
            ]
        )

    record.submitted_at = timezone.now()
    record.save(update_fields=["submitted_at", "updated_at"])

    record.refresh_from_db()
    return _build_employee_slip(record)
