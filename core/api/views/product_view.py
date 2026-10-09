from dataclasses import asdict
from typing import Dict, Any, Optional
from rest_framework.views import APIView

from core.infrastructure.security import IdentityTokenAuthentication, Principal
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from rest_framework.exceptions import MethodNotAllowed
from core.api.di import get_product_service
from core.api.serializers import ProductDetailSerializer, ProductListResponseSerializer
from core.application.services import ProductFilterParser
from core.domain.errors import IdentityUnavailableError, InvalidInputError, SkuTakenError

def _identity_unavailable() -> Response:
    return Response(
        {
            "error": "IDENTITY_UNAVAILABLE",
            "message": (
                "we could not check this merchant account right now, so the request was not "
                "applied. Nothing was created, changed or deleted."
            ),
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"Retry-After": "15"},
    )

def _seller(request: Request) -> Optional[Principal]:
    return request.user if isinstance(request.user, Principal) else None

def _invalid(error: InvalidInputError) -> Response:
    return Response(
        {"error": "INVALID_INPUT", "field": error.field, "message": error.reason},
        status=status.HTTP_400_BAD_REQUEST,
    )

def _sku_taken(error: SkuTakenError) -> Response:
    return Response({"error": "SKU_TAKEN", "message": str(error)}, status=status.HTTP_409_CONFLICT)

def _unauthenticated() -> Response:
    return Response(
        {"error": "a verified access token is required"}, status=status.HTTP_401_UNAUTHORIZED
    )

class ProductView(APIView):
    authentication_classes = [IdentityTokenAuthentication]
    def get(self, request: Request, sku: Optional[str] = None, product_id: Optional[int] = None) -> Response:
        if product_id is not None:
            raise MethodNotAllowed("GET")
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

        try:
            filter_dto = ProductFilterParser.parse(request.query_params)
        except InvalidInputError as invalid:
            return _invalid(invalid)

        res = service.list_products(filter_dto)
        response_serializer = ProductListResponseSerializer(asdict(res))
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, sku: Optional[str] = None, product_id: Optional[int] = None) -> Response:
        if sku is not None or product_id is not None:
            raise MethodNotAllowed("POST")
        principal = _seller(request)
        if principal is None:
            return _unauthenticated()
        merchant_principal_id = principal.principal_id

        service = get_product_service()
        body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        try:
            product = service.create_product(merchant_principal_id=merchant_principal_id, data=body)
            return Response({
                "id": product.id,
                "sku": product.sku,
                "title": product.title,
                "merchant_principal_id": product.merchant_principal_id,
                "category_id": product.category.id,
                "price": str(product.price),
                "is_active": product.is_active
            }, status=status.HTTP_201_CREATED)
        except IdentityUnavailableError:
            return _identity_unavailable()
        except PermissionError as pe:
            return Response({"error": str(pe)}, status=status.HTTP_403_FORBIDDEN)
        except InvalidInputError as invalid:
            return _invalid(invalid)
        except SkuTakenError as taken:
            return _sku_taken(taken)

    def put(self, request: Request, product_id: Optional[int] = None, sku: Optional[str] = None) -> Response:
        if product_id is None:
            raise MethodNotAllowed("PUT")
        principal = _seller(request)
        if principal is None:
            return _unauthenticated()
        merchant_principal_id = principal.principal_id

        service = get_product_service()
        body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        try:
            product = service.update_product(product_id=product_id, merchant_principal_id=merchant_principal_id, data=body)
            if not product:
                return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({
                "id": product.id,
                "sku": product.sku,
                "title": product.title,
                "merchant_principal_id": product.merchant_principal_id,
                "price": str(product.price),
                "is_active": product.is_active
            }, status=status.HTTP_200_OK)
        except IdentityUnavailableError:
            return _identity_unavailable()
        except PermissionError as pe:
            return Response({"error": str(pe)}, status=status.HTTP_403_FORBIDDEN)
        except InvalidInputError as invalid:
            return _invalid(invalid)
        except SkuTakenError as taken:
            return _sku_taken(taken)

    def delete(self, request: Request, product_id: Optional[int] = None, sku: Optional[str] = None) -> Response:
        if product_id is None:
            raise MethodNotAllowed("DELETE")
        principal = _seller(request)
        if principal is None:
            return _unauthenticated()
        merchant_principal_id = principal.principal_id

        service = get_product_service()
        try:
            deleted = service.delete_product(product_id=product_id, merchant_principal_id=merchant_principal_id)
            if not deleted:
                return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except IdentityUnavailableError:
            return _identity_unavailable()
        except PermissionError as pe:
            return Response({"error": str(pe)}, status=status.HTTP_403_FORBIDDEN)
