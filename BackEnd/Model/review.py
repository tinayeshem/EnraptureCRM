from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Review(BaseModel):
    review_id: Optional[int] = None
    customer_id: int
    booking_id: int
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
