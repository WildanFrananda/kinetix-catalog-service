# Four serializers were imported here and shipped in __all__ without the modules ever
# existing: order_item, checkout_request, reserve_stock_request and reservation_result.
# Every import of this package raised ModuleNotFoundError, so the service could not start at
# all — this is why kinetix-catalog-service restart-looped.
#
# They are not restored, they are removed: each is referenced in exactly zero places, and all
# four describe checkout, order and stock-reservation payloads, which belong to order-service
# and warehouse-service rather than the catalog. Reinstating them here would re-create the
# domain-boundary violation the audit recorded.

from core.api.serializers.product_summary_serializer import ProductSummarySerializer
from core.api.serializers.product_list_response_serializer import ProductListResponseSerializer
from core.api.serializers.warehouse_stock_serializer import WarehouseStockSerializer
from core.api.serializers.product_detail_serializer import ProductDetailSerializer

__all__ = [
    "ProductSummarySerializer",
    "ProductListResponseSerializer",
    "WarehouseStockSerializer",
    "ProductDetailSerializer",
]
