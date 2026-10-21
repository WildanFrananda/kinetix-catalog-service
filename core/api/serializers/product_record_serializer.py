from typing import Dict

from rest_framework import serializers


class ProductRecordSerializer(serializers.Serializer[Dict[str, object]]):
    id = serializers.IntegerField()
    sku = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField(source="category.name")
    category_slug = serializers.CharField(source="category.slug")
    category_id = serializers.IntegerField(source="category.id")
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    image_url = serializers.URLField()
    merchant_principal_id = serializers.CharField()
    weight_grams = serializers.IntegerField(allow_null=True)
    is_active = serializers.BooleanField()
