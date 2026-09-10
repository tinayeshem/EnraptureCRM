from datetime import date
from typing import Optional
from pydantic import BaseModel


class RoomBooking(BaseModel):
    room_booking_id: Optional[int] = None
    booking_id: int
    check_in_date: date
    check_out_date: date
    number_of_guests: int
    room_type: Optional[str] = None
