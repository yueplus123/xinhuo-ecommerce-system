"""值班打卡接口（职员端「值班打卡」页 public/duty.html 使用）。

规则：
  - 只能当天打卡、当天修改/撤销（按 TIME_ZONE 的本地日期），过了当天就锁定，漏了不能补；
  - 负责人本人可以打卡；老板 / CEO / 超级管理员可以代打、确认、改规则；
  - 请假：A/B 申请、老板批准；批准后那几天他的事交给另一个人，轮流顺序不变。
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

from backend.apps.catalog import duty
from backend.apps.catalog.models import DutyLeave, DutyRecord, DutySettings
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
        return date.fromisoformat((raw or "").strip()[:10])
    except ValueError:
        return None


def _role_of(user, cfg) -> str:
    if user and cfg.get("a_user") == user.id:
        return "a"
    if user and cfg.get("b_user") == user.id:
        return "b"
    return ""


def _record_json(r: DutyRecord, cfg: dict) -> dict:
    return {
        "by": _role_of(r.done_by, cfg),
        "by_name": _name(r.done_by),
        "assignee_name": _name(r.assignee),
        "by_manager": r.by_manager,
        "at": _ms(r.done_at),
        "edited_at": _ms(r.edited_at),
        "data": r.data or {},
        "img": r.image.url if r.image else None,
        "confirmed": bool(r.confirmed_at),
        "confirm_name": _name(r.confirmed_by),
        "confirm_at": _ms(r.confirmed_at),
    }


def _leave_json(lv: DutyLeave, cfg: dict) -> dict:
    return {
        "id": lv.id,
        "who": _role_of(lv.user, cfg),
        "user_name": _name(lv.user),
        "start": lv.start_date.isoformat(),
        "end": lv.end_date.isoformat(),
        "reason": lv.reason,
        "status": lv.status,
        "created_by_name": _name(lv.created_by),
        "created_at": _ms(lv.created_at),
        "decided_by_name": _name(lv.decided_by),
        "decided_at": _ms(lv.decided_at),
    }


def _find_task(d: date, task: str, cfg: dict):
    for t in duty.tasks_for(d, cfg):
        if t["task"] == task:
            return t
    return None


class DutyStateAPIView(APIView):
    """GET ?month=YYYY-MM：当前用户身份、规则、这个月的打卡记录。"""

    permission_classes = [StaffOnlyPermission]

    def get(self, request):
        cfg = duty.load_config()
        today = timezone.localdate()
        raw = (request.GET.get("month") or "").strip()
        try:
            y, m = (int(x) for x in raw.split("-")[:2]) if raw else (today.year, today.month)
            first = date(y, m, 1)
        except (ValueError, TypeError):
            first = date(today.year, today.month, 1)
        last = date(first.year, first.month, calendar.monthrange(first.year, first.month)[1])

        User = get_user_model()
        users = {u.id: u for u in User.objects.filter(id__in=[x for x in (cfg.get("a_user"), cfg.get("b_user")) if x])}
        recs = (
            DutyRecord.objects.filter(date__gte=first, date__lte=last)
            .select_related("done_by", "assignee", "confirmed_by")
        )
        manager = is_manager(request.user)
        payload = {
            "today": today.isoformat(),
            "month": f"{first.year}-{first.month:02d}",
            "me": {
                "id": request.user.id,
                "name": _name(request.user),
                "role": _role_of(request.user, cfg),
                "manager": manager,
            },
            "config": cfg,
            "names": {
                "a": _name(users.get(cfg.get("a_user"))) or "A（未设置）",
                "b": _name(users.get(cfg.get("b_user"))) or "B（未设置）",
            },
            "records": {f"{r.date.isoformat()}|{r.task}": _record_json(r, cfg) for r in recs},
            # 这个月相关的请假，加上所有待批准的（老板在「请假」页处理）
            "leaves": [
                _leave_json(lv, cfg)
                for lv in DutyLeave.objects.filter(
                    Q(start_date__lte=last, end_date__gte=first - timedelta(days=31)) | Q(status=DutyLeave.STATUS_PENDING)
                ).select_related("user", "created_by", "decided_by").order_by("-start_date", "-id")[:300]
            ],
        }
        if manager:
            payload["staff"] = [
                {"id": u.id, "name": _name(u)}
                for u in User.objects.filter(is_active=True, is_staff=True).order_by("username")
            ]
        return Response(payload)


class DutyCheckinAPIView(APIView):
    """POST（multipart）：date, task, data(JSON 字符串), image(可选), remove_image=1(可选)。"""

    permission_classes = [StaffOnlyPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        cfg = duty.load_config()
        today = timezone.localdate()
        d = _parse_day(request.data.get("date"))
        task = (request.data.get("task") or "").strip()
        if d is None or task not in duty.TASK_KEYS:
            return Response({"detail": "参数不对"}, status=status.HTTP_400_BAD_REQUEST)
        if d != today:
            return Response({"detail": "只能当天打卡，过了当天不能补。"}, status=status.HTTP_400_BAD_REQUEST)
        t = _find_task(d, task, cfg)
        if not t:
            return Response({"detail": "今天没有这件事。"}, status=status.HTTP_400_BAD_REQUEST)
        if not t.get("who"):
            return Response({"detail": "今天两个人都请假，这件事不用做。"}, status=status.HTTP_400_BAD_REQUEST)
        assignee_id = duty.user_id_for(t["who"], cfg)
        manager = is_manager(request.user)
        if request.user.id != assignee_id and not manager:
            return Response({"detail": "这件事不是你负责的。"}, status=status.HTTP_403_FORBIDDEN)

        try:
            raw = request.data.get("data") or "{}"
            data = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (ValueError, TypeError):
            return Response({"detail": "反馈内容格式不对"}, status=status.HTTP_400_BAD_REQUEST)
        clean = {"note": str(data.get("note") or "")[:500]}
        for k in ("qty", "stock"):
            v = data.get(k)
            if v not in (None, ""):
                try:
                    clean[k] = max(0, int(v))
                except (TypeError, ValueError):
                    return Response({"detail": "数量要填数字"}, status=status.HTTP_400_BAD_REQUEST)
        if task == "stock" and "stock" not in clean:
            return Response({"detail": "请填写补完后库存一共多少个。"}, status=status.HTTP_400_BAD_REQUEST)
        if task == "clean":
            checks = data.get("checks") or {}
            clean["checks"] = {"clean": bool(checks.get("clean")), "notify": bool(checks.get("notify"))}
            if not (clean["checks"]["clean"] and clean["checks"]["notify"]):
                return Response({"detail": "清理卡片和通知充值两步都做完才能打卡。"}, status=status.HTTP_400_BAD_REQUEST)

        img = request.FILES.get("image")
        if img and (img.size > MAX_IMAGE_BYTES or not (img.content_type or "").startswith("image/")):
            return Response({"detail": "截图要是图片，且不超过 8MB。"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        with transaction.atomic():
            rec = DutyRecord.objects.select_for_update().filter(date=d, task=task).first()
            if rec is None:
                # done_by 记真正点打卡的人；老板替负责人打卡时 by_manager=True
                rec = DutyRecord(date=d, task=task, done_at=now, done_by=request.user,
                                 by_manager=request.user.id != assignee_id)
            else:
                if request.user.id not in (rec.done_by_id, assignee_id) and not manager:
                    return Response({"detail": "只能改自己的打卡。"}, status=status.HTTP_403_FORBIDDEN)
                rec.edited_at = now
                rec.confirmed_by = None
                rec.confirmed_at = None
            rec.assignee_id = assignee_id
            rec.data = clean
            if request.data.get("remove_image") in ("1", "true", True) and rec.image:
                rec.image.delete(save=False)
                rec.image = None
            if img:
                if rec.image:
                    rec.image.delete(save=False)
                rec.image = img
            rec.save()
        return Response(_record_json(rec, cfg))


class DutyUndoAPIView(APIView):
    """POST {date, task}：撤销当天的打卡。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        d = _parse_day(request.data.get("date"))
        task = (request.data.get("task") or "").strip()
        if d != timezone.localdate():
            return Response({"detail": "过了当天就锁定了，不能撤销。"}, status=status.HTTP_400_BAD_REQUEST)
        rec = DutyRecord.objects.filter(date=d, task=task).first()
        if not rec:
            return Response(status=status.HTTP_204_NO_CONTENT)
        if request.user.id not in (rec.done_by_id, rec.assignee_id) and not is_manager(request.user):
            return Response({"detail": "只能撤销自己的打卡。"}, status=status.HTTP_403_FORBIDDEN)
        if rec.image:
            rec.image.delete(save=False)
        rec.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DutyConfirmAPIView(APIView):
    """POST {date, task, confirm: true/false}：老板确认 / 撤销确认（不限日期）。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        if not is_manager(request.user):
            return Response({"detail": "只有老板可以确认。"}, status=status.HTTP_403_FORBIDDEN)
        d = _parse_day(request.data.get("date"))
        rec = DutyRecord.objects.filter(date=d, task=(request.data.get("task") or "").strip()).first()
        if not rec:
            return Response({"detail": "还没有打卡记录。"}, status=status.HTTP_404_NOT_FOUND)
        if request.data.get("confirm") in (False, "false", "0", 0):
            rec.confirmed_by, rec.confirmed_at = None, None
        else:
            rec.confirmed_by, rec.confirmed_at = request.user, timezone.now()
        rec.save(update_fields=["confirmed_by", "confirmed_at"])
        return Response(_record_json(rec, duty.load_config()))


class DutySettingsAPIView(APIView):
    """PUT {config}：老板 / CEO 修改规则。"""

    permission_classes = [StaffOnlyPermission]

    def put(self, request):
        if not is_manager(request.user):
            return Response({"detail": "只有老板可以改规则。"}, status=status.HTTP_403_FORBIDDEN)
        incoming = request.data.get("config") or {}
        cfg = duty.load_config()
        try:
            for k in ("a_user", "b_user"):
                if k in incoming:
                    cfg[k] = int(incoming[k]) if incoming[k] not in (None, "") else None
            if "rotStart" in incoming and _parse_day(incoming["rotStart"]):
                cfg["rotStart"] = _parse_day(incoming["rotStart"]).isoformat()
            for k, allowed in (("rotFirst", ("a", "b")), ("stockMode", ("other", "same")),
                               ("endWho", ("sell", "a", "b")), ("unbindDefaultWho", ("a", "b"))):
                if incoming.get(k) in allowed:
                    cfg[k] = incoming[k]
            for k in ("stockStart", "stockEnd"):
                if k in incoming:
                    cfg[k] = max(0, int(incoming[k]))
            if "unbindDefaultDay" in incoming:
                cfg["unbindDefaultDay"] = min(3, max(1, int(incoming["unbindDefaultDay"])))
            if isinstance(incoming.get("stockOverride"), dict):
                cfg["stockOverride"] = {
                    k: max(0, int(v)) for k, v in incoming["stockOverride"].items() if _parse_day(k) and v not in (None, "")
                }
            if isinstance(incoming.get("unbindPlan"), dict):
                plans = {}
                for ym, p in incoming["unbindPlan"].items():
                    pd = _parse_day((p or {}).get("date"))
                    if pd and pd.day <= 3 and f"{pd.year}-{pd.month:02d}" == ym:
                        plans[ym] = {"date": pd.isoformat(), "who": p.get("who") if p.get("who") in ("a", "b") else "a"}
                cfg["unbindPlan"] = plans
            if isinstance(incoming.get("swaps"), dict):
                cfg["swaps"] = {
                    k: v for k, v in incoming["swaps"].items()
                    if v in ("a", "b") and "|" in k and _parse_day(k.split("|")[0]) and k.split("|")[1] in duty.TASK_KEYS
                }
            if isinstance(incoming.get("offDays"), list):
                cfg["offDays"] = sorted({_parse_day(x).isoformat() for x in incoming["offDays"] if _parse_day(x)})
        except (TypeError, ValueError):
            return Response({"detail": "设置里有数字填得不对"}, status=status.HTTP_400_BAD_REQUEST)
        if cfg.get("a_user") and cfg.get("a_user") == cfg.get("b_user"):
            return Response({"detail": "A 和 B 不能是同一个人"}, status=status.HTTP_400_BAD_REQUEST)
        obj = DutySettings.objects.order_by("id").first() or DutySettings()
        obj.config = {k: cfg.get(k) for k in duty.DEFAULTS}
        obj.updated_by = request.user
        obj.save()
        return Response({"config": duty.load_config()})


class DutyLeaveAPIView(APIView):
    """POST {start, end, reason, who?}：申请请假。

    A/B 本人申请 → 待老板批准；老板替 A/B 登记（带 who='a'|'b'）→ 直接生效。
    """

    permission_classes = [StaffOnlyPermission]

    def post(self, request):
        cfg = duty.load_config()
        today = timezone.localdate()
        start, end = _parse_day(request.data.get("start")), _parse_day(request.data.get("end") or request.data.get("start"))
        if not start or not end or end < start:
            return Response({"detail": "请假日期不对"}, status=status.HTTP_400_BAD_REQUEST)
        if (end - start).days > 60:
            return Response({"detail": "一次最多请 60 天"}, status=status.HTTP_400_BAD_REQUEST)
        manager = is_manager(request.user)
        who = (request.data.get("who") or "").strip()
        if manager and who in ("a", "b"):
            uid = duty.user_id_for(who, cfg)
            if not uid:
                return Response({"detail": "还没设置这个人"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if _role_of(request.user, cfg) not in ("a", "b"):
                return Response({"detail": "你不在值班名单里"}, status=status.HTTP_403_FORBIDDEN)
            if start < today:
                return Response({"detail": "不能给已经过去的日子请假"}, status=status.HTTP_400_BAD_REQUEST)
            uid = request.user.id
        overlap = DutyLeave.objects.filter(
            user_id=uid, status__in=(DutyLeave.STATUS_PENDING, DutyLeave.STATUS_APPROVED),
            start_date__lte=end, end_date__gte=start,
        ).exists()
        if overlap:
            return Response({"detail": "这段时间已经有请假记录了"}, status=status.HTTP_400_BAD_REQUEST)
        direct = manager and who in ("a", "b")
        lv = DutyLeave.objects.create(
            user_id=uid, start_date=start, end_date=end, reason=str(request.data.get("reason") or "")[:200],
            status=DutyLeave.STATUS_APPROVED if direct else DutyLeave.STATUS_PENDING,
            created_by=request.user,
            decided_by=request.user if direct else None,
            decided_at=timezone.now() if direct else None,
        )
        return Response(_leave_json(lv, cfg), status=status.HTTP_201_CREATED)


class DutyLeaveActionAPIView(APIView):
    """POST /duty/leave/<id>/<action>/：approve / reject（老板），cancel（本人撤销待批准的；老板可撤销任何）。"""

    permission_classes = [StaffOnlyPermission]

    def post(self, request, pk: int, action: str):
        cfg = duty.load_config()
        lv = DutyLeave.objects.filter(pk=pk).select_related("user").first()
        if not lv:
            return Response({"detail": "找不到这条请假"}, status=status.HTTP_404_NOT_FOUND)
        manager = is_manager(request.user)
        if action in ("approve", "reject"):
            if not manager:
                return Response({"detail": "只有老板可以批准"}, status=status.HTTP_403_FORBIDDEN)
            if lv.status != DutyLeave.STATUS_PENDING:
                return Response({"detail": "这条请假已经处理过了"}, status=status.HTTP_400_BAD_REQUEST)
            lv.status = DutyLeave.STATUS_APPROVED if action == "approve" else DutyLeave.STATUS_REJECTED
        elif action == "cancel":
            if manager:
                pass
            elif lv.user_id == request.user.id and lv.status == DutyLeave.STATUS_PENDING:
                pass
            else:
                return Response({"detail": "已批准的请假只能让老板撤销"}, status=status.HTTP_403_FORBIDDEN)
            if lv.status in (DutyLeave.STATUS_REJECTED, DutyLeave.STATUS_CANCELLED):
                return Response({"detail": "这条请假已经失效了"}, status=status.HTTP_400_BAD_REQUEST)
            lv.status = DutyLeave.STATUS_CANCELLED
        else:
            return Response({"detail": "未知操作"}, status=status.HTTP_400_BAD_REQUEST)
        lv.decided_by, lv.decided_at = request.user, timezone.now()
        lv.save(update_fields=["status", "decided_by", "decided_at"])
        return Response(_leave_json(lv, cfg))
