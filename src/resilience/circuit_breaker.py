"""Circuit Breaker Pattern Implementation (Fowler State Machine).

Inspired by App-vNext/Polly (14.3k stars) and Netflix Hystrix / Resilience4j.
Provides thread-safe state transitions across CLOSED, OPEN, and HALF-OPEN.
"""

from __future__ import annotations

import functools
import inspect
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, Type


class CircuitState(str, Enum):
    """Fowler circuit breaker operational states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when call is blocked because the circuit breaker is in OPEN state."""

    def __init__(self, breaker_name: str, state: CircuitState, remaining_cooldown: float):
        self.breaker_name = breaker_name
        self.state = state
        self.remaining_cooldown = max(0.0, remaining_cooldown)
        msg = (
            f"CircuitBreaker '{breaker_name}' is OPEN. "
            f"Call fast-failed ({self.remaining_cooldown:.2f}s cooldown remaining)."
        )
        super().__init__(msg)


class CircuitBreaker:
    """Thread-safe Circuit Breaker enforcing failure threshold and recovery cooldown."""

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_trials: int = 1,
        expected_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> None:
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = max(0.01, recovery_timeout)
        self.half_open_trials = max(1, half_open_trials)
        self.expected_exceptions = expected_exceptions

        self._lock = threading.RLock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._consecutive_successes = 0
        self._last_state_change = time.time()
        self._last_failure_time: Optional[float] = None
        self._total_calls = 0
        self._rejected_calls = 0

    @property
    def state(self) -> CircuitState:
        """Evaluate and return current state with auto-transition to HALF-OPEN."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.time() - self._last_state_change
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._consecutive_successes = 0
                    self._last_state_change = time.time()
            return self._state

    def is_call_permitted(self) -> bool:
        """Check if incoming execution is allowed under current state."""
        with self._lock:
            current_state = self.state
            if current_state == CircuitState.OPEN:
                self._rejected_calls += 1
                return False
            return True

    def record_success(self) -> None:
        """Record successful execution and update state machine counters."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._consecutive_successes += 1
                if self._consecutive_successes >= self.half_open_trials:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._consecutive_successes = 0
                    self._last_state_change = time.time()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self, exc: Exception) -> None:
        """Record failed execution. Increment failure count or reopen circuit."""
        with self._lock:
            if not isinstance(exc, self.expected_exceptions):
                return
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._last_state_change = time.time()

    def trip(self) -> None:
        """Manually force the circuit breaker into OPEN state."""
        with self._lock:
            self._state = CircuitState.OPEN
            self._last_state_change = time.time()

    def reset(self) -> None:
        """Manually reset the circuit breaker back to CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._consecutive_successes = 0
            self._last_state_change = time.time()

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Synchronously execute callable protected by circuit breaker."""
        with self._lock:
            self._total_calls += 1
            if not self.is_call_permitted():
                elapsed = time.time() - self._last_state_change
                remaining = self.recovery_timeout - elapsed
                raise CircuitBreakerOpenException(self.name, self._state, remaining)

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise

    async def call_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Asynchronously execute coroutine callable protected by circuit breaker."""
        with self._lock:
            self._total_calls += 1
            if not self.is_call_permitted():
                elapsed = time.time() - self._last_state_change
                remaining = self.recovery_timeout - elapsed
                raise CircuitBreakerOpenException(self.name, self._state, remaining)

        try:
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator wrapping synchronous or asynchronous callables."""
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.call_async(func, *args, **kwargs)
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call(func, *args, **kwargs)
        return sync_wrapper

    def get_metrics(self) -> Dict[str, Any]:
        """Return diagnostic metrics snapshot."""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "total_calls": self._total_calls,
                "rejected_calls": self._rejected_calls,
                "last_state_change": self._last_state_change,
            }
