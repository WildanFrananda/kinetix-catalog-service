from typing import Dict, Any
from core.domain.entities import Order
from core.domain.repositories import FulfillmentServicePort


class FakeFulfillmentServicePort(FulfillmentServicePort):
    def __init__(self) -> None:
        self.orders: Dict[int, Order] = {}

    def submit_fulfillment_order(self, order: Order) -> Dict[str, Any]:
        order_id = len(self.orders) + 1
        self.orders[order_id] = order
        return {
            "success": True,
            "order_id": order_id,
            "order_number": order.order_number,
            "status": "received"
        }

    def get_fulfillment_status(self, order_id: int) -> Dict[str, Any]:
        if order_id in self.orders:
            return {
                "success": True,
                "status": "received",
                "awb_number": f"AWB-{order_id}",
                "pod_photo_url": f"https://cdn.kinetix.internal/pod/{order_id}.jpg"
            }
        return {"success": False, "error": "Order not found"}
