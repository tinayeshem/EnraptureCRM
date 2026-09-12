from datetime import date
from typing import Optional
from pydantic import BaseModel


DEFAULT_CAMPSITE_ID: int = 1


class CampBooking(BaseModel):
    camp_booking_id: Optional[int] = None
    booking_id: int
    campsite_id: Optional[int] = DEFAULT_CAMPSITE_ID
    arrival_date: date
    departure_date: date
    number_of_campers: int
    tent_required: Optional[bool] = None
    equipment_rental: Optional[bool] = None
