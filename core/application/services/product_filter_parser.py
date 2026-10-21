import re
from typing import Mapping, Optional

from core.application.dto import ProductFilterDTO
from core.domain.errors import InvalidInputError

_DEFAULT_PAGE_SIZE = 10
_LARGEST_PAGE_SIZE = 100
_LARGEST_PAGE = 10_000
_LONGEST_NUMBER = 9
_DIGITS = re.compile(r"[0-9]+")


class ProductFilterParser:
    @staticmethod
    def parse(query: Mapping[str, str]) -> ProductFilterDTO:
        return ProductFilterDTO(
            category_slug=ProductFilterParser._optional("category", query.get("category")),
            search_query=ProductFilterParser._optional("q", query.get("q")),
            page=ProductFilterParser._whole("page", query.get("page"), 1, _LARGEST_PAGE),
            page_size=ProductFilterParser._whole(
                "page_size", query.get("page_size"), _DEFAULT_PAGE_SIZE, _LARGEST_PAGE_SIZE
            ),
        )

    @staticmethod
    def _optional(field: str, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        if "\x00" in value:
            raise InvalidInputError(field, "must not contain a NUL character")
        return value

    @staticmethod
    def _whole(field: str, value: Optional[str], default: int, largest: int) -> int:
        if value is None or value == "":
            return default
        if not _DIGITS.fullmatch(value):
            raise InvalidInputError(field, "must be a positive whole number")
        if len(value) > _LONGEST_NUMBER:
            raise InvalidInputError(field, f"must be at most {largest}")
        number = int(value)
        if number < 1:
            raise InvalidInputError(field, "must be at least 1")
        if number > largest:
            raise InvalidInputError(field, f"must be at most {largest}")
        return number
