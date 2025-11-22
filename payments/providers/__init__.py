from __future__ import annotations

"""
Единая точка входа для работы с YooKassa.

Используется PaymentSerializer через:

    from .providers import YooKassaError, create_yookassa_payment
"""

from .yookassa import YooKassaError, create_yookassa_payment

__all__ = [
    "YooKassaError",
    "create_yookassa_payment",
]
