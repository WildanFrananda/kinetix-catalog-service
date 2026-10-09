class CategoryInUseError(Exception):
    def __init__(self, category_id: int, product_count: int) -> None:
        super().__init__(
            f"category {category_id} still holds {product_count} product(s), active or withdrawn; "
            "move them to another category first"
        )
        self.category_id: int = category_id
        self.product_count: int = product_count
