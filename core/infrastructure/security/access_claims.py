from typing import TypedDict


class AccessClaims(TypedDict):
    sub: str
    jti: str
    iss: str
    aud: str
    exp: int
    iat: int
    token_use: str
    email: str
    role: str
