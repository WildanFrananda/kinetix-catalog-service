from dataclasses import asdict

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.caller import category_manager
from core.api.di import get_category_service
from core.api.request_body import json_object
from core.api.serializers import CategorySerializer
from core.api.views.public_read_api_view import PublicReadApiView

_NOT_FOUND = "no category with this id"


class CategoryDetailView(PublicReadApiView):
    def get(self, request: Request, category_id: int) -> Response:
        category = get_category_service().get_category_by_id(category_id)
        if category is None:
            raise NotFound(_NOT_FOUND, code="category_not_found")

        return Response(CategorySerializer(asdict(category)).data, status=status.HTTP_200_OK)

    def put(self, request: Request, category_id: int) -> Response:
        category_manager(request)
        body = json_object(request)
        category = get_category_service().update_category(
            category_id=category_id,
            name=body.get("name"),
            slug=body.get("slug"),
        )
        if category is None:
            raise NotFound(_NOT_FOUND, code="category_not_found")

        return Response(CategorySerializer(asdict(category)).data, status=status.HTTP_200_OK)

    def delete(self, request: Request, category_id: int) -> Response:
        category_manager(request)
        deleted = get_category_service().delete_category(category_id)
        if not deleted:
            raise NotFound(_NOT_FOUND, code="category_not_found")

        return Response(status=status.HTTP_204_NO_CONTENT)
