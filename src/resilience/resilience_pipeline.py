"""Unified Resilience Pipeline Architecture.

Chains Bulkhead -> Circuit Breaker -> Retry Policy -> Target Call -> Fallback Handler.
Inspired by App-vNext/Polly (14.3k stars) and Cockatiel (1.8k stars).
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Dict, Optional

from src.resilience.bulkhead import Bulkhead
from src.resilience.circuit_breaker import CircuitBreaker
from src.resilience.retry_policy import RetryPolicy


class ResiliencePipeline:
    """Unified fault-tolerance pipeline orchestrating isolation, state-machine, and retries."""

    def __init__(
        self,
        name: str = "default_pipeline",
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_policy: Optional[RetryPolicy] = None,
        bulkhead: Optional[Bulkhead] = None,
        fallback: Optional[Callable[[Exception], Any]] = None,
    ) -> None:
        self.name = name
        self.circuit_breaker = circuit_breaker
        self.retry_policy = retry_policy
        self.bulkhead = bulkhead
        self.fallback = fallback

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Synchronously execute func through bulkhead, breaker, retry, and fallback."""
        def _core_invocation() -> Any:
            def _with_retry() -> Any:
                if self.retry_policy:
                    return self.retry_policy.execute(func, *args, **kwargs)
                return func(*args, **kwargs)

            if self.circuit_breaker:
                return self.circuit_breaker.call(_with_retry)
            return _with_retry()

        try:
            if self.bulkhead:
                return self.bulkhead.execute(_core_invocation)
            return _core_invocation()
        except Exception as exc:
            if self.fallback is not None:
                return self.fallback(exc)
            raise

    async def execute_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Asynchronously execute coroutine func through resilience pipeline."""
        async def _core_async_invocation() -> Any:
            async def _with_retry_async() -> Any:
                if self.retry_policy:
                    return await self.retry_policy.execute_async(func, *args, **kwargs)
                if inspect.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            if self.circuit_breaker:
                return await self.circuit_breaker.call_async(_with_retry_async)
            return await _with_retry_async()

        try:
            if self.bulkhead:
                return await self.bulkhead.execute_async(_core_async_invocation)
            return await _core_async_invocation()
        except Exception as exc:
            if self.fallback is not None:
                if inspect.iscoroutinefunction(self.fallback):
                    return await self.fallback(exc)
                return self.fallback(exc)
            raise

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator for protecting synchronous or asynchronous functions."""
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.execute_async(func, *args, **kwargs)
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.execute(func, *args, **kwargs)
        return sync_wrapper

    def get_status(self) -> Dict[str, Any]:
        """Collect diagnostic metrics from configured pipeline components."""
        return {
            "name": self.name,
            "circuit_breaker": self.circuit_breaker.get_metrics() if self.circuit_breaker else None,
            "retry_policy": self.retry_policy.get_metrics() if self.retry_policy else None,
            "bulkhead": self.bulkhead.get_metrics() if self.bulkhead else None,
            "has_fallback": self.fallback is not None,
        }


class ResiliencePipelineBuilder:
    """Fluent builder for composing tailored Resilience Pipelines."""

    def __init__(self, name: str = "pipeline") -> None:
        self._name = name
        self._circuit_breaker: Optional[CircuitBreaker] = None
        self._retry_policy: Optional[RetryPolicy] = None
        self._bulkhead: Optional[Bulkhead] = None
        self._fallback: Optional[Callable[[Exception], Any]] = None

    def add_circuit_breaker(self, breaker: CircuitBreaker) -> ResiliencePipelineBuilder:
        self._circuit_breaker = breaker
        return self

    def add_retry_policy(self, retry: RetryPolicy) -> ResiliencePipelineBuilder:
        self._retry_policy = retry
        return self

    def add_bulkhead(self, bulkhead: Bulkhead) -> ResiliencePipelineBuilder:
        self._bulkhead = bulkhead
        return self

    def with_fallback(self, fallback: Callable[[Exception], Any]) -> ResiliencePipelineBuilder:
        self._fallback = fallback
        return self

    def build(self) -> ResiliencePipeline:
        return ResiliencePipeline(
            name=self._name,
            circuit_breaker=self._circuit_breaker,
            retry_policy=self._retry_policy,
            bulkhead=self._bulkhead,
            fallback=self._fallback,
        )
