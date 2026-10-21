import time
from typing import Dict, List, cast

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWK, PyJWKClient
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError, PyJWKSetError

from core.infrastructure.security.signing_key_set import SigningKeySet


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


class Identity:
    def __init__(self) -> None:
        self.private: Dict[str, rsa.RSAPrivateKey] = {}
        self.published: List[str] = []
        self.down = False
        self.fetches = 0

    def publish(self, kid: str) -> None:
        self.private[kid] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.published.append(kid)

    def sign(self, kid: str) -> str:
        if kid not in self.private:
            self.private[kid] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        claims = {"sub": "p", "exp": int(time.time()) + 900}
        return jwt.encode(claims, self.private[kid], algorithm="RS256", headers={"kid": kid})

    def get_signing_keys(self, refresh: bool = False) -> List[PyJWK]:
        self.fetches += 1
        if self.down:
            raise PyJWKClientConnectionError("cannot reach the JWKS endpoint")

        keys: List[PyJWK] = []
        for kid in self.published:
            jwk = RSAAlgorithm.to_jwk(self.private[kid].public_key(), as_dict=True)
            jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
            keys.append(PyJWK(jwk))
        return keys


def started() -> tuple[Identity, Clock, SigningKeySet]:
    identity = Identity()
    identity.publish("k1")
    clock = Clock()
    keys = SigningKeySet(cast(PyJWKClient, identity), clock=clock)
    keys.key_for(identity.sign("k1"))
    return identity, clock, keys


def test_a_known_key_is_answered_without_asking_identity() -> None:
    identity, _, keys = started()

    keys.key_for(identity.sign("k1"))
    keys.key_for(identity.sign("k1"))

    assert identity.fetches == 1


def test_unknown_keys_do_not_make_identity_answer_every_request() -> None:
    identity, _, keys = started()

    for i in range(50):
        with pytest.raises(PyJWKClientError, match="Unable to find a signing key that matches"):
            keys.key_for(identity.sign(f"forged-{i}"))

    assert identity.fetches == 1


def test_an_unknown_key_is_looked_for_again_once_the_interval_has_passed() -> None:
    identity, clock, keys = started()
    identity.publish("k2")
    clock.now += SigningKeySet.UNKNOWN_KEY_REFRESH_SECONDS + 1

    assert keys.key_for(identity.sign("k2")).key_id == "k2"
    with pytest.raises(PyJWKClientError):
        keys.key_for(identity.sign("forged"))

    assert identity.fetches == 2


def test_identity_that_cannot_be_reached_is_reported_as_such_and_not_asked_again() -> None:
    identity, clock, keys = started()
    identity.down = True
    clock.now += SigningKeySet.UNKNOWN_KEY_REFRESH_SECONDS + 1

    with pytest.raises(PyJWKClientConnectionError):
        keys.key_for(identity.sign("k2"))
    with pytest.raises(PyJWKClientConnectionError):
        keys.key_for(identity.sign("k3"))

    assert identity.fetches == 2
    assert keys.key_for(identity.sign("k1")).key_id == "k1"


def test_a_token_that_names_no_key_is_refused_without_asking_identity() -> None:
    identity, _, keys = started()
    token = jwt.encode({"sub": "p"}, identity.private["k1"], algorithm="RS256")

    with pytest.raises(jwt.InvalidTokenError):
        keys.key_for(token)

    assert identity.fetches == 1


def test_identity_publishing_an_empty_key_set_is_remembered_as_identity_failing() -> None:
    client = PyJWKClient("https://identity.invalid/.well-known/jwks.json")
    object.__setattr__(client, "fetch_data", lambda: {"keys": []})
    keys = SigningKeySet(client, clock=Clock())
    token = Identity().sign("k1")

    with pytest.raises(PyJWKSetError):
        keys.key_for(token)
    with pytest.raises(PyJWKSetError):
        keys.key_for(token)
