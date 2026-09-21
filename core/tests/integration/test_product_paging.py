from decimal import Decimal
from typing import List

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.domain.entities import Category, Product
from core.infrastructure.repositories import DjangoProductRepository


def _make_products(repo: DjangoProductRepository, how_many: int) -> Category:
    cat = repo.save_category(Category(id=None, name="Footwear", slug="footwear"))
    for n in range(how_many):
        repo.save(
            Product(
                id=None,
                sku=f"SHOE-{n:03d}",
                title=f"Running shoes {n:03d}",
                description="",
                price=Decimal("750000.00"),
                currency="IDR",
                image_url="",
                category=cat,
            )
        )
    return cat


@pytest.mark.django_db
class TestProductPagingHappensInTheDatabase:
    def test_a_page_is_limited_by_sql(self) -> None:
        repo = DjangoProductRepository()
        _make_products(repo, 25)

        with CaptureQueriesContext(connection) as captured:
            page, total = repo.find_page(offset=0, limit=5)

        assert len(page) == 5
        assert total == 25

        selects = [q["sql"] for q in captured.captured_queries if "FROM \"products\"" in q["sql"]]
        assert selects, "expected at least one query against products"

        fetches = [sql for sql in selects if "COUNT(" not in sql.upper()]
        assert fetches, "expected a query that fetches rows"
        for sql in fetches:
            assert "LIMIT" in sql.upper(), (
                "the page must be limited by the database. Without LIMIT this fetches every "
                f"matching row and slices in Python. SQL was: {sql}"
            )

    def test_the_total_is_counted_by_sql(self) -> None:
        repo = DjangoProductRepository()
        _make_products(repo, 25)

        with CaptureQueriesContext(connection) as captured:
            _, total = repo.find_page(offset=0, limit=5)

        assert total == 25
        counts = [
            q["sql"] for q in captured.captured_queries if "COUNT(" in q["sql"].upper()
        ]
        assert counts, (
            "the total must be a COUNT in the database. Counting the length of a fetched list "
            "means fetching the whole catalogue to answer how big it is."
        )

    def test_the_work_does_not_grow_with_the_catalogue(self) -> None:
        repo = DjangoProductRepository()
        _make_products(repo, 60)

        with CaptureQueriesContext(connection) as captured:
            page, _ = repo.find_page(offset=0, limit=10)

        assert len(page) == 10
        fetches = [
            q["sql"]
            for q in captured.captured_queries
            if "FROM \"products\"" in q["sql"] and "COUNT(" not in q["sql"].upper()
        ]
        assert len(fetches) == 1, "one query for the page, not one per row"
        assert "LIMIT 10" in fetches[0].upper()

    def test_later_pages_return_later_products(self) -> None:
        repo = DjangoProductRepository()
        _make_products(repo, 25)

        first, total = repo.find_page(offset=0, limit=10)
        second, _ = repo.find_page(offset=10, limit=10)
        last, _ = repo.find_page(offset=20, limit=10)

        assert total == 25
        assert len(first) == 10 and len(second) == 10 and len(last) == 5

        skus: List[str] = [p.sku for p in first + second + last]
        assert len(set(skus)) == 25, "every product appears exactly once across the pages"

    def test_a_page_past_the_end_is_empty_not_an_error(self) -> None:
        repo = DjangoProductRepository()
        _make_products(repo, 3)

        page, total = repo.find_page(offset=100, limit=10)

        assert page == []
        assert total == 3, "the count still describes the whole result, not the empty page"

    def test_filters_apply_to_both_the_page_and_the_count(self) -> None:
        repo = DjangoProductRepository()
        cat = _make_products(repo, 5)
        repo.save(
            Product(
                id=None,
                sku="BOOT-001",
                title="Leather boots",
                description="",
                price=Decimal("900000.00"),
                currency="IDR",
                image_url="",
                category=cat,
            )
        )

        page, total = repo.find_page(search_query="Running", offset=0, limit=10)

        assert total == 5, "a count that ignores the filter tells the client a page size it will never see"
        assert all("Running" in p.title for p in page)

    def test_withdrawn_products_are_in_neither(self) -> None:
        repo = DjangoProductRepository()
        _make_products(repo, 4)
        removed = repo.find_by_sku("SHOE-001")
        assert removed is not None and removed.id is not None
        repo.delete(removed.id)

        page, total = repo.find_page(offset=0, limit=10)

        assert total == 3
        assert "SHOE-001" not in [p.sku for p in page]
