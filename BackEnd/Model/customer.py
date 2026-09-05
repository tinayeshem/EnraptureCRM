from pydantic import BaseModel
from uuid import UUID


class Customer(BaseModel):
    customer_id : UUID
    firstName : str
    lastName :str
    email : str
    phone : str
    