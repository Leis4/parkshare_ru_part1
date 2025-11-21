from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from parking.models import Booking
from .models import Payment
from .providers import YooKassaError, create_yookassa_payment


class PaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для платежей.

    Политика повторных оплат:
    - если для брони уже существует платёж в статусе SUCCEEDED — новый
      платёж создать нельзя;
    - если платёж существует, но ещё неуспешен (CREATED/PENDING/FAILED/CANCELLED),
      он переиспользуется: переинициализируется через YooKassa и возвращается
      с новым payment_url.
    """

    payer = serializers.ReadOnlyField(source="payer.username")
    booking = serializers.PrimaryKeyRelatedField(read_only=True)
    booking_id = serializers.PrimaryKeyRelatedField(
        queryset=Booking.objects.all(),
        source="booking",
        write_only=True,
    )
    payment_url = serializers.CharField(read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "payer",
            "booking",
            "booking_id",
            "provider",
            "provider_payment_id",
            "amount",
            "currency",
            "status",
            "success",
            "failure",
            "created_at",
            "updated_at",
            "payment_url",
        )
        read_only_fields = (
            "id",
            "payer",
            "booking",
            "provider",
            "provider_payment_id",
            "amount",
            "currency",
            "status",
            "success",
            "failure",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs: dict) -> dict:
        request = self.context["request"]
        user = request.user

        booking: Booking = attrs["booking"]

        # Бронь должна принадлежать текущему пользователю
        if booking.user_id != user.id:
            raise serializers.ValidationError(
                "Нельзя создавать платёж для чужой брони."
            )

        # Бронь должна ожидать оплаты
        if booking.is_paid or booking.status != Booking.Status.PENDING:
            raise serializers.ValidationError(
                "Платёж можно создать только для брони в статусе 'Ожидает оплаты'."
            )

        # Бронь не должна быть отменена/истечь и не в прошлом
        now = timezone.now()
        if booking.status in (Booking.Status.CANCELLED, Booking.Status.EXPIRED) or booking.end_at <= now:
            raise serializers.ValidationError(
                "Нельзя создать платёж для отменённой, истекшей или прошлой брони."
            )

        if booking.total_price <= Decimal("0"):
            raise serializers.ValidationError(
                "Сумма бронирования должна быть больше нуля."
            )

        return attrs

    def create(self, validated_data: dict) -> Payment:
        request = self.context["request"]
        user = request.user
        booking: Booking = validated_data["booking"]

        # Пытаемся переиспользовать существующий платёж (если есть)
        existing: Payment | None = getattr(booking, "payment", None)
        if existing is not None:
            if existing.status == Payment.Status.SUCCEEDED:
                raise serializers.ValidationError(
                    "Для этой брони уже существует успешный платёж."
                )
            payment = existing
        else:
            payment = Payment(
                booking=booking,
                payer=user,
                amount=booking.total_price,
                currency=booking.currency or "RUB",
            )

        try:
            payment_url, provider_payment_id, raw = create_yookassa_payment(booking)
        except YooKassaError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc

        payment.provider = Payment.Provider.YOOKASSA
        payment.provider_payment_id = provider_payment_id
        payment.status = Payment.Status.PENDING
        payment.success = False
        payment.failure = False
        payment.raw_response = raw
        payment.save()

        # Временный атрибут, чтобы добавить URL в ответ сериализатора
        payment.payment_url = payment_url  # type: ignore[attr-defined]

        return payment
