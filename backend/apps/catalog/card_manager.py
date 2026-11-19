"""薪火卡管家（汇通卡 Chrome 插件）的权限：职员按「备注关键词」看卡。

- 超级管理员 / 老板 / CEO：能看全部卡（is_admin=True）
- 其他职员：只能看备注里包含自己关键词的卡；没有设置关键词就什么都看不到
- 游客：不能用
关键词只能在管理后台「卡管家权限」页修改。
"""

from __future__ import annotations

import re

from django.contrib.auth import get_user_model

from .models import CardManagerScope
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
