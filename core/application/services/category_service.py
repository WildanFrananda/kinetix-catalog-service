from typing import List, Optional
from core.domain.repositories import ProductRepository
from core.domain.entities import Category

class CategoryService:
    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    def list_categories(self) -> List[Category]:
        return self._product_repo.find_all_categories()

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        return self._product_repo.find_category_by_id(category_id)

    def create_category(self, name: str, slug: str) -> Category:
        category = Category(id=None, name=name, slug=slug)
        return self._product_repo.save_category(category)

    def update_category(self, category_id: int, name: str, slug: str) -> Optional[Category]:
        existing = self._product_repo.find_category_by_id(category_id)
        if not existing:
            return None
        category = Category(id=existing.id, name=name, slug=slug)
        return self._product_repo.save_category(category)

    def delete_category(self, category_id: int) -> bool:
        return self._product_repo.delete_category(category_id)
