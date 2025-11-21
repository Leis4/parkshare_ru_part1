from celery import shared_task

from backend.backend.parking.models import ParkingLot
from .features import bookings_dataframe
from .pricing import train_pricing_model


@shared_task
def update_models() -> None:
    """
    Периодически обучает модель цен и обновляет стресс-индексы по паркингам.
    """
    df = bookings_dataframe()
    train_pricing_model(df)

    lots = ParkingLot.objects.filter(is_active=True)
    for lot in lots:
        spots = lot.spots.all()
        if not spots:
            lot.stress_index = 0.0
            lot.save(update_fields=["stress_index"])
            continue
        values = [max(0.0, min(spot.occupancy_7d, 1.0)) for spot in spots]
        lot.stress_index = sum(values) / len(values)
        lot.save(update_fields=["stress_index"])
