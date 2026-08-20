from typing import Dict, Any
from rest_framework import serializers

class ReserveStockRequestSerializer(serializers.Serializer[Dict[str, Any]]):
    sku = serializers.CharField(max_length=64)
    quantity = serializers.IntegerField(min_value=1)
