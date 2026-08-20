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
    def save(self, product: Product) -> Product:
        pass

    @abstractmethod
    def save_category(self, category: Category) -> Category:
        pass
