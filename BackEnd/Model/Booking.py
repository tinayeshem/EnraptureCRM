from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class Booking(BaseModel):
    booking_id: Optional[int] = None
    customer_id: int
    booking_date: datetime
    booking_status: str
    total_price: Decimal
