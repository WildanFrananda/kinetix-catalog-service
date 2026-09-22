from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

import pytest

from core.domain.entities import Category, Product
from core.infrastructure.models import ProductModel
from core.infrastructure.repositories import DjangoProductRepository

NOON = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


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


def _stamp(sku: str, when: datetime) -> None:
    ProductModel.objects.filter(sku=sku).update(updated_at=when)


@pytest.mark.django_db
class TestTheCursorWalk:
    def test_walks_the_whole_catalogue_from_an_empty_cursor(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        for n in range(5):
            _save(repo, cat, f"SHOE-{n}")
            _stamp(f"SHOE-{n}", NOON + timedelta(minutes=n))

        page = repo.find_changed_since(limit=10)

        assert [p.sku for p in page.upserted] == ["SHOE-0", "SHOE-1", "SHOE-2", "SHOE-3", "SHOE-4"]
        assert page.has_more is False

    def test_resumes_without_repeating_or_skipping(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        for n in range(5):
            _save(repo, cat, f"SHOE-{n}")
            _stamp(f"SHOE-{n}", NOON + timedelta(minutes=n))

        seen: List[str] = []
        cursor_at, cursor_sku = None, ""
        for _ in range(10):  # bounded: a cursor that does not advance must not hang the test
            page = repo.find_changed_since(cursor_at, cursor_sku, limit=2)
            seen.extend(p.sku for p in page.upserted)
            cursor_at, cursor_sku = page.next_updated_through, page.next_last_sku
            if not page.has_more:
                break

        assert seen == ["SHOE-0", "SHOE-1", "SHOE-2", "SHOE-3", "SHOE-4"]
        assert len(seen) == len(set(seen))

    def test_two_products_written_in_the_same_instant_are_not_lost(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        for sku in ("SHOE-A", "SHOE-B", "SHOE-C"):
            _save(repo, cat, sku)
            _stamp(sku, NOON)

        first = repo.find_changed_since(limit=2)
        assert [p.sku for p in first.upserted] == ["SHOE-A", "SHOE-B"]
        assert first.has_more is True

        second = repo.find_changed_since(
            first.next_updated_through, first.next_last_sku, limit=2
        )

        assert [p.sku for p in second.upserted] == ["SHOE-C"], (
            "the third product shares its timestamp with the first two; a cursor on the "
            "timestamp alone would skip it or loop on it"
        )
        assert second.has_more is False

    def test_the_cursor_terminates_on_a_table_of_identical_timestamps(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        for n in range(7):
            _save(repo, cat, f"SHOE-{n}")
            _stamp(f"SHOE-{n}", NOON)

        seen: List[str] = []
        cursor_at, cursor_sku = None, ""
        for _ in range(20):
            page = repo.find_changed_since(cursor_at, cursor_sku, limit=2)
            seen.extend(p.sku for p in page.upserted)
            cursor_at, cursor_sku = page.next_updated_through, page.next_last_sku
            if not page.has_more:
                break

        assert len(seen) == 7 and len(set(seen)) == 7

    def test_a_withdrawn_product_is_a_removal_not_an_absence(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        kept = _save(repo, cat, "SHOE-KEPT")
        gone = _save(repo, cat, "SHOE-GONE")
        assert gone.id is not None
        repo.delete(gone.id)

        page = repo.find_changed_since(limit=10)

        assert "SHOE-GONE" in page.removed_skus
        assert [p.sku for p in page.upserted] == [kept.sku]

    def test_an_edited_product_comes_round_again(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        _save(repo, cat, "SHOE-1")
        _stamp("SHOE-1", NOON)

        caught_up = repo.find_changed_since(limit=10)
        assert caught_up.has_more is False

        _stamp("SHOE-1", NOON + timedelta(hours=1))
        after = repo.find_changed_since(
            caught_up.next_updated_through, caught_up.next_last_sku, limit=10
        )

        assert [p.sku for p in after.upserted] == ["SHOE-1"], (
            "an edit has to reach the consumer, which is the whole reason updated_at exists"
        )

    def test_an_empty_page_leaves_the_cursor_where_it_was(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        _save(repo, cat, "SHOE-1")
        _stamp("SHOE-1", NOON)

        first = repo.find_changed_since(limit=10)
        second = repo.find_changed_since(first.next_updated_through, first.next_last_sku, limit=10)

        assert second.upserted == [] and second.removed_skus == []
        assert second.next_updated_through == first.next_updated_through
        assert second.next_last_sku == first.next_last_sku

    def test_has_more_is_answered_by_the_same_query_as_the_page(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        for n in range(3):
            _save(repo, cat, f"SHOE-{n}")
            _stamp(f"SHOE-{n}", NOON + timedelta(minutes=n))

        assert repo.find_changed_since(limit=2).has_more is True
        assert repo.find_changed_since(limit=3).has_more is False
        assert repo.find_changed_since(limit=99).has_more is False

    def test_the_count_is_of_products_on_sale(self) -> None:
        repo = DjangoProductRepository()
        cat = _category(repo)
        _save(repo, cat, "SHOE-1")
        gone = _save(repo, cat, "SHOE-2")
        assert gone.id is not None
        repo.delete(gone.id)

        assert repo.count_active_products() == 1, (
            "a consumer compares its index against this; counting withdrawn products would make "
            "a correct index look short"
        )
