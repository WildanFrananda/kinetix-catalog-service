from typing import Optional, Dict, Any
from core.domain.entities import Order
from core.domain.repositories import FulfillmentServicePort

class FakeFulfillmentServicePort(FulfillmentServicePort):
    def __init__(self, return_success: bool = True) -> None:
        self.return_success = return_success
        self.last_submitted_order: Optional[Order] = None

    def submit_fulfillment_order(self, order: Order, merchant_api_key: str) -> Dict[str, Any]:
        self.last_submitted_order = order
        return {
            "success": self.return_success,
            "order_id": order.id,
            "status": "received" if self.return_success else "failed"
        }

    def get_fulfillment_status(self, order_id: int, merchant_api_key: str) -> Dict[str, Any]:
        return {"order_id": order_id, "status": "received"}
