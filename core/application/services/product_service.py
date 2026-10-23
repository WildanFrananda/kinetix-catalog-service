from dataclasses import replace
from typing import List, Dict, Mapping, Optional, TypeVar
import logging
from core.domain.repositories import ProductRepository, BinStockServicePort
from core.domain.repositories.identity_service_port import IdentityServicePort
from core.application.services.product_field_parser import ProductFieldParser
from core.domain.entities import Product, Category, StockInfo, StockStatus
from core.domain.errors import InvalidInputError, MerchantMayNotSellError, ProductNotOwnedError
from core.application.dto import (
    MerchantProductListResultDTO,
    ProductFilterDTO,
    ProductListResultDTO,
    ProductSummaryDTO,
    ProductDetailDTO,
    WarehouseStockDTO,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

class ProductService:
    def __init__(
        self,
        product_repo: ProductRepository,
        bin_stock_port: BinStockServicePort,
        identity_port: IdentityServicePort,
    ) -> None:
        self._product_repo = product_repo
        self._bin_stock_port = bin_stock_port
        self._identity_port = identity_port

    def list_products(self, filter_dto: ProductFilterDTO) -> ProductListResultDTO:
        page_number = max(filter_dto.page, 1)
        offset = (page_number - 1) * filter_dto.page_size

        paginated_products, total_count = self._product_repo.find_page(
            category_slug=filter_dto.category_slug,
            search_query=filter_dto.search_query,
            offset=offset,
            limit=filter_dto.page_size,
        )

        stock_map: Dict[str, StockInfo] = {}
        skus_by_merchant: Dict[str, List[str]] = {}
        for p in paginated_products:
            skus_by_merchant.setdefault(_merchant_principal_of(p), []).append(p.sku)

        for merchant_principal_id, skus in skus_by_merchant.items():
            try:
                stock_map.update(
                    self._bin_stock_port.get_bin_stock_for(skus, merchant_principal_id)
                )
            except Exception as exc:
                logger.warning(
                    "bin stock lookup failed for %d skus; reporting them as unknown: %s",
                    len(skus),
                    exc,
                )
                for sku in skus:
                    stock_map.setdefault(sku, StockInfo.unknown(sku))

        summaries: List[ProductSummaryDTO] = []
        for p in paginated_products:
            stock = stock_map.get(p.sku) or StockInfo.unknown(p.sku)
            quantity = stock.available_quantity
            product_id = p.id or 0
            summaries.append(
                ProductSummaryDTO(
                    id=product_id,
                    sku=p.sku,
                    title=p.title,
                    category=p.category.name,
                    category_slug=p.category.slug,
                    price=p.price,
                    currency=p.currency,
                    image_url=p.image_url,
                    merchant_principal_id=_merchant_principal_of(p),
                    weight_grams=p.weight_grams,
                    available_stock=quantity,
                    is_in_stock=None if quantity is None else quantity > 0,
                    stock_status=_status_of(stock)
                )
            )

        return ProductListResultDTO(
            count=total_count,
            page=page_number,
            page_size=filter_dto.page_size,
            results=summaries
        )

    def list_merchant_products(
        self,
        merchant_principal_id: str,
        filter_dto: ProductFilterDTO,
    ) -> MerchantProductListResultDTO:
        products, total_count = self._product_repo.find_page_of_merchant(
            merchant_principal_id=merchant_principal_id,
            category_slug=filter_dto.category_slug,
            search_query=filter_dto.search_query,
            offset=(filter_dto.page - 1) * filter_dto.page_size,
            limit=filter_dto.page_size,
        )

        return MerchantProductListResultDTO(
            count=total_count,
            page=filter_dto.page,
            page_size=filter_dto.page_size,
            results=products,
        )

    def get_product_detail(self, sku: str) -> Optional[ProductDetailDTO]:
        p = self._product_repo.find_by_sku(sku)
        if not p:
            return None

        try:
            stock = self._bin_stock_port.get_bin_stock_info(sku, _merchant_principal_of(p))
        except Exception as exc:
            logger.warning("bin stock lookup failed for %s; reporting it as unknown: %s", sku, exc)
            stock = StockInfo.unknown(sku)

        warehouse = WarehouseStockDTO(
            sku=p.sku,
            bin_location=stock.bin_location,
            available_quantity=stock.available_quantity,
            reserved_quantity=stock.reserved_quantity,
            stock_status=_status_of(stock)
        )

        product_id = p.id or 0
        return ProductDetailDTO(
            id=product_id,
            sku=p.sku,
            title=p.title,
            description=p.description,
            category=p.category.name,
            category_slug=p.category.slug,
            price=p.price,
            currency=p.currency,
            image_url=p.image_url,
            merchant_principal_id=_merchant_principal_of(p),
            weight_grams=p.weight_grams,
            warehouse_stock=warehouse
        )

    def _selling_merchant(self, principal_id: str) -> str:
        info = self._identity_port.get_merchant_info(principal_id)
        if not info:
            raise MerchantMayNotSellError("identity knows no merchant for this account")

        if not info.get("may_sell"):
            raise MerchantMayNotSellError(
                f"identity does not permit this merchant to trade (standing: "
                f"{info.get('status', 'unknown')})"
            )

        return str(info.get("merchant_principal_id") or principal_id)

    def create_product(self, merchant_principal_id: str, data: Mapping[str, object]) -> Product:
        fields = ProductFieldParser
        draft = Product(
            id=None,
            sku=fields.sku(data.get("sku")),
            title=fields.title(data.get("title")),
            description=fields.description(data.get("description")),
            price=fields.price(data.get("price")),
            currency=fields.currency(data.get("currency")),
            image_url=fields.image_url(data.get("image_url")),
            category=self._category(fields.category_id(data.get("category_id"))),
            is_active=True,
            weight_grams=fields.weight_grams(data.get("weight_grams"))
        )
        seller = self._selling_merchant(merchant_principal_id)

        return self._product_repo.save(replace(draft, merchant_principal_id=seller))

    def update_product(self, product_id: int, merchant_principal_id: str, data: Mapping[str, object]) -> Optional[Product]:
        changes = ProductFieldParser.changes(data)
        category = None if changes.category_id is None else self._category(changes.category_id)
        merchant_principal_id = self._selling_merchant(merchant_principal_id)

        existing = self._product_repo.find_by_id(product_id)
        if not existing:
            return None

        if existing.merchant_principal_id != merchant_principal_id:
            raise ProductNotOwnedError(product_id)

        if changes.sku is not None and changes.sku != existing.sku:
            raise InvalidInputError("sku", "cannot change once the product exists; a new SKU is a new product")

        updated = replace(
            existing,
            title=_given(changes.title, existing.title),
            description=_given(changes.description, existing.description),
            price=_given(changes.price, existing.price),
            currency=_given(changes.currency, existing.currency),
            image_url=_given(changes.image_url, existing.image_url),
            category=_given(category, existing.category),
            is_active=_given(changes.is_active, existing.is_active),
            weight_grams=_given(changes.weight_grams, existing.weight_grams),
        )

        return self._product_repo.save(updated)

    def delete_product(self, product_id: int, merchant_principal_id: str) -> bool:
        merchant_principal_id = self._selling_merchant(merchant_principal_id)

        existing = self._product_repo.find_by_id(product_id)
        if not existing:
            return False

        if existing.merchant_principal_id != merchant_principal_id:
            raise ProductNotOwnedError(product_id)

        return self._product_repo.delete(product_id)

    def _category(self, category_id: int) -> Category:
        category = self._product_repo.find_category_by_id(category_id)
        if not category:
            raise InvalidInputError("category_id", f"no category {category_id}")
        return category

def _given(change: Optional[T], current: T) -> T:
    return current if change is None else change

def _merchant_principal_of(product: object) -> str:
    return str(getattr(product, "merchant_principal_id", "") or "")

def _status_of(stock: StockInfo) -> StockStatus:
    """Three answers, not two: a missing quantity is not a quantity of zero."""
    quantity = stock.available_quantity
    if quantity is None:
        return StockStatus.UNKNOWN

    return StockStatus.IN_STOCK if quantity > 0 else StockStatus.OUT_OF_STOCK
