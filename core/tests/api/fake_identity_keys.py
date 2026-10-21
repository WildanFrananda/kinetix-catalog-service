import time
import uuid
from typing import List

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWK
from jwt.algorithms import RSAAlgorithm

from core.infrastructure.security import Principal

KEY_ID = "catalog-api-test-key"


class FakeIdentityKeys:
    def __init__(self, issuer: str, audience: str) -> None:
        self._issuer = issuer
        self._audience = audience
        self._private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def sign(self, principal: Principal, lifetime_seconds: int = 900) -> str:
        now = int(time.time())
        claims = {
            "sub": principal.principal_id,
            "jti": str(uuid.uuid4()),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": now,
            "exp": now + lifetime_seconds,
            "token_use": "access",
            "email": principal.email,
            "role": principal.role,
        }

        return jwt.encode(claims, self._private, algorithm="RS256", headers={"kid": KEY_ID})

    def get_signing_keys(self, refresh: bool = False) -> List[PyJWK]:
        jwk = RSAAlgorithm.to_jwk(self._private.public_key(), as_dict=True)
        jwk.update({"kid": KEY_ID, "alg": "RS256", "use": "sig"})

        return [PyJWK(jwk)]
