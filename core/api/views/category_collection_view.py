from dataclasses import asdict

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.admin_actions import CATEGORY_CREATE
from core.api.caller import category_manager
from core.api.di import get_category_service
from core.api.request_body import json_object
from core.api.serializers import CategorySerializer
from core.api.views.admin_audited_api_view import AdminAuditedApiView


class CategoryCollectionView(AdminAuditedApiView):
    def get(self, request: Request) -> Response:
        categories = get_category_service().list_categories()
        data = [CategorySerializer(asdict(category)).data for category in categories]

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        self.begin_admin_action(CATEGORY_CREATE, category_manager(request))
        body = json_object(request)
        category = get_category_service().create_category(name=body.get("name"), slug=body.get("slug"))

        return Response(CategorySerializer(asdict(category)).data, status=status.HTTP_201_CREATED)
