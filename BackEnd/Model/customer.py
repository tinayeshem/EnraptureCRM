from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Customer(BaseModel):
    customer_id: Optional[int] = None
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None