from typing import Optional, List, Dict
from core.domain.entities import Product, Category
from core.domain.repositories import ProductRepository

class FakeProductRepository(ProductRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Product] = {}

    def find_all(self, category_slug: Optional[str] = None, search_query: Optional[str] = None) -> List[Product]:
        res = list(self._store.values())
        if category_slug:
            res = [p for p in res if p.category.slug == category_slug]
        if search_query:
            res = [p for p in res if search_query.lower() in p.title.lower()]
        return res

    def find_by_sku(self, sku: str) -> Optional[Product]:
        return self._store.get(sku)

    def save(self, product: Product) -> Product:
        p_id = product.id or (len(self._store) + 1)
        saved = Product(
            id=p_id,
            sku=product.sku,
            title=product.title,
            description=product.description,
            price=product.price,
            currency=product.currency,
            image_url=product.image_url,
            category=product.category
        )
        self._store[product.sku] = saved
        return saved

    def save_category(self, category: Category) -> Category:
        return category
