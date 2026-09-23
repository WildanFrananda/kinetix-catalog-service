from typing import Set, Type

from catalog.v1 import catalog_pb2
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

    def test_batch_request_and_response(self) -> None:
        assert {"merchant_principal_id", "skus"} <= _fields(
            fulfillment_pb2.CheckBinStockBatchRequest
        )
        assert {"items"} <= _fields(fulfillment_pb2.CheckBinStockBatchResponse)

    def test_catalog_asks_warehouse_nothing_else(self) -> None:
        rpcs = {name for name in dir(BinStockGrpcClient) if not name.startswith("_")}
        assert rpcs == {"get_bin_stock_info", "get_bin_stock_for"}, rpcs


class TestCatalogContractThisServiceServes:
    def test_a_product_carries_what_a_read_model_needs(self) -> None:
        assert {
            "sku",
            "merchant_principal_id",
            "title",
            "description",
            "price",
            "image_url",
            "category_slug",
            "category_name",
            "updated_at",
        } <= _fields(catalog_pb2.Product)

    def test_price_is_the_shared_money_type(self) -> None:
        field = catalog_pb2.Product.DESCRIPTOR.fields_by_name["price"]
        assert field.message_type is not None
        assert field.message_type.full_name == "common.v1.Money"
        assert {"amount_minor", "currency"} <= {f.name for f in field.message_type.fields}

    def test_the_cursor_has_both_halves(self) -> None:
        assert {"updated_through", "last_sku"} <= _fields(catalog_pb2.Cursor)

    def test_removals_are_explicit(self) -> None:
        assert "removed_skus" in _fields(catalog_pb2.ChangedSinceResponse)
        field = catalog_pb2.ChangedSinceResponse.DESCRIPTOR.fields_by_name["removed_skus"]
        assert field.is_repeated

    def test_the_service_still_offers_what_the_servicer_implements(self) -> None:
        service = catalog_pb2.DESCRIPTOR.services_by_name["CatalogService"]
        assert {"ChangedSince", "GetProduct", "CountProducts"} <= {
            method.name for method in service.methods
        }
