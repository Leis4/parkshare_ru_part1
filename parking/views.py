# backend/parking/views.py

from __future__ import annotations

from typing import Any, Iterable, List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from core.permissions import IsAdminOrReadOnly
from core.utils import haversine_distance_km, parse_float
from vehicles.models import Vehicle

from .models import Booking, Complaint, ParkingLot, ParkingSpot, WaitlistEntry
from .serializers import (
    BookingSerializer,
    ComplaintSerializer,
    ParkingLotSerializer,
    ParkingSpotSerializer,
    WaitlistEntrySerializer,
)


# =======================
#   DRF ViewSets (API)
# =======================


class ParkingLotViewSet(viewsets.ModelViewSet):
    """
    CRUD по объектам парковки.

    - GET /api/parking/lots/ — список (фильтрация по городу/типу)
    - POST /api/parking/lots/ — создать (только владельцы/админы)
    """

    serializer_class = ParkingLotSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = ParkingLot.objects.select_related("owner")
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and not getattr(user, "is_owner", False)):
            qs = qs.filter(is_active=True, is_approved=True)

        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__iexact=city)

        parking_type = self.request.query_params.get("parking_type")
        if parking_type:
            qs = qs.filter(parking_type=parking_type)

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or not getattr(user, "is_owner", False):
            raise permissions.PermissionDenied(
                "Создавать объекты парковки могут только пользователи с ролью 'owner' или администраторы."
            )
        serializer.save(owner=user)


class ParkingSpotViewSet(viewsets.ModelViewSet):
    """
    CRUD по парковочным местам.

    - GET /api/parking/spots/?lat=...&lng=...&radius_km=2 — места рядом
    - Фильтры: ?city=, ?vehicle_type=, ?max_price=, ?has_ev=1, ?covered=1, ?is_24_7=1
    """

    serializer_class = ParkingSpotSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = (
            ParkingSpot.objects.select_related("lot", "lot__owner")
            .all()
        )
        user = self.request.user

        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            qs = qs.filter(
                status=ParkingSpot.SpotStatus.ACTIVE,
                lot__is_active=True,
                lot__is_approved=True,
            )
        else:
            # Управлять местами может только владелец/админ
            if not user.is_authenticated or (not getattr(user, "is_owner", False) and not user.is_superuser):
                return ParkingSpot.objects.none()
            qs = qs.filter(lot__owner=user)

        # Фильтрация
        params = self.request.query_params
        city = params.get("city")
        if city:
            qs = qs.filter(lot__city__iexact=city)

        vehicle_type = params.get("vehicle_type")
        if vehicle_type:
            qs = qs.filter(vehicle_type=vehicle_type)

        max_price = parse_float(params.get("max_price"))
        if max_price is not None:
            qs = qs.filter(hourly_price__lte=max_price)

        has_ev = params.get("has_ev")
        if has_ev == "1":
            qs = qs.filter(has_ev_charging=True)

        covered = params.get("covered")
        if covered == "1":
            qs = qs.filter(is_covered=True)

        is_24_7 = params.get("is_24_7")
        if is_24_7 == "1":
            qs = qs.filter(is_24_7=True)

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        lat = parse_float(request.query_params.get("lat"))
        lng = parse_float(request.query_params.get("lng"))
        radius_km = parse_float(request.query_params.get("radius_km"))

        if lat is not None and lng is not None and radius_km is not None:
            # Python‑фильтрация по расстоянию (работает и без PostGIS)
            filtered: List[ParkingSpot] = []
            for spot in queryset:
                lot = spot.lot
                if lot.latitude is None or lot.longitude is None:
                    continue
                distance = haversine_distance_km(lat, lng, lot.latitude, lot.longitude)
                if distance <= radius_km:
                    spot.distance_km = distance  # для сериализатора
                    filtered.append(spot)
            queryset = filtered

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    """
    Бронирования.

    - Пользователь видит свои бронирования.
    - Владелец видит свои бронирования и брони по своим местам.
    """

    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = (
            Booking.objects.select_related("spot", "spot__lot", "user", "vehicle")
            .all()
        )
        if not user.is_authenticated:
            return Booking.objects.none()

        if user.is_superuser:
            return qs

        if getattr(user, "is_owner", False):
            return qs.filter(Q(user=user) | Q(spot__lot__owner=user))
        return qs.filter(user=user)

    def perform_create(self, serializer):
        booking = serializer.save()
        return booking

    def destroy(self, request, *args, **kwargs):
        """
        Отмена бронирования: помечаем как CANCELLED,
        если оно ещё не началось.
        """
        instance: Booking = self.get_object()
        if instance.has_started:
            return Response(
                {"detail": "Нельзя отменить уже начавшееся бронирование."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.status = Booking.Status.CANCELLED
        instance.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class WaitlistViewSet(viewsets.ModelViewSet):
    """
    Лист ожидания. Пользователь управляет только своими записями.
    Админ может видеть всё.
    """

    serializer_class = WaitlistEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = WaitlistEntry.objects.select_related("spot", "spot__lot", "user")
        if user.is_superuser:
            return qs
        return qs.filter(user=user)


class ComplaintViewSet(viewsets.ModelViewSet):
    """
    Жалобы. Создатель видит свои, админ — все.
    """

    serializer_class = ComplaintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Complaint.objects.select_related("author", "spot", "booking")
        if user.is_superuser:
            return qs
        return qs.filter(author=user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# =======================
#   HTML-вьюхи
# =======================


class LandingPageView(TemplateView):
    """
    Лендинг с картой и списком парковок/мест.
    """

    template_name = "parking/landing.html"

    def get_context_data(self, **kwargs: Any):
        ctx = super().get_context_data(**kwargs)
        lots = (
            ParkingLot.objects.filter(is_active=True, is_approved=True)
            .select_related("owner")
            .order_by("city", "name")[:50]
        )
        spots = (
            ParkingSpot.objects.filter(
                status=ParkingSpot.SpotStatus.ACTIVE,
                lot__in=lots,
            )
            .select_related("lot", "lot__owner")
            .order_by("lot__city", "lot__name", "name")[:100]
        )
        ctx["lots"] = lots
        ctx["spots"] = spots
        return ctx


class UserDashboardView(LoginRequiredMixin, TemplateView):
    """
    Личный кабинет водителя: его машины и бронирования.
    """

    template_name = "parking/user_dashboard.html"

    def get_context_data(self, **kwargs: Any):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        vehicles = Vehicle.objects.filter(owner=user).order_by("-created_at")
        bookings = (
            Booking.objects.filter(user=user)
            .select_related("spot", "spot__lot")
            .order_by("-start_at")
        )
        ctx["vehicles"] = vehicles
        ctx["bookings"] = bookings
        return ctx


class OwnerDashboardView(LoginRequiredMixin, TemplateView):
    """
    Кабинет владельца: его паркинги, места и бронирования по ним.
    """

    template_name = "parking/owner_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (getattr(user, "is_owner", False) or user.is_superuser):
            # Если не владелец — отправляем в обычный кабинет
            return redirect("user_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        lots = (
            ParkingLot.objects.filter(owner=user)
            .prefetch_related("spots")
            .order_by("city", "name")
        )
        spots = ParkingSpot.objects.filter(lot__owner=user).select_related("lot")
        bookings = (
            Booking.objects.filter(spot__lot__owner=user)
            .select_related("spot", "spot__lot", "user", "vehicle")
            .order_by("-start_at")
        )
        ctx["lots"] = lots
        ctx["spots"] = spots
        ctx["bookings"] = bookings
        return ctx
