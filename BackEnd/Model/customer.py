from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None

    model_config = {"extra": "ignore"}


class Customer(CustomerCreate):
    customer_id: Optional[int] = None
    created_at: Optional[datetime] = None