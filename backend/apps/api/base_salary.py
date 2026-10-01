"""基本工资：按人设置底薪并保留录入记录。"""

from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from backend.apps.catalog.models import StaffBaseSalaryLog, StaffSalaryProfile

from .salary_payroll import _dec, _money, _payroll_personnel_queryset, _payroll_user_ids

_Q = Decimal("0.01")


def _quantize_money(v):
    return _dec(v).quantize(_Q, rounding=ROUND_HALF_UP)


def _quantize_rate_percent(v):
    if v is None or v == "":
        return None
    rate = _dec(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if rate <= 0 or rate > 100:
        raise ValueError("引力币提成比例须在 0～100 之间")
    return rate


def _parse_bool_yes_no(raw) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    text = str(raw).strip().lower()
    return text in ("1", "true", "yes", "on", "是")


def _yinli_separate_label(separate: bool, rate_percent) -> str:
    if not separate:
        return "否"
    rate = _dec(rate_percent)
    if rate <= 0:
        return "是"
    normalized = rate.normalize()
    if normalized == normalized.to_integral_value():
        return f"{int(normalized)}%"
    return f"{normalized}%"


def _profile_yinli_payload(profile) -> dict:
    separate = bool(profile and profile.yinli_separate)
    rate = profile.yinli_commission_rate_percent if profile else None
    return {
        "yinli_separate": separate,
        "yinli_commission_rate_percent": _money(_dec(rate)) if separate and rate is not None else None,
        "yinli_separate_label": _yinli_separate_label(separate, rate),
    }


def _profile_social_payload(profile) -> dict:
    has_social = bool(profile and profile.has_social_insurance)
    amount = profile.social_insurance_amount if profile and has_social else Decimal("0")
    return {
        "has_social_insurance": has_social,
        "social_insurance_amount": _money(_dec(amount)) if has_social else None,
        "social_insurance_label": "否" if not has_social else _money(_dec(amount)),
    }


def build_base_salary_payload() -> dict:
    personnel = list(_payroll_personnel_queryset().values("id", "username"))
    user_ids = [p["id"] for p in personnel]
    profiles = {p.user_id: p for p in StaffSalaryProfile.objects.filter(user_id__in=user_ids)}

    records = []
    for log in StaffBaseSalaryLog.objects.select_related("user", "created_by").order_by("-created_at", "-id")[:300]:
        created_by = ""
        if log.created_by_id:
            created_by = log.created_by.username or str(log.created_by_id)
        has_social = bool(log.has_social_insurance)
        records.append(
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username,
                "base_salary": _money(_dec(log.base_salary)),
                "yinli_separate": bool(log.yinli_separate),
                "yinli_commission_rate_percent": (
                    _money(_dec(log.yinli_commission_rate_percent))
                    if log.yinli_separate and log.yinli_commission_rate_percent is not None
                    else None
                ),
                "yinli_separate_label": _yinli_separate_label(log.yinli_separate, log.yinli_commission_rate_percent),
                "has_social_insurance": has_social,
                "social_insurance_amount": _money(_dec(log.social_insurance_amount)) if has_social else None,
                "social_insurance_label": (
                    "否" if not has_social else str(_money(_dec(log.social_insurance_amount)))
                ),
                "created_at": timezone.localtime(log.created_at).strftime("%Y-%m-%d %H:%M"),
                "created_by": created_by,
            }
        )

    current = []
    for person in personnel:
        uid = person["id"]
        profile = profiles.get(uid)
        base = profile.base_salary if profile else 0
        current.append(
            {
                "user_id": uid,
                "username": person["username"],
                "base_salary": _money(_dec(base)),
                **_profile_yinli_payload(profile),
                **_profile_social_payload(profile),
            }
        )

    return {
        "personnel": personnel,
        "current": current,
        "records": records,
    }


def save_base_salary(request) -> dict:
    try:
        user_id = int(request.data.get("user_id"))
    except (TypeError, ValueError):
        raise ValueError("请选择人员")

    if user_id not in set(_payroll_user_ids()):
        raise ValueError("无效人员")

    base_salary = _quantize_money(request.data.get("base_salary") if request.data.get("base_salary") is not None else 0)
    if base_salary < 0:
        raise ValueError("工资不能为负数")

    yinli_separate = _parse_bool_yes_no(request.data.get("yinli_separate"))
    yinli_rate = None
    if yinli_separate:
        try:
            yinli_rate = _quantize_rate_percent(request.data.get("yinli_commission_rate_percent"))
        except ValueError:
            raise
        if yinli_rate is None:
            raise ValueError("请填写引力币提成比例（%）")

    has_social = _parse_bool_yes_no(request.data.get("has_social_insurance"))
    social_amount = Decimal("0")
    if has_social:
        social_amount = _quantize_money(
            request.data.get("social_insurance_amount") if request.data.get("social_insurance_amount") is not None else 0
        )
        if social_amount <= 0:
            raise ValueError("请填写社保金额")

    StaffSalaryProfile.objects.update_or_create(
        user_id=user_id,
        defaults={
            "base_salary": base_salary,
            "yinli_separate": yinli_separate,
            "yinli_commission_rate_percent": yinli_rate if yinli_separate else None,
            "has_social_insurance": has_social,
            "social_insurance_amount": social_amount if has_social else Decimal("0"),
        },
    )
    StaffBaseSalaryLog.objects.create(
        user_id=user_id,
        base_salary=base_salary,
        yinli_separate=yinli_separate,
        yinli_commission_rate_percent=yinli_rate if yinli_separate else None,
        has_social_insurance=has_social,
        social_insurance_amount=social_amount if has_social else Decimal("0"),
        created_by=request.user if request.user.is_authenticated else None,
    )
    return build_base_salary_payload()
