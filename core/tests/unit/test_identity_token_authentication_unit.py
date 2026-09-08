import json
from typing import Any, Dict, Optional, Tuple

import pytest
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from rest_framework.exceptions import AuthenticationFailed

from core.infrastructure.security.identity_keys_unavailable import IdentityKeysUnavailable
from core.infrastructure.security.identity_token_authentication import (
    KID_MISMATCH,
    IdentityTokenAuthentication,
)
from core.infrastructure.security.token_verifier import TokenVerifier


class FakeRequest:
    def __init__(self, headers: Dict[str, str]) -> None:
        self.headers = headers


def _authenticate_raising(
    monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> Optional[Tuple[Any, Any]]:
    class Failing:
        def verify_access(self, token: str) -> Dict[str, Any]:
            raise error

    monkeypatch.setattr(TokenVerifier, "shared", staticmethod(lambda: Failing()))
    request = FakeRequest({"Authorization": "Bearer a.b.c"})
    return IdentityTokenAuthentication().authenticate(request)  # type: ignore[arg-type]


def test_kid_mismatch_is_a_verdict_on_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    error = PyJWKClientError('Unable to find a signing key that matches: "abc"')

    with pytest.raises(AuthenticationFailed):
        _authenticate_raising(monkeypatch, error)


@pytest.mark.parametrize(
    "error",
    [
        PyJWKClientConnectionError("cannot reach the JWKS endpoint"),
        PyJWKClientError("The JWKS endpoint did not return a JSON object"),
        PyJWKClientError("The JWKS endpoint did not contain any signing keys"),
        PyJWKClientError("some failure mode a future PyJWT grows"),
        json.JSONDecodeError("Expecting value", "<html>502 Bad Gateway</html>", 0),
    ],
)
def test_identity_being_broken_is_never_reported_as_a_bad_token(
    monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    with pytest.raises(IdentityKeysUnavailable):
        _authenticate_raising(monkeypatch, error)


def test_kid_mismatch_message_still_matches_the_installed_pyjwt() -> None:
    from jwt import PyJWKClient

    client = PyJWKClient("https://identity.invalid/.well-known/jwks.json")
    object.__setattr__(client, "get_signing_keys", lambda refresh=False: [])

    with pytest.raises(PyJWKClientError) as raised:
        client.get_signing_key("a-kid-nothing-signs")

    assert KID_MISMATCH in str(raised.value)
