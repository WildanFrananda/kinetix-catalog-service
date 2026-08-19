from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from orders.api.serializers import CheckoutRequestSerializer
from orders.api.di import get_checkout_service
from orders.application.dto import CreateOrderInputDTO, OrderItemDTO

class CheckoutView(APIView):
    def post(self, request: Request) -> Response:
        serializer = CheckoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        item_dtos = [
            OrderItemDTO(
                sku=it["sku"],
                product_name=it["product_name"],
                quantity=it["quantity"],
                price=it["price"]
            )
            for it in data["items"]
        ]

        dto = CreateOrderInputDTO(
            merchant_api_key=data.get("merchant_api_key", "GRPC_TEST_KEY_123"),
            buyer_name=data["buyer_name"],
            buyer_phone=data["buyer_phone"],
            street_address=data["street_address"],
            city=data["city"],
            postal_code=data["postal_code"],
            items=item_dtos
        )

        service = get_checkout_service()
        result = service.execute(dto)

        return Response({
            "success": result.success,
            "order_id": result.order_id,
            "order_number": result.order_number,
            "status": result.status,
            "total_amount": str(result.total_amount),
            "fulfillment_ref": result.fulfillment_ref,
            "message": result.message
        }, status=status.HTTP_201_CREATED)
