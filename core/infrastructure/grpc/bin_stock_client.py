import os
import sys
from typing import Optional, Dict, Any

# Ensure generated protobuf modules can be imported
generated_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "generated"))
if generated_dir not in sys.path:
    sys.path.insert(0, generated_dir)

import grpc
from core.domain.entities import StockInfo
from core.domain.repositories import BinStockServicePort

try:
    from fulfillment.v1 import bin_stock_service_pb2, bin_stock_service_pb2_grpc
except ImportError:
    from core.infrastructure.grpc.generated.fulfillment.v1 import bin_stock_service_pb2, bin_stock_service_pb2_grpc

class BinStockGrpcClient(BinStockServicePort):
    def __init__(self, target_host: Optional[str] = None) -> None:
        self._target_host = target_host or os.environ.get("OMS_GRPC_HOST", "localhost:50051")

    def get_bin_stock_info(self, sku: str) -> StockInfo:
        try:
            channel = grpc.insecure_channel(self._target_host)
            stub = bin_stock_service_pb2_grpc.BinStockServiceStub(channel)

            req = bin_stock_service_pb2.GetBinStockInfoRequest(
                merchant_api_key=os.environ.get("MERCHANT_API_KEY", "INTERNAL_OMS_KEY"),
                sku=sku
            )

            res = stub.GetBinStockInfo(req, timeout=5)
            return StockInfo(
                sku=res.sku,
                bin_location=res.bin_location,
                available_quantity=res.available_quantity,
                reserved_quantity=res.reserved_quantity
            )
        except Exception:
            return StockInfo(
                sku=sku,
                bin_location="Bin A-01 (Offline Fallback)",
                available_quantity=25,
                reserved_quantity=0
            )

    def reserve_stock(self, sku: str, quantity: int) -> Dict[str, Any]:
        try:
            channel = grpc.insecure_channel(self._target_host)
            stub = bin_stock_service_pb2_grpc.BinStockServiceStub(channel)

            req = bin_stock_service_pb2.ReserveStockRequest(
                merchant_api_key=os.environ.get("MERCHANT_API_KEY", "INTERNAL_OMS_KEY"),
                sku=sku,
                requested_quantity=quantity
            )

            res = stub.ReserveStock(req, timeout=5)
            return {
                "success": res.success,
                "bin_location": res.bin_location,
                "remaining_available": res.remaining_available
            }
        except Exception as e:
            return {
                "success": False,
                "bin_location": "Bin A-01",
                "remaining_available": 0,
                "error": str(e)
            }
