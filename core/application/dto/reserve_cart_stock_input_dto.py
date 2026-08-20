from dataclasses import dataclass

@dataclass(frozen=True)
class ReserveCartStockInputDTO:
    sku: str
    quantity: int
