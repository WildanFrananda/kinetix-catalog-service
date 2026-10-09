import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from core.domain.errors import InvalidInputError

_SKU = re.compile(r"^[^\s/]{1,64}$")
_TITLE_LIMIT = 255
_IMAGE_URL_LIMIT = 200
_CENT = Decimal("0.01")
_LARGEST_PRICE = Decimal("9999999999.99")
_SETTLEMENT_CURRENCY = "IDR"


class ProductFieldParser:
    @staticmethod
    def sku(value: object) -> str:
        text = ProductFieldParser._required_text("sku", value)
        if not _SKU.match(text):
            raise InvalidInputError("sku", "must be 1 to 64 characters with no spaces or slashes")
        return text

    @staticmethod
    def title(value: object) -> str:
        text = ProductFieldParser._required_text("title", value)
        if len(text) > _TITLE_LIMIT:
            raise InvalidInputError("title", f"must be at most {_TITLE_LIMIT} characters")
        return text

    @staticmethod
    def description(value: object) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise InvalidInputError("description", "must be text")
        return value

    @staticmethod
    def price(value: object) -> Decimal:
        if value is None:
            raise InvalidInputError("price", "is required")
        if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
            raise InvalidInputError("price", "must be a number")
        try:
            amount = Decimal(str(value).strip())
        except InvalidOperation:
            raise InvalidInputError("price", "must be a number") from None
        if not amount.is_finite():
            raise InvalidInputError("price", "must be a finite number")
        if amount <= 0:
            raise InvalidInputError("price", "must be more than zero")
        if amount != amount.quantize(_CENT):
            raise InvalidInputError("price", "must have at most two decimal places")
        if amount > _LARGEST_PRICE:
            raise InvalidInputError("price", f"must be at most {_LARGEST_PRICE}")
        return amount.quantize(_CENT)

    @staticmethod
    def currency(value: object) -> str:
        if value is None:
            return _SETTLEMENT_CURRENCY
        if value != _SETTLEMENT_CURRENCY:
            raise InvalidInputError("currency", f"must be {_SETTLEMENT_CURRENCY}")
        return _SETTLEMENT_CURRENCY

    @staticmethod
    def image_url(value: object) -> str:
        if value is None or value == "":
            return ""
        if not isinstance(value, str):
            raise InvalidInputError("image_url", "must be text")
        if len(value) > _IMAGE_URL_LIMIT:
            raise InvalidInputError("image_url", f"must be at most {_IMAGE_URL_LIMIT} characters")
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise InvalidInputError("image_url", "must be an http or https URL")
        return value

    @staticmethod
    def category_id(value: object) -> int:
        if value is None:
            raise InvalidInputError("category_id", "is required")
        if isinstance(value, bool):
            raise InvalidInputError("category_id", "must be a positive whole number")
        if isinstance(value, int):
            number = value
        elif isinstance(value, str) and value.strip().isdigit():
            number = int(value.strip())
        else:
            raise InvalidInputError("category_id", "must be a positive whole number")
        if number <= 0:
            raise InvalidInputError("category_id", "must be a positive whole number")
        return number

    @staticmethod
    def is_active(value: object) -> bool:
        if not isinstance(value, bool):
            raise InvalidInputError("is_active", "must be true or false")
        return value

    @staticmethod
    def _required_text(field: str, value: object) -> str:
        if value is None:
            raise InvalidInputError(field, "is required")
        if not isinstance(value, str):
            raise InvalidInputError(field, "must be text")
        text = value.strip()
        if not text:
            raise InvalidInputError(field, "must not be blank")
        return text
