from dataclasses import asdict

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.caller import selling_caller
from core.api.di import get_product_service
from core.api.serializers import MerchantProductListResponseSerializer
from core.application.services import ProductFilterParser
from core.infrastructure.security import IdentityTokenAuthentication


class MerchantProductCollectionView(APIView):
    authentication_classes = [IdentityTokenAuthentication]

    def get(self, request: Request) -> Response:
        seller = selling_caller(request)
        filter_dto = ProductFilterParser.parse(request.query_params)
        result = get_product_service().list_merchant_products(seller.principal_id, filter_dto)

        return Response(MerchantProductListResponseSerializer(asdict(result)).data, status=status.HTTP_200_OK)
