from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class BookingCreate(BaseModel):
    customer_id: int
    booking_date: Optional[datetime] = None
    booking_status: str = "confirmed"
    total_price: Decimal

    model_config = {"extra": "ignore"}


class Booking(BookingCreate):
    booking_id: Optional[int] = None
