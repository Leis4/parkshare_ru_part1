import os
from pathlib import Path
from typing import List

import environ

# Базовая директория Django-проекта (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Корень репозитория (где лежат templates/ и static/)
PROJECT_ROOT = BASE_DIR.parent

# Настройка окружения через django-environ
env = environ.Env(
    DEBUG=(bool, False),
)

# Читаем .env, если он существует
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

DEBUG: bool = env.bool("DEBUG", default=False)
SECRET_KEY: str = env("SECRET_KEY", default="unsafe-secret-key-change-me")

ALLOWED_HOSTS: List[str] = env.list("ALLOWED_HOSTS", default=["*"])

# Приложения Django
INSTALLED_APPS = [
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
        "DIRS": [PROJECT_ROOT / "templates"],
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

# База данных (Postgres/PostGIS для продакшена, SQLite по умолчанию)
DATABASES = {
    "default": env.db(
        "DATABASE_URL", default=f"sqlite:///{PROJECT_ROOT / 'db.sqlite3'}"
    )
}

# Подмена engine на PostGIS, если используем PostgreSQL
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

# Пользователь
AUTH_USER_MODEL = "accounts.User"

# Пароли
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

# Локализация
LANGUAGE_CODE = env("LANGUAGE_CODE", default="ru-ru")
TIME_ZONE = env("TIME_ZONE", default="Europe/Moscow")
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static & media
STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
STATICFILES_DIRS = [
    PROJECT_ROOT / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_ROOT / "media"

# PWA‑цвета (для meta и manifest)
PWA_APP_NAME = "ParkShare RU"
PWA_APP_SHORT_NAME = "ParkShare"
PWA_THEME_COLOR = "#0d6efd"
PWA_BACKGROUND_COLOR = "#ffffff"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.DefaultPageNumberPagination",
    "PAGE_SIZE": 20,
}

# CORS (минимальный дефолт)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Redis / Celery
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

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
    "recalculate_ai_analytics": {
        "task": "ai.tasks.recalculate_analytics",
        "schedule": 60 * 30,  # каждые 30 минут
    },
}

# Логи
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

# Безопасность (для продакшена переопределяется в .env)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
X_FRAME_OPTIONS = "DENY"

# Настройки шифрования (django-cryptography)
DJANGO_CRYPTography_KEY = SECRET_KEY  # используется библиотекой для симметричного шифрования

# Соль для номеров машин
VEHICLE_PLATE_SALT = env("VEHICLE_PLATE_SALT", default="change_me_vehicle_salt")

# Настройки YooKassa (пример, используются в payments.providers)
YOOKASSA_SHOP_ID = env("YOOKASSA_SHOP_ID", default="")
YOOKASSA_SECRET_KEY = env("YOOKASSA_SECRET_KEY", default="")
YOOKASSA_RETURN_URL = env("YOOKASSA_RETURN_URL", default="")
YOOKASSA_WEBHOOK_SECRET = env("YOOKASSA_WEBHOOK_SECRET", default="")

# Комиссия сервиса (процент)
SERVICE_COMMISSION_PERCENT = env.int("SERVICE_COMMISSION_PERCENT", default=10)

# Кэш (по умолчанию локальный in‑memory, в проде можно переключить на Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "parkshare_cache",
    }
}
