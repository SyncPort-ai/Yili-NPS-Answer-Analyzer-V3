"""Unit tests for async utilities and helpers"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from nps_report_v3.utils.async_helpers import (
    SemaphoreConfig, SemaphoreManager,
    AsyncBatchProcessor, ParallelExecutor,
    RetryWithBackoff, AsyncCircuitBreaker,
    AsyncRateLimiter, async_timeout,
    run_in_thread_pool
)


class TestSemaphoreManager:
    """Test SemaphoreManager class"""

    @pytest.mark.asyncio
    async def test_register_and_acquire(self):
        manager = SemaphoreManager()
        config = SemaphoreConfig(max_concurrent=2, name="test")
        manager.register(config)

        # Test acquiring and releasing
        async with manager.acquire("test"):
            metrics = manager.get_metrics("test")
            assert metrics["acquired"] == 1
            assert metrics["released"] == 0

        metrics = manager.get_metrics("test")
        assert metrics["released"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        manager = SemaphoreManager()
        config = SemaphoreConfig(max_concurrent=2, name="limited")
        manager.register(config)

        counter = {"value": 0, "max": 0}

        async def task():
            async with manager.acquire("limited"):
                counter["value"] += 1
                counter["max"] = max(counter["max"], counter["value"])
                await asyncio.sleep(0.01)
                counter["value"] -= 1

        # Run 5 tasks concurrently, but only 2 should run at once
        tasks = [task() for _ in range(5)]
        await asyncio.gather(*tasks)

        assert counter["max"] <= 2

    @pytest.mark.asyncio
    async def test_acquire_timeout(self):
        manager = SemaphoreManager()
        config = SemaphoreConfig(
            max_concurrent=1,
            name="timeout_test",
            acquire_timeout=0.01
        )
        manager.register(config)

        async def hold_semaphore():
            async with manager.acquire("timeout_test"):
                await asyncio.sleep(0.1)

        # Start holding task
        holder = asyncio.create_task(hold_semaphore())

        # Ensure holder task acquires the semaphore before attempting another acquire
        await asyncio.sleep(0.02)

        # Try to acquire with timeout
        with pytest.raises(asyncio.TimeoutError):
            async with manager.acquire("timeout_test"):
                pass

        await holder


class TestAsyncBatchProcessor:
    """Test AsyncBatchProcessor class"""

    @pytest.mark.asyncio
    async def test_process_batch(self):
        async def processor(item):
            return item * 2

        batch_processor = AsyncBatchProcessor(
            processor=processor,
            batch_size=3
        )

        items = [1, 2, 3, 4, 5]
        results = await batch_processor.process_all(items)

        # Check results
        assert len(results) == 5
        for i, (item, result, error) in enumerate(results):
            assert item == i + 1
            assert result == (i + 1) * 2
            assert error is None

    @pytest.mark.asyncio
    async def test_error_handling(self):
        async def processor(item):
            if item == 3:
                raise ValueError("Test error")
            return item * 2

        async def error_handler(item, error):
            return -1  # Fallback value

        batch_processor = AsyncBatchProcessor(
            processor=processor,
            batch_size=2,
            error_handler=error_handler
        )

        items = [1, 2, 3, 4, 5]
        results = await batch_processor.process_all(items)

        # Check that item 3 has error and fallback value
        for item, result, error in results:
            if item == 3:
                assert result == -1
                assert error is not None
            else:
                assert result == item * 2
                assert error is None

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        async def processor(item):
            await asyncio.sleep(0.001)
            return item

        progress_updates = []

        def progress_callback(completed, total):
            progress_updates.append((completed, total))

        batch_processor = AsyncBatchProcessor(
            processor=processor,
            batch_size=2
        )

        items = list(range(5))
        await batch_processor.process_all(items, progress_callback)

        assert len(progress_updates) > 0
        assert progress_updates[-1] == (5, 5)


class TestParallelExecutor:
    """Test ParallelExecutor class"""

    @pytest.mark.asyncio
    async def test_gather_with_timeout(self):
        async def fast_task():
            await asyncio.sleep(0.01)
            return "fast"

        async def slow_task():
            await asyncio.sleep(1)
            return "slow"

        # Test timeout
        with pytest.raises(asyncio.TimeoutError):
            await ParallelExecutor.gather_with_timeout(
                fast_task(),
                slow_task(),
                timeout=0.05
            )

        # Test without timeout
        results = await ParallelExecutor.gather_with_timeout(
            fast_task(),
            fast_task(),
            timeout=0.1
        )
        assert all(r == "fast" for r in results)

    @pytest.mark.asyncio
    async def test_race(self):
        async def task1():
            await asyncio.sleep(0.01)
            return "first"

        async def task2():
            await asyncio.sleep(0.1)
            return "second"

        result, pending = await ParallelExecutor.race(
            task1(),
            task2()
        )

        assert result == "first"
        assert len(pending) == 1

        # Clean up pending tasks
        for task in pending:
            task.cancel()

    @pytest.mark.asyncio
    async def test_parallel_map(self):
        async def square(x):
            await asyncio.sleep(0.001)
            return x * x

        items = list(range(10))
        results = await ParallelExecutor.parallel_map(
            square,
            items,
            max_concurrent=3
        )

        assert results == [x * x for x in items]

    @pytest.mark.asyncio
    async def test_staggered_start(self):
        start_times = []

        async def track_start():
            start_times.append(time.time())
            return len(start_times)

        coroutines = [track_start() for _ in range(5)]
        results = await ParallelExecutor.staggered_start(
            coroutines,
            delay=0.01,
            max_concurrent=2
        )

        assert len(results) == 5
        # Check that starts were staggered
        for i in range(1, len(start_times)):
            assert start_times[i] >= start_times[i-1]


class TestRetryWithBackoff:
    """Test RetryWithBackoff class"""

    @pytest.mark.asyncio
    async def test_successful_retry(self):
        call_count = {"count": 0}

        async def flaky_function():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ValueError("Temporary error")
            return "success"

        retrier = RetryWithBackoff(
            max_retries=3,
            initial_delay=0.01
        )

        result = await retrier.execute(flaky_function)
        assert result == "success"
        assert call_count["count"] == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        async def always_fails():
            raise ValueError("Permanent error")

        retrier = RetryWithBackoff(
            max_retries=2,
            initial_delay=0.01
        )

        with pytest.raises(ValueError, match="Permanent error"):
            await retrier.execute(always_fails)

    @pytest.mark.asyncio
    async def test_decorator_usage(self):
        call_count = {"count": 0}

        @RetryWithBackoff(max_retries=2, initial_delay=0.01)
        async def decorated_function():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise ValueError("Retry me")
            return "done"

        result = await decorated_function()
        assert result == "done"
        assert call_count["count"] == 2


class TestAsyncCircuitBreaker:
    """Test AsyncCircuitBreaker class"""

    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        breaker = AsyncCircuitBreaker(
            failure_threshold=3,
            timeout=0.1,
            recovery_timeout=0.05
        )

        async def failing_function():
            raise ValueError("Error")

        # Cause failures to open circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(failing_function)

        # Circuit should be open now
        assert breaker.is_open
        with pytest.raises(RuntimeError, match="Circuit breaker is open"):
            await breaker.call(failing_function)

    @pytest.mark.asyncio
    async def test_circuit_recovery(self):
        breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            timeout=0.1,
            recovery_timeout=0.05
        )

        call_count = {"count": 0}

        async def sometimes_fails():
            call_count["count"] += 1
            if call_count["count"] <= 2:
                raise ValueError("Error")
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(sometimes_fails)

        assert breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(0.06)

        # Circuit should be half-open, next call should succeed
        result = await breaker.call(sometimes_fails)
        assert result == "success"
        assert not breaker.is_open


class TestAsyncRateLimiter:
    """Test AsyncRateLimiter class"""

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        limiter = AsyncRateLimiter(rate=10, burst=2)  # 10 per second, burst of 2

        start_time = time.time()
        times = []

        for _ in range(5):
            async with limiter.limit():
                times.append(time.time() - start_time)

        # First 2 should be immediate (burst)
        assert times[0] < 0.01
        assert times[1] < 0.01

        # Rest should be rate limited
        for i in range(2, 5):
            assert times[i] > times[i-1]

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self):
        limiter = AsyncRateLimiter(rate=5, burst=5)

        # Acquire all tokens at once
        await limiter.acquire(5)

        # Next acquire should wait
        start = time.time()
        await limiter.acquire(1)
        elapsed = time.time() - start

        # Should wait approximately 1/5 second
        assert elapsed >= 0.15  # Allow some tolerance


class TestAsyncTimeout:
    """Test async_timeout decorator"""

    @pytest.mark.asyncio
    async def test_timeout_decorator(self):
        @async_timeout(0.05, "Custom timeout message")
        async def slow_function():
            await asyncio.sleep(0.1)
            return "done"

        with pytest.raises(TimeoutError, match="Custom timeout message"):
            await slow_function()

        @async_timeout(0.1)
        async def fast_function():
            await asyncio.sleep(0.01)
            return "done"

        result = await fast_function()
        assert result == "done"


class TestRunInThreadPool:
    """Test run_in_thread_pool function"""

    @pytest.mark.asyncio
    async def test_sync_function_in_thread(self):
        def cpu_bound_task(n):
            # Simulate CPU-bound work
            total = 0
            for i in range(n):
                total += i
            return total

        result = await run_in_thread_pool(cpu_bound_task, 1000)
        assert result == sum(range(1000))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
