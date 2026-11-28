"""数据大屏：收款周期 KPI、成员对比、渠道联动；本月/历史趋势固定展示。

对比口径：进行中的周期（本月 / 本周 / 年度）都和「同期」比——本月 1 日到今天 对比 上月 1 日到同一天；
上月（已结束）对比前一个整月。
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Case, Count, DecimalField, F, Q, Sum, When
from django.utils import timezone

from backend.apps.catalog.models import MonthlyGmvTarget, PaymentRecord, WechatBotRecord
from backend.apps.catalog.roles import BOSS_GROUP_NAME, CEO_GROUP_NAME, GUEST_GROUP_NAME, is_boss, is_ceo, is_guest

_PAYMENT_REFUND_CHANNEL = "退款项"
_CHANNEL_SHILEI = "十类收款"
_DATA_SCREEN_EXCLUDED_GROUPS = (BOSS_GROUP_NAME, CEO_GROUP_NAME, GUEST_GROUP_NAME)

# 与前端 wechatBotTables 一致：qty/sku 用数量合计，usdt 用美金合计
_BOT_BUSINESS_DEFS = (
    ("usdt", "USDT", "usdt"),
    ("pixivcoban", "充币", "qty"),
    ("shared", "共享", "qty"),
    ("package", "打包", "qty"),
    ("openrouter", "openrouter", "qty"),
    ("patreon", "patreon", "qty"),
    ("booth", "booth", "qty"),
    ("pictspace", "pictspace", "qty"),
    ("premium", "高级会员", "sku"),
    ("mega", "mega", "sku"),
    ("chatgpt", "gpt", "sku"),
    ("once_card", "一次卡", "qty"),
)
# 仅排除已作废；ACTIVE(未清空) / PROCESSED(已清空) 都计入
_BOT_EXCLUDED_STATUS = ("REVERSED", "DELETED", "VOID")


def _data_screen_excluded_user_ids():
    User = get_user_model()
    return set(User.objects.filter(groups__name__in=_DATA_SCREEN_EXCLUDED_GROUPS).values_list("pk", flat=True))


def _exclude_boss_ceo_payments(qs):
    excluded = _data_screen_excluded_user_ids()
    if not excluded:
        return qs
    return qs.exclude(user_id__in=excluded)


def _data_screen_personnel_queryset():
    User = get_user_model()
    return User.objects.filter(is_active=True, is_superuser=False).exclude(
        groups__name__in=_DATA_SCREEN_EXCLUDED_GROUPS
    )


def _money_two_decimals(v):
    if v is None:
        return 0.0
    return round(float(v), 2)


def _net_amount_expr():
    return Case(
        When(channel=_PAYMENT_REFUND_CHANNEL, then=-F("amount")),
        default=F("amount"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )


def _payment_records_net_sales_sum(qs):
    return qs.aggregate(s=Sum(_net_amount_expr()))["s"]


def _bot_period_qs(date_from: date | None, date_to: date | None):
    """周期内有效微信BOT记录（含未清空），按上海日历日，与收款 record_date 同一套周期。"""
    qs = WechatBotRecord.objects.all()
    bad = Q()
    for st in _BOT_EXCLUDED_STATUS:
        bad |= Q(status__iexact=st)
    if bad:
        qs = qs.exclude(bad)
    if date_from is not None and date_to is not None:
        qs = qs.filter(
            Q(occurred_at__date__gte=date_from, occurred_at__date__lte=date_to)
            | Q(occurred_at__isnull=True, created_at__date__gte=date_from, created_at__date__lte=date_to)
        )
    return qs


def _bot_business_metrics(date_from: date | None, date_to: date | None) -> list[dict]:
    """
    各业务 KPI：数量表/多SKU → quantity 合计；USDT → amount_usd 合计。
    """
    rows = (
        _bot_period_qs(date_from, date_to)
        .values("table_type")
        .annotate(qty=Sum("quantity"), usd=Sum("amount_usd"), cny=Sum("amount"), cnt=Count("id"))
    )
    by_type = {r["table_type"]: r for r in rows}
    out: list[dict] = []
    for key, label, layout in _BOT_BUSINESS_DEFS:
        r = by_type.get(key) or {}
        if layout == "usdt":
            value = _money_two_decimals(r.get("usd"))
            unit = "usd"
        elif layout == "amount":
            value = _money_two_decimals(r.get("cny"))
            unit = "cny"
        else:
            value = int(r.get("qty") or 0)
            unit = "qty"
        out.append(
            {
                "key": key,
                "label": label,
                "layout": layout,
                "unit": unit,
                "value": value,
                "count": int(r.get("cnt") or 0),
            }
        )
    return out


def _attach_bot_change(cur_rows: list[dict], prev_rows: list[dict] | None) -> list[dict]:
    prev_map = {r["key"]: r.get("value") for r in (prev_rows or [])}
    out = []
    for row in cur_rows:
        item = dict(row)
        if prev_rows is None:
            item["change_pct"] = None
            item["prev_value"] = None
        else:
            item["change_pct"] = _pct_change(row.get("value"), prev_map.get(row["key"]))
            item["prev_value"] = prev_map.get(row["key"], 0)
        out.append(item)
    return out


def data_screen_range_summary(qs, date_from=None, date_to=None):
    total_gmv = _money_two_decimals(_payment_records_net_sales_sum(qs))
    shilei = _money_two_decimals(qs.filter(channel=_CHANNEL_SHILEI).aggregate(s=Sum("amount"))["s"])
    order_count = qs.exclude(channel=_PAYMENT_REFUND_CHANNEL).aggregate(c=Sum("order_count"))["c"] or 0
    refund = _money_two_decimals(qs.filter(channel=_PAYMENT_REFUND_CHANNEL).aggregate(s=Sum("amount"))["s"])
    denom = total_gmv + refund
    refund_rate = round((refund / denom) * 100, 2) if denom > 0 else 0.0
    aov = round(total_gmv / order_count, 2) if order_count else 0.0
    shilei_ratio = round((shilei / total_gmv) * 100, 2) if total_gmv > 0 else 0.0

    bot_rows = {r["key"]: r for r in _bot_business_metrics(date_from, date_to)}
    pixivcoban_count = int((bot_rows.get("pixivcoban") or {}).get("count") or 0)
    chatgptplus_count = int((bot_rows.get("chatgpt") or {}).get("count") or 0)
    usdt_amount = float((bot_rows.get("usdt") or {}).get("value") or 0)

    return {
        "total_gmv": total_gmv,
        "shilei": shilei,
        "order_count": int(order_count),
        "refund": refund,
        "refund_rate": refund_rate,
        "aov": aov,
        "shilei_ratio": shilei_ratio,
        "pixivcoban_count": pixivcoban_count,
        "chatgptplus_count": chatgptplus_count,
        "usdt_amount": usdt_amount,
        "usdt_count": usdt_amount,
    }


def _pct_change(cur, prev):
    cur_f = float(cur or 0)
    prev_f = float(prev or 0)
    if prev_f > 0:
        return round((cur_f - prev_f) / prev_f * 100, 2)
    if cur_f > 0:
        return 100.0
    return 0.0


def _attach_change_metrics(summary: dict, prev_summary: dict | None):
    out = dict(summary)
    keys = (
        ("gmv_change_pct", "total_gmv"),
        ("order_change_pct", "order_count"),
        ("pixivcoban_change_pct", "pixivcoban_count"),
        ("chatgptplus_change_pct", "chatgptplus_count"),
        ("usdt_change_pct", "usdt_amount"),
        ("aov_change_pct", "aov"),
    )
    if not prev_summary:
        for pct_key, _ in keys:
            out[pct_key] = None
        out["prev_total_gmv"] = out["prev_order_count"] = out["prev_aov"] = None
        return out
    for pct_key, field in keys:
        out[pct_key] = _pct_change(summary.get(field), prev_summary.get(field))
    out["prev_total_gmv"] = prev_summary.get("total_gmv")
    out["prev_order_count"] = prev_summary.get("order_count")
    out["prev_aov"] = prev_summary.get("aov")
    return out


def data_screen_staff_metrics(date_from, date_to_inclusive):
    payer_ids = list(
        _exclude_boss_ceo_payments(
            PaymentRecord.objects.filter(record_date__gte=date_from, record_date__lte=date_to_inclusive)
        )
        .values_list("user_id", flat=True)
        .distinct()
    )
    staff_rows = list(
        _data_screen_personnel_queryset()
        .filter(Q(is_staff=True) | Q(pk__in=payer_ids))
        .order_by("username")
        .values("id", "username")
    )
    ids_list = [r["id"] for r in staff_rows]
    base = _exclude_boss_ceo_payments(
        PaymentRecord.objects.filter(
            record_date__gte=date_from,
            record_date__lte=date_to_inclusive,
            user_id__in=ids_list,
        )
    )

    gmv_map = {
        row["user_id"]: _money_two_decimals(row["s"])
        for row in base.values("user_id").annotate(s=Sum(_net_amount_expr()))
    }
    shilei_map = {
        row["user_id"]: _money_two_decimals(row["s"])
        for row in base.filter(channel=_CHANNEL_SHILEI).values("user_id").annotate(s=Sum("amount"))
    }
    ord_map = {
        row["user_id"]: row["c"] or 0
        for row in base.exclude(channel=_PAYMENT_REFUND_CHANNEL).values("user_id").annotate(c=Sum("order_count"))
    }
    ref_map = {
        row["user_id"]: _money_two_decimals(row["s"])
        for row in base.filter(channel=_PAYMENT_REFUND_CHANNEL).values("user_id").annotate(s=Sum("amount"))
    }

    out = []
    for row in staff_rows:
        uid = row["id"]
        out.append(
            {
                "user__username": row["username"],
                "gmv": gmv_map.get(uid, 0),
                "shilei": shilei_map.get(uid, 0),
                "order_count": ord_map.get(uid, 0),
                "refund": ref_map.get(uid, 0),
            }
        )
    out.sort(key=lambda x: (-(x["gmv"] or 0), x["user__username"] or ""))
    return out


def _channel_rank_list(qs, limit=10):
    rows = (
        qs.exclude(channel=_PAYMENT_REFUND_CHANNEL)
        .values("channel")
        .annotate(c=Sum("order_count"))
        .order_by("-c")[:limit]
    )
    return [{"channel": r["channel"] or "—", "c": int(r["c"] or 0)} for r in rows]


def _channel_amount_bar(qs):
    rows = qs.values("channel").annotate(s=Sum(_net_amount_expr())).order_by("-s")
    return [{"channel": r["channel"] or "—", "amount": _money_two_decimals(r["s"])} for r in rows]


def _iter_days(date_from, date_to):
    d = date_from
    while d <= date_to:
        yield d
        d += timedelta(days=1)


def _trend_daily(date_from, date_to, qs, grain="day"):
    by_bucket = defaultdict(float)
    for rd, ch, amt in qs.values_list("record_date", "channel", "amount"):
        day = rd.date() if hasattr(rd, "date") else rd
        sign = -1.0 if ch == _PAYMENT_REFUND_CHANNEL else 1.0
        key = day.replace(day=1) if grain == "month" else day
        by_bucket[key] += sign * float(amt or 0)

    if grain == "month":
        out = []
        cur = date_from.replace(day=1)
        end = date_to.replace(day=1)
        while cur <= end:
            out.append({"date": cur.strftime("%Y-%m"), "sales": round(by_bucket.get(cur, 0.0), 2)})
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        return out

    return [
        {"date": d.strftime("%m-%d"), "sales": round(by_bucket.get(d, 0.0), 2)}
        for d in _iter_days(date_from, date_to)
    ]


def _history_month_gmv(months: int = 12):
    """近 N 个自然月 GMV（含本月），不受周期下拉影响。"""
    today = timezone.localdate()
    end_month = today.replace(day=1)
    y, m = end_month.year, end_month.month
    for _ in range(months - 1):
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
    start_month = date(y, m, 1)

    qs = _exclude_boss_ceo_payments(
        PaymentRecord.objects.filter(record_date__gte=start_month, record_date__lte=today)
    )
    by_month = defaultdict(float)
    for rd, ch, amt in qs.values_list("record_date", "channel", "amount"):
        day = rd.date() if hasattr(rd, "date") else rd
        key = day.replace(day=1)
        sign = -1.0 if ch == _PAYMENT_REFUND_CHANNEL else 1.0
        by_month[key] += sign * float(amt or 0)

    out = []
    cur = start_month
    while cur <= end_month:
        out.append({"date": cur.strftime("%Y-%m"), "gmv": round(by_month.get(cur, 0.0), 2)})
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return out


def _staff_daily(date_from, date_to):
    dates = list(_iter_days(date_from, date_to))
    labels = [d.strftime("%m-%d") for d in dates]
    by_user_day = defaultdict(lambda: defaultdict(float))
    user_order = []
    seen = set()
    for record_date, username, ch, amt in _exclude_boss_ceo_payments(
        PaymentRecord.objects.filter(record_date__gte=date_from, record_date__lte=date_to)
    ).values_list("record_date", "user__username", "channel", "amount"):
        day = record_date.date() if hasattr(record_date, "date") else record_date
        un = (username or "").strip() or "未知"
        if un not in seen:
            seen.add(un)
            user_order.append(un)
        sign = -1.0 if ch == _PAYMENT_REFUND_CHANNEL else 1.0
        by_user_day[un][day] += sign * float(amt or 0)
    totals = {u: sum(by_user_day[u].values()) for u in user_order}
    user_order.sort(key=lambda u: -totals.get(u, 0.0))
    return {
        "dates": labels,
        "series": [
            {"name": u, "data": [round(float(by_user_day[u].get(dt, 0.0)), 2) for dt in dates]}
            for u in user_order
        ],
    }


def _shift_months(d: date, n: int) -> date:
    """d 所在月往前/后 n 个月的 1 日。"""
    idx = d.year * 12 + (d.month - 1) + n
    return date(idx // 12, idx % 12 + 1, 1)


def _month_days(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]


def _safe_replace_year(d: date, year: int) -> date:
    try:
        return d.replace(year=year)
    except ValueError:  # 2 月 29 日 → 28 日
        return d.replace(year=year, day=28)


def same_period_prev(kind: str, date_from: date, date_to: date) -> tuple[date, date]:
    """同期区间。month：上月 1 日 ~ 上月同一天（上月没有这一天就到上月最后一天）。"""
    if kind == "month":
        start = _shift_months(date_from, -1)
        end = start + (date_to - date_from)
        last = start.replace(day=_month_days(start))
        return start, min(end, last)
    if kind == "week":
        return date_from - timedelta(days=7), date_to - timedelta(days=7)
    if kind == "year":
        return _safe_replace_year(date_from, date_from.year - 1), _safe_replace_year(date_to, date_to.year - 1)
    raise ValueError(kind)


def _staff_compare(cur_staff: list[dict], prev_staff: list[dict]) -> list[dict]:
    """各成员 本周期 vs 同期 GMV（两边都为 0 的不列）。"""
    prev_map = {r["user__username"]: r.get("gmv") or 0 for r in prev_staff}
    rows, seen = [], set()
    for r in cur_staff:
        name = r["user__username"]
        seen.add(name)
        rows.append({"user__username": name, "gmv": r.get("gmv") or 0, "prev_gmv": prev_map.get(name, 0)})
    for name, v in prev_map.items():
        if name not in seen:
            rows.append({"user__username": name, "gmv": 0, "prev_gmv": v})
    rows = [r for r in rows if r["gmv"] or r["prev_gmv"]]
    for r in rows:
        r["change_pct"] = _pct_change(r["gmv"], r["prev_gmv"])
    rows.sort(key=lambda x: (-(x["gmv"] or 0), x["user__username"] or ""))
    return rows


def month_goal(today: date | None = None) -> dict:
    """本月目标 + 月底预测。预测 = 1 日到昨天已收 + 昨天为止日均 × 剩余天数（含今天）。"""
    today = today or timezone.localdate()
    month_start = today.replace(day=1)
    dim = _month_days(today)
    days_left = dim - today.day + 1

    def _gmv(d0, d1):
        if d1 < d0:
            return 0.0
        return _money_two_decimals(_payment_records_net_sales_sum(_exclude_boss_ceo_payments(
            PaymentRecord.objects.filter(record_date__gte=d0, record_date__lte=d1))))

    gmv = _gmv(month_start, today)
    before_today = _gmv(month_start, today - timedelta(days=1))
    if today.day > 1:
        avg = round(before_today / (today.day - 1), 2)
        forecast = round(before_today + avg * days_left, 2)
    else:
        avg = forecast = None

    t = MonthlyGmvTarget.objects.filter(month=month_start).first()
    target = _money_two_decimals(t.target) if t else None
    out = {
        "month": month_start.strftime("%Y-%m"),
        "target": target,
        "gmv": gmv,
        "days_in_month": dim,
        "days_left": days_left,
        "avg_daily": avg,
        "forecast": forecast,
        "done_pct": None,
        "forecast_pct": None,
        "per_day_needed": None,
    }
    if target:
        out["done_pct"] = round(gmv / target * 100, 1)
        out["per_day_needed"] = round(max(target - gmv, 0) / days_left, 2)
        if forecast is not None:
            out["forecast_pct"] = round(forecast / target * 100, 1)
    return out


def _can_see_everyone(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or is_boss(user) or is_ceo(user)))


def daily_four_months(user=None, today: date | None = None) -> dict:
    """每日收款 · 本月和近 3 个月（按每月 1–31 日对齐）。

    管理员 / 老板 / CEO：全部 + 每个成员；普通员工：全部 + 自己（默认自己）；游客：只有全部。
    """
    today = today or timezone.localdate()
    starts = [_shift_months(today, -i) for i in range(4)]  # 本月, 上月, ...
    months = []
    for i, m0 in enumerate(starts):
        dim = _month_days(m0)
        months.append({
            "key": m0.strftime("%Y-%m"),
            "label": f"{m0.month}月" + ("（本月）" if i == 0 else ""),
            "days": dim,
            "upto": today.day if i == 0 else dim,
        })

    everyone = _can_see_everyone(user)
    guest = bool(user and user.is_authenticated and is_guest(user)) or not (user and user.is_authenticated)
    qs = _exclude_boss_ceo_payments(
        PaymentRecord.objects.filter(record_date__gte=starts[-1], record_date__lte=today)
    )
    by_user = defaultdict(lambda: defaultdict(float))
    total = defaultdict(float)
    names = {}
    for rd, uid, uname, ch, amt in qs.values_list("record_date", "user_id", "user__username", "channel", "amount"):
        day = rd.date() if hasattr(rd, "date") else rd
        v = (-1.0 if ch == _PAYMENT_REFUND_CHANNEL else 1.0) * float(amt or 0)
        total[day] += v
        if uid is not None:
            by_user[uid][day] += v
            names[uid] = (uname or "").strip() or "未知"

    def _series(day_map):
        out = []
        for m0, m in zip(starts, months):
            out.append([round(day_map.get(m0.replace(day=d), 0.0), 2) for d in range(1, m["upto"] + 1)])
        return out

    options = [{"key": "all", "name": "全部"}]
    series = {"all": _series(total)}
    default = "all"
    if everyone:
        for uid in sorted(by_user, key=lambda u: -sum(by_user[u].values())):
            options.append({"key": str(uid), "name": names[uid]})
            series[str(uid)] = _series(by_user[uid])
    elif not guest:
        key = str(user.pk)
        options.append({"key": key, "name": f"我自己（{(user.username or '').strip()}）"})
        series[key] = _series(by_user.get(user.pk, {}))
        default = key
    return {"months": months, "options": options, "series": series, "default": default}


def _range_summary(d0, d1):
    return data_screen_range_summary(
        _exclude_boss_ceo_payments(PaymentRecord.objects.filter(record_date__gte=d0, record_date__lte=d1)),
        date_from=d0,
        date_to=d1,
    )


def _build_period_block(date_from, date_to, prev_range=None, cmp_label=""):
    """prev_range=(起, 止)：对比区间（同期）。"""
    qs = _exclude_boss_ceo_payments(
        PaymentRecord.objects.filter(record_date__gte=date_from, record_date__lte=date_to)
    )
    prev_summary = _range_summary(*prev_range) if prev_range else None
    prev_bot = _bot_business_metrics(*prev_range) if prev_range else None
    summary = _attach_change_metrics(
        data_screen_range_summary(qs, date_from=date_from, date_to=date_to),
        prev_summary,
    )
    summary["date_from"] = date_from.isoformat()
    summary["date_to"] = date_to.isoformat()
    summary["cmp_label"] = cmp_label
    summary["cmp_from"] = prev_range[0].isoformat() if prev_range else None
    summary["cmp_to"] = prev_range[1].isoformat() if prev_range else None
    bot_business = _attach_bot_change(_bot_business_metrics(date_from, date_to), prev_bot)
    staff = data_screen_staff_metrics(date_from, date_to)
    staff_compare = _staff_compare(staff, data_screen_staff_metrics(*prev_range)) if prev_range else []
    return {
        "summary": summary,
        "staff": staff,
        "staff_compare": staff_compare,
        "channel_rank_list": _channel_rank_list(qs),
        "channel_amount_bar": _channel_amount_bar(qs),
        "staff_daily": _staff_daily(date_from, date_to),
        "bot_business": bot_business,
    }


def build_data_screen_payload(user=None):
    today = timezone.localdate()
    start_week = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    prev2_end = prev_month_start - timedelta(days=1)
    prev2_start = prev2_end.replace(day=1)

    month_block = _build_period_block(
        month_start, today, prev_range=same_period_prev("month", month_start, today), cmp_label="上月同期"
    )
    month_block["goal"] = month_goal(today)
    week_block = _build_period_block(
        start_week, today, prev_range=same_period_prev("week", start_week, today), cmp_label="上周同期"
    )
    prev_month_block = _build_period_block(
        prev_month_start, prev_month_end, prev_range=(prev2_start, prev2_end), cmp_label="前月"
    )
    year_block = _build_period_block(
        year_start, today, prev_range=same_period_prev("year", year_start, today), cmp_label="去年同期"
    )

    month_qs = _exclude_boss_ceo_payments(
        PaymentRecord.objects.filter(record_date__gte=month_start, record_date__lte=today)
    )
    month_sales_trend = _trend_daily(month_start, today, month_qs, grain="day")
    history_month_gmv = _history_month_gmv(12)

    return {
        "month": month_block,
        "week": week_block,
        "prev_month": prev_month_block,
        "year": year_block,
        # 固定图表（不受本月/本周/上月/年度筛选）
        "month_sales_trend": month_sales_trend,
        "history_month_gmv": history_month_gmv,
        "daily_4m": daily_four_months(user, today),
        # 兼容旧字段
        "channel_rank_list": month_block["channel_rank_list"],
        "channel_amount_bar": month_block["channel_amount_bar"],
        "trend_7d": month_sales_trend[:7] if month_sales_trend else [],
        "trend_30d": month_sales_trend,
        "staff_month_daily": month_block["staff_daily"],
    }
