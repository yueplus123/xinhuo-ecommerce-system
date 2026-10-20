"""职员端最近登录 IP 写入（不落 User 表，兼容默认 auth.User）。"""


def get_client_ip(request) -> str:
    if not request:
        return ""
    # 反代（nginx）会把真实客户端 IP 追加在 X-Forwarded-For 末尾；首段可被客户端伪造，故取末段
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[-1].strip()[:64]
    return (request.META.get("REMOTE_ADDR") or "").strip()[:64]


def touch_staff_last_login(request, user_id) -> None:
    """更新 last_login，并写入最近一次登录 IP（不含登录日志）。"""
    if user_id is None:
        return
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from .models import StaffLoginMeta

    User = get_user_model()
    ip = get_client_ip(request)

    User.objects.filter(pk=user_id).update(last_login=timezone.now())

    StaffLoginMeta.objects.update_or_create(
        user_id=user_id,
        defaults={"last_login_ip": ip[:64]},
    )


def record_staff_login(request, user_id) -> None:
    """密码/会话登录：更新 last_login、meta，并写入登录日志。"""
    if user_id is None:
        return
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from .models import StaffLoginLog, StaffLoginMeta

    User = get_user_model()
    ip = get_client_ip(request)
    now = timezone.now()

    User.objects.filter(pk=user_id).update(last_login=now)

    StaffLoginMeta.objects.update_or_create(
        user_id=user_id,
        defaults={"last_login_ip": ip[:64]},
    )

    StaffLoginLog.objects.create(
        user_id=user_id,
        ip=ip[:64],
        logged_at=now,
    )
