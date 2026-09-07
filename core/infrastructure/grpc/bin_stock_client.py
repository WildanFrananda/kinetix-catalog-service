import logging
from typing import Any, Dict, Optional

import grpc
from fulfillment.v1 import fulfillment_pb2, fulfillment_pb2_grpc

from core.domain.entities.stock_info import StockInfo
from core.domain.repositories import BinStockServicePort
from core.infrastructure.grpc.required_env import required_env
from core.infrastructure.resilience import CircuitBreaker, CircuitOpenError
from core.infrastructure.security import channel_credentials
from core.infrastructure.observability import request_id_metadata

logger = logging.getLogger(__name__)


class BinStockGrpcClient(BinStockServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host: str = target_host or required_env("WAREHOUSE_GRPC_URL")
        self._channel = grpc.secure_channel(self._target_host, channel_credentials())
        self._stub = fulfillment_pb2_grpc.BinStockServiceStub(self._channel)
        self._breaker = CircuitBreaker("warehouse-bin-stock")

    def get_bin_stock_info(self, sku: str, merchant_principal_id: str) -> StockInfo:
        request = fulfillment_pb2.CheckBinStockRequest(
            merchant_principal_id=merchant_principal_id, sku=sku
        )
        metadata = request_id_metadata()

        try:
            response = self._breaker.call(
                lambda: self._stub.CheckBinStock(request, timeout=5.0, metadata=metadata)
            )
        except (grpc.RpcError, CircuitOpenError) as error:
            logger.warning("warehouse did not answer for %s (%s); stock reported as none", sku, error)
            return _unknown_stock(sku)

        if not response.found:
            return _unknown_stock(sku)

        return StockInfo(
            sku=response.sku,
            bin_location=response.bin_location,
            available_quantity=response.available_stock,
            reserved_quantity=response.allocated_stock,
        )

    def check_bin_stock(self, sku: str, merchant_principal_id: str) -> Dict[str, Any]:
        request = fulfillment_pb2.CheckBinStockRequest(
            merchant_principal_id=merchant_principal_id, sku=sku
        )
        metadata = request_id_metadata()

        try:
            response = self._breaker.call(
                lambda: self._stub.CheckBinStock(request, timeout=5.0, metadata=metadata)
            )
        except CircuitOpenError as circuit_open:
            return {"success": False, "error": str(circuit_open)}
        except grpc.RpcError as rpc_error:
            return {"success": False, "error": f"gRPC CheckBinStock failed: {rpc_error.details()}"}

        if not response.found:
            return {"success": False, "error": f"warehouse holds no stock record for {sku}"}

        return {
            "success": True,
            "sku": response.sku,
            "product_name": response.product_name,
            "physical_stock": response.physical_stock,
            "allocated_stock": response.allocated_stock,
            "available_stock": response.available_stock,
            "bin_location": response.bin_location,
            "low_stock_warning": response.low_stock_warning,
        }

    def reserve_stock(self, sku: str, quantity: int, merchant_principal_id: str) -> Dict[str, Any]:
        request = fulfillment_pb2.ReserveStockRequest(
            merchant_principal_id=merchant_principal_id,
            sku=sku,
            quantity=quantity,
            order_number="",
        )
        metadata = request_id_metadata()

        try:
            response = self._breaker.call(
                lambda: self._stub.ReserveStock(request, timeout=5.0, metadata=metadata)
            )
        except CircuitOpenError as circuit_open:
            return {
                "success": False,
                "unavailable": True,
                "error": f"warehouse is not being called right now, so no stock was reserved: {circuit_open}",
            }
        except grpc.RpcError as rpc_error:
            return {
                "success": False,
                "unavailable": True,
                "error": f"warehouse is unreachable, so no stock was reserved: {rpc_error.details()}",
            }

        if response.HasField("error"):
            return {
                "success": False,
                "error": f"reservation refused ({response.error.error_code}): {response.error.message}",
            }

        return {
            "success": response.success,
            "bin_location": response.bin_location,
            "remaining_available": response.remaining_available,
        }

def _unknown_stock(sku: str) -> StockInfo:
    """What this service knows about a SKU warehouse cannot account for: nothing."""
    return StockInfo(sku=sku, bin_location="", available_quantity=0, reserved_quantity=0)
