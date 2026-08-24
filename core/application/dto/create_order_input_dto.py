from dataclasses import dataclass
from typing import List, Optional
from core.application.dto.order_item_dto import OrderItemDTO

@dataclass(frozen=True)
class CreateOrderInputDTO:
    merchant_api_key: str
    buyer_name: str
    buyer_phone: str
    street_address: str
    city: str
    postal_code: str
    items: List[OrderItemDTO]
    idempotency_key: Optional[str] = None
