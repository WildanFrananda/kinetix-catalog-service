from dataclasses import replace
from decimal import Decimal
from typing import List

import psycopg
import pytest
from django.db import connection, transaction
from psycopg.rows import TupleRow

from core.domain.entities import Category, Product, ProductChangePage
from core.infrastructure.repositories import DjangoProductRepository


def _category(repo: DjangoProductRepository) -> Category:
    return repo.save_category(Category(id=None, name="Footwear", slug="footwear"))


def _save(repo: DjangoProductRepository, cat: Category, sku: str) -> Product:
    return repo.save(
        Product(
            id=None,
            sku=sku,
            title=f"Shoes {sku}",
            description="",
            price=Decimal("750000.00"),
            currency="IDR",
            image_url="",
            category=cat,
            merchant_principal_id="shop-1",
        )
    )


def _walk(repo: DjangoProductRepository, page: ProductChangePage, limit: int) -> List[str]:
    seen: List[str] = []
    for _ in range(20):
        assert page.next_transaction_id is not None
        page = repo.find_changed_after(page.next_transaction_id, page.next_last_sku, limit=limit)
        seen.extend(p.sku for p in page.upserted)
        seen.extend(page.removed_skus)
        if not page.has_more:
            return seen
    raise AssertionError("the cursor did not reach the end")


def _start() -> ProductChangePage:
    return ProductChangePage(
        upserted=[],
        removed_skus=[],
        next_updated_through=None,
        next_last_sku="",
        has_more=True,
        next_transaction_id=0,
    )


def _second_session() -> psycopg.Connection[TupleRow]:
    settings = connection.settings_dict
    return psycopg.connect(
        dbname=str(settings["NAME"]),
        user=str(settings["USER"]),
        password=str(settings["PASSWORD"]),
        host=str(settings["HOST"]),
        port=str(settings["PORT"]),
    )


@pytest.mark.django_db(transaction=True)
class TestTheTransactionCursor:
    def test_walks_every_product_once_in_the_order_they_were_written(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        for n in range(5):
            _save(repo, cat, f"SHOE-{n}")

        seen = _walk(repo, _start(), limit=2)

        assert seen == ["SHOE-0", "SHOE-1", "SHOE-2", "SHOE-3", "SHOE-4"]

    def test_a_late_commit_is_served_late_and_not_skipped(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        _save(repo, cat, "SHOE-EARLY")
        _save(repo, cat, "SHOE-LATER")
        caught_up = repo.find_changed_after(0, "", limit=10)
        assert caught_up.has_more is False

        with _second_session() as other:
            other.execute("UPDATE products SET title = 'Edited first' WHERE sku = 'SHOE-EARLY'")

            later = repo.find_by_sku("SHOE-LATER")
            assert later is not None
            repo.save(replace(later, title="Edited second"))

            assert caught_up.next_transaction_id is not None
            held = repo.find_changed_after(
                caught_up.next_transaction_id, caught_up.next_last_sku, limit=10
            )
            assert held.upserted == [], (
                "SHOE-LATER committed while SHOE-EARLY's transaction was still open; serving it "
                "would move the cursor past SHOE-EARLY before SHOE-EARLY is visible"
            )
            assert held.next_transaction_id == caught_up.next_transaction_id

            other.commit()

        assert caught_up.next_transaction_id is not None
        after = repo.find_changed_after(
            caught_up.next_transaction_id, caught_up.next_last_sku, limit=10
        )

        assert [p.sku for p in after.upserted] == ["SHOE-EARLY", "SHOE-LATER"]

    def test_one_transaction_is_paged_by_sku_without_losing_any(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        with transaction.atomic():
            for sku in ("SHOE-C", "SHOE-A", "SHOE-B"):
                _save(repo, cat, sku)

        first = repo.find_changed_after(0, "", limit=2)
        second = _walk(repo, first, limit=2)

        assert [p.sku for p in first.upserted] == ["SHOE-A", "SHOE-B"]
        assert first.has_more is True
        assert second == ["SHOE-C"]

    def test_a_product_changed_again_moves_to_the_end(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        first = _save(repo, cat, "SHOE-1")
        _save(repo, cat, "SHOE-2")
        repo.save(replace(first, title="Renamed"))

        page = repo.find_changed_after(0, "", limit=10)

        assert [p.sku for p in page.upserted] == ["SHOE-2", "SHOE-1"]
        assert page.upserted[1].title == "Renamed"

    def test_a_withdrawn_product_is_a_removal(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        _save(repo, cat, "SHOE-KEPT")
        gone = _save(repo, cat, "SHOE-GONE")
        assert gone.id is not None
        caught_up = repo.find_changed_after(0, "", limit=10)
        repo.delete(gone.id)

        assert caught_up.next_transaction_id is not None
        after = repo.find_changed_after(
            caught_up.next_transaction_id, caught_up.next_last_sku, limit=10
        )

        assert after.removed_skus == ["SHOE-GONE"]
        assert after.upserted == []


@pytest.mark.django_db(transaction=True)
class TestACategoryChangeReachesTheFeed:
    def _caught_up(self, repo: DjangoProductRepository) -> ProductChangePage:
        page = repo.find_changed_after(0, "", limit=100)
        assert page.has_more is False

        return page

    def _after(self, repo: DjangoProductRepository, cursor: ProductChangePage) -> ProductChangePage:
        assert cursor.next_transaction_id is not None

        return repo.find_changed_after(cursor.next_transaction_id, cursor.next_last_sku, limit=100)

    def test_a_new_slug_sends_every_product_filed_under_it_again(self) -> None:
        repo = DjangoProductRepository()
        shoes = _category(repo)
        bags = repo.save_category(Category(id=None, name="Bags", slug="bags"))
        _save(repo, shoes, "SHOE-1")
        _save(repo, shoes, "SHOE-2")
        _save(repo, bags, "BAG-1")
        caught_up = self._caught_up(repo)

        repo.save_category(replace(shoes, slug="sneakers"))

        after = self._after(repo, caught_up)
        assert [p.sku for p in after.upserted] == ["SHOE-1", "SHOE-2"]
        assert {p.category.slug for p in after.upserted} == {"sneakers"}
        assert after.next_transaction_id is not None and caught_up.next_transaction_id is not None
        assert after.next_transaction_id > caught_up.next_transaction_id

    def test_a_new_name_sends_them_again_too(self) -> None:
        repo = DjangoProductRepository()
        shoes = _category(repo)
        _save(repo, shoes, "SHOE-1")
        caught_up = self._caught_up(repo)

        repo.save_category(replace(shoes, name="Sneakers"))

        after = self._after(repo, caught_up)
        assert [p.category.name for p in after.upserted] == ["Sneakers"]

    def test_a_withdrawn_product_under_a_renamed_category_is_reported_removed_again(self) -> None:
        repo = DjangoProductRepository()
        shoes = _category(repo)
        gone = _save(repo, shoes, "SHOE-GONE")
        assert gone.id is not None
        repo.delete(gone.id)
        caught_up = self._caught_up(repo)

        repo.save_category(replace(shoes, slug="sneakers"))

        after = self._after(repo, caught_up)
        assert after.removed_skus == ["SHOE-GONE"]
        assert after.upserted == []

    def test_a_category_saved_unchanged_sends_nothing(self) -> None:
        repo = DjangoProductRepository()
        shoes = _category(repo)
        _save(repo, shoes, "SHOE-1")
        caught_up = self._caught_up(repo)

        repo.save_category(shoes)

        after = self._after(repo, caught_up)
        assert after.upserted == [] and after.removed_skus == []

    def test_the_products_are_stamped_by_the_transaction_that_renamed_the_category(self) -> None:
        repo = DjangoProductRepository()
        shoes = _category(repo)
        _save(repo, shoes, "SHOE-1")

        with transaction.atomic():
            repo.save_category(replace(shoes, slug="sneakers"))
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT change_transaction_id = pg_current_xact_id() FROM products WHERE sku = %s",
                    ["SHOE-1"],
                )
                stamped = cursor.fetchone()

        assert stamped == (True,)

    def test_a_rename_rolled_back_leaves_the_products_as_they_were(self) -> None:
        repo = DjangoProductRepository()
        shoes = _category(repo)
        _save(repo, shoes, "SHOE-1")
        caught_up = self._caught_up(repo)

        with pytest.raises(RuntimeError):
            with transaction.atomic():
                repo.save_category(replace(shoes, slug="sneakers"))
                raise RuntimeError("the admin's request failed after the rename")

        after = self._after(repo, caught_up)
        assert after.upserted == []
        assert repo.find_category_by_id(shoes.id or 0) == shoes
