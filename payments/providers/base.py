# payments/providers/base.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import Payment  # <-- ВАЖНО: относительный импорт, а не backend.payments



class PaymentProvider(ABC):
    """
    Базовый интерфейс платёжного провайдера.
    """

    @abstractmethod
    def create_payment(
        self,
        payment: Payment,
        return_url: str,
        webhook_url: str,
    ) -> Dict[str, Any]:
        """
        Создать платёж у провайдера и вернуть его данные (включая confirmation_url).
        """
        raise NotImplementedError("Метод create_payment должен быть реализован.")

    @abstractmethod
    def handle_webhook(self, request) -> Optional[Payment]:
        """
        Обработать webhook от провайдера и обновить Payment/Booking.
        """
        raise NotImplementedError("Метод handle_webhook должен быть реализован.")

    @abstractmethod
    def refund(self, payment: Payment, amount: Optional[float] = None) -> None:
        """
        Инициировать возврат по платежу.
        """
        raise NotImplementedError("Метод refund должен быть реализован.")
