import json
import logging
from typing import Optional, Tuple

from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from core.infrastructure.security.access_claims import AccessClaims
from core.infrastructure.security.identity_keys_unavailable import IdentityKeysUnavailable
from core.infrastructure.security.principal import Principal
from core.infrastructure.security.token_verifier import TokenVerifier

logger = logging.getLogger(__name__)

KID_MISMATCH = "Unable to find a signing key that matches"

class IdentityTokenAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request: Request) -> Optional[Tuple[Principal, AccessClaims]]:
        header = request.headers.get("Authorization", "")
        parts = header.split()

        if len(parts) != 2 or parts[0].lower() != self.keyword.lower() or not parts[1]:
            return None

        try:
            claims = TokenVerifier.shared().verify_access(parts[1])
        except PyJWKClientConnectionError as unreachable:
            logger.error("identity's JWKS endpoint did not answer: %s", unreachable)
            raise IdentityKeysUnavailable() from unreachable
        except PyJWKClientError as jwks_error:
            if KID_MISMATCH in str(jwks_error):
                logger.warning("token verification failed: %s", jwks_error)
                raise AuthenticationFailed("Invalid token") from jwks_error

            logger.error("identity's JWKS endpoint answered, but not usably: %s", jwks_error)
            raise IdentityKeysUnavailable() from jwks_error
        except json.JSONDecodeError as malformed:
            logger.error("identity's JWKS endposint did not return JSON: %s", malformed)
            raise IdentityKeysUnavailable() from malformed
        except Exception as cause:
            logger.warning("token verification failed: %s", cause)
            raise AuthenticationFailed("Invalid token") from cause

        principal = Principal(
            principal_id=claims["sub"],
            email=claims["email"],
            role=claims["role"],
        )
        return (principal, claims)

    def authenticate_header(self, request: Request) -> str:
        return self.keyword
