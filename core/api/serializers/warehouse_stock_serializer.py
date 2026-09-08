from typing import Dict, Any
from rest_framework import serializers

class WarehouseStockSerializer(serializers.Serializer[Dict[str, Any]]):
    sku = serializers.CharField()
    bin_location = serializers.CharField(allow_null=True)
    available_quantity = serializers.IntegerField(allow_null=True)
    reserved_quantity = serializers.IntegerField(allow_null=True)
    stock_status = serializers.CharField()
