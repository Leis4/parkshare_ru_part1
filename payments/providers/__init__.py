from __future__ import annotations

from django.conf import settings

from .base import PaymentProvider
from .yookassa import (
    YooKassaProvider,
    YooKassaError,
    create_yookassa_payment,
)

__all__ = [
    "PaymentProvider",
    "YooKassaProvider",
    "YooKassaError",
    "create_yookassa_payment",
    "get_payment_provider",
]


def get_payment_provider() -> PaymentProvider:
    provider_name = getattr(settings, "PAYMENTS_PROVIDER", "yookassa")
    if provider_name == "yookassa":
        return YooKassaProvider()
    raise ValueError(f"Неизвестный платёжный провайдер: {provider_name}")
