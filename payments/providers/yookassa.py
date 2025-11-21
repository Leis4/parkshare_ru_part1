from __future__ import annotations

import logging
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest
from yookassa import Configuration, Payment as YooPayment

from ..models import Payment
from .base import PaymentProvider

logger = logging.getLogger(__name__)


class YooKassaError(Exception):
    """Обёртка над ошибками платёжного провайдера."""
    pass


def _setup_yookassa() -> None:
    """
    Настраивает SDK YooKassa из Django settings.

    Ожидает:
    - YOOKASSA_SHOP_ID
    - YOOKASSA_API_KEY
    """
    Configuration.account_id = getattr(settings, "YOOKASSA_SHOP_ID", None)
    Configuration.secret_key = getattr(settings, "YOOKASSA_API_KEY", None)


class YooKassaProvider(PaymentProvider):
    """
    Платёжный провайдер YooKassa.
    Ожидает, что Payment имеет поле `amount`.
    """

    def create_payment(self, payment: Payment, return_url: str) -> Dict[str, Any]:
        try:
            _setup_yookassa()

            if not getattr(payment, "amount", None):
                raise YooKassaError(
                    "У Payment отсутствует поле amount — исправьте модель."
                )

            amount = {
                "value": str(payment.amount),
                "currency": "RUB",
            }

            data = {
                "amount": amount,
                "capture": True,
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url,
                },
                "description": f"Оплата бронирования #{payment.id}",
                "metadata": {"payment_id": str(payment.id)},
            }

            y_payment = YooPayment.create(data)

            if hasattr(payment, "provider"):
                payment.provider = "yookassa"
            if hasattr(payment, "provider_payment_id"):
                payment.provider_payment_id = y_payment.id

            payment.save(update_fields=["provider", "provider_payment_id"])

            try:
                return y_payment.json()
            except Exception:
                return {
                    "id": y_payment.id,
                    "status": getattr(y_payment, "status", None),
                    "amount": amount,
                }

        except YooKassaError:
            raise
        except Exception as exc:
            logger.exception("Ошибка YooKassa")
            raise YooKassaError(str(exc)) from exc


def create_yookassa_payment(
    request: HttpRequest,
    payment: Payment,
    return_url: str,
) -> Dict[str, Any]:
    """
    Функция для обратной совместимости.
    """
    provider = YooKassaProvider()
    return provider.create_payment(payment=payment, return_url=return_url)
