"""日元充值汇率：取数、计算、企微推送文案。

应充美元 = 日元 ÷ (1 美元 = 多少日元) × 系数，只在最后一步向上取整到美分（ROUND_CEILING）。
例：汇率 160、系数 1.025 → 8,000 日元 = 51.25 美元（不是 51.26）。

取数：按顺序试 SOURCES 里的公开接口，第一个成功且通过校验的就用；全部失败则不动数据库。
服务器在国内，某个接口连不上时会自动用下一个；用
    python backend/manage.py fetch_card_fx_rate --test
可以一次性测试每个接口能不能连上。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone as dt_timezone
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

from django.utils import timezone

from .models import CardFxRate, CardFxSettings
from .wecom_webhook import _urlopen

AMOUNTS = (1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000)
DEFAULT_FACTOR = Decimal("1.0250")
FACTOR_MIN = Decimal("1.000")
FACTOR_MAX = Decimal("1.100")
STALE_DAYS = 4
TIMEOUT = 15
JPY_RANGE = (Decimal("80"), Decimal("300"))
CNY_RANGE = (Decimal("5"), Decimal("10"))
_WEEKDAY_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


class CardFxError(Exception):
    """取数 / 校验失败。"""


@dataclass
class FxQuote:
    rate_date: date
    usd_jpy: Decimal
    usd_cny: Decimal
    source: str


# ---------- 取数 ----------


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "xinhuo-card-fx/1.0"})
    try:
        with _urlopen(req, timeout=TIMEOUT) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise CardFxError(f"HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise CardFxError(f"网络错误: {getattr(e, 'reason', e)}") from e
    try:
        data = json.loads(text)
    except ValueError as e:
        raise CardFxError("返回的不是 JSON") from e
    if not isinstance(data, dict):
        raise CardFxError("返回格式不对")
    return data


def _dec(v) -> Decimal:
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError) as e:
        raise CardFxError(f"汇率不是数字: {v!r}") from e
    if not d.is_finite():
        raise CardFxError(f"汇率不是数字: {v!r}")
    return d


def _date(v) -> date:
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError) as e:
        raise CardFxError(f"日期无法解析: {v!r}") from e


def _from_frankfurter() -> FxQuote:
    d = _get_json("https://api.frankfurter.dev/v1/latest?base=USD&symbols=CNY,JPY")
    if d.get("base") != "USD":
        raise CardFxError(f"base 不是 USD: {d.get('base')!r}")
    rates = d.get("rates") or {}
    return FxQuote(_date(d.get("date")), _dec(rates.get("JPY")), _dec(rates.get("CNY")), "frankfurter")


def _from_er_api() -> FxQuote:
    d = _get_json("https://open.er-api.com/v6/latest/USD")
    if d.get("result") != "success" or d.get("base_code") != "USD":
        raise CardFxError(f"返回异常: result={d.get('result')!r} base={d.get('base_code')!r}")
    try:
        day = datetime.fromtimestamp(int(d.get("time_last_update_unix")), tz=dt_timezone.utc).date()
    except (TypeError, ValueError, OverflowError) as e:
        raise CardFxError("日期无法解析") from e
    rates = d.get("rates") or {}
    return FxQuote(day, _dec(rates.get("JPY")), _dec(rates.get("CNY")), "er-api")


def _from_currency_api() -> FxQuote:
    last: Exception | None = None
    for url in (
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
        "https://latest.currency-api.pages.dev/v1/currencies/usd.json",
    ):
        try:
            d = _get_json(url)
            rates = d.get("usd") or {}
            return FxQuote(_date(d.get("date")), _dec(rates.get("jpy")), _dec(rates.get("cny")), "currency-api")
        except CardFxError as e:
            last = e
    raise CardFxError(str(last))


# 按顺序尝试；想换数据源只改这里
SOURCES = {
    "frankfurter": _from_frankfurter,
    "er-api": _from_er_api,
    "currency-api": _from_currency_api,
}


def validate(q: FxQuote, today: date | None = None) -> FxQuote:
    today = today or timezone.localdate()
    if q.rate_date > today:
        raise CardFxError(f"汇率日期 {q.rate_date} 晚于今天 {today}")
    if not (JPY_RANGE[0] <= q.usd_jpy <= JPY_RANGE[1]):
        raise CardFxError(f"美元兑日元 {q.usd_jpy} 不在 80–300 之间")
    if not (CNY_RANGE[0] <= q.usd_cny <= CNY_RANGE[1]):
        raise CardFxError(f"美元兑人民币 {q.usd_cny} 不在 5–10 之间")
    q.usd_jpy = q.usd_jpy.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    q.usd_cny = q.usd_cny.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return q


def fetch_quote(source: str | None = None) -> tuple[FxQuote, list[str]]:
    """取一条通过校验的汇率；返回 (结果, 失败记录)。全部失败抛 CardFxError。"""
    names = [source] if source else list(SOURCES)
    errors: list[str] = []
    for name in names:
        fn = SOURCES.get(name)
        if fn is None:
            raise CardFxError(f"没有这个数据源：{name}（可选 {', '.join(SOURCES)}）")
        try:
            return validate(fn()), errors
        except CardFxError as e:
            errors.append(f"{name}: {e}")
    raise CardFxError("所有数据源都失败：" + "；".join(errors))


def save_quote(q: FxQuote) -> tuple[CardFxRate, bool]:
    return CardFxRate.objects.update_or_create(
        rate_date=q.rate_date,
        defaults={"usd_jpy": q.usd_jpy, "usd_cny": q.usd_cny, "source": q.source},
    )


# ---------- 系数 ----------


def get_settings() -> CardFxSettings:
    obj = CardFxSettings.objects.order_by("id").first()
    if obj is None:
        obj = CardFxSettings.objects.create(factor=DEFAULT_FACTOR)
    return obj


def parse_factor(raw) -> Decimal:
    """校验系数：1.000–1.100，最多 4 位小数。不合格抛 ValueError（带中文提示）。"""
    s = str(raw if raw is not None else "").strip()
    if not s:
        raise ValueError("请输入系数")
    try:
        d = Decimal(s)
    except InvalidOperation as e:
        raise ValueError("系数必须是数字，例如 1.028") from e
    if not d.is_finite():
        raise ValueError("系数必须是数字，例如 1.028")
    if d < FACTOR_MIN or d > FACTOR_MAX:
        raise ValueError("系数必须在 1.000 到 1.100 之间")
    if d.as_tuple().exponent < -4:
        raise ValueError("系数最多 4 位小数")
    return d.quantize(Decimal("0.0001"))


def set_factor(raw, user=None) -> CardFxSettings:
    obj = get_settings()
    obj.factor = parse_factor(raw)
    obj.updated_by = user if (user is not None and getattr(user, "pk", None)) else None
    obj.save()
    return obj


# ---------- 计算 ----------


def charge_usd(jpy: int | Decimal, usd_jpy: Decimal, factor: Decimal) -> Decimal:
    """应充美元，只在最后一步向上取整到 0.01。"""
    with localcontext() as ctx:
        ctx.prec = 40
        raw = Decimal(jpy) * Decimal(factor) / Decimal(usd_jpy)
        return raw.quantize(Decimal("0.01"), rounding=ROUND_CEILING)


def factor_percent(factor: Decimal) -> str:
    return str((Decimal(factor) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def latest_rate() -> CardFxRate | None:
    return CardFxRate.objects.order_by("-rate_date").first()


def build_payload(today: date | None = None, factor: Decimal | None = None) -> dict:
    """factor 不为空时用它代替已保存的系数（管理后台保存前预览用，不写库）。"""
    today = today or timezone.localdate()
    st = get_settings()
    use = st.factor if factor is None else factor
    rate = latest_rate()
    out = {
        "has_data": rate is not None,
        "rate_date": None,
        "usd_jpy": None,
        "usd_cny": None,
        "source": None,
        "fetched_at": None,
        "factor": str(use),
        "factor_percent": factor_percent(use),
        "saved_factor": str(st.factor),
        "stale_days": None,
        "is_stale": False,
        "stale_after_days": STALE_DAYS,
        "items": [],
        "settings_updated_at": st.updated_at.isoformat() if st.updated_at else None,
        "settings_updated_by": _user_name(st.updated_by),
    }
    if rate is None:
        return out
    stale = (today - rate.rate_date).days
    out.update(
        rate_date=rate.rate_date.isoformat(),
        usd_jpy=str(rate.usd_jpy),
        usd_cny=str(rate.usd_cny),
        source=rate.source,
        fetched_at=rate.fetched_at.isoformat() if rate.fetched_at else None,
        stale_days=stale,
        is_stale=stale > STALE_DAYS,
        items=[{"jpy": a, "usd": str(charge_usd(a, rate.usd_jpy, use))} for a in AMOUNTS],
    )
    return out


def _user_name(u) -> str:
    if not u:
        return ""
    return (u.get_full_name() or "").strip() or u.username


# ---------- 企微文案 ----------


def _md(d: date) -> str:
    return f"{d.month}月{d.day}日"


def build_wecom_markdown(today: date | None = None, page_url: str = "") -> str | None:
    """没有汇率数据时返回 None。"""
    today = today or timezone.localdate()
    p = build_payload(today)
    if not p["has_data"]:
        return None
    rd = date.fromisoformat(p["rate_date"])
    lines = [
        "**日元充值汇率**",
        f'<font color="comment">{_md(today)} {_WEEKDAY_CN[today.weekday()]} · 汇率日期 {_md(rd)}</font>',
    ]
    if p["is_stale"]:
        lines.append(f'<font color="warning">⚠️ 汇率已 {p["stale_days"]} 天未更新，充值请多留余量</font>')
    lines.append("")
    lines.append(f"> 美元兑人民币 **{p['usd_cny']}**　乘以 **{p['factor_percent']}%**")
    for it in p["items"]:
        lines.append(f"> {it['jpy']:,} 日元 → 充 **${it['usd']}**")
    if page_url:
        lines.append("")
        lines.append(f"[打开大厅查看]({page_url})")
    return "\n".join(lines)
