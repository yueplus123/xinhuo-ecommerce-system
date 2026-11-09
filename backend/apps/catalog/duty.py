"""值班打卡的排班规则（前端 public/duty.html 用同一套算法显示）。

四件事：
  sell   销卡：每天，A、B 一人一天轮流
  stock  增加成品号库存：每天，A、B 轮流（默认和销卡错开）；当天库存目标从月初 stockStart 递增到月底 stockEnd，可按天改
  clean  清理卡片 + 通知充值：每月最后一天
  unbind 解绑卡片：每月 1–3 号里选一天

临时情况（不改轮流规则）：
  swaps    单天调班：'YYYY-MM-DD|task' -> 'a'|'b'
  offDays  全员停做的日期：那天不排任何事，也不算漏做
  请假     DutyLeave 批准后，请假人那几天的事交给另一个人；两人都请假则这件事当天不做
"""

from __future__ import annotations

import calendar
from datetime import date

from django.utils import timezone

from .models import DutyLeave, DutySettings

DEFAULTS = {
    "a_user": None,  # A 的用户 id
    "b_user": None,  # B 的用户 id
    "rotStart": None,  # 'YYYY-MM-DD'：这天由 rotFirst 销卡，之后一人一天
    "rotFirst": "a",
    "stockMode": "other",  # other = 和销卡错开；same = 同一个人
    "stockStart": 200,
    "stockEnd": 500,
    "stockOverride": {},  # 'YYYY-MM-DD' -> 数量
    "endWho": "sell",  # 月底清理：sell = 当天销卡的人；a / b
    "unbindPlan": {},  # 'YYYY-MM' -> {"date": 'YYYY-MM-DD', "who": 'a'|'b'}
    "unbindDefaultDay": 2,
    "unbindDefaultWho": "a",
    "swaps": {},  # 'YYYY-MM-DD|task' -> 'a'|'b'
    "offDays": [],  # ['YYYY-MM-DD']
}

TASK_KEYS = ("sell", "stock", "clean", "unbind")


def load_config() -> dict:
    obj = DutySettings.objects.order_by("id").first()
    cfg = dict(DEFAULTS)
    if obj and isinstance(obj.config, dict):
        cfg.update(obj.config)
    if not cfg.get("rotStart"):
        today = timezone.localdate()
        cfg["rotStart"] = date(today.year, today.month, 1).isoformat()
    return cfg


def _other(k: str) -> str:
    return "b" if k == "a" else "a"


def sell_who(d: date, cfg: dict) -> str:
    start = date.fromisoformat(cfg["rotStart"])
    n = (d - start).days
    return cfg.get("rotFirst", "a") if n % 2 == 0 else _other(cfg.get("rotFirst", "a"))


def stock_target(d: date, cfg: dict) -> int:
    ov = (cfg.get("stockOverride") or {}).get(d.isoformat())
    if ov not in (None, ""):
        return int(ov)
    n = calendar.monthrange(d.year, d.month)[1]
    start, end = int(cfg.get("stockStart") or 0), int(cfg.get("stockEnd") or 0)
    return round(start + (end - start) * (d.day - 1) / (n - 1))


def unbind_plan(year: int, month: int, cfg: dict) -> dict:
    ym = f"{year}-{month:02d}"
    plan = (cfg.get("unbindPlan") or {}).get(ym)
    if plan and plan.get("date"):
        return {"date": plan["date"], "who": plan.get("who") or "a"}
    day = int(cfg.get("unbindDefaultDay") or 2)
    return {"date": f"{ym}-{day:02d}", "who": cfg.get("unbindDefaultWho") or "a"}


def tasks_on(d: date, cfg: dict, on_leave=frozenset()) -> list[dict]:
    """返回当天要做的事：[{task, who('a'|'b'|None), target?, swapped?, cover_for?, skip?}]。

    on_leave：当天请假（已批准）的人，'a' / 'b' 的集合。
    """
    ds = d.isoformat()
    if ds in (cfg.get("offDays") or []):
        return []
    sw = sell_who(d, cfg)
    out = [
        {"task": "sell", "who": sw},
        {"task": "stock", "who": sw if cfg.get("stockMode") == "same" else _other(sw), "target": stock_target(d, cfg)},
    ]
    if d.day == calendar.monthrange(d.year, d.month)[1]:
        end_who = cfg.get("endWho") or "sell"
        out.append({"task": "clean", "who": sw if end_who == "sell" else end_who})
    plan = unbind_plan(d.year, d.month, cfg)
    if plan["date"] == ds:
        out.append({"task": "unbind", "who": plan["who"]})
    swaps = cfg.get("swaps") or {}
    for t in out:
        forced = swaps.get(f"{ds}|{t['task']}")
        if forced in ("a", "b") and forced != t["who"]:
            t["who"], t["swapped"] = forced, True
        if t["who"] in on_leave:
            alt = _other(t["who"])
            if alt in on_leave:
                t["cover_for"], t["who"], t["skip"] = t["who"], None, True
            else:
                t["cover_for"], t["who"] = t["who"], alt
    return out


def leave_roles_on(d: date, cfg: dict) -> set:
    """当天已批准请假的人（'a' / 'b'）。"""
    ids = set(
        DutyLeave.objects.filter(status=DutyLeave.STATUS_APPROVED, start_date__lte=d, end_date__gte=d)
        .values_list("user_id", flat=True)
    )
    roles = set()
    if cfg.get("a_user") in ids:
        roles.add("a")
    if cfg.get("b_user") in ids:
        roles.add("b")
    return roles


def tasks_for(d: date, cfg: dict | None = None) -> list[dict]:
    """按数据库里的请假记录算当天的事。"""
    cfg = cfg or load_config()
    return tasks_on(d, cfg, leave_roles_on(d, cfg))


def user_id_for(who: str, cfg: dict):
    return cfg.get("a_user") if who == "a" else cfg.get("b_user")
