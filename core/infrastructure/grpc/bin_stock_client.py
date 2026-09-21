import logging
from typing import Optional

import grpc
from fulfillment.v1 import fulfillment_pb2, fulfillment_pb2_grpc

from core.domain.entities.stock_info import StockInfo
from core.domain.repositories import BinStockServicePort
from core.infrastructure.grpc.mesh_channel import mesh_channel
from core.infrastructure.grpc.required_env import required_env
from core.infrastructure.metrics import (
    GrpcClientMetricsInterceptor,
    declare_grpc_client_calls,
)
from core.infrastructure.resilience import CircuitBreaker, CircuitOpenError
from core.infrastructure.observability import request_id_metadata

logger = logging.getLogger(__name__)

METRICS_PEER = "kinetix-warehouse-service"

_SERVICE = fulfillment_pb2.DESCRIPTOR.services_by_name["BinStockService"]
declare_grpc_client_calls(METRICS_PEER, _SERVICE, ["CheckBinStock"])


class BinStockGrpcClient(BinStockServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host: str = target_host or required_env("WAREHOUSE_GRPC_URL")
        self._channel = grpc.intercept_channel(
            mesh_channel(self._target_host),
            GrpcClientMetricsInterceptor(METRICS_PEER),
        )
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
        except CircuitOpenError:
            logger.debug("warehouse is not being called right now; stock for %s is unknown", sku)
            return StockInfo.unknown(sku)
        except grpc.RpcError as rpc_error:
            logger.warning(
                "warehouse did not answer for %s (%s); stock reported as unknown",
                sku,
                rpc_error.details(),
            )
            return StockInfo.unknown(sku)

        if not response.found:
            return _no_stock_record(sku)

        return StockInfo(
            sku=response.sku,
            bin_location=response.bin_location,
            available_quantity=response.available_stock,
            reserved_quantity=response.allocated_stock,
        )


def _no_stock_record(sku: str) -> StockInfo:
    return StockInfo(sku=sku, bin_location="", available_quantity=0, reserved_quantity=0)
