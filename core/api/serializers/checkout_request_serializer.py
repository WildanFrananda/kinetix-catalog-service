import os
from typing import Dict, Any
from rest_framework import serializers
from core.api.serializers.order_item_serializer import OrderItemSerializer

class CheckoutRequestSerializer(serializers.Serializer[Dict[str, Any]]):
    merchant_api_key = serializers.CharField(
        max_length=128,
        required=False,
        default=os.environ.get("MERCHANT_API_KEY", "INTERNAL_OMS_KEY")
    )
    buyer_name = serializers.CharField(max_length=128)
    buyer_phone = serializers.CharField(max_length=32)
    street_address = serializers.CharField()
    city = serializers.CharField(max_length=64)
    postal_code = serializers.CharField(max_length=16)
    items = OrderItemSerializer(many=True)
    voucher_code = serializers.CharField(max_length=64, required=False, allow_null=True, allow_blank=True, default=None)
