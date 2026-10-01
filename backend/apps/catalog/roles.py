"""职员端角色组：老板、CEO、游客（全员业绩 / 记账 / 只读浏览等）。"""

from django.contrib.auth.models import Group

BOSS_GROUP_NAME = "老板"
CEO_GROUP_NAME = "CEO"
GUEST_GROUP_NAME = "游客"


def ensure_boss_group():
    group, _ = Group.objects.get_or_create(name=BOSS_GROUP_NAME)
    return group


def ensure_ceo_group():
    group, _ = Group.objects.get_or_create(name=CEO_GROUP_NAME)
    return group


def ensure_guest_group():
    group, _ = Group.objects.get_or_create(name=GUEST_GROUP_NAME)
    return group


def is_boss(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    return user.groups.filter(name=BOSS_GROUP_NAME).exists()


def is_ceo(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    return user.groups.filter(name=CEO_GROUP_NAME).exists()


def is_guest(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    return user.groups.filter(name=GUEST_GROUP_NAME).exists()


def is_employee(user) -> bool:
    """职员端「员工」：已开通职员权限，且非管理员、非老板、非 CEO、非游客。"""
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    return bool(
        user.is_staff
        and user.is_active
        and not user.is_superuser
        and not is_boss(user)
        and not is_ceo(user)
        and not is_guest(user)
    )
