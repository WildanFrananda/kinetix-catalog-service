import re
from decimal import Decimal, InvalidOperation
from typing import Mapping
from urllib.parse import urlparse

from core.application.dto import ProductChangesDTO
from core.domain.errors import InvalidInputError

_SKU = re.compile(r"^[^\s/]{1,64}$")
_ROUTE_NAMES = frozenset({"create", ".", ".."})
_ROUTED_ELSEWHERE = ("search", "suggest")
_WHOLE_NUMBER = re.compile(r"[0-9]{1,19}")
_LARGEST_ID = 9_223_372_036_854_775_807
_TITLE_LIMIT = 255
_IMAGE_URL_LIMIT = 200
_CENT = Decimal("0.01")
_LARGEST_PRICE = Decimal("9999999999.99")
_SETTLEMENT_CURRENCY = "IDR"
_HEAVIEST_GRAMS = 1_000_000
_NUL = "\x00"


class ProductFieldParser:
    @staticmethod
    def sku(value: object) -> str:
        text = ProductFieldParser._required_text("sku", value)
        if not _SKU.match(text):
            raise InvalidInputError("sku", "must be 1 to 64 characters with no spaces or slashes")
        if text in _ROUTE_NAMES or text.startswith(_ROUTED_ELSEWHERE):
            raise InvalidInputError(
                "sku",
                "must not be create, . or .., nor start with search or suggest: its product page could not be reached",
            )
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
        return ProductFieldParser._storable("description", value)

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
        return ProductFieldParser._storable("image_url", value)

    @staticmethod
    def weight_grams(value: object) -> int:
        if value is None:
            raise InvalidInputError("weight_grams", "is required: shipping is priced by weight")
        grams = ProductFieldParser._whole_number("weight_grams", value, "must be a positive whole number of grams")
        if grams <= 0:
            raise InvalidInputError("weight_grams", "must be a positive whole number of grams")
        if grams > _HEAVIEST_GRAMS:
            raise InvalidInputError("weight_grams", f"must be at most {_HEAVIEST_GRAMS} grams")
        return grams

    @staticmethod
    def category_id(value: object) -> int:
        if value is None:
            raise InvalidInputError("category_id", "is required")
        number = ProductFieldParser._whole_number("category_id", value, "must be a positive whole number")
        if number <= 0:
            raise InvalidInputError("category_id", "must be a positive whole number")
        if number > _LARGEST_ID:
            raise InvalidInputError("category_id", f"no category {number}")
        return number

    @staticmethod
    def is_active(value: object) -> bool:
        if not isinstance(value, bool):
            raise InvalidInputError("is_active", "must be true or false")
        return value

    @staticmethod
    def changes(data: Mapping[str, object]) -> ProductChangesDTO:
        fields = ProductFieldParser
        return ProductChangesDTO(
            sku=fields._required_text("sku", data["sku"]) if "sku" in data else None,
            title=fields.title(data["title"]) if "title" in data else None,
            description=fields.description(data["description"]) if "description" in data else None,
            price=fields.price(data["price"]) if "price" in data else None,
            currency=fields.currency(data["currency"]) if "currency" in data else None,
            image_url=fields.image_url(data["image_url"]) if "image_url" in data else None,
            category_id=fields.category_id(data["category_id"]) if "category_id" in data else None,
            is_active=fields.is_active(data["is_active"]) if "is_active" in data else None,
            weight_grams=fields.weight_grams(data["weight_grams"]) if "weight_grams" in data else None,
        )

    @staticmethod
    def _whole_number(field: str, value: object, reason: str) -> int:
        if isinstance(value, bool):
            raise InvalidInputError(field, reason)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and _WHOLE_NUMBER.fullmatch(value.strip()):
            return int(value.strip())
        raise InvalidInputError(field, reason)

    @staticmethod
    def _required_text(field: str, value: object) -> str:
        if value is None:
            raise InvalidInputError(field, "is required")
        if not isinstance(value, str):
            raise InvalidInputError(field, "must be text")
        text = value.strip()
        if not text:
            raise InvalidInputError(field, "must not be blank")
        return ProductFieldParser._storable(field, text)

    @staticmethod
    def _storable(field: str, text: str) -> str:
        if _NUL in text:
            raise InvalidInputError(field, "must not contain a NUL character")
        return text
