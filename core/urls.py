from django.urls import path
from core.api.views import ProductView, CategoryView

urlpatterns = [
    path("categories/", CategoryView.as_view(), name="category-list"),
    path("categories/<int:category_id>/", CategoryView.as_view(), name="category-detail"),
    path("products/", ProductView.as_view(), name="product-list"),
    path("products/create/", ProductView.as_view(), name="product-create"),
    path("products/manage/<int:product_id>/", ProductView.as_view(), name="product-manage"),
    path("products/<str:sku>/", ProductView.as_view(), name="product-detail"),
]
