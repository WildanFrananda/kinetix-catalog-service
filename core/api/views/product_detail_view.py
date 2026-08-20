from dataclasses import asdict
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from core.api.di import get_product_service
from core.api.serializers import ProductDetailSerializer

class ProductDetailView(APIView):
    def get(self, request: Request, sku: str) -> Response:
        service = get_product_service()
        try:
            result = service.get_product_detail(sku)
            serializer = ProductDetailSerializer(asdict(result))
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
