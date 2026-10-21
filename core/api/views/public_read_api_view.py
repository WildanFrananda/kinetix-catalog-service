from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import APIView

from core.infrastructure.security import IdentityTokenAuthentication


class PublicReadApiView(APIView):
    authentication_classes = [IdentityTokenAuthentication]

    def perform_authentication(self, request: Request) -> None:
        if request.method in SAFE_METHODS:
            return

        super().perform_authentication(request)
