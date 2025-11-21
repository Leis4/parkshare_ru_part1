from __future__ import annotations

import pandas as pd

from backend.backend.parking.models import Booking


def bookings_dataframe() -> pd.DataFrame:
    """
    Собирает историю бронирований в DataFrame для обучения/аналитики.
    """
    qs = Booking.objects.filter(
        status__in=[
            Booking.Status.CONFIRMED,
            Booking.Status.ACTIVE,
            Booking.Status.COMPLETED,
        ]
    ).select_related("spot", "spot__lot")

    rows = []
    for b in qs:
        rows.append(
            {
                "booking_id": str(b.id),
                "spot_id": str(b.spot_id),
                "lot_id": str(b.spot.lot_id),
                "city": b.spot.lot.city,
                "start": b.start,
                "end": b.end,
                "duration_hours": b.duration_hours,
                "price": float(b.total_price),
                "dow": b.start.weekday(),
                "hour": b.start.hour,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["is_weekend"] = df["dow"] >= 5
    return df
