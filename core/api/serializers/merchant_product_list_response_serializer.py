from typing import Dict

from rest_framework import serializers

from core.api.serializers.product_record_serializer import ProductRecordSerializer


class MerchantProductListResponseSerializer(serializers.Serializer[Dict[str, object]]):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = ProductRecordSerializer(many=True)
