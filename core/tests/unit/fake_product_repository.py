from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import replace
from core.domain.entities import Product, Category, ProductChangePage
from core.domain.errors import CategoryInUseError, CategoryTakenError, SkuTakenError
from core.domain.repositories import ProductRepository

class FakeProductRepository(ProductRepository):
    def __init__(self) -> None:
        self._store: Dict[str, Product] = {}
        self._categories: Dict[int, Category] = {}
        self._next_id = 1

    def find_page(
        self,
        category_slug: Optional[str] = None,
        search_query: Optional[str] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> Tuple[List[Product], int]:
        res = [p for p in self._store.values() if p.is_active]
        if category_slug:
            res = [p for p in res if p.category.slug == category_slug]
        if search_query:
            res = [p for p in res if search_query.lower() in p.title.lower()]

        self.last_page_request = (offset, limit)
        return res[offset : offset + limit], len(res)

    def find_changed_since(
        self,
        updated_through: Optional[datetime] = None,
        last_sku: str = "",
        limit: int = 100,
    ) -> ProductChangePage:
        self.last_changed_since_limit = limit

        rows = sorted(
            (p for p in self._store.values() if p.updated_at is not None),
            key=lambda p: (p.updated_at, p.sku),
        )
        if updated_through is not None:
            rows = [
                p
                for p in rows
                if p.updated_at is not None
                and (
                    p.updated_at > updated_through
                    or (p.updated_at == updated_through and p.sku > last_sku)
                )
            ]

        has_more = len(rows) > limit
        rows = rows[:limit]

        upserted = [p for p in rows if p.is_active]
        removed = [p.sku for p in rows if not p.is_active]

        if rows:
            next_updated_through = rows[-1].updated_at
            next_last_sku = rows[-1].sku
        else:
            next_updated_through = updated_through
            next_last_sku = last_sku

        return ProductChangePage(
            upserted=upserted,
            removed_skus=removed,
            next_updated_through=next_updated_through,
            next_last_sku=next_last_sku,
            has_more=has_more,
        )

    def count_active_products(self) -> int:
        return len([p for p in self._store.values() if p.is_active])

    def find_by_sku(self, sku: str) -> Optional[Product]:
        p = self._store.get(sku)
        return p if p and p.is_active else None

    def find_by_id(self, product_id: int) -> Optional[Product]:
        for p in self._store.values():
            if p.id == product_id:
                return p
        return None

    def save(self, product: Product) -> Product:
        holder = self._store.get(product.sku)
        if holder is not None and holder.id != product.id:
            raise SkuTakenError(product.sku)

        if product.id is None:
            saved = replace(product, id=self._next_id, stock_info=None)
            self._next_id += 1
        else:
            current = self.find_by_id(product.id)
            if current is None:
                raise LookupError(f"no product {product.id} to update")
            del self._store[current.sku]
            saved = replace(product, stock_info=None)

        self._store[saved.sku] = saved
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
                merchant_principal_id=p.merchant_principal_id,
                is_active=False
            )
            return True
        return False

    def find_all_categories(self) -> List[Category]:
        return list(self._categories.values())

    def find_category_by_id(self, category_id: int) -> Optional[Category]:
        return self._categories.get(category_id)

    def save_category(self, category: Category) -> Category:
        """A category with an id the fake has never seen is filed under that id, as a fixture."""
        for other in self._categories.values():
            if other.id != category.id and (other.name == category.name or other.slug == category.slug):
                raise CategoryTakenError(category.name, category.slug)

        c_id = category.id or (max(self._categories, default=0) + 1)
        saved = Category(id=c_id, name=category.name, slug=category.slug)
        self._categories[c_id] = saved
        return saved

    def delete_category(self, category_id: int) -> bool:
        in_use = [p for p in self._store.values() if p.category.id == category_id]
        if in_use:
            raise CategoryInUseError(category_id, len(in_use))
        if category_id in self._categories:
            del self._categories[category_id]
            return True
        return False
