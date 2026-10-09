from decimal import Decimal
from typing import Dict

import pytest

from core.application.services import ProductFieldParser, ProductFilterParser
from core.domain.errors import InvalidInputError


class TestProductFieldParserUnit:
    @pytest.mark.parametrize(
        "value",
        ["-5000", "0", "0.00", "10.001", "NaN", "Infinity", "abc", "", True, None, [], "10000000000.00"],
    )
    def test_a_price_that_cannot_be_sold_is_refused(self, value: object) -> None:
        with pytest.raises(InvalidInputError) as refused:
            ProductFieldParser.price(value)
        assert refused.value.field == "price"

    @pytest.mark.parametrize(
        ("value", "stored"),
        [("189000", Decimal("189000.00")), (189000.5, Decimal("189000.50")), ("0.01", Decimal("0.01"))],
    )
    def test_a_price_is_stored_to_the_cent(self, value: object, stored: Decimal) -> None:
        assert ProductFieldParser.price(value) == stored

    @pytest.mark.parametrize("value", ["USD", "idr", "", 360])
    def test_only_the_currency_order_settles_in_is_accepted(self, value: object) -> None:
        with pytest.raises(InvalidInputError) as refused:
            ProductFieldParser.currency(value)
        assert refused.value.field == "currency"

    def test_an_absent_currency_is_the_settlement_currency(self) -> None:
        assert ProductFieldParser.currency(None) == "IDR"

    @pytest.mark.parametrize("value", [None, "", "  ", "has space", "a/b", "x" * 65, 12])
    def test_an_unusable_sku_is_refused(self, value: object) -> None:
        with pytest.raises(InvalidInputError) as refused:
            ProductFieldParser.sku(value)
        assert refused.value.field == "sku"

    @pytest.mark.parametrize("value", ["false", "true", 0, 1, None])
    def test_is_active_must_be_a_boolean_not_text_that_reads_like_one(self, value: object) -> None:
        with pytest.raises(InvalidInputError) as refused:
            ProductFieldParser.is_active(value)
        assert refused.value.field == "is_active"

    @pytest.mark.parametrize("value", ["javascript:alert(1)", "not a url", "ftp://host/x", "https://" + "x" * 200])
    def test_an_image_url_must_be_http_and_fit_the_column(self, value: str) -> None:
        with pytest.raises(InvalidInputError) as refused:
            ProductFieldParser.image_url(value)
        assert refused.value.field == "image_url"

    @pytest.mark.parametrize("value", [None, 0, -3, True, "three", "1.5"])
    def test_a_category_id_must_be_a_positive_whole_number(self, value: object) -> None:
        with pytest.raises(InvalidInputError) as refused:
            ProductFieldParser.category_id(value)
        assert refused.value.field == "category_id"


class TestProductFilterParserUnit:
    def test_an_empty_query_is_the_first_page_of_ten(self) -> None:
        parsed = ProductFilterParser.parse({})
        assert (parsed.page, parsed.page_size, parsed.category_slug, parsed.search_query) == (1, 10, None, None)

    @pytest.mark.parametrize(
        ("query", "field"),
        [
            ({"page": "abc"}, "page"),
            ({"page": "0"}, "page"),
            ({"page": "-1"}, "page"),
            ({"page_size": "0"}, "page_size"),
            ({"page_size": "101"}, "page_size"),
            ({"page_size": "1e3"}, "page_size"),
        ],
    )
    def test_a_query_that_is_not_a_page_is_refused(self, query: Dict[str, str], field: str) -> None:
        with pytest.raises(InvalidInputError) as refused:
            ProductFilterParser.parse(query)
        assert refused.value.field == field
