from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class OrderItem(BaseModel):
    product_id: Optional[str] = None
    name: str
    quantity: int = Field(default=1, ge=1)
    price: float = Field(default=0.0, ge=0.0)


class AddressModel(BaseModel):
    street_address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    zip_code: int = 0


class MoneyModel(BaseModel):
    currency_code: str = "USD"
    units: int = 0
    nanos: int = 0


class EmailAgentRequest(BaseModel):
    email: EmailStr
    order_id: str
    user_name: str = "Customer"
    items: List[OrderItem] = []
    total: float = 0.0
    currency_code: str = "USD"
    shipping_address: AddressModel = AddressModel()
    email_type: str = "order_confirmation"
    handoff_contract: Optional[Dict[str, Any]] = None


class EmailAgentResponse(BaseModel):
    mode: str
    email_type: str
    subject: str
    body: str
    microservice_status: str
    llm_used: bool

class EmailInstructionRequest(BaseModel):
    instruction: str