from django.urls import path
from core.api.views import (
    CategoryCollectionView,
    CategoryDetailView,
    ProductCollectionView,
    ProductCreateView,
    ProductDetailView,
    ProductManageView,
)

urlpatterns = [
    path("categories", CategoryCollectionView.as_view()),
    path("categories/", CategoryCollectionView.as_view(), name="category-list"),
    path("categories/<int:category_id>", CategoryDetailView.as_view()),
    path("categories/<int:category_id>/", CategoryDetailView.as_view(), name="category-detail"),
    path("products", ProductCollectionView.as_view()),
    path("products/", ProductCollectionView.as_view(), name="product-list"),
    path("products/create", ProductCreateView.as_view()),
    path("products/create/", ProductCreateView.as_view(), name="product-create"),
    path("products/manage/<int:product_id>", ProductManageView.as_view()),
    path("products/manage/<int:product_id>/", ProductManageView.as_view(), name="product-manage"),
    path("products/<str:sku>", ProductDetailView.as_view()),
    path("products/<str:sku>/", ProductDetailView.as_view(), name="product-detail"),
]
