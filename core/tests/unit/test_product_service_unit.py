from decimal import Decimal
from typing import Dict
import pytest
from core.domain.entities import Product, Category, StockStatus
from core.domain.errors import (
    IdentityUnavailableError,
    InvalidInputError,
    MerchantMayNotSellError,
    ProductNotOwnedError,
)
from core.application.dto import ProductFilterDTO
from core.application.services import ProductService
from core.application.services.category_service import CategoryService
from core.tests.unit.fake_product_repository import FakeProductRepository
from core.tests.unit.fake_bin_stock_service_port import FakeBinStockServicePort
from core.tests.unit.fake_identity_service_port import FakeIdentityServicePort
from core.tests.unit.fake_unreachable_bin_stock_service_port import (
    FakeUnreachableBinStockServicePort,
)

class TestProductServiceUnit:
    def test_list_products_returns_paginated_summaries(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()

        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=port, identity_port=FakeIdentityServicePort())
        res = service.list_products(ProductFilterDTO(page=1, page_size=10))

        assert res.count == 1
        assert res.results[0].sku == "SKU-1"

    def test_get_product_detail_returns_warehouse_stock(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()

        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=port, identity_port=FakeIdentityServicePort())
        detail = service.get_product_detail("SKU-1")

        assert detail is not None
        assert detail.sku == "SKU-1"
        assert detail.warehouse_stock.bin_location == "Bin A-04"

    def test_create_product_success(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()

        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        service = ProductService(product_repo=repo, bin_stock_port=port, identity_port=FakeIdentityServicePort())
        product = service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
            "sku": "SHOES-RUN-42",
            "title": "Running Shoes 42",
            "description": "Pro running shoes",
            "price": "500000.00",
            "category_id": cat.id,

            "weight_grams": 250
        })

        assert product.id is not None
        assert product.sku == "SHOES-RUN-42"
        assert product.merchant_principal_id == "3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3"

    def test_update_product_idor_protection_rejects_other_merchant(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()
        cat = repo.save_category(Category(id=1, name="Shoes", slug="shoes"))

        service = ProductService(product_repo=repo, bin_stock_port=port, identity_port=FakeIdentityServicePort())
        p = service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
            "sku": "SHOES-50",
            "title": "Merchant 50 Product",
            "price": "100000.00",
            "category_id": cat.id,

            "weight_grams": 250
        })

        assert p.id is not None
        with pytest.raises(ProductNotOwnedError, match="Product does not belong to this merchant"):
            service.update_product(product_id=p.id, merchant_principal_id="9f1d4a3e-1c62-4d0a-9a7b-2f5c8e0b41d7", data={"title": "Hacked Title"})

    def test_delete_product_idor_protection_rejects_other_merchant(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()
        cat = repo.save_category(Category(id=1, name="Shoes", slug="shoes"))

        service = ProductService(product_repo=repo, bin_stock_port=port, identity_port=FakeIdentityServicePort())
        p = service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
            "sku": "SHOES-50",
            "title": "Merchant 50 Product",
            "price": "100000.00",
            "category_id": cat.id,

            "weight_grams": 250
        })

        assert p.id is not None
        with pytest.raises(ProductNotOwnedError, match="Product does not belong to this merchant"):
            service.delete_product(product_id=p.id, merchant_principal_id="9f1d4a3e-1c62-4d0a-9a7b-2f5c8e0b41d7")

    def test_unreachable_warehouse_lists_stock_as_unknown_not_zero(self) -> None:
        """The estate's house bug: an outage rendered as a confident 'out of stock'."""
        repo = FakeProductRepository()
        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=FakeUnreachableBinStockServicePort(), identity_port=FakeIdentityServicePort())
        summary = service.list_products(ProductFilterDTO(page=1, page_size=10)).results[0]

        assert summary.available_stock is None
        assert summary.is_in_stock is None
        assert summary.stock_status is StockStatus.UNKNOWN

    def test_unreachable_warehouse_details_stock_as_unknown_not_zero(self) -> None:
        repo = FakeProductRepository()
        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=FakeUnreachableBinStockServicePort(), identity_port=FakeIdentityServicePort())
        detail = service.get_product_detail("SKU-1")

        assert detail is not None
        assert detail.warehouse_stock.available_quantity is None
        assert detail.warehouse_stock.bin_location is None
        assert detail.warehouse_stock.stock_status is StockStatus.UNKNOWN

    def test_a_warehouse_that_answers_zero_is_out_of_stock_not_unknown(self) -> None:
        """The other half of the distinction: a real sell-out must still read as a real zero."""
        repo = FakeProductRepository()
        cat = Category(id=1, name="Apparel", slug="apparel")
        repo.save(Product(id=None, sku="SKU-1", title="Tee 1", description="Desc", price=Decimal("100.00"), currency="IDR", image_url="", category=cat))

        service = ProductService(product_repo=repo, bin_stock_port=FakeBinStockServicePort(available_quantity=0), identity_port=FakeIdentityServicePort())
        summary = service.list_products(ProductFilterDTO(page=1, page_size=10)).results[0]

        assert summary.available_stock == 0
        assert summary.is_in_stock is False
        assert summary.stock_status is StockStatus.OUT_OF_STOCK

    def test_identity_outage_is_not_reported_as_an_unverified_merchant(self) -> None:
        """MerchantMayNotSellError becomes HTTP 403. An outage is not that."""
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        service = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort(unavailable=True),
        )

        with pytest.raises(IdentityUnavailableError):
            service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
                "sku": "SHOES-RUN-42",
                "title": "Running Shoes 42",
                "price": "500000.00",
                "category_id": cat.id,

                "weight_grams": 250
            })

    @pytest.mark.parametrize(
        "identity,expected",
        [
            (
                FakeIdentityServicePort(status="pending", may_sell=False),
                "does not permit this merchant to trade",
            ),
            (FakeIdentityServicePort(status=None), "knows no merchant"),
        ],
        ids=["identity says no", "identity has no such merchant"],
    )
    def test_a_real_negative_from_identity_is_still_a_permission_error(
        self, identity: FakeIdentityServicePort, expected: str
    ) -> None:
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        service = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=identity,
        )

        with pytest.raises(MerchantMayNotSellError, match=expected):
            service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
                "sku": "SHOES-RUN-42",
                "title": "Running Shoes 42",
                "price": "500000.00",
                "category_id": cat.id,

                "weight_grams": 250
            })

    def test_a_standing_catalog_never_heard_of_is_identitys_to_allow(self) -> None:
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))

        service = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort(status="on_probation", may_sell=True),
        )

        product = service.create_product(
            merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3",
            data={
                "sku": "SHOES-RUN-42",
                "title": "Running Shoes 42",
                "price": "500000.00",
                "category_id": cat.id,

                "weight_grams": 250,
            },
        )

        assert product.id is not None

    def test_the_tenant_key_is_the_merchant_identity_names_not_the_token_subject(self) -> None:
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        token_subject = "3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3"
        merchant = "8a1f0c62-9d47-4b3e-b0a5-1e7c2f4d6b90"

        service = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort(merchant_principal_id=merchant),
        )

        product = service.create_product(
            merchant_principal_id=token_subject,
            data={
                "sku": "SHOES-RUN-42",
                "title": "Running Shoes 42",
                "price": "500000.00",
                "category_id": cat.id,

                "weight_grams": 250,
            },
        )

        assert product.merchant_principal_id == merchant
        assert product.merchant_principal_id != token_subject

    def test_identity_outage_blocks_update_and_delete_too(self) -> None:
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=1, name="Shoes", slug="shoes"))
        service = ProductService(product_repo=repo, bin_stock_port=FakeBinStockServicePort(), identity_port=FakeIdentityServicePort())
        created = service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
            "sku": "SHOES-50",
            "title": "Merchant 50 Product",
            "price": "100000.00",
            "category_id": cat.id,

            "weight_grams": 250
        })

        assert created.id is not None
        offline = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort(unavailable=True),
        )

        with pytest.raises(IdentityUnavailableError):
            offline.update_product(product_id=created.id, merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={"title": "New"})
        with pytest.raises(IdentityUnavailableError):
            offline.delete_product(product_id=created.id, merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3")

    def test_category_crud_operations(self) -> None:
        repo = FakeProductRepository()
        cat_service = CategoryService(product_repo=repo)

        cat = cat_service.create_category(name="Gadgets", slug="gadgets")
        assert cat.id is not None
        assert cat.name == "Gadgets"

        updated = cat_service.update_category(category_id=cat.id, name="Smart Gadgets", slug="smart-gadgets")
        assert updated is not None
        assert updated.name == "Smart Gadgets"

        deleted = cat_service.delete_category(cat.id)
        assert deleted is True

    def test_a_product_is_not_created_without_its_weight(self) -> None:
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        service = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort()
        )

        with pytest.raises(InvalidInputError) as refused:
            service.create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data={
                "sku": "SHOES-RUN-43",
                "title": "Running Shoes 43",
                "price": "500000.00",
                "category_id": cat.id
            })

        assert refused.value.field == "weight_grams"

    def test_a_product_without_a_weight_gets_one_by_update_and_keeps_it(self) -> None:
        repo = FakeProductRepository()
        cat = repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        legacy = repo.save(Product(
            id=None,
            sku="SHOES-OLD-41",
            title="Old Shoes 41",
            description="",
            price=Decimal("300000.00"),
            currency="IDR",
            image_url="",
            category=cat,
            merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3"
        ))
        service = ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort()
        )
        assert legacy.id is not None
        assert legacy.weight_grams is None

        weighed = service.update_product(legacy.id, "3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", {"weight_grams": "1100"})
        retitled = service.update_product(legacy.id, "3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", {"title": "Old Shoes"})

        assert weighed is not None and weighed.weight_grams == 1100
        assert retitled is not None and retitled.weight_grams == 1100


class TestTheBodyIsCheckedFirst:
    def _shelved(self) -> FakeProductRepository:
        repo = FakeProductRepository()
        repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        return repo

    def _offline(self, repo: FakeProductRepository) -> ProductService:
        return ProductService(
            product_repo=repo,
            bin_stock_port=FakeBinStockServicePort(),
            identity_port=FakeIdentityServicePort(unavailable=True),
        )

    @pytest.mark.parametrize(
        ("field", "value"),
        [("sku", -1), ("title", -1), ("price", "-1"), ("category_id", -1), ("category_id", 999), ("weight_grams", -1)],
    )
    def test_a_bad_create_is_a_bad_body_even_while_identity_is_down(self, field: str, value: object) -> None:
        repo = self._shelved()
        body: Dict[str, object] = {
            "sku": "SHOES-1",
            "title": "Shoes",
            "price": "1000.00",
            "category_id": 1,
            "weight_grams": 250,
        }
        body[field] = value

        with pytest.raises(InvalidInputError) as refused:
            self._offline(repo).create_product(merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", data=body)

        assert refused.value.field == field

    @pytest.mark.parametrize(
        ("field", "value"),
        [("price", "abc"), ("category_id", 999), ("is_active", "yes"), ("weight_grams", "²")],
    )
    def test_a_bad_update_is_a_bad_body_even_while_identity_is_down(self, field: str, value: object) -> None:
        repo = self._shelved()
        online = ProductService(product_repo=repo, bin_stock_port=FakeBinStockServicePort(), identity_port=FakeIdentityServicePort())
        created = online.create_product(
            merchant_principal_id="3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3",
            data={"sku": "SHOES-2", "title": "Shoes", "price": "1000.00", "category_id": 1, "weight_grams": 250},
        )

        with pytest.raises(InvalidInputError) as refused:
            self._offline(repo).update_product(created.id or 0, "3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3", {field: value})

        assert refused.value.field == field


class TestASkuIsPermanent:
    MERCHANT = "3c9a77b1-58de-4a01-8f2e-6d4b19c0a8f3"

    def _created(self, repo: FakeProductRepository) -> Product:
        repo.save_category(Category(id=None, name="Shoes", slug="shoes"))
        service = ProductService(product_repo=repo, bin_stock_port=FakeBinStockServicePort(), identity_port=FakeIdentityServicePort())
        return service.create_product(
            merchant_principal_id=self.MERCHANT,
            data={"sku": "SHOES-50", "title": "Shoes", "price": "1000.00", "category_id": 1, "weight_grams": 250},
        )

    def test_a_sku_cannot_change_once_the_product_exists(self) -> None:
        repo = FakeProductRepository()
        created = self._created(repo)
        service = ProductService(product_repo=repo, bin_stock_port=FakeBinStockServicePort(), identity_port=FakeIdentityServicePort())

        with pytest.raises(InvalidInputError) as refused:
            service.update_product(created.id or 0, self.MERCHANT, {"sku": "SHOES-51", "title": "Renamed"})

        assert refused.value.field == "sku"
        assert repo.find_by_id(created.id or 0) == created
        assert repo.find_by_sku("SHOES-51") is None

    def test_restating_the_same_sku_is_not_a_change(self) -> None:
        repo = FakeProductRepository()
        created = self._created(repo)
        service = ProductService(product_repo=repo, bin_stock_port=FakeBinStockServicePort(), identity_port=FakeIdentityServicePort())

        updated = service.update_product(created.id or 0, self.MERCHANT, {"sku": "SHOES-50", "title": "Renamed"})

        assert updated is not None
        assert (updated.sku, updated.title) == ("SHOES-50", "Renamed")

class TestStockIsAskedForOnce:
    def _page_of(self, repo: FakeProductRepository, skus: list[str]) -> None:
        cat = Category(id=1, name="Apparel", slug="apparel")
        for sku in skus:
            repo.save(
                Product(
                    id=None,
                    sku=sku,
                    title=f"Tee {sku}",
                    description="Desc",
                    price=Decimal("100.00"),
                    currency="IDR",
                    image_url="",
                    category=cat,
                )
            )

    def test_a_page_of_products_is_one_call(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()
        self._page_of(repo, ["SKU-1", "SKU-2", "SKU-3"])

        service = ProductService(product_repo=repo, bin_stock_port=port, identity_port=FakeIdentityServicePort())
        result = service.list_products(ProductFilterDTO(page=1, page_size=10))

        assert len(result.results) == 3
        assert len(port.batches_asked) == 1, (
            "one call per merchant; a list of one-sku batches means the fan-out came back"
        )
        assert sorted(port.batches_asked[0]) == ["SKU-1", "SKU-2", "SKU-3"]

    def test_an_empty_page_asks_nothing(self) -> None:
        repo = FakeProductRepository()
        port = FakeBinStockServicePort()

        service = ProductService(product_repo=repo, bin_stock_port=port, identity_port=FakeIdentityServicePort())
        result = service.list_products(ProductFilterDTO(page=1, page_size=10))

        assert result.count == 0
        assert port.batches_asked == []

    def test_a_warehouse_that_cannot_answer_leaves_stock_unknown(self) -> None:
        repo = FakeProductRepository()
        port = FakeUnreachableBinStockServicePort()
        self._page_of(repo, ["SKU-1", "SKU-2"])

        service = ProductService(product_repo=repo, bin_stock_port=port, identity_port=FakeIdentityServicePort())
        result = service.list_products(ProductFilterDTO(page=1, page_size=10))

        for summary in result.results:
            assert summary.available_stock is None, (
                "an unanswered warehouse is not a shop with nothing in it"
            )
            assert summary.is_in_stock is None
