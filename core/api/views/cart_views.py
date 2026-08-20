from dataclasses import asdict
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from core.application.dto import ReserveCartStockInputDTO
from core.api.di import get_order_service
from core.api.serializers import ReserveStockRequestSerializer, ReservationResultSerializer

class ReserveStockView(APIView):
    def post(self, request: Request) -> Response:
        serializer = ReserveStockRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        dto = ReserveCartStockInputDTO(
            sku=data["sku"],
            quantity=data["quantity"]
        )

        service = get_order_service()
        try:
            result = service.reserve_cart_stock(dto)
            response_serializer = ReservationResultSerializer(asdict(result))
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
