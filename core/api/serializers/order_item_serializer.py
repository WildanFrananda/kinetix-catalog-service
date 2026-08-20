from typing import Dict, Any
from rest_framework import serializers

class OrderItemSerializer(serializers.Serializer[Dict[str, Any]]):
    sku = serializers.CharField(max_length=64)
    product_name = serializers.CharField(max_length=255)
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
