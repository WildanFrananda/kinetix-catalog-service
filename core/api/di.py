from core.application.services import ProductService
from core.application.services.category_service import CategoryService
from core.infrastructure.repositories import DjangoProductRepository
from core.infrastructure.grpc.bin_stock_client import BinStockGrpcClient
from core.infrastructure.grpc.identity_client import IdentityGrpcClient

def get_product_service() -> ProductService:
    product_repo = DjangoProductRepository()
    bin_stock_client = BinStockGrpcClient()
    identity_client = IdentityGrpcClient()
    return ProductService(
        product_repo=product_repo,
        bin_stock_port=bin_stock_client,
        identity_port=identity_client
    )

def get_category_service() -> CategoryService:
    product_repo = DjangoProductRepository()
    return CategoryService(product_repo=product_repo)
