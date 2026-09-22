import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import grpc
from catalog.v1 import catalog_pb2, catalog_pb2_grpc
from common.v1 import common_pb2
from google.protobuf.timestamp_pb2 import Timestamp

from core.domain.entities import Product
from core.domain.repositories import ProductRepository

logger = logging.getLogger(__name__)

MAX_PAGE = 500
DEFAULT_PAGE = 100

class CatalogServicer(catalog_pb2_grpc.CatalogServiceServicer):  # type: ignore[misc]
    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    def ChangedSince(
        self,
        request: catalog_pb2.ChangedSinceRequest,
        context: grpc.ServicerContext,
    ) -> catalog_pb2.ChangedSinceResponse:
        limit = request.limit if request.limit > 0 else DEFAULT_PAGE
        limit = min(limit, MAX_PAGE)

        updated_through = _from_proto_time(request.cursor.updated_through)

        page = self._product_repo.find_changed_since(
            updated_through=updated_through,
            last_sku=request.cursor.last_sku,
            limit=limit,
        )

        response = catalog_pb2.ChangedSinceResponse(
            upserted=[_to_proto_product(p) for p in page.upserted],
            removed_skus=page.removed_skus,
            has_more=page.has_more,
        )
        response.next.last_sku = page.next_last_sku
        if page.next_updated_through is not None:
            response.next.updated_through.FromDatetime(page.next_updated_through)

        return response

    def GetProduct(
        self,
        request: catalog_pb2.GetProductRequest,
        context: grpc.ServicerContext,
    ) -> catalog_pb2.GetProductResponse:
        if not request.sku:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "sku is required")

        product = self._product_repo.find_by_sku(request.sku)
        if product is None:
            return catalog_pb2.GetProductResponse(found=False)

        return catalog_pb2.GetProductResponse(found=True, product=_to_proto_product(product))

    def CountProducts(
        self,
        request: catalog_pb2.CountProductsRequest,
        context: grpc.ServicerContext,
    ) -> catalog_pb2.CountProductsResponse:
        return catalog_pb2.CountProductsResponse(
            total=self._product_repo.count_active_products()
        )


def _from_proto_time(value: Timestamp) -> Optional[datetime]:
    if value.seconds == 0 and value.nanos == 0:
        return None
    return value.ToDatetime(tzinfo=timezone.utc)


def _to_proto_product(product: Product) -> catalog_pb2.Product:
    message = catalog_pb2.Product(
        sku=product.sku,
        merchant_principal_id=product.merchant_principal_id or "",
        title=product.title,
        description=product.description,
        price=common_pb2.Money(
            amount_minor=_to_minor_units(product.price),
            currency=product.currency,
        ),
        image_url=product.image_url,
        category_slug=product.category.slug,
        category_name=product.category.name,
    )
    if product.updated_at is not None:
        message.updated_at.FromDatetime(product.updated_at)
    return message


def _to_minor_units(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())
