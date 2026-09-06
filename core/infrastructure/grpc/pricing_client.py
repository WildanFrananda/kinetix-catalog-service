import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import grpc
from pricing.v1 import pricing_pb2, pricing_pb2_grpc

from core.domain.repositories import PricingServicePort
from core.infrastructure.grpc.money import from_money, to_money
from core.infrastructure.grpc.required_env import required_env
from core.infrastructure.security import channel_credentials


logger = logging.getLogger(__name__)

class PricingGrpcClient(PricingServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host: str = target_host or required_env("PRICING_GRPC_URL")
        self._channel = grpc.secure_channel(self._target_host, channel_credentials())
        self._stub = pricing_pb2_grpc.PricingServiceStub(self._channel)

    def calculate_price(
        self,
        items: List[Dict[str, Any]],
        voucher_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delegates pricing calculation to kinetix-pricing-service via gRPC over port 50054.
        """
        pb_items = [
            pricing_pb2.PriceItemRequest(
                product_id=str(it.get("product_id", it.get("sku", ""))),
                category_id=it.get("category_id"),
                base_price=to_money(Decimal(str(it.get("base_price", it.get("price", "0"))))),
                quantity=int(it.get("quantity", 1)),
            )
            for it in items
        ]

        req = pricing_pb2.CalculatePriceRequest(
            items=pb_items,
            voucher_code=voucher_code,
        )

        try:
            res = self._stub.CalculatePrice(req, timeout=5)
            return {
                "success": True,
                "subtotal": from_money(res.subtotal),
                "total_discount": from_money(res.total_discount),
                "voucher_discount": from_money(res.voucher_discount),
                "final_total": from_money(res.final_total),
                "applied_voucher": res.applied_voucher if res.HasField("applied_voucher") else None,
                "items": [
                    {
                        "product_id": item_res.product_id,
                        "base_price": from_money(item_res.base_price),
                        "final_unit_price": from_money(item_res.final_unit_price),
                        "quantity": item_res.quantity,
                        "line_total": from_money(item_res.line_total),
                        "applied_flash_sale": item_res.applied_flash_sale if item_res.HasField("applied_flash_sale") else None,
                        "applied_discount": item_res.applied_discount if item_res.HasField("applied_discount") else None,
                    }
                    for item_res in res.items
                ],
            }
        except Exception as exc:
            logger.error(
                "pricing did not answer (%s); prices below are the base prices with no discount "
                "applied", exc
            )
            fallback_subtotal = Decimal("0")
            fallback_items = []
            for it in items:
                base_p = Decimal(str(it.get("base_price", it.get("price", "0"))))
                qty = int(it.get("quantity", 1))
                line_t = base_p * Decimal(qty)
                fallback_subtotal += line_t
                fallback_items.append({
                    "product_id": str(it.get("product_id", it.get("sku", ""))),
                    "base_price": base_p,
                    "final_unit_price": base_p,
                    "quantity": qty,
                    "line_total": line_t,
                    "applied_flash_sale": None,
                    "applied_discount": None,
                })

            return {
                "success": False,
                "subtotal": fallback_subtotal,
                "total_discount": Decimal("0"),
                "voucher_discount": Decimal("0"),
                "final_total": fallback_subtotal,
                "applied_voucher": None,
                "items": fallback_items,
                "error": f"Pricing service gRPC error: {exc}",
            }
