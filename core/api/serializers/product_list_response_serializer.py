from typing import Dict, Any
from rest_framework import serializers
from core.api.serializers.product_summary_serializer import ProductSummarySerializer

class ProductListResponseSerializer(serializers.Serializer[Dict[str, Any]]):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = ProductSummarySerializer(many=True)
