from typing import Dict, Any, Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from core.api.di import get_category_service
from core.domain.errors import CategoryInUseError, CategoryTakenError, InvalidInputError
from core.infrastructure.security import IdentityTokenAuthentication, Principal

def _invalid(error: InvalidInputError) -> Response:
    return Response(
        {"error": "INVALID_INPUT", "field": error.field, "message": error.reason},
        status=status.HTTP_400_BAD_REQUEST,
    )

class CategoryView(APIView):
    authentication_classes = [IdentityTokenAuthentication]

    @staticmethod
    def _require_admin(request: Request) -> Optional[Response]:
        principal = request.user if isinstance(request.user, Principal) else None
        if principal is None:
            return Response(
                {"error": "a verified access token is required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if principal.role != "admin":
            return Response(
                {"error": "this account may not manage categories"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None
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
        denied = self._require_admin(request)
        if denied is not None:
            return denied
        service = get_category_service()
        body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        name = str(body.get("name", ""))
        slug = str(body.get("slug", ""))
        try:
            category = service.create_category(name=name, slug=slug)
        except InvalidInputError as invalid:
            return _invalid(invalid)
        except CategoryTakenError as taken:
            return Response({"error": "CATEGORY_TAKEN", "message": str(taken)}, status=status.HTTP_409_CONFLICT)
        return Response({"id": category.id, "name": category.name, "slug": category.slug}, status=status.HTTP_201_CREATED)

    def put(self, request: Request, category_id: int) -> Response:
        denied = self._require_admin(request)
        if denied is not None:
            return denied
        service = get_category_service()
        body: Dict[str, Any] = request.data if isinstance(request.data, dict) else {}
        name = str(body.get("name", ""))
        slug = str(body.get("slug", ""))
        try:
            category = service.update_category(category_id=category_id, name=name, slug=slug)
        except InvalidInputError as invalid:
            return _invalid(invalid)
        except CategoryTakenError as taken:
            return Response({"error": "CATEGORY_TAKEN", "message": str(taken)}, status=status.HTTP_409_CONFLICT)
        if not category:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"id": category.id, "name": category.name, "slug": category.slug}, status=status.HTTP_200_OK)

    def delete(self, request: Request, category_id: int) -> Response:
        denied = self._require_admin(request)
        if denied is not None:
            return denied
        service = get_category_service()
        try:
            deleted = service.delete_category(category_id)
        except CategoryInUseError as in_use:
            return Response(
                {"error": "CATEGORY_IN_USE", "message": str(in_use), "product_count": in_use.product_count},
                status=status.HTTP_409_CONFLICT,
            )
        if not deleted:
            return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
