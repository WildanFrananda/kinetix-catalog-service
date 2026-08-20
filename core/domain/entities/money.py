from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    currency: str
    amount: Decimal
