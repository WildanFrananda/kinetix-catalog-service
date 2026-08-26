from core.application.services import ProductService, OrderService
from core.infrastructure.repositories import DjangoProductRepository, DjangoOrderRepository
from core.infrastructure.grpc.bin_stock_client import BinStockGrpcClient
from core.infrastructure.grpc.fulfillment_client import FulfillmentGrpcClient
from core.infrastructure.grpc.pricing_client import PricingGrpcClient

def get_product_service() -> ProductService:
    product_repo = DjangoProductRepository()
    bin_stock_client = BinStockGrpcClient()
    return ProductService(product_repo=product_repo, bin_stock_port=bin_stock_client)

def get_order_service() -> OrderService:
    order_repo = DjangoOrderRepository()
    fulfillment_client = FulfillmentGrpcClient()
    bin_stock_client = BinStockGrpcClient()
    pricing_client = PricingGrpcClient()
    return OrderService(
        order_repo=order_repo,
        fulfillment_port=fulfillment_client,
        bin_stock_port=bin_stock_client,
        pricing_port=pricing_client
    )
