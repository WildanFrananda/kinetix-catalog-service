from django.urls import path
from orders.api.views import CheckoutView

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
]
