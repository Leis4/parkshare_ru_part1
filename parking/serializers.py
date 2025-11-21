# backend/parking/serializers.py

from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from core.utils import haversine_distance_km
from .models import Booking, Complaint, ParkingLot, ParkingSpot, WaitlistEntry


class ParkingLotSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    spots_count = serializers.SerializerMethodField()

    class Meta:
        model = ParkingLot
        fields = (
            "id",
            "name",
            "city",
            "address",
            "parking_type",
            "description",
            "latitude",
            "longitude",
            "is_active",
            "is_approved",
            "is_private",
            "owner",
            "spots_count",
        )
        read_only_fields = ("id", "is_approved", "owner", "spots_count")

    def get_spots_count(self, obj: ParkingLot) -> int:
        return obj.spots.filter(status=ParkingSpot.SpotStatus.ACTIVE).count()

    def create(self, validated_data):
        request = self.context.get("request")
        owner = getattr(request, "user", None)
        if owner is not None and owner.is_authenticated:
            validated_data["owner"] = owner
        lot = super().create(validated_data)
        if lot.latitude is not None and lot.longitude is not None:
            lot.set_coordinates(lot.latitude, lot.longitude)
            lot.save(update_fields=["latitude", "longitude", "location"])
        return lot

    def update(self, instance, validated_data):
        lat = validated_data.get("latitude", instance.latitude)
        lng = validated_data.get("longitude", instance.longitude)
        instance = super().update(instance, validated_data)
        instance.set_coordinates(lat, lng)
        instance.save(update_fields=["latitude", "longitude", "location"])
        return instance


class ParkingSpotSerializer(serializers.ModelSerializer):
    lot_name = serializers.ReadOnlyField(source="lot.name")
    city = serializers.ReadOnlyField(source="lot.city")
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = ParkingSpot
        fields = (
            "id",
            "lot",
            "lot_name",
            "city",
            "name",
            "description",
            "vehicle_type",
            "is_covered",
            "has_ev_charging",
            "is_24_7",
            "max_height_m",
            "hourly_price",
            "nightly_price",
            "daily_price",
            "monthly_price",
            "allow_dynamic_pricing",
            "status",
            "distance_km",
        )
        read_only_fields = ("id", "distance_km")

    def get_distance_km(self, obj: ParkingSpot):
        # Если в viewset уже посчитали и повесили атрибут — используем его.
        distance = getattr(obj, "distance_km", None)
        if distance is not None:
            return round(float(distance), 2)

        request = self.context.get("request")
        if not request:
            return None
        lat_param = request.query_params.get("lat")
        lng_param = request.query_params.get("lng")
        if not lat_param or not lng_param:
            return None
        if obj.lot.latitude is None or obj.lot.longitude is None:
            return None

        try:
            lat = float(lat_param)
            lng = float(lng_param)
        except (TypeError, ValueError):
            return None
        return round(haversine_distance_km(lat, lng, obj.lot.latitude, obj.lot.longitude), 2)


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    spot_name = serializers.ReadOnlyField(source="spot.name")
    lot_name = serializers.ReadOnlyField(source="spot.lot.name")

    class Meta:
        model = Booking
        fields = (
            "id",
            "user",
            "spot",
            "spot_name",
            "lot_name",
            "vehicle",
            "booking_type",
            "start_at",
            "end_at",
            "status",
            "total_price",
            "currency",
            "is_paid",
            "created_at",
            "updated_at",
            "external_payment_id",
        )
        read_only_fields = (
            "id",
            "user",
            "status",
            "total_price",
            "currency",
            "is_paid",
            "created_at",
            "updated_at",
            "external_payment_id",
            "spot_name",
            "lot_name",
        )

    def validate(self, attrs):
        request = self.context["request"]
        spot: ParkingSpot = attrs.get("spot", getattr(self.instance, "spot", None))
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None))
        booking_type = attrs.get(
            "booking_type", getattr(self.instance, "booking_type", Booking.BookingType.HOURLY)
        )

        if not spot or not start_at or not end_at:
            raise serializers.ValidationError("Необходимо указать место и интервал бронирования.")

        if start_at >= end_at:
            raise serializers.ValidationError("Дата начала должна быть меньше даты окончания.")

        if start_at < timezone.now():
            raise serializers.ValidationError("Нельзя создавать бронирование в прошлом.")

        if not spot.is_active:
            raise serializers.ValidationError("Выбранное место сейчас недоступно для бронирования.")

        exclude_id = self.instance.id if self.instance else None
        if not Booking.is_spot_available(spot, start_at, end_at, exclude_booking_id=exclude_id):
            raise serializers.ValidationError("На выбранный период это место уже забронировано.")

        attrs["spot"] = spot
        attrs["start_at"] = start_at
        attrs["end_at"] = end_at
        attrs["booking_type"] = booking_type
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        booking = Booking(
            user=user,
            **validated_data,
        )
        booking.total_price = booking.calculate_price()
        booking.currency = "RUB"
        booking.status = Booking.Status.PENDING
        booking.save()
        return booking

    def update(self, instance, validated_data):
        for field in ("spot", "start_at", "end_at", "booking_type", "vehicle"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Разрешаем менять только PENDING‑брони (упрощение)
        if instance.status != Booking.Status.PENDING:
            raise serializers.ValidationError("Можно редактировать только бронирования в статусе 'Ожидает оплаты'.")

        instance.total_price = instance.calculate_price()
        instance.save()
        return instance


class WaitlistEntrySerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    spot_name = serializers.ReadOnlyField(source="spot.name")

    class Meta:
        model = WaitlistEntry
        fields = (
            "id",
            "user",
            "spot",
            "spot_name",
            "desired_start",
            "desired_end",
            "auto_book",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "spot_name", "status", "created_at", "updated_at")

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        entry = WaitlistEntry.objects.create(user=user, **validated_data)
        return entry


class ComplaintSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    spot_name = serializers.ReadOnlyField(source="spot.name")
    booking_id = serializers.ReadOnlyField(source="booking.id")

    class Meta:
        model = Complaint
        fields = (
            "id",
            "author",
            "booking",
            "booking_id",
            "spot",
            "spot_name",
            "category",
            "description",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "status", "created_at", "updated_at", "spot_name", "booking_id")

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        complaint = Complaint.objects.create(author=user, **validated_data)
        return complaint
