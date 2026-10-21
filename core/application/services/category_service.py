import re
from typing import List, Optional
from core.domain.repositories import ProductRepository
from core.domain.entities import Category
from core.domain.errors import InvalidInputError

_NAME_LIMIT = 128
_SLUG = re.compile(r"[-a-zA-Z0-9_]{1,128}")

class CategoryService:
    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    def list_categories(self) -> List[Category]:
        return self._product_repo.find_all_categories()

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        return self._product_repo.find_category_by_id(category_id)

    def create_category(self, name: object, slug: object) -> Category:
        category = Category(id=None, name=_name(name), slug=_slug(slug))
        return self._product_repo.save_category(category)

    def update_category(self, category_id: int, name: object, slug: object) -> Optional[Category]:
        named = _name(name)
        slugged = _slug(slug)

        existing = self._product_repo.find_category_by_id(category_id)
        if not existing:
            return None

        return self._product_repo.save_category(Category(id=existing.id, name=named, slug=slugged))

    def delete_category(self, category_id: int) -> bool:
        return self._product_repo.delete_category(category_id)

def _text(field: str, value: object) -> str:
    if value is None:
        raise InvalidInputError(field, "is required")
    if not isinstance(value, str):
        raise InvalidInputError(field, "must be text")
    if "\x00" in value:
        raise InvalidInputError(field, "must not contain a NUL character")
    return value

def _name(value: object) -> str:
    text = _text("name", value).strip()
    if not text:
        raise InvalidInputError("name", "must not be blank")
    if len(text) > _NAME_LIMIT:
        raise InvalidInputError("name", f"must be at most {_NAME_LIMIT} characters")
    return text

def _slug(value: object) -> str:
    text = _text("slug", value)
    if not _SLUG.fullmatch(text):
        raise InvalidInputError("slug", "must be 1 to 128 letters, digits, hyphens or underscores")
    return text
