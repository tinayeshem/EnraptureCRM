from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from enum import Enum


class Status(Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"
    
    

class Booking(BaseModel):
    booking_id : UUID
    customer_id : UUID
    booking_date : datetime
    booking_status : Status
    total_price : Decimal



