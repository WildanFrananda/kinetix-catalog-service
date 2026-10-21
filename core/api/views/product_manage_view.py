from dataclasses import asdict

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.caller import signed_in_caller
from core.api.di import get_product_service
from core.api.request_body import json_object
from core.api.serializers import ProductRecordSerializer
from core.api.views.public_read_api_view import PublicReadApiView

_NOT_FOUND = "no product with this id"


class ProductManageView(PublicReadApiView):
    def put(self, request: Request, product_id: int) -> Response:
        seller = signed_in_caller(request)
        product = get_product_service().update_product(
            product_id=product_id,
            merchant_principal_id=seller.principal_id,
            data=json_object(request),
        )
        if product is None:
            raise NotFound(_NOT_FOUND, code="product_not_found")

        return Response(ProductRecordSerializer(asdict(product)).data, status=status.HTTP_200_OK)

    def delete(self, request: Request, product_id: int) -> Response:
        seller = signed_in_caller(request)
        deleted = get_product_service().delete_product(
            product_id=product_id,
            merchant_principal_id=seller.principal_id,
        )
        if not deleted:
            raise NotFound(_NOT_FOUND, code="product_not_found")

        return Response(status=status.HTTP_204_NO_CONTENT)
