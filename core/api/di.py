from core.application.services import ProductService
from core.infrastructure.repositories import DjangoProductRepository
from core.infrastructure.grpc.bin_stock_client import BinStockGrpcClient

def get_product_service() -> ProductService:
    product_repo = DjangoProductRepository()
    bin_stock_client = BinStockGrpcClient()
    return ProductService(product_repo=product_repo, bin_stock_port=bin_stock_client)
