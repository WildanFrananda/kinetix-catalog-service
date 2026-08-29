from abc import ABC, abstractmethod
from typing import Optional, List
from core.domain.entities.product import Product
from core.domain.entities.category import Category

class ProductRepository(ABC):
    @abstractmethod
    def find_all(self, category_slug: Optional[str] = None, search_query: Optional[str] = None) -> List[Product]:
        pass

    @abstractmethod
    def find_by_sku(self, sku: str) -> Optional[Product]:
        pass

    @abstractmethod
    def find_by_id(self, product_id: int) -> Optional[Product]:
        pass

    @abstractmethod
    def save(self, product: Product) -> Product:
        pass

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        pass

    @abstractmethod
    def find_all_categories(self) -> List[Category]:
        pass

    @abstractmethod
    def find_category_by_id(self, category_id: int) -> Optional[Category]:
        pass

    @abstractmethod
    def save_category(self, category: Category) -> Category:
        pass

    @abstractmethod
    def delete_category(self, category_id: int) -> bool:
        pass
