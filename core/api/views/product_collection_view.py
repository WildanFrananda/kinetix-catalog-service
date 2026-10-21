from dataclasses import asdict

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.di import get_product_service
from core.api.serializers import ProductListResponseSerializer
from core.api.views.public_read_api_view import PublicReadApiView
from core.application.services import ProductFilterParser


class ProductCollectionView(PublicReadApiView):
    def get(self, request: Request) -> Response:
        filter_dto = ProductFilterParser.parse(request.query_params)
        result = get_product_service().list_products(filter_dto)

        return Response(ProductListResponseSerializer(asdict(result)).data, status=status.HTTP_200_OK)
