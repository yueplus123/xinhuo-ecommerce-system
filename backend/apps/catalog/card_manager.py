"""薪火卡管家（汇通卡 Chrome 插件）的权限：职员按「备注关键词」看卡。

- 超级管理员 / 老板 / CEO：能看全部卡（is_admin=True）
- 其他职员：只能看备注里包含自己关键词的卡；没有设置关键词就什么都看不到
- 游客：不能用
关键词只能在管理后台「卡管家权限」页修改。
"""

from __future__ import annotations

import re

from django.contrib.auth import get_user_model

from .models import CardManagerScope, CardOtpCode, CardOtpLink, CardRiskHandled
from .roles import is_boss, is_ceo, is_guest

MAX_KEYWORDS = 50
MAX_KEYWORD_LEN = 30
_SPLIT = re.compile(r"[\n\r,，、;；]+")


def parse_keywords(raw) -> list[str]:
    """接受字符串（换行 / 逗号分隔）或列表；去空白、去重，保持原顺序。"""
    if raw is None:
        return []
    items = raw if isinstance(raw, (list, tuple)) else _SPLIT.split(str(raw))
    out: list[str] = []
    for x in items:
        s = str(x).strip()
        if not s:
            continue
        if len(s) > MAX_KEYWORD_LEN:
            raise ValueError(f"关键词「{s[:10]}…」太长，最多 {MAX_KEYWORD_LEN} 个字")
        if s not in out:
            out.append(s)
    if len(out) > MAX_KEYWORDS:
        raise ValueError(f"关键词最多 {MAX_KEYWORDS} 个")
    return out


def is_card_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or is_boss(user) or is_ceo(user)))


def keywords_of(user) -> list[str]:
    scope = CardManagerScope.objects.filter(user_id=user.pk).first()
    return parse_keywords(scope.keywords) if scope else []


def set_keywords(user, raw, by) -> list[str]:
    kws = parse_keywords(raw)
    CardManagerScope.objects.update_or_create(user=user, defaults={"keywords": "\n".join(kws), "updated_by": by})
    return kws


def staff_rows() -> list[dict]:
    """所有在职职员（不含游客）及其关键词，按用户名排序。"""
    User = get_user_model()
    users = User.objects.filter(is_active=True, is_staff=True).order_by("username")
    scopes = {s.user_id: s for s in CardManagerScope.objects.select_related("updated_by")}
    rows = []
    for u in users:
        if is_guest(u):
            continue
        s = scopes.get(u.pk)
        rows.append(
            {
                "id": u.pk,
                "username": u.username,
                "is_admin": is_card_admin(u),
                "keywords": parse_keywords(s.keywords) if s else [],
                "updated_at": s.updated_at.isoformat() if s else None,
                "updated_by": (s.updated_by.username if s and s.updated_by else ""),
            }
        )
    return rows


def me_payload(user) -> dict:
    admin = is_card_admin(user)
    data = {
        "user": {"id": user.pk, "username": user.username},
        "is_admin": admin,
        "keywords": keywords_of(user),
    }
    if admin:
        # 管理员在插件里可以「按员工」统计，所以把每个职员的关键词也给它
        data["staff"] = [{"id": r["id"], "username": r["username"], "keywords": r["keywords"]} for r in staff_rows()]
    return data


# ---------------- 风险卡「已处理」记录 ----------------
RISK_KEYS = {"of", "cvv", "nosup", "nobal", "silent", "near", "expired"}
RESULTS = {k for k, _ in CardRiskHandled.RESULT_CHOICES}
HANDLED_KEEP_DAYS = 180  # 插件只取最近 180 天的处理记录
MAX_BATCH = 500


def can_see_remark(user, remark: str, kws: list[str] | None = None) -> bool:
    """管理员能看全部；员工只能看备注包含自己关键词的卡。"""
    if is_card_admin(user):
        return True
    r = str(remark or "")
    return any(k and k in r for k in (kws if kws is not None else keywords_of(user)))


def handled_row(h: CardRiskHandled) -> dict:
    return {
        "card_id": h.card_id,
        "risk": h.risk,
        "mark": h.mark,
        "result": h.result,
        "note": h.note,
        "card_suffix": h.card_suffix,
        "handled_by": h.handled_by.username if h.handled_by else "",
        "handled_at": h.handled_at.isoformat(),
    }


def list_handled(user) -> list[dict]:
    from datetime import timedelta

    from django.utils import timezone

    since = timezone.now() - timedelta(days=HANDLED_KEEP_DAYS)
    qs = CardRiskHandled.objects.filter(handled_at__gte=since).select_related("handled_by").order_by("-handled_at")
    kws = keywords_of(user)
    return [handled_row(h) for h in qs if can_see_remark(user, h.card_remark, kws)]


def _clean_item(raw) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("数据格式不对")
    card_id = str(raw.get("card_id") or "").strip()
    risk = str(raw.get("risk") or "").strip()
    result = str(raw.get("result") or "ok").strip()
    if not card_id or len(card_id) > 64:
        raise ValueError("卡ID不对")
    if risk not in RISK_KEYS:
        raise ValueError(f"不认识的风险类型：{risk[:20]}")
    if result not in RESULTS:
        raise ValueError(f"不认识的处理结果：{result[:20]}")
    return {
        "card_id": card_id,
        "risk": risk,
        "mark": str(raw.get("mark") or "")[:64],
        "result": result,
        "note": str(raw.get("note") or "").strip()[:200],
        "card_suffix": str(raw.get("card_suffix") or "")[:8],
        "card_remark": str(raw.get("card_remark") or "")[:255],
    }


def mark_handled(user, items) -> list[dict]:
    """把一批（卡, 风险）记成已处理；同一张卡同一种风险只留最新一条。"""
    if not isinstance(items, list) or not items:
        raise ValueError("没有要处理的风险")
    if len(items) > MAX_BATCH:
        raise ValueError(f"一次最多处理 {MAX_BATCH} 条")
    rows = [_clean_item(x) for x in items]
    kws = keywords_of(user)
    for r in rows:
        if not can_see_remark(user, r["card_remark"], kws):
            raise PermissionError(f"没有权限处理这张卡（****{r['card_suffix']}）")
    out = []
    for r in rows:
        h, _ = CardRiskHandled.objects.update_or_create(
            card_id=r["card_id"],
            risk=r["risk"],
            defaults={**{k: v for k, v in r.items() if k not in ("card_id", "risk")}, "handled_by": user},
        )
        out.append(handled_row(h))
    return out


def undo_handled(user, card_id, risk) -> bool:
    h = CardRiskHandled.objects.filter(card_id=str(card_id or ""), risk=str(risk or "")).first()
    if not h:
        return False
    if not can_see_remark(user, h.card_remark):
        raise PermissionError("没有权限撤销这条记录")
    h.delete()
    return True


# ---------------- 接码链接：客户凭链接看某张卡最近的验证码 ----------------
OTP_KEEP_DAYS = 3  # 验证码只留 3 天
OTP_SHOW_MINUTES = 15  # 接码页只显示最近 15 分钟的验证码
OTP_MAX_UPLOAD = 300


def _cst_to_aware(s: str):
    """汇通交易时间是北京时间的「YYYY-MM-DD HH:MM:SS」。"""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    dt = datetime.strptime(str(s or "")[:19], "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))


def link_row(link: CardOtpLink | None) -> dict | None:
    if not link:
        return None
    return {
        "card_id": link.card_id,
        "token": link.token,
        "created_by": link.created_by.username if link.created_by else "",
        "created_at": link.created_at.isoformat(),
        "view_count": link.view_count,
        "last_view_at": link.last_view_at.isoformat() if link.last_view_at else None,
    }


def active_link(card_id: str) -> CardOtpLink | None:
    return CardOtpLink.objects.filter(card_id=card_id, revoked_at__isnull=True).select_related("created_by").first()


def _card_info(raw) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("数据格式不对")
    card_id = str(raw.get("card_id") or "").strip()
    if not card_id or len(card_id) > 64:
        raise ValueError("卡ID不对")
    return {
        "card_id": card_id,
        "card_bin": str(raw.get("card_bin") or "")[:8],
        "card_suffix": str(raw.get("card_suffix") or "")[:8],
        "card_remark": str(raw.get("card_remark") or "")[:255],
    }


def get_link(user, raw, create: bool = False, renew: bool = False) -> dict | None:
    """读取 / 生成 / 作废并重新生成某张卡的接码链接。"""
    import secrets

    from django.utils import timezone

    info = _card_info(raw)
    if not can_see_remark(user, info["card_remark"]):
        raise PermissionError("没有权限操作这张卡")
    link = active_link(info["card_id"])
    if link and renew:
        link.revoked_at = timezone.now()
        link.save(update_fields=["revoked_at"])
        link = None
    if not link and (create or renew):
        link = CardOtpLink.objects.create(**info, token=secrets.token_urlsafe(18), created_by=user)
    return link_row(link)


def revoke_link(user, raw) -> bool:
    from django.utils import timezone

    info = _card_info(raw)
    link = active_link(info["card_id"])
    if not link:
        return False
    if not can_see_remark(user, link.card_remark or info["card_remark"]):
        raise PermissionError("没有权限操作这张卡")
    link.revoked_at = timezone.now()
    link.save(update_fields=["revoked_at"])
    return True


def upload_codes(user, items) -> int:
    """推送电脑上的插件把读到的验证码传上来（只有管理员账号能传）。"""
    from datetime import timedelta

    from django.utils import timezone

    if not is_card_admin(user):
        raise PermissionError("只有管理员账号能上传验证码")
    if not isinstance(items, list):
        raise ValueError("数据格式不对")
    if len(items) > OTP_MAX_UPLOAD:
        raise ValueError(f"一次最多 {OTP_MAX_UPLOAD} 条")
    n = 0
    for raw in items:
        if not isinstance(raw, dict):
            continue
        card_id, pno, code = str(raw.get("card_id") or "")[:64], str(raw.get("payment_no") or "")[:64], str(raw.get("code") or "")
        if not card_id or not pno or not code.isdigit() or not (4 <= len(code) <= 8):
            continue
        try:
            trans_at = _cst_to_aware(raw.get("trans_time"))
        except ValueError:
            continue
        _, created = CardOtpCode.objects.get_or_create(payment_no=pno, defaults={"card_id": card_id, "code": code, "trans_at": trans_at})
        n += int(created)
    CardOtpCode.objects.filter(trans_at__lt=timezone.now() - timedelta(days=OTP_KEEP_DAYS)).delete()
    return n


def public_codes(token: str) -> dict | None:
    """客户接码页：凭 token 看这张卡最近 15 分钟的验证码。不返回备注等内部信息。"""
    from datetime import timedelta

    from django.db.models import F
    from django.utils import timezone

    link = CardOtpLink.objects.filter(token=str(token or ""), revoked_at__isnull=True).first()
    if not link:
        return None
    now = timezone.now()
    CardOtpLink.objects.filter(pk=link.pk).update(view_count=F("view_count") + 1, last_view_at=now)
    since = now - timedelta(minutes=OTP_SHOW_MINUTES)
    qs = CardOtpCode.objects.filter(card_id=link.card_id, trans_at__gte=since).order_by("-trans_at")[:10]
    return {
        "card": f"{link.card_bin or '****'}****{link.card_suffix}",
        "minutes": OTP_SHOW_MINUTES,
        "now": now.isoformat(),
        "codes": [{"code": c.code, "time": c.trans_at.isoformat()} for c in qs],
    }
