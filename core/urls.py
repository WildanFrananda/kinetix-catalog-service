from django.urls import path
from core.api.views import ProductListView, ProductDetailView

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<str:sku>/", ProductDetailView.as_view(), name="product-detail"),
]
