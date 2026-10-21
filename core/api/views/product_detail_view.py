from dataclasses import asdict

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.di import get_product_service
from core.api.serializers import ProductDetailSerializer
from core.api.views.public_read_api_view import PublicReadApiView


class ProductDetailView(PublicReadApiView):
    def get(self, request: Request, sku: str) -> Response:
        detail = get_product_service().get_product_detail(sku)
        if detail is None:
            raise NotFound("no product with this SKU is on sale", code="product_not_found")

        return Response(ProductDetailSerializer(asdict(detail)).data, status=status.HTTP_200_OK)
