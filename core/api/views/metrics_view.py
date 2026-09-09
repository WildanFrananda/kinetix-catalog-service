import logging

from django.http import HttpRequest, HttpResponse
from django.views import View
from prometheus_client import CONTENT_TYPE_LATEST

from core.infrastructure.metrics import MetricsUnavailable, render_metrics

logger = logging.getLogger(__name__)


class MetricsView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        try:
            body = render_metrics()
        except MetricsUnavailable as failure:
            logger.error("metrics could not be collected: %s", failure)
            return HttpResponse(
                f"# metrics unavailable: {failure}\n",
                status=503,
                content_type=CONTENT_TYPE_LATEST,
            )

        return HttpResponse(body, content_type=CONTENT_TYPE_LATEST)
