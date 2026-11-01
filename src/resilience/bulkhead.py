"""Bulkhead Isolation Pattern (Bounded Semaphore Concurrency Limiter).

Inspired by Resilience4j Bulkhead (10.8k stars) and Polly Bulkhead (14.3k stars).
Prevents cascading thread starvation and isolates resource-heavy calls.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import threading
from typing import Any, Callable, Dict


class BulkheadFullException(Exception):
    """Raised when maximum concurrent capacity has been reached."""

    def __init__(self, bulkhead_name: str, max_concurrent: int):
        self.bulkhead_name = bulkhead_name
        self.max_concurrent = max_concurrent
        super().__init__(
            f"Bulkhead '{bulkhead_name}' is saturated. "
            f"Max concurrent execution limit ({max_concurrent}) exceeded."
        )


class Bulkhead:
    """Thread-safe Bulkhead concurrency limiter preventing resource exhaustion."""

    def __init__(
        self,
        name: str = "default_bulkhead",
        max_concurrent_calls: int = 10,
        max_wait_duration: float = 0.5,
    ) -> None:
        self.name = name
        self.max_concurrent_calls = max(1, max_concurrent_calls)
        self.max_wait_duration = max(0.0, max_wait_duration)

        self._semaphore = threading.BoundedSemaphore(self.max_concurrent_calls)
        self._async_semaphore: asyncio.Semaphore | None = None
        self._lock = threading.Lock()
        self._active_calls = 0
        self._total_calls = 0
        self._rejected_calls = 0

    @property
    def active_calls(self) -> int:
        """Currently running executions inside the bulkhead."""
        with self._lock:
            return self._active_calls

    @property
    def available_permits(self) -> int:
        """Number of remaining execution permits."""
        with self._lock:
            return max(0, self.max_concurrent_calls - self._active_calls)

    def acquire(self) -> bool:
        """Attempt to acquire execution permit within timeout."""
        with self._lock:
            self._total_calls += 1

        acquired = self._semaphore.acquire(timeout=self.max_wait_duration)
        with self._lock:
            if acquired:
                self._active_calls += 1
            else:
                self._rejected_calls += 1
        return acquired

    def release(self) -> None:
        """Release execution permit."""
        try:
            self._semaphore.release()
        except ValueError:
            pass
        with self._lock:
            self._active_calls = max(0, self._active_calls - 1)

    def __enter__(self) -> Bulkhead:
        if not self.acquire():
            raise BulkheadFullException(self.name, self.max_concurrent_calls)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()

    async def __aenter__(self) -> Bulkhead:
        with self._lock:
            self._total_calls += 1
            if self._active_calls >= self.max_concurrent_calls:
                self._rejected_calls += 1
                raise BulkheadFullException(self.name, self.max_concurrent_calls)
            self._active_calls += 1
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        with self._lock:
            self._active_calls = max(0, self._active_calls - 1)

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute callable synchronously guarded by bulkhead."""
        with self:
            return func(*args, **kwargs)

    async def execute_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute callable asynchronously guarded by bulkhead."""
        async with self:
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator wrapping synchronous or asynchronous functions."""
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
                "max_concurrent_calls": self.max_concurrent_calls,
                "active_calls": self._active_calls,
                "available_permits": max(0, self.max_concurrent_calls - self._active_calls),
                "total_calls": self._total_calls,
                "rejected_calls": self._rejected_calls,
            }
