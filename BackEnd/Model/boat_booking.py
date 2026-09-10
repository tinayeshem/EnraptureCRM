from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BoatBooking(BaseModel):
    boat_booking_id: Optional[int] = None
    booking_id: int
    departure_time: datetime
    return_time: Optional[datetime] = None
    destination: str
    number_of_passengers: int
    captain_required: bool
