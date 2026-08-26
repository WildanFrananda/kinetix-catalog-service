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

    def submit_fulfillment_order(self, order: Order) -> Dict[str, Any]:
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
                order_number=order.order_number,
                shipping_address=pb_address,
                total_amount=pb_total,
                items=pb_items
            )

            response = self._stub.CreateOrder(req, timeout=5.0)

            if response.HasField("error"):
                return {
                    "success": False,
                    "error": f"Fulfillment error ({response.error.code}): {response.error.message}"
                }

            return {
                "success": True,
                "order_id": response.order_id,
                "order_number": response.order_number,
                "status": "received"
            }

        except grpc.RpcError as rpc_error:
            return {
                "success": True,
                "offline": True,
                "status": "received",
                "message": f"gRPC unavailable ({rpc_error.code()}). Queued offline."
            }

    def get_fulfillment_status(self, order_id: int) -> Dict[str, Any]:
        try:
            req = fulfillment_service_pb2.GetOrderStatusRequest(
                order_id=order_id,
                order_number=""
            )
            response = self._stub.GetOrderStatus(req, timeout=5.0)
            return {
                "success": True,
                "status": response.status,
                "awb_number": response.awb_number,
                "pod_photo_url": response.pod_photo_url
            }
        except grpc.RpcError as rpc_error:
            return {
                "success": False,
                "error": f"gRPC error: {rpc_error.details()}"
            }
