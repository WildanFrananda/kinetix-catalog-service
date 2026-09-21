from typing import Set, Type

from fulfillment.v1 import fulfillment_pb2
from google.protobuf.message import Message
from identity.v1 import identity_pb2

from core.infrastructure.grpc.bin_stock_client import BinStockGrpcClient


def _fields(message: Type[Message]) -> Set[str]:
    return {field.name for field in message.DESCRIPTOR.fields}


class TestContractFields:
    def test_merchant_info_carries_identitys_decision(self) -> None:
        assert {"found", "may_sell", "merchant_principal_id", "store_name", "status"} <= _fields(
            identity_pb2.GetMerchantInfoResponse
        )

    def test_may_sell_is_a_decision_not_a_status(self) -> None:
        field = identity_pb2.GetMerchantInfoResponse.DESCRIPTOR.fields_by_name["may_sell"]
        assert field.type == field.TYPE_BOOL

    def test_merchant_info_is_asked_by_principal(self) -> None:
        assert "principal_id" in _fields(identity_pb2.GetMerchantInfoRequest)

    def test_every_merchant_status_this_service_names_still_exists(self) -> None:
        for name in (
            "MERCHANT_STATUS_UNSPECIFIED",
            "MERCHANT_STATUS_PENDING",
            "MERCHANT_STATUS_VERIFIED",
            "MERCHANT_STATUS_SUSPENDED",
            "MERCHANT_STATUS_CLOSED",
        ):
            assert hasattr(identity_pb2, name), name

    def test_bin_stock_request_and_response(self) -> None:
        assert {"merchant_principal_id", "sku"} <= _fields(fulfillment_pb2.CheckBinStockRequest)
        assert {"found", "sku", "bin_location", "available_stock", "allocated_stock"} <= _fields(
            fulfillment_pb2.CheckBinStockResponse
        )

    def test_catalog_asks_warehouse_nothing_else(self) -> None:
        rpcs = {name for name in dir(BinStockGrpcClient) if not name.startswith("_")}
        assert rpcs == {"get_bin_stock_info"}, rpcs
