"""Unit tests for monitoring and profiling"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
import psutil

from nps_report_v3.monitoring.profiler import (
    MemoryMonitor, ExecutionProfiler, MetricsCollector,
    WorkflowProfiler, profile_async, profile_sync,
    PerformanceMetric, ExecutionProfile
)


class TestMemoryMonitor:
    """Test MemoryMonitor class"""

    def test_get_memory_usage(self):
        monitor = MemoryMonitor()

        memory_mb = monitor.get_memory_usage_mb()
        assert memory_mb > 0
        assert isinstance(memory_mb, float)

    def test_get_memory_percent(self):
        monitor = MemoryMonitor()

        memory_percent = monitor.get_memory_percent()
        assert 0 <= memory_percent <= 100
        assert isinstance(memory_percent, float)

    def test_check_memory_pressure(self):
        monitor = MemoryMonitor(threshold_mb=10)  # Very low threshold

        # Should exceed threshold
        assert monitor.check_memory_pressure() is True

        monitor.threshold_mb = 100000  # Very high threshold
        assert monitor.check_memory_pressure() is False

    def test_memory_delta(self):
        monitor = MemoryMonitor()
        baseline = monitor.baseline_mb

        delta = monitor.get_memory_delta_mb()
        assert abs(delta) < 10  # Should be small initially

        # Reset baseline
        monitor.reset_baseline()
        delta_after_reset = monitor.get_memory_delta_mb()
        assert abs(delta_after_reset) < 1  # Should be near zero


class TestExecutionProfiler:
    """Test ExecutionProfiler class"""

    def test_start_and_end_profile(self):
        profiler = ExecutionProfiler()

        profile = profiler.start_profile("test_operation", {"key": "value"})
        assert profile.name == "test_operation"
        assert profile.start_time > 0
        assert profile.memory_before_mb > 0
        assert profile.metadata["key"] == "value"

        time.sleep(0.01)  # Small delay
        profiler.end_profile(profile)

        assert profile.end_time > profile.start_time
        assert profile.duration_ms > 0
        assert profile.memory_after_mb > 0
        assert profile.memory_delta_mb is not None

    def test_profile_with_error(self):
        profiler = ExecutionProfiler()

        profile = profiler.start_profile("error_operation")
        profiler.end_profile(profile, error="Test error")

        assert profile.error == "Test error"
        assert len(profiler.profiles) == 1

    def test_get_summary(self):
        profiler = ExecutionProfiler()

        # Empty summary
        assert profiler.get_summary() == {}

        # Add some profiles
        profile1 = profiler.start_profile("op1")
        time.sleep(0.01)
        profiler.end_profile(profile1)

        profile2 = profiler.start_profile("op2")
        time.sleep(0.02)
        profiler.end_profile(profile2)

        summary = profiler.get_summary()
        assert summary["total_operations"] == 2
        assert summary["total_duration_ms"] > 0
        assert "average_duration_ms" in summary
        assert "slowest_operation" in summary


class TestMetricsCollector:
    """Test MetricsCollector class"""

    def test_increment_counter(self):
        collector = MetricsCollector()

        collector.increment_counter("requests")
        collector.increment_counter("requests")
        collector.increment_counter("errors", 3)

        assert collector.counters["requests"] == 2
        assert collector.counters["errors"] == 3

    def test_set_gauge(self):
        collector = MetricsCollector()

        collector.set_gauge("temperature", 25.5)
        collector.set_gauge("temperature", 26.0)  # Override

        assert collector.gauges["temperature"] == 26.0

    def test_record_histogram(self):
        collector = MetricsCollector()

        collector.record_histogram("latency", 100)
        collector.record_histogram("latency", 150)
        collector.record_histogram("latency", 200)

        assert len(collector.histograms["latency"]) == 3
        assert collector.histograms["latency"] == [100, 150, 200]

    def test_get_summary(self):
        collector = MetricsCollector()

        collector.increment_counter("requests", 10)
        collector.set_gauge("memory_mb", 512)
        collector.record_histogram("latency", 100)
        collector.record_histogram("latency", 200)
        collector.record_histogram("latency", 300)

        summary = collector.get_summary()

        assert summary["counters"]["requests"] == 10
        assert summary["gauges"]["memory_mb"] == 512
        assert summary["histograms"]["latency"]["count"] == 3
        assert summary["histograms"]["latency"]["mean"] == 200
        assert summary["histograms"]["latency"]["median"] == 200
        assert summary["histograms"]["latency"]["min"] == 100
        assert summary["histograms"]["latency"]["max"] == 300


class TestWorkflowProfiler:
    """Test WorkflowProfiler class"""

    def test_profile_agent(self):
        profiler = WorkflowProfiler("test_workflow")

        # Start profiling agent
        profile = profiler.profile_agent("A0")
        assert "A0" in profiler.agent_profiles

        time.sleep(0.01)

        # End profiling
        profiler.end_agent_profile("A0", success=True)

        # Check metrics
        assert profiler.metrics.counters["agent.A0.executions"] == 1
        assert profiler.metrics.counters["agent.A0.success"] == 1
        assert len(profiler.metrics.histograms["agent.A0.duration_ms"]) == 1

    def test_profile_agent_failure(self):
        profiler = WorkflowProfiler("test_workflow")

        profile = profiler.profile_agent("B1")
        profiler.end_agent_profile("B1", success=False, error="Test error")

        assert profiler.metrics.counters["agent.B1.failure"] == 1
        assert profiler.agent_profiles["B1"].error == "Test error"

    def test_get_report(self):
        profiler = WorkflowProfiler("test_workflow")

        # Profile multiple agents
        profile1 = profiler.profile_agent("A0")
        time.sleep(0.01)
        profiler.end_agent_profile("A0", success=True)

        profile2 = profiler.profile_agent("B1")
        time.sleep(0.01)
        profiler.end_agent_profile("B1", success=False, error="Error")

        report = profiler.get_report()

        assert report["workflow_id"] == "test_workflow"
        assert "profiling_summary" in report
        assert "metrics_summary" in report
        assert "agent_profiles" in report
        assert "A0" in report["agent_profiles"]
        assert "B1" in report["agent_profiles"]
        assert report["agent_profiles"]["B1"]["error"] == "Error"


class TestProfileDecorators:
    """Test profiling decorators"""

    @pytest.mark.asyncio
    async def test_profile_async_decorator(self, caplog):
        @profile_async("test_async_function")
        async def async_function(value):
            await asyncio.sleep(0.01)
            return value * 2

        result = await async_function(5)

        assert result == 10
        # Check that profiling was logged
        assert "Profiled test_async_function" in caplog.text

    def test_profile_sync_decorator(self, caplog):
        @profile_sync("test_sync_function")
        def sync_function(value):
            time.sleep(0.01)
            return value + 10

        result = sync_function(5)

        assert result == 15
        # Check that profiling was logged
        assert "Profiled test_sync_function" in caplog.text

    @pytest.mark.asyncio
    async def test_profile_async_with_exception(self):
        @profile_async()
        async def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await failing_function()

    def test_profile_sync_with_exception(self):
        @profile_sync()
        def failing_function():
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError, match="Test error"):
            failing_function()


class TestPerformanceMetric:
    """Test PerformanceMetric dataclass"""

    def test_metric_creation(self):
        from datetime import datetime

        metric = PerformanceMetric(
            name="test_metric",
            value=42.5,
            unit="ms",
            timestamp=datetime.utcnow(),
            tags={"env": "test"}
        )

        assert metric.name == "test_metric"
        assert metric.value == 42.5
        assert metric.unit == "ms"
        assert metric.tags["env"] == "test"


class TestExecutionProfile:
    """Test ExecutionProfile dataclass"""

    def test_profile_creation(self):
        profile = ExecutionProfile(
            name="test_profile",
            start_time=time.time(),
            memory_before_mb=100.0
        )

        assert profile.name == "test_profile"
        assert profile.start_time > 0
        assert profile.memory_before_mb == 100.0
        assert profile.end_time is None
        assert profile.duration_ms is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])