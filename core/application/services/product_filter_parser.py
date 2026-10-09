from typing import Mapping, Optional

from core.application.dto import ProductFilterDTO
from core.domain.errors import InvalidInputError

_DEFAULT_PAGE_SIZE = 10
_LARGEST_PAGE_SIZE = 100


class ProductFilterParser:
    @staticmethod
    def parse(query: Mapping[str, str]) -> ProductFilterDTO:
        return ProductFilterDTO(
            category_slug=ProductFilterParser._optional(query.get("category")),
            search_query=ProductFilterParser._optional(query.get("q")),
            page=ProductFilterParser._whole("page", query.get("page"), 1, None),
            page_size=ProductFilterParser._whole(
                "page_size", query.get("page_size"), _DEFAULT_PAGE_SIZE, _LARGEST_PAGE_SIZE
            ),
        )

    @staticmethod
    def _optional(value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        return value

    @staticmethod
    def _whole(field: str, value: Optional[str], default: int, largest: Optional[int]) -> int:
        if value is None or value == "":
            return default
        if not value.isdigit():
            raise InvalidInputError(field, "must be a positive whole number")
        number = int(value)
        if number < 1:
            raise InvalidInputError(field, "must be at least 1")
        if largest is not None and number > largest:
            raise InvalidInputError(field, f"must be at most {largest}")
        return number
