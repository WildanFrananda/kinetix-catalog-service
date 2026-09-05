import logging

from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views import View

logger = logging.getLogger(__name__)


class ReadinessView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:
            logger.error("readiness check failed: %s", exc)
            return JsonResponse(
                {"status": "unavailable", "database": "unreachable"}, status=503
            )

        return JsonResponse({"status": "ok", "database": "reachable"})
