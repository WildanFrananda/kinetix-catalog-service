from typing import Optional, List, Dict
from core.domain.entities import Product, Category
from core.domain.repositories import ProductRepository

class FakeProductRepository(ProductRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Product] = {}
        self._categories: Dict[int, Category] = {}

    def find_all(self, category_slug: Optional[str] = None, search_query: Optional[str] = None) -> List[Product]:
        res = [p for p in self._store.values() if p.is_active]
        if category_slug:
            res = [p for p in res if p.category.slug == category_slug]
        if search_query:
            res = [p for p in res if search_query.lower() in p.title.lower()]
        return res

    def find_by_sku(self, sku: str) -> Optional[Product]:
        p = self._store.get(sku)
        return p if p and p.is_active else None

    def find_by_id(self, product_id: int) -> Optional[Product]:
        for p in self._store.values():
            if p.id == product_id:
                return p
        return None

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
            category=product.category,
            merchant_id=product.merchant_id,
            is_active=product.is_active
        )
        self._store[product.sku] = saved
        return saved

    def delete(self, product_id: int) -> bool:
        p = self.find_by_id(product_id)
        if p:
            self._store[p.sku] = Product(
                id=p.id,
                sku=p.sku,
                title=p.title,
                description=p.description,
                price=p.price,
                currency=p.currency,
                image_url=p.image_url,
                category=p.category,
                merchant_id=p.merchant_id,
                is_active=False
            )
            return True
        return False

    def find_all_categories(self) -> List[Category]:
        return list(self._categories.values())

    def find_category_by_id(self, category_id: int) -> Optional[Category]:
        return self._categories.get(category_id)

    def save_category(self, category: Category) -> Category:
        c_id = category.id or (len(self._categories) + 1)
        saved = Category(id=c_id, name=category.name, slug=category.slug)
        self._categories[c_id] = saved
        return saved

    def delete_category(self, category_id: int) -> bool:
        if category_id in self._categories:
            del self._categories[category_id]
            return True
        return False
