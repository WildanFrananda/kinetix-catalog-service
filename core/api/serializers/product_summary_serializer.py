from typing import Dict, Any
from rest_framework import serializers

class ProductSummarySerializer(serializers.Serializer[Dict[str, Any]]):
    id = serializers.IntegerField()
    sku = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    image_url = serializers.URLField()
    available_stock = serializers.IntegerField()
    is_in_stock = serializers.BooleanField()
