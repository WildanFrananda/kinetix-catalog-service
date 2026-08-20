from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class CheckoutResultDTO:
    success: bool
    order_id: Optional[int]
    order_number: str
    status: str
    total_amount: Decimal
    fulfillment_ref: str
    message: str
