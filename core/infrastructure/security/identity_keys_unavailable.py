from rest_framework import status
from rest_framework.exceptions import APIException


class IdentityKeysUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = (
        "we could not verify this token right now because identity did not answer. "
        "The token was not rejected."
    )
    default_code = "identity_keys_unavailable"
