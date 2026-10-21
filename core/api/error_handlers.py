from django.http import HttpRequest, JsonResponse

from core.api.error_body import INTERNAL_ERROR_MESSAGE, error_body


def bad_request(request: HttpRequest, exception: Exception) -> JsonResponse:
    return JsonResponse(error_body("BAD_REQUEST", "this request could not be read"), status=400)


def page_not_found(request: HttpRequest, exception: Exception) -> JsonResponse:
    return JsonResponse(error_body("NOT_FOUND", "nothing is served at this path"), status=404)


def server_error(request: HttpRequest) -> JsonResponse:
    return JsonResponse(error_body("INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE), status=500)
