import re
from typing import List, Optional
from core.domain.repositories import ProductRepository
from core.domain.entities import Category
from core.domain.errors import InvalidInputError

_NAME_LIMIT = 128
_SLUG = re.compile(r"^[-a-zA-Z0-9_]{1,128}$")

class CategoryService:
    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    def list_categories(self) -> List[Category]:
        return self._product_repo.find_all_categories()

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        return self._product_repo.find_category_by_id(category_id)

    def create_category(self, name: str, slug: str) -> Category:
        category = Category(id=None, name=_name(name), slug=_slug(slug))
        return self._product_repo.save_category(category)

    def update_category(self, category_id: int, name: str, slug: str) -> Optional[Category]:
        existing = self._product_repo.find_category_by_id(category_id)
        if not existing:
            return None
        category = Category(id=existing.id, name=_name(name), slug=_slug(slug))
        return self._product_repo.save_category(category)

    def delete_category(self, category_id: int) -> bool:
        return self._product_repo.delete_category(category_id)

def _name(value: str) -> str:
    text = value.strip()
    if not text:
        raise InvalidInputError("name", "must not be blank")
    if len(text) > _NAME_LIMIT:
        raise InvalidInputError("name", f"must be at most {_NAME_LIMIT} characters")
    return text

def _slug(value: str) -> str:
    if not _SLUG.match(value):
        raise InvalidInputError("slug", "must be 1 to 128 letters, digits, hyphens or underscores")
    return value
