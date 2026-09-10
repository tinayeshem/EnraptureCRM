from datetime import date
from typing import Optional
from pydantic import BaseModel


class CampBooking(BaseModel):
    camp_booking_id: Optional[int] = None
    booking_id: int
    campsite_id: int
    arrival_date: date
    departure_date: date
    number_of_campers: int
    tent_required: Optional[bool] = None
    equipment_rental: Optional[bool] = None
