from typing import Dict, Any
from rest_framework import serializers
from core.api.serializers.warehouse_stock_serializer import WarehouseStockSerializer

class ProductDetailSerializer(serializers.Serializer[Dict[str, Any]]):
    id = serializers.IntegerField()
    sku = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    image_url = serializers.URLField()
    warehouse_stock = WarehouseStockSerializer()
