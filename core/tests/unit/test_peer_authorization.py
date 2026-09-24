from __future__ import annotations

from typing import Dict, List, Optional, cast

import grpc
import pytest

from core.infrastructure.security.allowed_peers import allowed_peers
from core.infrastructure.security.peer_authorization_interceptor import (
    PeerAuthorizationInterceptor,
    service_of,
    trust_domains,
)
from core.infrastructure.security.service_identity_error import ServiceIdentityError


class FakeContext:
    def __init__(self, sans: List[bytes]) -> None:
        self._auth: Dict[str, List[bytes]] = {"x509_subject_alternative_name": sans}
        self.aborted: Optional[str] = None

    def auth_context(self) -> Dict[str, List[bytes]]:
        return self._auth

    def abort(self, code: grpc.StatusCode, detail: str) -> None:
        self.aborted = detail
        raise grpc.RpcError(detail)


class FakeCallDetails:
    def __init__(self, method: str) -> None:
        self.method = method
        self.invocation_metadata: List[object] = []


def handler_for(calls: List[str]) -> grpc.RpcMethodHandler[object, object]:
    def behaviour(request: object, context: grpc.ServicerContext) -> str:
        calls.append("served")
        return "answered"

    return grpc.unary_unary_rpc_method_handler(behaviour)


def details(method: str) -> grpc.HandlerCallDetails:
    return cast(grpc.HandlerCallDetails, FakeCallDetails(method))


def served_by(handler: grpc.RpcMethodHandler[object, object], context: FakeContext) -> None:
    behaviour = handler.unary_unary
    assert behaviour is not None
    behaviour(object(), cast(grpc.ServicerContext, context))


def spiffe(service: str) -> bytes:
    return f"spiffe://kinetix.local/service/{service}".encode()


class TestAllowedPeers:
    def test_it_reads_a_comma_separated_list(self) -> None:
        assert allowed_peers("search, order ,warehouse") == frozenset(
            {"search", "order", "warehouse"}
        )

    def test_an_unset_list_is_refused_rather_than_read_as_allow_all(self) -> None:
        with pytest.raises(ServiceIdentityError):
            allowed_peers("")

    def test_a_list_of_separators_is_refused_too(self) -> None:
        with pytest.raises(ServiceIdentityError):
            allowed_peers(" , , ")


class TestServiceOf:
    def test_it_reads_the_service_out_of_a_spiffe_id(self) -> None:
        assert service_of([b"kinetix-search-service", spiffe("search")]) == "search"

    def test_a_dns_name_alone_names_nobody(self) -> None:
        assert service_of([b"kinetix-search-service"]) is None

    def test_no_certificate_names_nobody(self) -> None:
        assert service_of([]) is None

    def test_an_id_from_another_trust_domain_names_nobody(self) -> None:
        foreign = b"spiffe://prod.kinetix/service/search"

        assert service_of([foreign]) is None

    def test_a_cutover_can_accept_both_domains_at_once(self) -> None:
        both = ("kinetix.local", "prod.kinetix")

        assert service_of([b"spiffe://prod.kinetix/service/search"], both) == "search"
        assert service_of([spiffe("search")], both) == "search"

    def test_a_domain_this_one_is_merely_a_prefix_of_is_refused(self) -> None:
        assert service_of([b"spiffe://kinetix.local.example.com/service/search"]) is None

    def test_a_path_is_not_a_service_name(self) -> None:
        assert service_of([b"spiffe://kinetix.local/service/a/b"]) is None

    def test_an_id_that_names_no_service_is_refused(self) -> None:
        assert service_of([b"spiffe://kinetix.local/service/"]) is None
        assert service_of([b"spiffe://kinetix.local/agent/search"]) is None


class TestTrustDomains:
    def test_an_unset_variable_is_the_domain_the_estate_runs_today(self) -> None:
        assert trust_domains() == ("kinetix.local",)

    def test_it_reads_a_comma_separated_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KINETIX_TRUST_DOMAIN", "kinetix.local, prod.kinetix ")

        assert trust_domains() == ("kinetix.local", "prod.kinetix")

    def test_a_list_of_separators_falls_back_rather_than_accepting_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KINETIX_TRUST_DOMAIN", " , , ")

        assert trust_domains() == ("kinetix.local",)


class TestPeerAuthorization:
    def interceptor(self) -> PeerAuthorizationInterceptor:
        return PeerAuthorizationInterceptor(frozenset({"search"}))

    def test_a_named_caller_is_served(self) -> None:
        calls: List[str] = []
        handler = self.interceptor().intercept_service(
            lambda _: handler_for(calls),
            details("/catalog.v1.CatalogService/ChangedSince"),
        )

        assert handler is not None
        served_by(handler, FakeContext([spiffe("search")]))
        assert calls == ["served"]

    def test_a_caller_nobody_named_is_refused(self) -> None:
        calls: List[str] = []
        handler = self.interceptor().intercept_service(
            lambda _: handler_for(calls),
            details("/catalog.v1.CatalogService/ChangedSince"),
        )
        context = FakeContext([spiffe("review")])

        assert handler is not None
        with pytest.raises(grpc.RpcError):
            served_by(handler, context)

        assert context.aborted is not None
        assert calls == [], "a refused call must not reach the repository"

    def test_a_caller_with_no_spiffe_id_is_refused(self) -> None:
        calls: List[str] = []
        handler = self.interceptor().intercept_service(
            lambda _: handler_for(calls),
            details("/catalog.v1.CatalogService/ChangedSince"),
        )
        context = FakeContext([b"kinetix-search-service"])

        assert handler is not None
        with pytest.raises(grpc.RpcError):
            served_by(handler, context)

        assert calls == []

    def test_the_health_probe_is_left_open(self) -> None:
        calls: List[str] = []
        handler = self.interceptor().intercept_service(
            lambda _: handler_for(calls),
            details("/grpc.health.v1.Health/Check"),
        )

        assert handler is not None
        served_by(handler, FakeContext([]))
        assert calls == ["served"], "the container's own probe holds no allow-list entry"
