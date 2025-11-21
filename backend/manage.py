#!/usr/bin/env python
import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что он установлен и "
            "доступен в вашем виртуальном окружении."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
