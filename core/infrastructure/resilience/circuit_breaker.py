import logging
import threading
from time import monotonic
from typing import Callable, TypeVar

from core.infrastructure.resilience.circuit_open_error import CircuitOpenError
from core.infrastructure.resilience.circuit_state import CircuitState
from core.infrastructure.resilience.is_peer_fault import is_peer_fault

logger = logging.getLogger(__name__)

T = TypeVar("T")

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        fail_max: int = 3,
        reset_timeout: float = 15.0,
        success_threshold: int = 2,
    ) -> None:
        self._name: str = name
        self._fail_max: int = fail_max
        self._reset_timeout: float = reset_timeout
        self._success_threshold: int = success_threshold

        self._lock: threading.Lock = threading.Lock()
        self._state: CircuitState = CircuitState.CLOSED
        self._failures: int = 0
        self._successes: int = 0
        self._opened_at: float = 0.0
        self._trial_in_flight: bool = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    def call(self, operation: Callable[[], T]) -> T:
        is_trial = self._admit()
        healthy = True
        try:
            result = operation()
        except Exception as error:
            healthy = not is_peer_fault(error)
            raise
        finally:
            self._settle(is_trial, healthy=healthy)

        return result

    def _admit(self) -> bool:
        with self._lock:
            if self._state is CircuitState.OPEN:
                if monotonic() - self._opened_at < self._reset_timeout:
                    raise CircuitOpenError(self._name)

                self._state = CircuitState.HALF_OPEN
                self._successes = 0
                logger.info("circuit '%s' is half-open; admitting one trial call", self._name)

            if self._state is CircuitState.HALF_OPEN:
                if self._trial_in_flight:
                    raise CircuitOpenError(self._name)

                self._trial_in_flight = True
                return True

            return False

    def _settle(self, was_trial: bool, healthy: bool) -> None:
        with self._lock:
            if was_trial:
                self._trial_in_flight = False

            if not healthy:
                self._successes = 0
                if self._state is CircuitState.OPEN:
                    return

                self._failures += 1
                if self._state is CircuitState.HALF_OPEN or self._failures >= self._fail_max:
                    self._trip()
                return

            self._failures = 0
            if self._state is CircuitState.HALF_OPEN:
                self._successes += 1
                if self._successes >= self._success_threshold:
                    self._state = CircuitState.CLOSED
                    self._successes = 0
                    logger.info("circuit '%s' closed; the peer is answering again", self._name)

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = monotonic()
        self._failures = 0
        self._successes = 0
        logger.warning(
            "circuit '%s' opened; calls fail fast for the next %.0fs",
            self._name,
            self._reset_timeout,
        )
