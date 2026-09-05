from django.http import HttpRequest, JsonResponse
from django.views import View

class HealthView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse({"status": "ok", "service": "kinetix-catalog-service"})
