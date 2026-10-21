from dataclasses import asdict

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.caller import signed_in_caller
from core.api.di import get_product_service
from core.api.request_body import json_object
from core.api.serializers import ProductRecordSerializer
from core.api.views.public_read_api_view import PublicReadApiView


class ProductCreateView(PublicReadApiView):
    def post(self, request: Request) -> Response:
        seller = signed_in_caller(request)
        product = get_product_service().create_product(
            merchant_principal_id=seller.principal_id,
            data=json_object(request),
        )

        return Response(ProductRecordSerializer(asdict(product)).data, status=status.HTTP_201_CREATED)
