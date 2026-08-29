from typing import Dict, Any, Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from core.api.di import get_category_service

class CategoryView(APIView):
    def get(self, request: Request, category_id: Optional[int] = None) -> Response:
        service = get_category_service()
        if category_id is not None:
            c = service.get_category_by_id(category_id)
            if not c:
                return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"id": c.id, "name": c.name, "slug": c.slug}, status=status.HTTP_200_OK)

        categories = service.list_categories()
        data = [{"id": c.id, "name": c.name, "slug": c.slug} for c in categories]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        service = get_category_service()
        body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        name = str(body.get("name", ""))
        slug = str(body.get("slug", ""))
        if not name or not slug:
            return Response({"error": "name and slug are required"}, status=status.HTTP_400_BAD_REQUEST)
        category = service.create_category(name=name, slug=slug)
        return Response({"id": category.id, "name": category.name, "slug": category.slug}, status=status.HTTP_201_CREATED)

    def put(self, request: Request, category_id: int) -> Response:
        service = get_category_service()
        body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        name = str(body.get("name", ""))
        slug = str(body.get("slug", ""))
        category = service.update_category(category_id=category_id, name=name, slug=slug)
        if not category:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"id": category.id, "name": category.name, "slug": category.slug}, status=status.HTTP_200_OK)

    def delete(self, request: Request, category_id: int) -> Response:
        service = get_category_service()
        deleted = service.delete_category(category_id)
        if not deleted:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
