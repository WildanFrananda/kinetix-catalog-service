import os
import sys
from typing import Dict, Any, Optional


# Ensure generated protobuf modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "generated")))

import grpc
from orders.domain.entities import Order
from orders.domain.repositories import FulfillmentServicePort

try:
    from fulfillment.v1 import fulfillment_service_pb2, fulfillment_service_pb2_grpc
    from common.v1 import types_pb2
except ImportError:
    from orders.infrastructure.grpc.generated.fulfillment.v1 import fulfillment_service_pb2, fulfillment_service_pb2_grpc
    from orders.infrastructure.grpc.generated.common.v1 import types_pb2

class FulfillmentGrpcClient(FulfillmentServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host = target_host or os.environ.get("OMS_GRPC_HOST", "localhost:50051")


    def submit_fulfillment_order(self, order: Order, merchant_api_key: str) -> Dict[str, Any]:
        try:
            channel = grpc.insecure_channel(self._target_host)
            stub = fulfillment_service_pb2_grpc.FulfillmentServiceStub(channel)

            pb_address = types_pb2.Address(
                recipient_name=order.shipping_address.recipient_name,
                phone_number=order.shipping_address.phone_number,
                street_address=order.shipping_address.street_address,
                city=order.shipping_address.city,
                postal_code=order.shipping_address.postal_code
            )

            pb_total = types_pb2.Money(
                currency_code=order.total_amount.currency,
                units=int(order.total_amount.amount),
                nanos=int((order.total_amount.amount % 1) * 1_000_000_000)
            )

            pb_items = [
                types_pb2.OrderItem(
                    sku=it.sku,
                    product_name=it.product_name,
                    quantity=it.quantity,
                    price=types_pb2.Money(
                        currency_code=it.price.currency,
                        units=int(it.price.amount),
                        nanos=int((it.price.amount % 1) * 1_000_000_000)
                    ),
                    bin_location=it.bin_location or "Rak A-01"
                )
                for it in order.items
            ]

            req = fulfillment_service_pb2.CreateOrderRequest(
                merchant_api_key=merchant_api_key,
                order_number=order.order_number,
                shipping_address=pb_address,
                total_amount=pb_total,
                items=pb_items,
                buyer_name=order.buyer_name,
                buyer_phone=order.buyer_phone
            )

            res = stub.CreateOrder(req, timeout=5)

            if res.error and res.error.error_code:
                return {
                    "success": False,
                    "order_id": order.id,
                    "status": "error",
                    "error": res.error.message
                }

            return {
                "success": True,
                "order_id": res.order_id,
                "order_number": res.order_number,
                "status": "received",
                "merchant_id": res.merchant_id
            }
        except Exception as e:
            return {
                "success": False,
                "order_id": order.id,
                "status": "queued_local",
                "error": f"OMS gRPC offline fallback: {str(e)}"
            }

    def get_fulfillment_status(self, order_id: int, merchant_api_key: str) -> Dict[str, Any]:
        try:
            channel = grpc.insecure_channel(self._target_host)
            stub = fulfillment_service_pb2_grpc.FulfillmentServiceStub(channel)

            req = fulfillment_service_pb2.GetOrderStatusRequest(
                merchant_api_key=merchant_api_key,
                order_id=order_id
            )

            res = stub.GetOrderStatus(req, timeout=5)
            return {
                "order_id": res.order_id,
                "order_number": res.order_number,
                "status": res.status,
                "updated_at": res.updated_at
            }
        except Exception as e:
            return {
                "order_id": order_id,
                "status": "unknown",
                "error": str(e)
            }
