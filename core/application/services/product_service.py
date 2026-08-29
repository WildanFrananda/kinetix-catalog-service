from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from core.domain.repositories import ProductRepository, BinStockServicePort
from core.domain.repositories.identity_service_port import IdentityServicePort
from core.domain.entities import Product, Category, StockInfo
from core.application.dto import (
    ProductFilterDTO,
    ProductListResultDTO,
    ProductSummaryDTO,
    ProductDetailDTO,
    WarehouseStockDTO,
)

class ProductService:
    def __init__(
        self,
        product_repo: ProductRepository,
        bin_stock_port: BinStockServicePort,
        identity_port: Optional[IdentityServicePort] = None
    ) -> None:
        self._product_repo = product_repo
        self._bin_stock_port = bin_stock_port
        self._identity_port = identity_port

    def list_products(self, filter_dto: ProductFilterDTO) -> ProductListResultDTO:
        products = self._product_repo.find_all(
            category_slug=filter_dto.category_slug,
            search_query=filter_dto.search_query
        )

        total_count = len(products)
        start_idx = (filter_dto.page - 1) * filter_dto.page_size
        end_idx = start_idx + filter_dto.page_size
        paginated_products = products[start_idx:end_idx]

        stock_map: Dict[str, StockInfo] = {}
        if paginated_products:
            with ThreadPoolExecutor(max_workers=min(len(paginated_products), 10)) as executor:
                futures = {
                    executor.submit(self._bin_stock_port.get_bin_stock_info, p.sku): p.sku
                    for p in paginated_products
                }
                for future in futures:
                    sku = futures[future]
                    try:
                        stock_map[sku] = future.result()
                    except Exception:
                        stock_map[sku] = StockInfo(sku=sku, bin_location="Unavailable", available_quantity=0, reserved_quantity=0)

        summaries: List[ProductSummaryDTO] = []
        for p in paginated_products:
            stock = stock_map.get(p.sku) or StockInfo(sku=p.sku, bin_location="Unavailable", available_quantity=0, reserved_quantity=0)
            product_id = p.id or 0
            summaries.append(
                ProductSummaryDTO(
                    id=product_id,
                    sku=p.sku,
                    title=p.title,
                    category=p.category.name,
                    price=p.price,
                    currency=p.currency,
                    image_url=p.image_url,
                    available_stock=stock.available_quantity,
                    is_in_stock=stock.available_quantity > 0
                )
            )

        return ProductListResultDTO(
            count=total_count,
            page=filter_dto.page,
            page_size=filter_dto.page_size,
            results=summaries
        )

    def get_product_detail(self, sku: str) -> Optional[ProductDetailDTO]:
        p = self._product_repo.find_by_sku(sku)
        if not p:
            return None

        try:
            stock = self._bin_stock_port.get_bin_stock_info(sku)
        except Exception:
            stock = StockInfo(sku=sku, bin_location="Unavailable", available_quantity=0, reserved_quantity=0)

        warehouse = WarehouseStockDTO(
            sku=p.sku,
            bin_location=stock.bin_location,
            available_quantity=stock.available_quantity,
            reserved_quantity=stock.reserved_quantity
        )

        product_id = p.id or 0
        return ProductDetailDTO(
            id=product_id,
            sku=p.sku,
            title=p.title,
            description=p.description,
            category=p.category.name,
            price=p.price,
            currency=p.currency,
            image_url=p.image_url,
            warehouse_stock=warehouse
        )

    def create_product(self, merchant_id: int, data: Dict[str, Any]) -> Product:
        if self._identity_port:
            info = self._identity_port.get_merchant_info(merchant_id)
            if not info or info.get("status") not in ["verified", "active"]:
                raise PermissionError("Merchant account is not verified/active")

        cat = self._product_repo.find_category_by_id(int(data["category_id"]))
        if not cat:
            raise ValueError(f"Category {data['category_id']} not found")

        product = Product(
            id=None,
            sku=str(data["sku"]),
            title=str(data["title"]),
            description=str(data.get("description", "")),
            price=Decimal(str(data["price"])),
            currency=str(data.get("currency", "IDR")),
            image_url=str(data.get("image_url", "")),
            category=cat,
            merchant_id=merchant_id,
            is_active=True
        )
        return self._product_repo.save(product)

    def update_product(self, product_id: int, merchant_id: int, data: Dict[str, Any]) -> Optional[Product]:
        if self._identity_port:
            info = self._identity_port.get_merchant_info(merchant_id)
            if not info or info.get("status") not in ["verified", "active"]:
                raise PermissionError("Merchant account is not verified/active")

        existing = self._product_repo.find_by_id(product_id)
        if not existing:
            return None

        if existing.merchant_id is not None and existing.merchant_id != merchant_id:
            raise PermissionError("Product does not belong to this merchant")

        category = existing.category
        if "category_id" in data:
            cat = self._product_repo.find_category_by_id(int(data["category_id"]))
            if not cat:
                raise ValueError(f"Category {data['category_id']} not found")
            category = cat

        updated = Product(
            id=existing.id,
            sku=str(data.get("sku", existing.sku)),
            title=str(data.get("title", existing.title)),
            description=str(data.get("description", existing.description)),
            price=Decimal(str(data["price"])) if "price" in data else existing.price,
            currency=str(data.get("currency", existing.currency)),
            image_url=str(data.get("image_url", existing.image_url)),
            category=category,
            merchant_id=merchant_id,
            is_active=bool(data.get("is_active", existing.is_active))
        )
        return self._product_repo.save(updated)

    def delete_product(self, product_id: int, merchant_id: int) -> bool:
        if self._identity_port:
            info = self._identity_port.get_merchant_info(merchant_id)
            if not info or info.get("status") not in ["verified", "active"]:
                raise PermissionError("Merchant account is not verified/active")

        existing = self._product_repo.find_by_id(product_id)
        if not existing:
            return False

        if existing.merchant_id is not None and existing.merchant_id != merchant_id:
            raise PermissionError("Product does not belong to this merchant")

        return self._product_repo.delete(product_id)
