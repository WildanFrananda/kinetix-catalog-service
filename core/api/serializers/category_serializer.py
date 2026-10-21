from typing import Dict

from rest_framework import serializers


class CategorySerializer(serializers.Serializer[Dict[str, object]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
