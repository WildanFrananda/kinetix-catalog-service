from django.urls import path
from core.api.views import ProductListView, ProductDetailView, CheckoutView, ReserveStockView

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<str:sku>/", ProductDetailView.as_view(), name="product-detail"),
    path("orders/checkout/", CheckoutView.as_view(), name="checkout"),
    path("cart/reserve/", ReserveStockView.as_view(), name="cart-reserve-stock"),
]
