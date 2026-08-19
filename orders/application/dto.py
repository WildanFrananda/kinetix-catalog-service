from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

@dataclass(frozen=True)
class OrderItemDTO:
    sku: str
    product_name: str
    quantity: int
    price: Decimal

@dataclass(frozen=True)
class CreateOrderInputDTO:
    merchant_api_key: str
    buyer_name: str
    buyer_phone: str
    street_address: str
    city: str
    postal_code: str
    items: List[OrderItemDTO]

@dataclass(frozen=True)
class CheckoutResultDTO:
    success: bool
    order_id: Optional[int]
    order_number: str
    status: str
    total_amount: Decimal
    fulfillment_ref: str
    message: str
