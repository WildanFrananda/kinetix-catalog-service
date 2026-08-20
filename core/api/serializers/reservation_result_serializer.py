from typing import Dict, Any
from rest_framework import serializers

class ReservationResultSerializer(serializers.Serializer[Dict[str, Any]]):
    sku = serializers.CharField()
    quantity = serializers.IntegerField()
    success = serializers.BooleanField()
    bin_location = serializers.CharField()
    message = serializers.CharField()
    expires_in_seconds = serializers.IntegerField()
