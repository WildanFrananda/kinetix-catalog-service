import json
import threading
import time
from typing import Callable, Dict, Optional

import jwt
from jwt import PyJWK, PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError


class SigningKeySet:
    UNKNOWN_KEY_REFRESH_SECONDS: float = 10.0

    def __init__(self, client: PyJWKClient, clock: Callable[[], float] = time.monotonic) -> None:
        self._client = client
        self._clock = clock
        self._state = threading.Lock()
        self._refreshing = threading.Lock()
        self._keys: Dict[str, PyJWK] = {}
        self._last_refresh: Optional[float] = None
        self._last_error: Optional[Exception] = None

    def key_for(self, token: str) -> PyJWK:
        kid = jwt.get_unverified_header(token).get("kid")
        if not isinstance(kid, str) or not kid:
            raise InvalidTokenError("the token names no signing key")

        known = self._lookup(kid)
        if known is not None:
            return known

        self._refresh_for_unknown(kid)

        found = self._lookup(kid)
        if found is not None:
            return found

        with self._state:
            error = self._last_error

        if error is not None:
            raise error

        raise PyJWKClientError(f'Unable to find a signing key that matches: "{kid}"')

    def _lookup(self, kid: str) -> Optional[PyJWK]:
        with self._state:
            return self._keys.get(kid)

    def _refresh_for_unknown(self, kid: str) -> None:
        with self._refreshing:
            if self._lookup(kid) is not None:
                return

            with self._state:
                last = self._last_refresh

            if last is not None and self._clock() - last < self.UNKNOWN_KEY_REFRESH_SECONDS:
                return

            self._refresh()

    def _refresh(self) -> None:
        with self._state:
            self._last_refresh = self._clock()

        try:
            keys = self._client.get_signing_keys(refresh=True)
        except (PyJWKClientError, json.JSONDecodeError) as error:
            with self._state:
                self._last_error = error
            return

        fresh = {key.key_id: key for key in keys if key.key_id}

        with self._state:
            self._keys = fresh
            self._last_error = None
