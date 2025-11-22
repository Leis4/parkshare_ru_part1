"""
Пакет настроек Django.

По умолчанию используются настройки для локальной разработки
(`backend.config.settings.local`).

Для продакшена задайте переменную окружения:

    DJANGO_SETTINGS_MODULE=backend.config.settings.production
"""

from .local import *  # noqa: F401,F403
