from typing import Optional, Tuple

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from core.infrastructure.security.access_claims import AccessClaims
from core.infrastructure.security.principal import Principal
from core.infrastructure.security.token_verifier import TokenVerifier

class IdentityTokenAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request: Request) -> Optional[Tuple[Principal, AccessClaims]]:
        header = request.headers.get("Authorization", "")
        parts = header.split()

        if len(parts) != 2 or parts[0].lower() != self.keyword.lower() or not parts[1]:
            return None

        try:
            claims = TokenVerifier.shared().verify_access(parts[1])
        except Exception:
            raise AuthenticationFailed("Invalid token")

        principal = Principal(
            principal_id=claims["sub"],
            user_id=claims["uid"],
            email=claims["email"],
            role=claims["role"],
        )
        return (principal, claims)

    def authenticate_header(self, request: Request) -> str:
        return self.keyword
