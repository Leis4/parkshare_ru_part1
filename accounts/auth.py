# accounts/auth.py

from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model

from core.utils import normalize_phone

User = get_user_model()


def find_user_by_identifier(identifier: str) -> Optional[User]:
    """
    ВРЕМЕННО: ищем только по username.

    Раньше тут был поиск по email_encrypted / phone_encrypted,
    но django-cryptography не даёт по этим полям делать filter/get.
    """
    if not identifier:
        return None

    ident = identifier.strip()
    qs = User.objects.filter(is_active=True)

    # 1) Логин (username)
    try:
        return qs.get(username__iexact=ident)
    except User.DoesNotExist:
        return None
    except User.MultipleObjectsReturned:
        return qs.filter(username__iexact=ident).order_by("date_joined").first()

