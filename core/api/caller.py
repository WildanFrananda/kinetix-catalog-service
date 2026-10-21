from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.request import Request

from core.infrastructure.security import Principal


def signed_in_caller(request: Request) -> Principal:
    user = request.user
    if not isinstance(user, Principal):
        raise NotAuthenticated("a verified access token is required")

    return user


def category_manager(request: Request) -> Principal:
    principal = signed_in_caller(request)
    if principal.role != "admin":
        raise PermissionDenied("this account may not manage categories", code="admin_required")

    return principal
