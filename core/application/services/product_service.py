from typing import List
from core.domain.repositories import ProductRepository, BinStockServicePort
from core.application.dto import (
    ProductFilterDTO,
    ProductListResultDTO,
    ProductSummaryDTO,
    ProductDetailDTO,
    WarehouseStockDTO,
)

class ProductService:
    def __init__(self, product_repo: ProductRepository, bin_stock_port: BinStockServicePort) -> None:
        self._product_repo = product_repo
        self._bin_stock_port = bin_stock_port

    def list_products(self, filter_dto: ProductFilterDTO) -> ProductListResultDTO:
        products = self._product_repo.find_all(
            category_slug=filter_dto.category_slug,
            search_query=filter_dto.search_query
        )

        total_count = len(products)
        start_idx = (filter_dto.page - 1) * filter_dto.page_size
        end_idx = start_idx + filter_dto.page_size
        paginated_products = products[start_idx:end_idx]

        summaries: List[ProductSummaryDTO] = []
        for p in paginated_products:
            stock = self._bin_stock_port.get_bin_stock_info(p.sku)
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

    def get_product_detail(self, sku: str) -> ProductDetailDTO:
        product = self._product_repo.find_by_sku(sku)
        if not product:
            raise ValueError(f"Product with SKU '{sku}' not found")

        stock = self._bin_stock_port.get_bin_stock_info(sku)
        product_id = product.id or 0

        return ProductDetailDTO(
            id=product_id,
            sku=product.sku,
            title=product.title,
            description=product.description,
            category=product.category.name,
            price=product.price,
            currency=product.currency,
            image_url=product.image_url,
            warehouse_stock=WarehouseStockDTO(
                sku=stock.sku,
                bin_location=stock.bin_location,
                available_quantity=stock.available_quantity,
                reserved_quantity=stock.reserved_quantity
            )
        )
