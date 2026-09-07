import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import pytest

from core.infrastructure.resilience import CircuitBreaker, CircuitOpenError, CircuitState


class PeerDown(Exception):
    """Stands in for an UNAVAILABLE RpcError; classified by the monkeypatched is_peer_fault."""


class PeerRefused(Exception):
    """Stands in for a NOT_FOUND RpcError: the peer answered, it just said no."""


@pytest.fixture(autouse=True)
def classify_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    """`is_peer_fault` needs real grpc types; these tests are about the state machine, not gRPC."""
    monkeypatch.setattr(
        "core.infrastructure.resilience.circuit_breaker.is_peer_fault",
        lambda error: isinstance(error, PeerDown),
    )


def _fail(breaker: CircuitBreaker, error: Exception) -> None:
    def raise_it() -> None:
        raise error

    with pytest.raises(type(error)):
        breaker.call(raise_it)


def test_opens_after_fail_max_peer_faults() -> None:
    breaker = CircuitBreaker("peer", fail_max=3)

    for _ in range(2):
        _fail(breaker, PeerDown())
    below_threshold = breaker.state

    _fail(breaker, PeerDown())
    at_threshold = breaker.state

    assert below_threshold is CircuitState.CLOSED
    assert at_threshold is CircuitState.OPEN


def test_open_circuit_does_not_call_the_operation() -> None:
    breaker = CircuitBreaker("peer", fail_max=1)
    _fail(breaker, PeerDown())

    calls: List[int] = []

    with pytest.raises(CircuitOpenError):
        breaker.call(lambda: calls.append(1))

    assert calls == []


def test_a_peer_that_answers_never_trips_it() -> None:
    breaker = CircuitBreaker("peer", fail_max=2)

    for _ in range(10):
        _fail(breaker, PeerRefused())

    assert breaker.state is CircuitState.CLOSED


def test_closes_again_after_success_threshold_trials() -> None:
    breaker = CircuitBreaker("peer", fail_max=1, reset_timeout=0.0, success_threshold=2)
    _fail(breaker, PeerDown())

    assert breaker.call(lambda: "first") == "first"
    after_first_trial = breaker.state

    assert breaker.call(lambda: "second") == "second"
    after_second_trial = breaker.state

    assert after_first_trial is CircuitState.HALF_OPEN
    assert after_second_trial is CircuitState.CLOSED


def test_a_failed_trial_reopens_immediately() -> None:
    breaker = CircuitBreaker("peer", fail_max=3, reset_timeout=0.0, success_threshold=2)
    for _ in range(3):
        _fail(breaker, PeerDown())

    _fail(breaker, PeerDown())
    assert breaker.state is CircuitState.OPEN


def test_half_open_admits_exactly_one_caller() -> None:
    breaker = CircuitBreaker("peer", fail_max=1, reset_timeout=0.0, success_threshold=5)
    _fail(breaker, PeerDown())

    admitted: List[int] = []
    together = threading.Barrier(5)

    def trial(index: int) -> None:
        admitted.append(index)
        time.sleep(0.5)

    def attempt(index: int) -> bool:
        together.wait()
        try:
            breaker.call(lambda: trial(index))
            return True
        except CircuitOpenError:
            return False

    with ThreadPoolExecutor(max_workers=5) as executor:
        outcomes = list(executor.map(attempt, range(5)))

    assert len(admitted) == 1
    assert outcomes.count(True) == 1


def test_the_lock_is_not_held_across_the_call() -> None:
    """The reason this breaker exists rather than an off-the-shelf one."""
    breaker = CircuitBreaker("peer")

    with ThreadPoolExecutor(max_workers=10) as executor:
        started = time.perf_counter()
        list(executor.map(lambda _: breaker.call(lambda: time.sleep(0.2)), range(10)))
        elapsed = time.perf_counter() - started

    assert elapsed < 1.0
