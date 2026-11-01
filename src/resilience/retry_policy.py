"""Exponential Backoff Retry Policy with Full Jitter.

Inspired by Polly (14.3k stars) and AWS Architecture Blog Full Jitter algorithm:
sleep = uniform(0, min(max_backoff, initial_backoff * (backoff_factor ** (attempt - 1))))
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import random
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple, Type


class MaxRetriesExceededException(Exception):
    """Raised when all retry attempts fail."""

    def __init__(self, policy_name: str, attempts: int, last_exception: Exception):
        self.policy_name = policy_name
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"RetryPolicy '{policy_name}' exhausted all {attempts} attempts. "
            f"Last exception: {type(last_exception).__name__}: {last_exception}"
        )


class RetryPolicy:
    """Thread-safe Exponential Backoff Retry Policy with Full Jitter."""

    def __init__(
        self,
        name: str = "default_retry",
        max_attempts: int = 3,
        initial_backoff: float = 0.1,
        backoff_factor: float = 2.0,
        max_backoff: float = 10.0,
        retry_on: Tuple[Type[Exception], ...] = (Exception,),
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    ) -> None:
        self.name = name
        self.max_attempts = max(1, max_attempts)
        self.initial_backoff = max(0.001, initial_backoff)
        self.backoff_factor = max(1.0, backoff_factor)
        self.max_backoff = max(self.initial_backoff, max_backoff)
        self.retry_on = retry_on
        self.on_retry = on_retry

        self._lock = threading.Lock()
        self._total_executions = 0
        self._total_retries = 0
        self._total_successes = 0
        self._total_failures = 0

    def calculate_delay(self, attempt: int) -> float:
        """Compute full jitter backoff: uniform(0, min(max_backoff, initial * (factor ** (attempt-1))))."""
        ceiling = min(
            self.max_backoff,
            self.initial_backoff * (self.backoff_factor ** max(0, attempt - 1)),
        )
        return random.uniform(0.0, ceiling)

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Synchronously execute callable with exponential backoff and full jitter."""
        with self._lock:
            self._total_executions += 1

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                with self._lock:
                    self._total_successes += 1
                return result
            except self.retry_on as exc:
                last_exc = exc
                if attempt >= self.max_attempts:
                    break
                with self._lock:
                    self._total_retries += 1
                delay = self.calculate_delay(attempt)
                if self.on_retry:
                    try:
                        self.on_retry(attempt, exc, delay)
                    except Exception:
                        pass
                time.sleep(delay)

        with self._lock:
            self._total_failures += 1
        raise MaxRetriesExceededException(self.name, self.max_attempts, last_exc)  # type: ignore

    async def execute_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Asynchronously execute coroutine callable with non-blocking backoff and jitter."""
        with self._lock:
            self._total_executions += 1

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                with self._lock:
                    self._total_successes += 1
                return result
            except self.retry_on as exc:
                last_exc = exc
                if attempt >= self.max_attempts:
                    break
                with self._lock:
                    self._total_retries += 1
                delay = self.calculate_delay(attempt)
                if self.on_retry:
                    try:
                        self.on_retry(attempt, exc, delay)
                    except Exception:
                        pass
                await asyncio.sleep(delay)

        with self._lock:
            self._total_failures += 1
        raise MaxRetriesExceededException(self.name, self.max_attempts, last_exc)  # type: ignore

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator wrapping synchronous or asynchronous callables."""
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.execute_async(func, *args, **kwargs)
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.execute(func, *args, **kwargs)
        return sync_wrapper

    def get_metrics(self) -> Dict[str, Any]:
        """Return diagnostic metrics snapshot."""
        with self._lock:
            return {
                "name": self.name,
                "max_attempts": self.max_attempts,
                "total_executions": self._total_executions,
                "total_retries": self._total_retries,
                "total_successes": self._total_successes,
                "total_failures": self._total_failures,
            }
