from dataclasses import dataclass

@dataclass(frozen=True)
class WarehouseStockDTO:
    sku: str
    bin_location: str
    available_quantity: int
    reserved_quantity: int
