from django.db import models

class CategoryModel(models.Model):
    id: int
    objects: models.Manager["CategoryModel"]

    name = models.CharField(max_length=128, unique=True, db_index=True)
    slug = models.SlugField(max_length=128, unique=True, db_index=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name
