class CategoryTakenError(Exception):
    def __init__(self, name: str, slug: str) -> None:
        super().__init__(f"another category already uses the name {name} or the slug {slug}")
        self.name: str = name
        self.slug: str = slug
