"""值班打卡接口（职员端「值班打卡」页 public/duty.html 使用）。

角色：
  管理者（超级管理员 / 老板 / CEO）：管理事务和分配、看全部、代打卡、确认、批准请假、调班、设全员休息；
  员工：只看到分给自己的事务，打卡、申请请假。
规则：只能当天打卡、当天修改/撤销（按 TIME_ZONE 的本地日期），过了当天就锁定，漏了不能补。
打卡成功后推送企业微信群（catalog/duty_notify.py）。
"""

from __future__ import annotations

import calendar
import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.apps.catalog import duty, duty_notify
from backend.apps.catalog.models import DutyLeave, DutyRecord, DutyTask
from backend.apps.catalog.roles import is_boss, is_ceo

from .views import StaffOnlyPermission

MAX_IMAGE_BYTES = 8 * 1024 * 1024


def is_manager(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or is_boss(user) or is_ceo(user)))


def _name(user) -> str:
    if not user:
        return ""
    return (user.get_full_name() or "").strip() or user.username


def _ms(dt):
    return int(dt.timestamp() * 1000) if dt else None


def _parse_day(raw):
    try:
        return date.fromisoformat(str(raw or "").strip()[:10])
    except ValueError:
        return None


def _int(v, default=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _task_json(t: DutyTask) -> dict:
    return {
        "id": t.id, "key": t.key, "name": t.name, "icon": t.icon, "color": t.color, "description": t.description,
        "sort_order": t.sort_order, "is_active": t.is_active,
        "freq_type": t.freq_type, "freq_weekdays": t.freq_weekdays or [], "freq_monthdays": t.freq_monthdays or [],
        "freq_interval": t.freq_interval, "start_date": t.start_date.isoformat() if t.start_date else None,
        "end_date": t.end_date.isoformat() if t.end_date else None,
        "assign_mode": t.assign_mode, "assignees": t.assignees or [],
        "qty_enabled": t.qty_enabled, "qty_label": t.qty_label, "qty_unit": t.qty_unit, "qty_required": t.qty_required,
        "target_mode": t.target_mode, "target_start": t.target_start, "target_end": t.target_end,
        "target_overrides": t.target_overrides or {}, "checklist": t.checklist or [], "image_mode": t.image_mode,
        "push_wecom": t.push_wecom,
    }


def _record_json(r: DutyRecord) -> dict:
    return {
        "date": r.date.isoformat(), "task": r.task, "user": r.assignee_id,
        "by": r.done_by_id, "by_name": _name(r.done_by), "by_manager": r.by_manager,
        "at": _ms(r.done_at), "edited_at": _ms(r.edited_at), "data": r.data or {},
        "img": r.image.url if r.image else None,
        "confirmed": bool(r.confirmed_at), "confirm_name": _name(r.confirmed_by), "confirm_at": _ms(r.confirmed_at),
    }


def _leave_json(lv: DutyLeave) -> dict:
    return {
        "id": lv.id, "user": lv.user_id, "user_name": _name(lv.user),
        "start": lv.start_date.isoformat(), "end": lv.end_date.isoformat(), "reason": lv.reason, "status": lv.status,
        "created_by_name": _name(lv.created_by), "created_at": _ms(lv.created_at),
        "decided_by_name": _name(lv.decided_by), "decided_at": _ms(lv.decided_at),
    }


def _month_range(raw: str, today: date):
    try:
        y, m = (int(x) for x in raw.split("-")[:2])
        first = date(y, m, 1)
    except (ValueError, TypeError, AttributeError):
        first = date(today.year, today.month, 1)
    return first, date(first.year, first.month, calendar.monthrange(first.year, first.month)[1])


def _find_assignment(d: date, task_key: str, user_id: int):
    for a in duty.assignments_for(d):
        if a["task"] == task_key and a["user"] == user_id:
            return a
    return None


class DutyStateAPIView(APIView):
    """GET ?month=YYYY-MM：我是谁、事务、这个月每天的分配、打卡记录、请假、接下来 14 天我的安排。"""

    permission_classes = [StaffOnlyPermission]

    def get(self, request):
        today = timezone.localdate()
        first, last = _month_range(request.GET.get("month") or "", today)
        manager = is_manager(request.user)
        uid = request.user.id
        cfg = duty.load_config()
        tasks = list(DutyTask.objects.order_by("sort_order", "id"))
        active = [t for t in tasks if t.is_active]
        sched = duty.schedule(first, last, active, cfg)
        upcoming = duty.schedule(today, today + timedelta(days=13), active, cfg)

        recs = DutyRecord.objects.filter(date__gte=first, date__lte=last).select_related("done_by", "confirmed_by")
        leaves = DutyLeave.objects.filter(
            Q(start_date__lte=last, end_date__gte=first - timedelta(days=31)) | Q(status=DutyLeave.STATUS_PENDING)
        ).select_related("user", "created_by", "decided_by").order_by("-start_date", "-id")
        if not manager:
            # 员工只看自己的
            sched = {d: [a for a in lst if a["user"] == uid or a.get("cover_for") == uid] for d, lst in sched.items()}
            recs = recs.filter(assignee_id=uid)
            leaves = leaves.filter(user_id=uid)
        upcoming = {d: [a for a in lst if a["user"] == uid] for d, lst in upcoming.items()}

        User = get_user_model()
        ids = {uid}
        for t in tasks:
            ids.update(duty._clean_ids(t.assignees))
        users_qs = User.objects.filter(is_active=True, is_staff=True) if manager else User.objects.filter(id__in=ids)
        payload = {
            "today": today.isoformat(),
            "month": f"{first.year}-{first.month:02d}",
            "me": {"id": uid, "name": _name(request.user), "manager": manager},
            "users": {str(u.id): _name(u) for u in users_qs.order_by("username")},
            "tasks": [_task_json(t) for t in tasks if manager or t.is_active],
            "config": cfg if manager else {"offDays": cfg.get("offDays") or []},
            "schedule": sched,
            "upcoming": upcoming,
            "records": [_record_json(r) for r in recs],
            "leaves": [_leave_json(lv) for lv in leaves[:300]],
            "push_enabled": bool(duty_notify.webhook_url()),
        }
        return Response(payload)


class DutyCheckinAPIView(APIView):
    """POST（multipart）：date, task, data(JSON 字符串), image(可选), remove_image=1(可选), user(管理者代打时传)。"""

    permission_classes = [StaffOnlyPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        today = timezone.localdate()
        d = _parse_day(request.data.get("date"))
        key = str(request.data.get("task") or "").strip()
        manager = is_manager(request.user)
        target_user = _int(request.data.get("user")) if manager else request.user.id
        target_user = target_user or request.user.id
        if d is None or not key:
            return Response({"detail": "参数不对"}, status=status.HTTP_400_BAD_REQUEST)
        if d != today:
            return Response({"detail": "只能当天打卡，过了当天不能补。"}, status=status.HTTP_400_BAD_REQUEST)
        task = DutyTask.objects.filter(key=key, is_active=True).first()
        a = task and _find_assignment(d, key, target_user)
        if not a:
            return Response({"detail": "今天没有分给这个人的这件事。"}, status=status.HTTP_403_FORBIDDEN)

        try:
            raw = request.data.get("data") or "{}"
            data = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (ValueError, TypeError):
            return Response({"detail": "反馈内容格式不对"}, status=status.HTTP_400_BAD_REQUEST)
        clean = {"note": str(data.get("note") or "")[:500]}
        if task.qty_enabled:
            v = data.get("qty")
            if v in (None, ""):
                if task.qty_required:
                    return Response({"detail": f"请填写{task.qty_label or '数量'}"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                q = _int(v)
                if q is None or q < 0:
                    return Response({"detail": "数量要填数字"}, status=status.HTTP_400_BAD_REQUEST)
                clean["qty"] = q
        if task.checklist:
            checks = data.get("checks") or {}
            clean["checks"] = {str(i): bool(checks.get(str(i))) for i in range(len(task.checklist))}
            if not all(clean["checks"].values()):
                return Response({"detail": "清单里的每一项都做完才能打卡。"}, status=status.HTTP_400_BAD_REQUEST)

        img = request.FILES.get("image")
        if img and (img.size > MAX_IMAGE_BYTES or not (img.content_type or "").startswith("image/")):
            return Response({"detail": "截图要是图片，且不超过 8MB。"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            rec = DutyRecord.objects.select_for_update().filter(date=d, task=key, assignee_id=target_user).first()
            edited = rec is not None
            if rec is None:
                rec = DutyRecord(date=d, task=key, assignee_id=target_user, done_at=now, done_by=request.user,
                                 by_manager=request.user.id != target_user)
            else:
                rec.edited_at = now
                rec.confirmed_by = None
                rec.confirmed_at = None
            rec.data = clean
            if request.data.get("remove_image") in ("1", "true", True) and rec.image:
                rec.image.delete(save=False)
                rec.image = None
            if img:
                if rec.image:
                    rec.image.delete(save=False)
                rec.image = img
            if task.image_mode == DutyTask.IMAGE_REQUIRED and not rec.image:
                transaction.set_rollback(True)
                return Response({"detail": "这件事需要上传截图。"}, status=status.HTTP_400_BAD_REQUEST)
            rec.save()

        if task.push_wecom and not edited:
            self._push(task, rec, a, d)
        return Response(_record_json(rec))

    @staticmethod
    def _push(task, rec, a, d):
        User = get_user_model()
        todays = duty.assignments_for(d)
        live = [x for x in todays if x.get("user")]
        done_keys = set(DutyRecord.objects.filter(date=d).values_list("task", "assignee_id"))
        names = {u.id: _name(u) for u in User.objects.filter(id__in={x["user"] for x in live} | {a.get("cover_for") or 0})}
        tnames = dict(DutyTask.objects.values_list("key", "name"))
        remaining = [f"{tnames.get(x['task'], x['task'])} @{names.get(x['user'], '')}" for x in live
                     if (x["task"], x["user"]) not in done_keys]
        md = duty_notify.build_checkin_markdown(
            task=task, rec=rec, doer_name=_name(rec.done_by), assignee_name=names.get(rec.assignee_id) or _name(rec.done_by),
            cover_for_name=names.get(a.get("cover_for"), "") if a.get("cover_for") else "",
            target=a.get("target"), progress=(len(live) - len(remaining), len(live)), remaining=remaining,
        )
        transaction.on_commit(lambda: duty_notify.push_async(md))


class DutyUndoAPIView(APIView):
    """POST {date, task, user?}：撤销当天的打卡。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        d = _parse_day(request.data.get("date"))
        if d != timezone.localdate():
            return Response({"detail": "过了当天就锁定了，不能撤销。"}, status=status.HTTP_400_BAD_REQUEST)
        manager = is_manager(request.user)
        uid = (_int(request.data.get("user")) if manager else None) or request.user.id
        rec = DutyRecord.objects.filter(date=d, task=str(request.data.get("task") or ""), assignee_id=uid).first()
        if not rec:
            return Response(status=status.HTTP_204_NO_CONTENT)
        if request.user.id not in (rec.done_by_id, rec.assignee_id) and not manager:
            return Response({"detail": "只能撤销自己的打卡。"}, status=status.HTTP_403_FORBIDDEN)
        if rec.image:
            rec.image.delete(save=False)
        rec.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DutyConfirmAPIView(APIView):
    """POST {date, task, user, confirm}：管理者确认 / 撤销确认（不限日期）。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        if not is_manager(request.user):
            return Response({"detail": "只有管理者可以确认。"}, status=status.HTTP_403_FORBIDDEN)
        rec = DutyRecord.objects.filter(date=_parse_day(request.data.get("date")),
                                        task=str(request.data.get("task") or ""),
                                        assignee_id=_int(request.data.get("user"))).first()
        if not rec:
            return Response({"detail": "还没有打卡记录。"}, status=status.HTTP_404_NOT_FOUND)
        if request.data.get("confirm") in (False, "false", "0", 0):
            rec.confirmed_by, rec.confirmed_at = None, None
        else:
            rec.confirmed_by, rec.confirmed_at = request.user, timezone.now()
        rec.save(update_fields=["confirmed_by", "confirmed_at"])
        return Response(_record_json(rec))


class DutySettingsAPIView(APIView):
    """PUT {config: {swaps?, offDays?}}：单天调班、全员休息（管理者）。"""

    permission_classes = [StaffOnlyPermission]

    def put(self, request):
        if not is_manager(request.user):
            return Response({"detail": "只有管理者可以改。"}, status=status.HTTP_403_FORBIDDEN)
        incoming = request.data.get("config") or {}
        cfg = duty.load_config()
        if isinstance(incoming.get("swaps"), dict):
            keys = set(DutyTask.objects.values_list("key", flat=True))
            cfg["swaps"] = {
                k: _int(v) for k, v in incoming["swaps"].items()
                if _int(v) and "|" in k and _parse_day(k.split("|")[0]) and k.split("|", 1)[1] in keys
            }
        if isinstance(incoming.get("offDays"), list):
            cfg["offDays"] = sorted({_parse_day(x).isoformat() for x in incoming["offDays"] if _parse_day(x)})
        duty.save_config(cfg, request.user)
        return Response({"config": duty.load_config()})


# ---------------- 事务管理 ----------------

_FIELDS_STR = {"name": 60, "icon": 8, "color": 9, "description": 500, "qty_label": 30, "qty_unit": 10}


def _apply_task(t: DutyTask, src: dict) -> str | None:
    """把前端传来的事务设置写进 t，有问题返回错误提示。"""
    for k, n in _FIELDS_STR.items():
        if k in src:
            setattr(t, k, str(src.get(k) or "").strip()[:n])
    if not t.name:
        return "请填写事务名称"
    if "freq_type" in src:
        if src["freq_type"] not in dict(DutyTask.FREQ_CHOICES):
            return "频率不对"
        t.freq_type = src["freq_type"]
    if "freq_weekdays" in src:
        t.freq_weekdays = sorted({x for x in (_int(v) for v in src["freq_weekdays"] or []) if x is not None and 0 <= x <= 6})
    if "freq_monthdays" in src:
        t.freq_monthdays = sorted({x for x in (_int(v) for v in src["freq_monthdays"] or [])
                                   if x is not None and (1 <= x <= 31 or x == -1)})
    if "freq_interval" in src:
        t.freq_interval = max(1, min(365, _int(src["freq_interval"], 1)))
    if t.freq_type == DutyTask.FREQ_WEEKLY and not t.freq_weekdays:
        return "请选择每周哪几天"
    if t.freq_type == DutyTask.FREQ_MONTHLY and not t.freq_monthdays:
        return "请选择每月哪几号"
    if "start_date" in src:
        t.start_date = _parse_day(src["start_date"])
    if not t.start_date:
        return "请填写开始日期"
    if "end_date" in src:
        t.end_date = _parse_day(src["end_date"]) if src.get("end_date") else None
    if t.end_date and t.end_date < t.start_date:
        return "结束日期不能早于开始日期"
    if "assign_mode" in src:
        if src["assign_mode"] not in dict(DutyTask.ASSIGN_CHOICES):
            return "分配方式不对"
        t.assign_mode = src["assign_mode"]
    if "assignees" in src:
        User = get_user_model()
        ids = [x for x in (_int(v) for v in src["assignees"] or []) if x][:60]
        valid = set(User.objects.filter(id__in=ids, is_active=True).values_list("id", flat=True))
        t.assignees = [x for x in ids if x in valid]
    if t.assign_mode == DutyTask.ASSIGN_FIXED and len(t.assignees) > 1:
        t.assignees = list(dict.fromkeys(t.assignees))
    for k in ("qty_enabled", "qty_required", "push_wecom", "is_active"):
        if k in src:
            setattr(t, k, bool(src[k]))
    if "target_mode" in src:
        if src["target_mode"] not in dict(DutyTask.TARGET_CHOICES):
            return "数量目标不对"
        t.target_mode = src["target_mode"]
    for k in ("target_start", "target_end"):
        if k in src:
            setattr(t, k, _int(src[k]))
    if t.target_mode == DutyTask.TARGET_FIXED and t.target_start is None:
        return "请填写数量目标"
    if t.target_mode == DutyTask.TARGET_RAMP and (t.target_start is None or t.target_end is None):
        return "请填写月初和月底的数量目标"
    if "target_overrides" in src and isinstance(src["target_overrides"], dict):
        t.target_overrides = {k: _int(v) for k, v in src["target_overrides"].items()
                              if _parse_day(k) and _int(v) is not None}
    if "checklist" in src:
        t.checklist = [str(x).strip()[:40] for x in (src["checklist"] or []) if str(x).strip()][:10]
    if "image_mode" in src:
        if src["image_mode"] not in dict(DutyTask.IMAGE_CHOICES):
            return "截图设置不对"
        t.image_mode = src["image_mode"]
    if "sort_order" in src:
        t.sort_order = _int(src["sort_order"], 0)
    return None


class DutyTaskListAPIView(APIView):
    """POST：新增事务（管理者）。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        if not is_manager(request.user):
            return Response({"detail": "只有管理者可以管理事务。"}, status=status.HTTP_403_FORBIDDEN)
        t = DutyTask(key="tmp", sort_order=(DutyTask.objects.order_by("-sort_order").values_list("sort_order", flat=True)
                                             .first() or 0) + 1)
        err = _apply_task(t, request.data)
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            t.key = f"tmp{timezone.now().timestamp()}"[:32]
            t.save()
            t.key = f"t{t.id}"
            t.save(update_fields=["key"])
        return Response(_task_json(t), status=status.HTTP_201_CREATED)


class DutyTaskDetailAPIView(APIView):
    """PUT：修改事务；DELETE：删除（有打卡记录的改为停用，保留记录）。"""

    permission_classes = [StaffOnlyPermission]

    def put(self, request, pk: int):
        if not is_manager(request.user):
            return Response({"detail": "只有管理者可以管理事务。"}, status=status.HTTP_403_FORBIDDEN)
        t = DutyTask.objects.filter(pk=pk).first()
        if not t:
            return Response({"detail": "找不到这件事"}, status=status.HTTP_404_NOT_FOUND)
        err = _apply_task(t, request.data)
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        t.save()
        return Response(_task_json(t))

    def delete(self, request, pk: int):
        if not is_manager(request.user):
            return Response({"detail": "只有管理者可以管理事务。"}, status=status.HTTP_403_FORBIDDEN)
        t = DutyTask.objects.filter(pk=pk).first()
        if not t:
            return Response(status=status.HTTP_204_NO_CONTENT)
        if DutyRecord.objects.filter(task=t.key).exists():
            t.is_active = False
            t.save(update_fields=["is_active"])
            return Response({"detail": "这件事有打卡记录，已改为停用（记录保留）。", "archived": True})
        t.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DutyTaskPreviewAPIView(APIView):
    """POST 事务设置（不保存）：返回接下来 10 次是哪天、轮到谁，方便管理者确认。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        if not is_manager(request.user):
            return Response({"detail": "只有管理者可以管理事务。"}, status=status.HTTP_403_FORBIDDEN)
        t = DutyTask(key=str(request.data.get("key") or "preview"))
        err = _apply_task(t, {**request.data, "is_active": True})
        if err:
            return Response({"detail": err, "items": []})
        today = timezone.localdate()
        cur, out, cfg = max(today, t.start_date), [], {"swaps": {}, "offDays": []}
        for _ in range(800):
            if t.end_date and cur > t.end_date:
                break
            for a in duty.assignments_on(cur, [t], cfg, set()):
                out.append({"date": cur.isoformat(), "user": a["user"], "target": a.get("target")})
            if len(out) >= 10:
                break
            cur += timedelta(days=1)
        return Response({"items": out[:10]})


# ---------------- 请假 ----------------

class DutyLeaveAPIView(APIView):
    """POST {start, end, reason, user?}：员工申请请假（待批准）；管理者替人登记（带 user）直接生效。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        today = timezone.localdate()
        start = _parse_day(request.data.get("start"))
        end = _parse_day(request.data.get("end") or request.data.get("start"))
        if not start or not end or end < start:
            return Response({"detail": "请假日期不对"}, status=status.HTTP_400_BAD_REQUEST)
        if (end - start).days > 60:
            return Response({"detail": "一次最多请 60 天"}, status=status.HTTP_400_BAD_REQUEST)
        manager = is_manager(request.user)
        for_user = _int(request.data.get("user")) if manager else None
        direct = bool(for_user)
        uid = for_user or request.user.id
        if not direct and start < today:
            return Response({"detail": "不能给已经过去的日子请假"}, status=status.HTTP_400_BAD_REQUEST)
        if not get_user_model().objects.filter(id=uid, is_active=True).exists():
            return Response({"detail": "找不到这个人"}, status=status.HTTP_400_BAD_REQUEST)
        if DutyLeave.objects.filter(user_id=uid, status__in=(DutyLeave.STATUS_PENDING, DutyLeave.STATUS_APPROVED),
                                    start_date__lte=end, end_date__gte=start).exists():
            return Response({"detail": "这段时间已经有请假记录了"}, status=status.HTTP_400_BAD_REQUEST)
        lv = DutyLeave.objects.create(
            user_id=uid, start_date=start, end_date=end, reason=str(request.data.get("reason") or "")[:200],
            status=DutyLeave.STATUS_APPROVED if direct else DutyLeave.STATUS_PENDING, created_by=request.user,
            decided_by=request.user if direct else None, decided_at=timezone.now() if direct else None,
        )
        return Response(_leave_json(lv), status=status.HTTP_201_CREATED)


class DutyLeaveActionAPIView(APIView):
    """POST /duty/leave/<id>/<action>/：approve / reject（管理者），cancel（本人撤销待批准的；管理者可撤销任何）。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request, pk: int, action: str):
        lv = DutyLeave.objects.filter(pk=pk).select_related("user").first()
        if not lv:
            return Response({"detail": "找不到这条请假"}, status=status.HTTP_404_NOT_FOUND)
        manager = is_manager(request.user)
        if action in ("approve", "reject"):
            if not manager:
                return Response({"detail": "只有管理者可以批准"}, status=status.HTTP_403_FORBIDDEN)
            if lv.status != DutyLeave.STATUS_PENDING:
                return Response({"detail": "这条请假已经处理过了"}, status=status.HTTP_400_BAD_REQUEST)
            lv.status = DutyLeave.STATUS_APPROVED if action == "approve" else DutyLeave.STATUS_REJECTED
        elif action == "cancel":
            if not manager and not (lv.user_id == request.user.id and lv.status == DutyLeave.STATUS_PENDING):
                return Response({"detail": "已批准的请假只能让管理者撤销"}, status=status.HTTP_403_FORBIDDEN)
            if lv.status in (DutyLeave.STATUS_REJECTED, DutyLeave.STATUS_CANCELLED):
                return Response({"detail": "这条请假已经失效了"}, status=status.HTTP_400_BAD_REQUEST)
            lv.status = DutyLeave.STATUS_CANCELLED
        else:
            return Response({"detail": "未知操作"}, status=status.HTTP_400_BAD_REQUEST)
        lv.decided_by, lv.decided_at = request.user, timezone.now()
        lv.save(update_fields=["status", "decided_by", "decided_at"])
        return Response(_leave_json(lv))

