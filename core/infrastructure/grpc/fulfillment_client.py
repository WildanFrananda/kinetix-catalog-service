import os
import sys
from typing import Dict, Any, Optional

generated_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "generated"))
if generated_dir not in sys.path:
    sys.path.insert(0, generated_dir)

import grpc
from core.domain.entities import Order
from core.domain.repositories import FulfillmentServicePort

try:
    from fulfillment.v1 import fulfillment_service_pb2, fulfillment_service_pb2_grpc
    from common.v1 import types_pb2
except ImportError:
    from core.infrastructure.grpc.generated.fulfillment.v1 import fulfillment_service_pb2, fulfillment_service_pb2_grpc
    from core.infrastructure.grpc.generated.common.v1 import types_pb2

class FulfillmentGrpcClient(FulfillmentServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host = target_host or os.environ.get("OMS_GRPC_HOST", "localhost:50051")
        # Reuse gRPC channel connection across requests to prevent socket/memory leaks
        self._channel = grpc.insecure_channel(self._target_host)
        self._stub = fulfillment_service_pb2_grpc.FulfillmentServiceStub(self._channel)

    def submit_fulfillment_order(self, order: Order, merchant_api_key: str) -> Dict[str, Any]:
        try:
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
                delivery_address=pb_address,
                total_amount=pb_total,
                items=pb_items
            )

            res = self._stub.CreateOrder(req, timeout=5)
            if res.HasField("error"):
                return {
                    "success": False,
                    "order_id": 0,
                    "message": f"gRPC Error [{res.error.error_code}]: {res.error.message}",
                    "offline": False
                }

            return {
                "success": True,
                "order_id": res.order_id,
                "order_number": res.order_number,
                "status": res.status,
                "offline": False
            }
        except Exception as e:
            return {
                "success": False,
                "order_id": 0,
                "message": f"Fulfillment Service gRPC Exception: {str(e)}",
                "offline": True
            }

    def get_fulfillment_status(self, order_id: int, merchant_api_key: str) -> Dict[str, Any]:
        return {
            "order_id": order_id,
            "status": "PROCESSING"
        }
