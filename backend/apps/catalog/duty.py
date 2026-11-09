"""值班打卡的排班引擎：事务（DutyTask）按频率出现，按分配方式落到具体的人。

频率 freq_type：
  daily     每天
  weekly    每周几（freq_weekdays：0=周一 … 6=周日）
  monthly   每月几号（freq_monthdays：1–31，-1 = 每月最后一天）
  interval  从开始日期起每隔 N 天（freq_interval）
  once      只做一次（start_date 那天）

分配 assign_mode：
  fixed     固定 assignees[0]；他请假时由列表里下一个没请假的人代做
  rotate    按 assignees 顺序每次轮换（同一个人放两次 = 他做得多）；请假时顺延给下一个没请假的人，轮流顺序本身不变
  all       assignees 里每个人都要做、各自打卡；请假的人当天免做

临时调整（DutySettings.config）：
  swaps     'YYYY-MM-DD|task_key' -> user_id   某天某件事改给某人（fixed / rotate 才有效）
  offDays   ['YYYY-MM-DD']                     全员休息，不排任何事，也不算漏做
请假：已取消（2026-11），排班不再考虑请假。
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from django.utils import timezone

from .models import DutyLeave, DutySettings, DutyTask

DEFAULTS = {"swaps": {}, "offDays": []}


def load_config() -> dict:
    obj = DutySettings.objects.order_by("id").first()
    cfg = dict(DEFAULTS)
    if obj and isinstance(obj.config, dict):
        cfg["swaps"] = obj.config.get("swaps") or {}
        cfg["offDays"] = obj.config.get("offDays") or []
    return cfg


def save_config(cfg: dict, user=None) -> None:
    obj = DutySettings.objects.order_by("id").first() or DutySettings()
    base = obj.config if isinstance(obj.config, dict) else {}
    base.update({k: cfg.get(k, DEFAULTS[k]) for k in DEFAULTS})
    obj.config = base
    obj.updated_by = user
    obj.save()


def _last_day(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]


def occurs(t: DutyTask, d: date) -> bool:
    if not t.start_date or d < t.start_date or (t.end_date and d > t.end_date):
        return False
    ft = t.freq_type
    if ft == DutyTask.FREQ_DAILY:
        return True
    if ft == DutyTask.FREQ_WEEKLY:
        return d.weekday() in (t.freq_weekdays or [])
    if ft == DutyTask.FREQ_MONTHLY:
        days = t.freq_monthdays or []
        return d.day in days or (-1 in days and d.day == _last_day(d))
    if ft == DutyTask.FREQ_INTERVAL:
        n = max(1, int(t.freq_interval or 1))
        return (d - t.start_date).days % n == 0
    if ft == DutyTask.FREQ_ONCE:
        return d == t.start_date
    return False


def occ_index(t: DutyTask, d: date) -> int:
    """从开始日期到 d（不含）一共出现过几次，用来决定轮到谁。"""
    if d <= t.start_date:
        return 0
    span = (d - t.start_date).days
    ft = t.freq_type
    if ft == DutyTask.FREQ_DAILY:
        return span
    if ft == DutyTask.FREQ_INTERVAL:
        n = max(1, int(t.freq_interval or 1))
        return (span + n - 1) // n
    if ft == DutyTask.FREQ_WEEKLY:
        wd = set(t.freq_weekdays or [])
        full, rest = divmod(span, 7)
        cnt = full * len(wd)
        for i in range(rest):
            if (t.start_date + timedelta(days=full * 7 + i)).weekday() in wd:
                cnt += 1
        return cnt
    if ft == DutyTask.FREQ_MONTHLY:
        cnt, cur = 0, date(t.start_date.year, t.start_date.month, 1)
        while cur <= d:
            last = _last_day(cur)
            days = {x for x in (t.freq_monthdays or []) if 1 <= x <= last}
            if -1 in (t.freq_monthdays or []):
                days.add(last)
            for x in days:
                day = date(cur.year, cur.month, x)
                if t.start_date <= day < d:
                    cnt += 1
            cur = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
        return cnt
    return 0


def target_for(t: DutyTask, d: date):
    """当天的数量目标；没有目标返回 None。"""
    ov = (t.target_overrides or {}).get(d.isoformat())
    if ov not in (None, ""):
        return int(ov)
    if t.target_mode == DutyTask.TARGET_FIXED:
        return t.target_start
    if t.target_mode == DutyTask.TARGET_RAMP:
        n = _last_day(d)
        a, b = int(t.target_start or 0), int(t.target_end or 0)
        return round(a + (b - a) * (d.day - 1) / max(1, n - 1))
    return None


def _clean_ids(ids) -> list[int]:
    out = []
    for x in ids or []:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out


def assignments_on(d: date, tasks, cfg: dict, on_leave: set) -> list[dict]:
    """当天所有要做的事：[{task, user, plan_user, cover_for?, swapped?, skip?, target}]，一人一条。"""
    ds = d.isoformat()
    if ds in (cfg.get("offDays") or []):
        return []
    swaps = cfg.get("swaps") or {}
    out = []
    for t in tasks:
        if not t.is_active or not occurs(t, d):
            continue
        seq = _clean_ids(t.assignees)
        if not seq:
            out.append({"task": t.key, "user": None, "plan_user": None, "skip": True, "unassigned": True,
                        "target": target_for(t, d)})
            continue
        tgt = target_for(t, d)
        if t.assign_mode == DutyTask.ASSIGN_ALL:
            for uid in dict.fromkeys(seq):
                item = {"task": t.key, "user": uid, "plan_user": uid, "target": tgt}
                if uid in on_leave:
                    item.update(cover_for=uid, user=None, skip=True)
                out.append(item)
            continue
        idx = occ_index(t, d) % len(seq) if t.assign_mode == DutyTask.ASSIGN_ROTATE else 0
        plan = seq[idx]
        item = {"task": t.key, "user": plan, "plan_user": plan, "target": tgt}
        forced = swaps.get(f"{ds}|{t.key}")
        try:
            forced = int(forced) if forced not in (None, "") else None
        except (TypeError, ValueError):
            forced = None
        if forced and forced != plan:
            item.update(user=forced, swapped=True)
        if item["user"] in on_leave:
            orig = item["user"]
            cover = None
            for k in range(1, len(seq) + 1):
                cand = seq[(idx + k) % len(seq)]
                if cand != orig and cand not in on_leave:
                    cover = cand
                    break
            item.update(cover_for=orig, user=cover)
            if cover is None:
                item["skip"] = True
        out.append(item)
    return out


def leave_map(first: date, last: date) -> dict:
    """{date: set(user_id)}：这段时间每天已批准请假的人。"""
    out: dict = {}
    for lv in DutyLeave.objects.filter(status=DutyLeave.STATUS_APPROVED, start_date__lte=last, end_date__gte=first):
        cur = max(lv.start_date, first)
        while cur <= min(lv.end_date, last):
            out.setdefault(cur, set()).add(lv.user_id)
            cur += timedelta(days=1)
    return out


def active_tasks():
    return list(DutyTask.objects.filter(is_active=True).order_by("sort_order", "id"))


def schedule(first: date, last: date, tasks=None, cfg=None) -> dict:
    """{ 'YYYY-MM-DD': [assignment, ...] }"""
    tasks = active_tasks() if tasks is None else tasks
    cfg = cfg or load_config()
    # 请假模块已取消：排班不再看请假记录（DutyLeave 表保留，不影响）
    out = {}
    cur = first
    while cur <= last:
        out[cur.isoformat()] = assignments_on(cur, tasks, cfg, set())
        cur += timedelta(days=1)
    return out


def assignments_for(d: date) -> list[dict]:
    return schedule(d, d)[d.isoformat()]


def today() -> date:
    return timezone.localdate()
