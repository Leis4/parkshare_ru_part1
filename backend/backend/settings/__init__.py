"""
Пакет настроек Django.

По умолчанию используются настройки для локальной разработки
(`backend.settings.local`).

Для продакшена задайте переменную окружения:

    DJANGO_SETTINGS_MODULE=backend.settings.production
"""

from .local import *  # noqa: F401,F403
