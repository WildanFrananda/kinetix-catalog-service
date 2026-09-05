import os
from typing import Optional

import jwt
from jwt import InvalidTokenError
from jwt import PyJWKClient

from core.infrastructure.security.access_claims import AccessClaims


class TokenVerifier:
    _instance: Optional["TokenVerifier"] = None

    def __init__(self) -> None:
        self._issuer: str = self._required("JWT_ISSUER")
        self._audience: str = self._required("JWT_AUDIENCE")
        self._jwks: PyJWKClient = PyJWKClient(self._required("IDENTITY_JWKS_URL"), cache_keys=True)

    @staticmethod
    def _required(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            raise RuntimeError(f"{name} is required and has no default.")
        return value

    @classmethod
    def shared(cls) -> "TokenVerifier":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def verify_access(self, token: str) -> AccessClaims:
        key = self._jwks.get_signing_key_from_jwt(token).key
        payload: object = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=self._issuer,
            audience=self._audience,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        return self._as_access_claims(payload)

    @staticmethod
    def _as_access_claims(payload: object) -> AccessClaims:
        if not isinstance(payload, dict):
            raise InvalidTokenError("token payload is not an object")

        def text(name: str) -> str:
            value = payload.get(name)
            if not isinstance(value, str):
                raise InvalidTokenError(f"claim '{name}' is missing or not a string")
            return value

        def number(name: str) -> int:
            value = payload.get(name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise InvalidTokenError(f"claim '{name}' is missing or not an integer")
            return value

        token_use = text("token_use")
        if token_use != "access":
            raise InvalidTokenError("not an access token")

        return AccessClaims(
            sub=text("sub"),
            jti=text("jti"),
            iss=text("iss"),
            aud=text("aud"),
            exp=number("exp"),
            iat=number("iat"),
            token_use=token_use,
            uid=number("uid"),
            email=text("email"),
            role=text("role"),
        )
