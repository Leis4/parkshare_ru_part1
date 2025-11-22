import os
from pathlib import Path
from typing import List

import environ

# ---------------------------------------------------------------------------
# Пути
# ---------------------------------------------------------------------------

# BASE_DIR — корень репозитория: C:\Users\Sultan\Downloads\parkshare_ru_part1
BASE_DIR = Path(__file__).resolve().parents[3]

# Тут главная правка: больше не уходим на уровень выше
PROJECT_ROOT = BASE_DIR  # C:\Users\Sultan\Downloads\parkshare_ru_part1


# ---------------------------------------------------------------------------
# Окружение
# ---------------------------------------------------------------------------

env = environ.Env(
    DEBUG=(bool, False),
)

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

DEBUG: bool = env.bool("DEBUG", default=False)
SECRET_KEY: str = env("SECRET_KEY", default="unsafe-secret-key-change-me")

ALLOWED_HOSTS: List[str] = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# Приложения
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Сторонние
    "rest_framework",
    "corsheaders",
    "django_cryptography",
    "drf_spectacular",

    # Проектные
    "accounts",
    "vehicles",
    "parking",
    "payments",
    "ai",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.config.wsgi.application"
ASGI_APPLICATION = "backend.config.asgi.application"

# ---------------------------------------------------------------------------
# Базы данных
# ---------------------------------------------------------------------------

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}

# Если используем PostgreSQL — переключаемся на PostGIS
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

# ---------------------------------------------------------------------------
# Пользователь / аутентификация
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ---------------------------------------------------------------------------
# Локализация
# ---------------------------------------------------------------------------

LANGUAGE_CODE = env("LANGUAGE_CODE", default="ru-ru")
TIME_ZONE = env("TIME_ZONE", default="Europe/Moscow")
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Статика / медиа
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# PWA
# ---------------------------------------------------------------------------

PWA_APP_NAME = "ParkShare RU"
PWA_APP_SHORT_NAME = "ParkShare"
PWA_THEME_COLOR = "#0d6efd"
PWA_BACKGROUND_COLOR = "#050816"

# ---------------------------------------------------------------------------
# DRF / OpenAPI
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.DefaultPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ParkShare RU API",
    "DESCRIPTION": "API сервиса бронирования парковочных мест ParkShare RU.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Redis / Celery
# ---------------------------------------------------------------------------

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    "expire_unpaid_bookings": {
        "task": "parking.tasks.expire_unpaid_bookings",
        "schedule": 60 * 10,  # каждые 10 минут
    },
    "update_ai_models": {
        "task": "ai.tasks.update_models",
        "schedule": 60 * 60,  # раз в час
    },
    "check_stale_payments": {
        "task": "payments.tasks.check_stale_payments",
        "schedule": 60 * 15,  # каждые 15 минут
    },
}

# ---------------------------------------------------------------------------
# Логи
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "parkshare": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="ParkShare RU <noreply@example.com>",
)
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# ---------------------------------------------------------------------------
# Безопасность (базовый уровень, детали переопределяются в production.py)
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# django-cryptography
# ---------------------------------------------------------------------------

DJANGO_CRYPTography_KEY = SECRET_KEY

# ---------------------------------------------------------------------------
# Бизнес-настройки
# ---------------------------------------------------------------------------

VEHICLE_PLATE_SALT = env("VEHICLE_PLATE_SALT", default="change_me_vehicle_salt")

YOOKASSA_SHOP_ID = env("YOOKASSA_SHOP_ID", default="")
YOOKASSA_SECRET_KEY = env("YOOKASSA_SECRET_KEY", default="")
YOOKASSA_RETURN_URL = env("YOOKASSA_RETURN_URL", default="")
YOOKASSA_WEBHOOK_SECRET = env("YOOKASSA_WEBHOOK_SECRET", default="")

SERVICE_COMMISSION_PERCENT = env.int("SERVICE_COMMISSION_PERCENT", default=10)

# ---------------------------------------------------------------------------
# Кэш по умолчанию — in-memory (в продакшене можно переключить на Redis)
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "parkshare_cache",
    }
}
