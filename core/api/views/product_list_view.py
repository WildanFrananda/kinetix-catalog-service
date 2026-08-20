from dataclasses import asdict
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from core.application.dto import ProductFilterDTO
from core.api.di import get_product_service
from core.api.serializers import ProductListResponseSerializer

class ProductListView(APIView):
    def get(self, request: Request) -> Response:
        category_slug = request.query_params.get("category")
        search_query = request.query_params.get("search")
        page = int(request.query_params.get("page", "1"))
        page_size = int(request.query_params.get("page_size", "10"))

        dto = ProductFilterDTO(
            category_slug=category_slug,
            search_query=search_query,
            page=page,
            page_size=page_size
        )

        service = get_product_service()
        result = service.list_products(dto)
        serializer = ProductListResponseSerializer(asdict(result))
        return Response(serializer.data, status=status.HTTP_200_OK)
