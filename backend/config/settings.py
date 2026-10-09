import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv_files():
    """从项目根目录或 backend 目录加载 `.env`（不覆盖已有环境变量）。`.env` 已在 .gitignore 中，勿提交。"""
    for env_path in (BASE_DIR.parent / ".env", BASE_DIR / ".env"):
        if not env_path.is_file():
            continue
        try:
            text = env_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


_load_dotenv_files()

# SQLite：目录必须事先存在，否则报 unable to open database file；Windows 下用绝对路径字符串更稳
_SQLITE_DIR = BASE_DIR / "data"
_SQLITE_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "media").mkdir(parents=True, exist_ok=True)

DEBUG = os.environ.get("BACKEND_DEBUG", "0").strip().lower() in ("1", "true", "yes")
# 生产环境（DEBUG=0）必须显式配置密钥；本地开发（DEBUG=1）才允许使用内置开发密钥
SECRET_KEY = os.environ.get("BACKEND_SECRET_KEY") or ("backend-dev-secret-key-only-for-local-debug-0000" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("未配置 BACKEND_SECRET_KEY：生产环境请在 .env 中设置强随机密钥（本地开发可设 BACKEND_DEBUG=1）。")
ALLOWED_HOSTS = [
    x.strip()
    for x in os.environ.get("BACKEND_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(",")
    if x.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "backend.apps.catalog",
    "backend.apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "backend.apps.catalog.views.backoffice_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str((_SQLITE_DIR / "backend.sqlite3").resolve()),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = str((BASE_DIR / "media").resolve())

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "backoffice:backoffice_home"
LOGOUT_REDIRECT_URL = "login"

# 管理后台 / django-admin 会话：自登录起 12 小时有效，到期需重新登录
SESSION_COOKIE_AGE = 12 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = False

# 职员端 JWT：自签发起 12 小时有效；不轮换 refresh，避免刷新延长总时长
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=12),
    "ROTATE_REFRESH_TOKENS": False,
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    # 登录/刷新令牌接口按 IP 限流，防暴力破解（视图上用 throttle_scope="auth"）
    "DEFAULT_THROTTLE_RATES": {"auth": "20/min"},
}

CORS_ALLOWED_ORIGINS = [
    x.strip()
    for x in os.environ.get(
        "BACKEND_CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if x.strip()
]
CORS_ALLOW_CREDENTIALS = True

# 生产环境安全加固；本地 DEBUG=1 不启用
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "SAMEORIGIN"
    CSRF_TRUSTED_ORIGINS = [o.split()[0] for o in CORS_ALLOWED_ORIGINS]
    # 站点已上 HTTPS 后，在 .env 设 BACKEND_HTTPS=1：Cookie 仅走 HTTPS，并信任反代的 X-Forwarded-Proto。
    # 纯 HTTP 访问时不要设，否则浏览器不会回传登录 Cookie 导致无法登录。
    if os.environ.get("BACKEND_HTTPS", "").strip().lower() in ("1", "true", "yes"):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True

# 企业微信内部群「消息推送」Webhook（见官方文档：消息推送配置说明）
WECOM_REMINDER_ENABLED = (os.environ.get("WECOM_REMINDER_ENABLED") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
WECOM_GROUP_WEBHOOK_URL = (os.environ.get("WECOM_GROUP_WEBHOOK_URL") or "").strip()

# 企微「订阅提醒」汇总消息中的跳转链接（Vue 路由为 /customer/subscription-reminders）
_staff_reminders_full = (os.environ.get("STAFF_FRONTEND_SUBSCRIPTION_REMINDERS_URL") or "").strip()
_staff_base = (os.environ.get("STAFF_FRONTEND_BASE_URL") or "").strip().rstrip("/") or "http://localhost:5173"
STAFF_FRONTEND_BASE_URL = _staff_base
STAFF_FRONTEND_SUBSCRIPTION_REMINDERS_URL = _staff_reminders_full or (
    f"{_staff_base}/customer/subscription-reminders" if _staff_base else ""
)

# 外部系统实时推送收款（对方 POST → 我方）
EXTERNAL_PUSH_API_KEY = (os.environ.get("EXTERNAL_PUSH_API_KEY") or "").strip()
EXTERNAL_PUSH_DEFAULT_USERNAME = (os.environ.get("EXTERNAL_PUSH_DEFAULT_USERNAME") or "").strip()
