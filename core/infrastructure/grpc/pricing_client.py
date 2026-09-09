import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import grpc
from pricing.v1 import pricing_pb2, pricing_pb2_grpc

from core.domain.repositories import PricingServicePort
from core.infrastructure.grpc.money import from_money, to_money
from core.infrastructure.grpc.pricing_unavailable import PricingUnavailable
from core.infrastructure.grpc.required_env import required_env
from core.infrastructure.metrics import (
    GrpcClientMetricsInterceptor,
    declare_grpc_client_calls,
)
from core.infrastructure.security import channel_credentials
from core.infrastructure.observability import request_id_metadata


logger = logging.getLogger(__name__)

METRICS_PEER = "kinetix-pricing-service"

_SERVICE = pricing_pb2.DESCRIPTOR.services_by_name["PricingService"]
declare_grpc_client_calls(METRICS_PEER, _SERVICE, ["CalculatePrice"])

class PricingGrpcClient(PricingServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host: str = target_host or required_env("PRICING_GRPC_URL")
        self._channel = grpc.intercept_channel(
            grpc.secure_channel(self._target_host, channel_credentials()),
            GrpcClientMetricsInterceptor(METRICS_PEER),
        )
        self._stub = pricing_pb2_grpc.PricingServiceStub(self._channel)

    def calculate_price(
        self,
        items: List[Dict[str, Any]],
        voucher_code: Optional[str] = None
    ) -> Dict[str, Any]:
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
            res = self._stub.CalculatePrice(req, timeout=5, metadata=request_id_metadata())
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
            logger.error("pricing did not answer, so no price was produced: %s", exc)
            raise PricingUnavailable(
                "pricing could not be reached, so this cart was not priced"
            ) from exc
