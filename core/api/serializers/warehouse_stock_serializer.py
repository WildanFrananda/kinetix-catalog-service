from typing import Dict, Any
from rest_framework import serializers

class WarehouseStockSerializer(serializers.Serializer[Dict[str, Any]]):
    sku = serializers.CharField()
    bin_location = serializers.CharField()
    available_quantity = serializers.IntegerField()
    reserved_quantity = serializers.IntegerField()
