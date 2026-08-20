from dataclasses import dataclass
from decimal import Decimal
from core.application.dto.warehouse_stock_dto import WarehouseStockDTO

@dataclass(frozen=True)
class ProductDetailDTO:
    id: int
    sku: str
    title: str
    description: str
    category: str
    price: Decimal
    currency: str
    image_url: str
    warehouse_stock: WarehouseStockDTO
