from typing import Optional
from pydantic import BaseModel


class ShuttleBooking(BaseModel):
    shuttle_booking_id: Optional[int] = None
    persons_count: int
    vehicle: str
    duration: int
