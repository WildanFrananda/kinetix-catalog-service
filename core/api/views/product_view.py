from dataclasses import asdict
from typing import Dict, Any, Optional
from rest_framework.views import APIView

from core.infrastructure.security import IdentityTokenAuthentication, Principal
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from core.api.di import get_product_service
from core.api.serializers import ProductDetailSerializer, ProductListResponseSerializer
from core.application.dto import ProductFilterDTO

class ProductView(APIView):
    authentication_classes = [IdentityTokenAuthentication]
    def get(self, request: Request, sku: Optional[str] = None) -> Response:
        service = get_product_service()
        if sku is not None:
            try:
                result = service.get_product_detail(sku)
                if not result:
                    return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
                serializer = ProductDetailSerializer(asdict(result))
                return Response(serializer.data, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        category_slug = request.query_params.get("category")
        search_query = request.query_params.get("q")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        filter_dto = ProductFilterDTO(
            category_slug=category_slug,
            search_query=search_query,
            page=page,
            page_size=page_size
        )

        res = service.list_products(filter_dto)
        response_serializer = ProductListResponseSerializer(asdict(res))
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        principal = request.user if isinstance(request.user, Principal) else None
        if principal is None:
            return Response({"error": "a verified access token is required"}, status=status.HTTP_401_UNAUTHORIZED)
        if principal.role not in ("seller", "admin"):
            return Response({"error": "this account may not manage products"}, status=status.HTTP_403_FORBIDDEN)
        merchant_id = principal.user_id

        service = get_product_service()
        body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        try:
            product = service.create_product(merchant_id=merchant_id, data=body)
            return Response({
                "id": product.id,
                "sku": product.sku,
                "title": product.title,
                "merchant_id": product.merchant_id,
                "category_id": product.category.id,
                "price": str(product.price),
                "is_active": product.is_active
            }, status=status.HTTP_201_CREATED)
        except PermissionError as pe:
            return Response({"error": str(pe)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request: Request, product_id: int) -> Response:
        principal = request.user if isinstance(request.user, Principal) else None
        if principal is None:
            return Response({"error": "a verified access token is required"}, status=status.HTTP_401_UNAUTHORIZED)
        if principal.role not in ("seller", "admin"):
            return Response({"error": "this account may not manage products"}, status=status.HTTP_403_FORBIDDEN)
        merchant_id = principal.user_id

        service = get_product_service()
        body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        try:
            product = service.update_product(product_id=product_id, merchant_id=merchant_id, data=body)
            if not product:
                return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({
                "id": product.id,
                "sku": product.sku,
                "title": product.title,
                "merchant_id": product.merchant_id,
                "price": str(product.price),
                "is_active": product.is_active
            }, status=status.HTTP_200_OK)
        except PermissionError as pe:
            return Response({"error": str(pe)}, status=status.HTTP_403_FORBIDDEN)

    def delete(self, request: Request, product_id: int) -> Response:
        principal = request.user if isinstance(request.user, Principal) else None
        if principal is None:
            return Response({"error": "a verified access token is required"}, status=status.HTTP_401_UNAUTHORIZED)
        if principal.role not in ("seller", "admin"):
            return Response({"error": "this account may not manage products"}, status=status.HTTP_403_FORBIDDEN)
        merchant_id = principal.user_id

        service = get_product_service()
        try:
            deleted = service.delete_product(product_id=product_id, merchant_id=merchant_id)
            if not deleted:
                return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionError as pe:
            return Response({"error": str(pe)}, status=status.HTTP_403_FORBIDDEN)
