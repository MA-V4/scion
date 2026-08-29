from __future__ import annotations

import time

from gateway.reliability.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_opens_after_threshold_failures():
    cb = CircuitBreaker(name="test", failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_circuit_transitions_to_half_open_after_timeout():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_s=0.01)
    cb.record_failure()
    time.sleep(0.02)
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_closes_after_success_in_half_open():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout_s=0.01)
    cb.record_failure()
    time.sleep(0.02)
    _ = cb.state  # trigger transition to half_open
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
