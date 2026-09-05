from typing import TypedDict


class AccessClaims(TypedDict):
    sub: str
    jti: str
    iss: str
    aud: str
    exp: int
    iat: int
    token_use: str
    uid: int
    email: str
    role: str
