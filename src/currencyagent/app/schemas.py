from pydantic import BaseModel
from typing import Optional, Any


class CurrencyRequest(BaseModel):
    query: str
    from_currency: Optional[str] = "USD"
    to_currency: Optional[str] = "EUR"
    units: Optional[int] = 0
    nanos: Optional[int] = 0
    handoff_contract: Optional[dict] = None


class CurrencyResponse(BaseModel):
    mode: str
    action: str
    data: Any