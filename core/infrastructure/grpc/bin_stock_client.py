import os
import sys
from typing import Dict, Any, Optional

generated_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "generated"))
if generated_dir not in sys.path:
    sys.path.insert(0, generated_dir)

import grpc
from core.domain.repositories import BinStockServicePort
from core.domain.entities.stock_info import StockInfo

try:
    from fulfillment.v1 import bin_stock_service_pb2, bin_stock_service_pb2_grpc
except ImportError:
    from core.infrastructure.grpc.generated.fulfillment.v1 import bin_stock_service_pb2, bin_stock_service_pb2_grpc


class BinStockGrpcClient(BinStockServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host = target_host or os.environ.get("OMS_GRPC_HOST", "localhost:50051")
        self._channel = grpc.insecure_channel(self._target_host)
        self._stub = bin_stock_service_pb2_grpc.BinStockServiceStub(self._channel)

    def get_bin_stock_info(self, sku: str) -> StockInfo:
        try:
            req = bin_stock_service_pb2.CheckBinStockRequest(
                sku=sku
            )
            response = self._stub.CheckBinStock(req, timeout=5.0)
            return StockInfo(
                sku=response.sku,
                bin_location=response.bin_location,
                available_quantity=response.available_stock,
                reserved_quantity=response.allocated_stock,
            )
        except grpc.RpcError:
            return StockInfo(
                sku=sku,
                bin_location="N/A",
                available_quantity=0,
                reserved_quantity=0,
            )

    def check_bin_stock(self, sku: str) -> Dict[str, Any]:
        try:
            req = bin_stock_service_pb2.CheckBinStockRequest(
                sku=sku
            )
            response = self._stub.CheckBinStock(req, timeout=5.0)
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
        except grpc.RpcError as rpc_error:
            return {
                "success": False,
                "error": f"gRPC CheckBinStock failed: {rpc_error.details()}"
            }

    def reserve_stock(self, sku: str, quantity: int) -> Dict[str, Any]:
        try:
            req = bin_stock_service_pb2.ReserveStockRequest(
                sku=sku,
                quantity=quantity,
                order_number=""
            )
            response = self._stub.ReserveStock(req, timeout=5.0)

            if response.HasField("error"):
                return {
                    "success": False,
                    "error": f"Reservation failed ({response.error.code}): {response.error.message}"
                }

            return {
                "success": response.success,
                "bin_location": response.bin_location,
                "remaining_available": response.remaining_available
            }
        except grpc.RpcError:
            return {
                "success": True,
                "unavailable": True,
                "message": "gRPC server unreachable. Operating in offline reservation mode."
            }
