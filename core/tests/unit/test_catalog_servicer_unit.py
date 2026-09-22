from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, cast

import grpc
import pytest
from catalog.v1 import catalog_pb2

from core.domain.entities import Category, Product
from core.infrastructure.grpc.catalog_servicer import CatalogServicer, MAX_PAGE
from core.tests.unit.fake_product_repository import FakeProductRepository

NOON = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
CATEGORY = Category(id=1, name="Footwear", slug="footwear")


def _ctx(context: "_Context") -> grpc.ServicerContext:
    return cast(grpc.ServicerContext, context)


class _Context:
    def __init__(self) -> None:
        self.aborted: Optional[str] = None

    def abort(self, code: object, details: str) -> None:
        self.aborted = details
        raise RuntimeError(details)


def _product(sku: str, when: datetime, active: bool = True, price: str = "750000.00") -> Product:
    return Product(
        id=None,
        sku=sku,
        title=f"Shoes {sku}",
        description="",
        price=Decimal(price),
        currency="IDR",
        image_url="",
        category=CATEGORY,
        merchant_principal_id="shop-1",
        is_active=active,
        updated_at=when,
    )


def _repo_with(*products: Product) -> FakeProductRepository:
    repo = FakeProductRepository()
    for p in products:
        repo.save(p)
        repo._store[p.sku] = p  # noqa: SLF001
    return repo


class TestChangedSince:
    def test_upserts_and_removals_are_separate(self) -> None:
        repo = _repo_with(
            _product("SHOE-1", NOON),
            _product("SHOE-2", NOON + timedelta(minutes=1), active=False),
        )
        servicer = CatalogServicer(repo)

        response = servicer.ChangedSince(catalog_pb2.ChangedSinceRequest(limit=10), _ctx(_Context()))

        assert [p.sku for p in response.upserted] == ["SHOE-1"]
        assert list(response.removed_skus) == ["SHOE-2"]

    def test_an_unset_cursor_means_the_beginning_not_the_epoch(self) -> None:
        repo = _repo_with(_product("SHOE-1", datetime(1969, 7, 20, tzinfo=timezone.utc)))
        servicer = CatalogServicer(repo)

        response = servicer.ChangedSince(catalog_pb2.ChangedSinceRequest(limit=10), _ctx(_Context()))

        assert [p.sku for p in response.upserted] == ["SHOE-1"]

    def test_the_page_is_capped_however_much_is_asked_for(self) -> None:
        repo = _repo_with(*[_product(f"SHOE-{n}", NOON + timedelta(seconds=n)) for n in range(5)])
        servicer = CatalogServicer(repo)

        servicer.ChangedSince(catalog_pb2.ChangedSinceRequest(limit=1_000_000), _ctx(_Context()))

        assert repo.last_changed_since_limit == MAX_PAGE, (
            "one consumer asking for the whole catalogue in a single call is how a read model "
            "takes down the service it reads from"
        )

    def test_the_cursor_comes_back_for_the_caller_to_resume_from(self) -> None:
        last = NOON + timedelta(minutes=2)
        repo = _repo_with(_product("SHOE-1", NOON), _product("SHOE-2", last))
        servicer = CatalogServicer(repo)

        response = servicer.ChangedSince(catalog_pb2.ChangedSinceRequest(limit=10), _ctx(_Context()))

        assert response.next.last_sku == "SHOE-2"
        assert response.next.updated_through.ToDatetime(tzinfo=timezone.utc) == last

    def test_has_more_is_reported(self) -> None:
        repo = _repo_with(*[_product(f"SHOE-{n}", NOON + timedelta(seconds=n)) for n in range(5)])
        servicer = CatalogServicer(repo)

        assert servicer.ChangedSince(
            catalog_pb2.ChangedSinceRequest(limit=2), _ctx(_Context())
        ).has_more is True
        assert servicer.ChangedSince(
            catalog_pb2.ChangedSinceRequest(limit=10), _ctx(_Context())
        ).has_more is False


class TestPriceConversion:
    @pytest.mark.parametrize(
        ("rupiah", "sen"),
        [
            ("0.00", 0),
            ("0.01", 1),
            ("750000.00", 75_000_000),
            ("1234567.89", 123_456_789),
            ("99999999.99", 9_999_999_999),
        ],
    )
    def test_money_goes_out_in_minor_units_exactly(self, rupiah: str, sen: int) -> None:
        repo = _repo_with(_product("SHOE-1", NOON, price=rupiah))
        servicer = CatalogServicer(repo)

        response = servicer.ChangedSince(catalog_pb2.ChangedSinceRequest(limit=10), _ctx(_Context()))

        assert response.upserted[0].price.amount_minor == sen
        assert response.upserted[0].price.currency == "IDR"


class TestGetProduct:
    def test_a_missing_product_is_found_false_not_an_error(self) -> None:
        servicer = CatalogServicer(FakeProductRepository())

        response = servicer.GetProduct(catalog_pb2.GetProductRequest(sku="NOPE"), _ctx(_Context()))

        assert response.found is False

    def test_a_product_comes_back_whole(self) -> None:
        repo = _repo_with(_product("SHOE-1", NOON))
        servicer = CatalogServicer(repo)

        response = servicer.GetProduct(catalog_pb2.GetProductRequest(sku="SHOE-1"), _ctx(_Context()))

        assert response.found is True
        assert response.product.sku == "SHOE-1"
        assert response.product.category_slug == "footwear"
        assert response.product.merchant_principal_id == "shop-1"

    def test_an_empty_sku_is_refused(self) -> None:
        servicer = CatalogServicer(FakeProductRepository())
        context = _Context()

        with pytest.raises(RuntimeError):
            servicer.GetProduct(catalog_pb2.GetProductRequest(sku=""), _ctx(context))

        assert context.aborted == "sku is required"


class TestCountProducts:
    def test_counts_what_is_on_sale(self) -> None:
        repo = _repo_with(
            _product("SHOE-1", NOON),
            _product("SHOE-2", NOON, active=False),
        )
        servicer = CatalogServicer(repo)

        response = servicer.CountProducts(catalog_pb2.CountProductsRequest(), _ctx(_Context()))

        assert response.total == 1
