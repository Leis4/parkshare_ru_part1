# accounts/auth.py

from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model

from core.utils import normalize_phone

User = get_user_model()


def find_user_by_identifier(identifier: str) -> Optional[User]:
    """
    Возвращает пользователя по логину / email / телефону.

    Используется в HTML-форме логина и в API.
    """
    if not identifier:
        return None

    ident = identifier.strip()
    qs = User.objects.filter(is_active=True)

    # 1) Email
    if "@" in ident:
        email = ident.lower()
        try:
            return qs.get(email_encrypted=email)
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            return qs.filter(email_encrypted=email).order_by("date_joined").first()

    # 2) Телефон
    phone = normalize_phone(ident)
    if phone:
        user = qs.filter(phone_encrypted=phone).order_by("date_joined").first()
        if user:
            return user

    # 3) Логин
    try:
        return qs.get(username__iexact=ident)
    except User.DoesNotExist:
        return None
    except User.MultipleObjectsReturned:
        return qs.filter(username__iexact=ident).order_by("date_joined").first()
