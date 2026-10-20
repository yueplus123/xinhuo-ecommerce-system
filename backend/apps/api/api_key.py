from hmac import compare_digest

from django.conf import settings


def configured_api_key() -> str:
    return (getattr(settings, "EXTERNAL_PUSH_API_KEY", "") or "").strip()


def api_key_ok(request) -> bool:
    """外部系统推送/查询共用的 API Key 校验（X-Api-Key 或 Bearer）。"""
    expected = configured_api_key()
    if not expected:
        return False
    got = (
        (request.headers.get("X-Api-Key") or "")
        or (request.META.get("HTTP_X_API_KEY") or "")
        or ""
    ).strip()
    if not got:
        auth = (request.headers.get("Authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
    return bool(got) and compare_digest(got.encode(), expected.encode())
