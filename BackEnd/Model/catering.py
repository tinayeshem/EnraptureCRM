from typing import Optional
from pydantic import BaseModel


class Catering(BaseModel):
    order_id: Optional[int] = None
    event_type: str
    person_count: int
