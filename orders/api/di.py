from orders.application.services import CheckoutOrderService
from orders.infrastructure.repositories import DjangoOrderRepository
from orders.infrastructure.grpc.fulfillment_client import FulfillmentGrpcClient

def get_checkout_service() -> CheckoutOrderService:
    """Factory function for constructing the CheckoutOrderService dependency graph."""
    order_repo = DjangoOrderRepository()
    fulfillment_client = FulfillmentGrpcClient()

    return CheckoutOrderService(order_repo=order_repo, fulfillment_port=fulfillment_client)
