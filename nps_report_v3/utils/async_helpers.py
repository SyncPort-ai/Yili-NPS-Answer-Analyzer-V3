"""
Async utilities and helpers for NPS V3 API.
Provides concurrency control, batch processing, and parallel execution utilities.
"""

import asyncio
import time
import logging
from collections import deque
from typing import (
    TypeVar, Generic, Callable, Awaitable,
    List, Optional, Any, Dict, Tuple
)
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from functools import wraps
import random

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class SemaphoreConfig:
    """Configuration for semaphore management"""
    max_concurrent: int = 5
    acquire_timeout: Optional[float] = None
    name: str = "default"


class SemaphoreManager:
    """
    Manage multiple semaphores for different resource pools.
    Useful for controlling concurrency at different levels.
    """

    def __init__(self):
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._configs: Dict[str, SemaphoreConfig] = {}
        self._metrics: Dict[str, Dict[str, int]] = {}

    def register(self, config: SemaphoreConfig) -> None:
        """Register a new semaphore"""
        self._semaphores[config.name] = asyncio.Semaphore(config.max_concurrent)
        self._configs[config.name] = config
        self._metrics[config.name] = {
            "acquired": 0,
            "released": 0,
            "timeouts": 0,
            "failures": 0
        }

    @asynccontextmanager
    async def acquire(self, name: str = "default"):
        """Acquire semaphore with metrics tracking"""
        if name not in self._semaphores:
            raise ValueError(f"Semaphore '{name}' not registered")

        semaphore = self._semaphores[name]
        config = self._configs[name]
        metrics = self._metrics[name]
        acquired = False

        try:
            if config.acquire_timeout:
                await asyncio.wait_for(semaphore.acquire(), timeout=config.acquire_timeout)
            else:
                await semaphore.acquire()

            acquired = True
            metrics["acquired"] += 1
            logger.debug(f"Acquired semaphore '{name}' (active: {metrics['acquired'] - metrics['released']})")

            yield

        except asyncio.TimeoutError:
            metrics["timeouts"] += 1
            logger.warning(f"Timeout acquiring semaphore '{name}'")
            raise
        except Exception as e:
            metrics["failures"] += 1
            logger.error(f"Error with semaphore '{name}': {e}")
            raise
        finally:
            if acquired:
                semaphore.release()
                metrics["released"] += 1
                logger.debug(f"Released semaphore '{name}'")

    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for semaphores"""
        if name:
            return self._metrics.get(name, {})
        return dict(self._metrics)


class AsyncBatchProcessor(Generic[T, R]):
    """
    Process items in batches asynchronously with error handling.
    Useful for processing large datasets efficiently.
    """

    def __init__(
        self,
        processor: Callable[[T], Awaitable[R]],
        batch_size: int = 10,
        max_concurrent_batches: int = 3,
        error_handler: Optional[Callable[[T, Exception], Awaitable[Optional[R]]]] = None
    ):
        self.processor = processor
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.error_handler = error_handler
        self._semaphore = asyncio.Semaphore(max_concurrent_batches)

    async def process_batch(self, batch: List[T]) -> List[Tuple[T, Optional[R], Optional[Exception]]]:
        """Process a single batch with error handling"""
        results = []

        for item in batch:
            try:
                result = await self.processor(item)
                results.append((item, result, None))
            except Exception as e:
                logger.error(f"Error processing item {item}: {e}")

                if self.error_handler:
                    try:
                        fallback_result = await self.error_handler(item, e)
                        results.append((item, fallback_result, e))
                    except Exception as handler_error:
                        logger.error(f"Error handler failed: {handler_error}")
                        results.append((item, None, handler_error))
                else:
                    results.append((item, None, e))

        return results

    async def process_all(
        self,
        items: List[T],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Tuple[T, Optional[R], Optional[Exception]]]:
        """Process all items in batches"""
        # Split into batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        all_results = []
        completed_items = 0
        total_items = len(items)

        async def process_with_semaphore(batch: List[T], batch_idx: int):
            async with self._semaphore:
                logger.debug(f"Processing batch {batch_idx + 1}/{len(batches)}")
                results = await self.process_batch(batch)

                nonlocal completed_items
                completed_items += len(batch)

                if progress_callback:
                    progress_callback(completed_items, total_items)

                return results

        # Process batches concurrently
        batch_tasks = [
            process_with_semaphore(batch, idx)
            for idx, batch in enumerate(batches)
        ]

        batch_results = await asyncio.gather(*batch_tasks)

        # Flatten results
        for batch_result in batch_results:
            all_results.extend(batch_result)

        return all_results


class ParallelExecutor:
    """
    Execute multiple async functions in parallel with various strategies.
    """

    @staticmethod
    async def gather_with_timeout(
        *coroutines: Awaitable[T],
        timeout: Optional[float] = None,
        return_exceptions: bool = True
    ) -> List[Any]:
        """Gather with optional timeout"""
        if timeout:
            return await asyncio.wait_for(
                asyncio.gather(*coroutines, return_exceptions=return_exceptions),
                timeout=timeout
            )
        return await asyncio.gather(*coroutines, return_exceptions=return_exceptions)

    @staticmethod
    async def race(*coroutines: Awaitable[T]) -> Tuple[T, List[asyncio.Task]]:
        """
        Return the result of the first completed coroutine.
        Also returns remaining tasks for cleanup.
        """
        tasks = [asyncio.create_task(coro) for coro in coroutines]

        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        # Get the first result
        first_done = done.pop()
        result = await first_done

        return result, list(pending)

    @staticmethod
    async def parallel_map(
        func: Callable[[T], Awaitable[R]],
        items: List[T],
        max_concurrent: int = 10
    ) -> List[R]:
        """
        Map a function over items with concurrency limit.
        Maintains order of results.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(item: T, index: int) -> Tuple[int, R]:
            async with semaphore:
                result = await func(item)
                return index, result

        tasks = [
            process_with_semaphore(item, idx)
            for idx, item in enumerate(items)
        ]

        results = await asyncio.gather(*tasks)

        # Sort by original index
        results.sort(key=lambda x: x[0])

        return [result for _, result in results]

    @staticmethod
    async def staggered_start(
        coroutines: List[Awaitable[T]],
        delay: float = 0.1,
        max_concurrent: int = 5
    ) -> List[T]:
        """
        Start coroutines with a staggered delay to avoid thundering herd.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def delayed_start(coro: Awaitable[T], start_delay: float) -> T:
            await asyncio.sleep(start_delay)
            async with semaphore:
                return await coro

        tasks = [
            delayed_start(coro, idx * delay)
            for idx, coro in enumerate(coroutines)
        ]

        return await asyncio.gather(*tasks)


class RetryWithBackoff:
    """
    Retry async operations with exponential backoff.
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on: Optional[Tuple[type, ...]] = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on or (Exception,)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt"""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            delay *= random.uniform(0.5, 1.5)

        return delay

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)

            except self.retry_on as e:
                last_exception = e

                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded for {func.__name__}")
                    raise

                delay = self.calculate_delay(attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{self.max_retries} for {func.__name__} "
                    f"after {delay:.2f}s delay. Error: {e}"
                )
                await asyncio.sleep(delay)

        raise last_exception

    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Decorator usage"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.execute(func, *args, **kwargs)
        return wrapper


class AsyncCircuitBreaker:
    """
    Circuit breaker pattern for async operations.
    Prevents cascading failures by temporarily blocking calls to failing services.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        recovery_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half_open

    @property
    def is_open(self) -> bool:
        """Check if circuit is open"""
        if self._state == "open":
            # Check if recovery timeout has passed
            if self._last_failure_time:
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = "half_open"
                    self._failure_count = 0
                    return False
            return True
        return False

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Call function through circuit breaker"""
        if self.is_open:
            raise RuntimeError("Circuit breaker is open")

        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )

            # Success - reset failure count
            if self._state == "half_open":
                self._state = "closed"
            self._failure_count = 0

            return result

        except Exception as e:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                self._state = "open"
                logger.error(f"Circuit breaker opened after {self._failure_count} failures")

            raise


class AsyncRateLimiter:
    """
    Rate limiter for async operations using token bucket algorithm.
    """

    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: Number of operations per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self._tokens = burst
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary"""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_update

                # Add tokens based on elapsed time
                self._tokens = min(
                    self.burst,
                    self._tokens + elapsed * self.rate
                )
                self._last_update = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    break

                # Calculate wait time
                wait_time = (tokens - self._tokens) / self.rate
                await asyncio.sleep(wait_time)

    @asynccontextmanager
    async def limit(self, tokens: int = 1):
        """Context manager for rate limiting"""
        await self.acquire(tokens)
        yield


def async_timeout(
    seconds: float,
    error_message: str = "Operation timed out"
) -> Callable:
    """
    Decorator for adding timeout to async functions.
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"{error_message}: {func.__name__}")
        return wrapper
    return decorator


async def run_in_thread_pool(
    func: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """
    Run a synchronous function in a thread pool.
    Useful for CPU-bound or blocking I/O operations.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


# Global semaphore manager instance
_semaphore_manager = SemaphoreManager()

def get_semaphore_manager() -> SemaphoreManager:
    """Get global semaphore manager instance"""
    return _semaphore_manager
