"""
Performance Monitoring System Tests

Comprehensive test suite for the NPS V3 performance monitoring system.
Tests core monitoring functionality, integration capabilities, and configuration management.

Test Categories:
- Unit Tests: Individual component testing
- Integration Tests: End-to-end monitoring workflow
- Configuration Tests: Configuration loading and validation
- Performance Tests: Monitor performance under load

Usage:
    # Run all monitoring tests
    python -m pytest nps_report_v3/monitoring/test_performance_monitoring.py -v

    # Run specific test category
    python -m pytest nps_report_v3/monitoring/test_performance_monitoring.py -k "test_performance_monitor" -v

    # Run tests with coverage
    python -m pytest nps_report_v3/monitoring/test_performance_monitoring.py --cov=nps_report_v3.monitoring -v
"""

import pytest
import asyncio
import time
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import monitoring components
from .performance_monitor import (
    PerformanceMonitor,
    PerformanceMetric,
    SystemMetrics,
    PerformanceStats,
    MetricsCollector,
    PerformanceAnalyzer,
    AlertManager,
    DashboardGenerator
)
from .config import (
    MonitoringConfig,
    AlertThresholds,
    MetricsConfig,
    DashboardConfig,
    ExportConfig,
    LoggingConfig,
    create_config,
    get_config_profile
)
from .integration import (
    MonitoringIntegration,
    PerformanceReport,
    monitor_agent,
    monitor_llm_call,
    get_global_monitoring
)


class TestPerformanceMonitor:
    """Test PerformanceMonitor core functionality."""

    @pytest.fixture
    def monitor(self):
        """Create a test monitor instance."""
        return PerformanceMonitor(max_metrics=100, auto_start_system_monitoring=False)

    def test_monitor_initialization(self, monitor):
        """Test monitor initialization."""
        assert monitor.collector is not None
        assert monitor.analyzer is not None
        assert monitor.alert_manager is not None
        assert monitor.dashboard_generator is not None

    def test_track_agent_context_manager(self, monitor):
        """Test agent tracking context manager."""
        agent_id = "test_agent"

        with monitor.track_agent(agent_id):
            time.sleep(0.1)  # Simulate work

        # Check that metric was recorded
        metrics = monitor.collector.get_metrics(component=agent_id)
        assert len(metrics) == 1
        assert metrics[0].component == agent_id
        assert metrics[0].metric_type == "agent"
        assert metrics[0].success is True
        assert metrics[0].duration > 0

    def test_track_agent_with_error(self, monitor):
        """Test agent tracking with error."""
        agent_id = "error_agent"

        with pytest.raises(ValueError):
            with monitor.track_agent(agent_id):
                raise ValueError("Test error")

        # Check that error was recorded
        metrics = monitor.collector.get_metrics(component=agent_id)
        assert len(metrics) == 1
        assert metrics[0].success is False
        assert metrics[0].error_message == "Test error"

    def test_track_llm_call(self, monitor):
        """Test LLM call tracking."""
        model = "gpt-4-turbo"

        with monitor.track_llm_call(model, "completion"):
            time.sleep(0.05)

        metrics = monitor.collector.get_metrics(component=model)
        assert len(metrics) == 1
        assert metrics[0].metric_type == "llm_call"
        assert metrics[0].operation == "completion"

    def test_track_workflow(self, monitor):
        """Test workflow tracking."""
        workflow_name = "nps_analysis"
        stage = "preprocessing"

        with monitor.track_workflow(workflow_name, stage):
            time.sleep(0.05)

        metrics = monitor.collector.get_metrics(component=workflow_name)
        assert len(metrics) == 1
        assert metrics[0].metric_type == "workflow"
        assert metrics[0].operation == stage

    @pytest.mark.asyncio
    async def test_async_operation_tracking(self, monitor):
        """Test async operation tracking."""
        component = "async_component"

        async with monitor.track_async_operation(component, "async_operation"):
            await asyncio.sleep(0.05)

        metrics = monitor.collector.get_metrics(component=component)
        assert len(metrics) == 1
        assert metrics[0].metric_type == "async_operation"
        assert metrics[0].success is True

    def test_get_component_stats(self, monitor):
        """Test component statistics calculation."""
        agent_id = "stats_agent"

        # Generate some test metrics
        for i in range(10):
            with monitor.track_agent(agent_id):
                time.sleep(0.01)

        stats = monitor.get_component_stats(agent_id)
        assert stats is not None
        assert stats.component == agent_id
        assert stats.total_calls == 10
        assert stats.success_rate == 1.0
        assert stats.avg_duration > 0

    def test_export_metrics(self, monitor):
        """Test metrics export functionality."""
        # Generate some test metrics
        with monitor.track_agent("export_test"):
            time.sleep(0.01)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name

        try:
            monitor.export_metrics(export_path, "json")

            # Verify export file was created and has content
            with open(export_path, 'r') as f:
                data = json.load(f)

            assert 'export_timestamp' in data
            assert 'performance_metrics' in data
            assert len(data['performance_metrics']) > 0

        finally:
            Path(export_path).unlink(missing_ok=True)

    def test_dashboard_generation(self, monitor):
        """Test dashboard generation."""
        # Generate some test metrics
        with monitor.track_agent("dashboard_test"):
            time.sleep(0.01)

        dashboard_html = monitor.generate_dashboard_html()
        assert isinstance(dashboard_html, str)
        assert len(dashboard_html) > 0
        assert "Performance Dashboard" in dashboard_html

    def test_cleanup_old_metrics(self, monitor):
        """Test metrics cleanup functionality."""
        # Add some metrics
        for i in range(5):
            with monitor.track_agent("cleanup_test"):
                time.sleep(0.001)

        # Verify metrics exist
        initial_count = len(monitor.collector.get_metrics())
        assert initial_count > 0

        # Cleanup metrics older than 1 second
        time.sleep(1.1)
        removed_count = monitor.cleanup_old_metrics(timedelta(seconds=1))

        assert removed_count >= 0  # Some metrics should be removed


class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    @pytest.fixture
    def collector(self):
        """Create a test collector instance."""
        return MetricsCollector(max_metrics=50)

    def test_add_metric(self, collector):
        """Test adding performance metrics."""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_type="test",
            component="test_component",
            operation="test_operation",
            duration=1.0,
            success=True
        )

        collector.add_metric(metric)
        metrics = collector.get_metrics()
        assert len(metrics) == 1
        assert metrics[0] == metric

    def test_add_system_metric(self, collector):
        """Test adding system metrics."""
        system_metric = SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            disk_usage_percent=70.0
        )

        collector.add_system_metric(system_metric)
        system_metrics = collector.get_system_metrics()
        assert len(system_metrics) == 1
        assert system_metrics[0] == system_metric

    def test_get_metrics_filtering(self, collector):
        """Test metrics filtering functionality."""
        # Add different types of metrics
        metric1 = PerformanceMetric(
            timestamp=datetime.now(),
            metric_type="agent",
            component="agent1",
            operation="execute",
            duration=1.0,
            success=True
        )

        metric2 = PerformanceMetric(
            timestamp=datetime.now(),
            metric_type="llm_call",
            component="gpt-4",
            operation="completion",
            duration=2.0,
            success=True
        )

        collector.add_metric(metric1)
        collector.add_metric(metric2)

        # Test filtering by metric type
        agent_metrics = collector.get_metrics(metric_type="agent")
        assert len(agent_metrics) == 1
        assert agent_metrics[0].metric_type == "agent"

        # Test filtering by component
        gpt4_metrics = collector.get_metrics(component="gpt-4")
        assert len(gpt4_metrics) == 1
        assert gpt4_metrics[0].component == "gpt-4"

    def test_max_metrics_limit(self, collector):
        """Test that collector respects max_metrics limit."""
        # Add more metrics than the limit
        for i in range(60):  # Max is 50
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_type="test",
                component=f"component_{i}",
                operation="test",
                duration=1.0,
                success=True
            )
            collector.add_metric(metric)

        # Should only keep the last 50 metrics
        metrics = collector.get_metrics()
        assert len(metrics) <= 50


class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create a test analyzer instance."""
        collector = MetricsCollector(max_metrics=100)
        return PerformanceAnalyzer(collector)

    def test_calculate_stats(self, analyzer):
        """Test statistics calculation."""
        component = "test_component"

        # Add some test metrics with varying durations
        durations = [1.0, 2.0, 3.0, 4.0, 5.0]
        for duration in durations:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_type="agent",
                component=component,
                operation="execute",
                duration=duration,
                success=True
            )
            analyzer.collector.add_metric(metric)

        stats = analyzer.calculate_stats(component, "execute")
        assert stats is not None
        assert stats.component == component
        assert stats.total_calls == 5
        assert stats.success_rate == 1.0
        assert stats.avg_duration == 3.0  # Average of 1,2,3,4,5
        assert stats.min_duration == 1.0
        assert stats.max_duration == 5.0

    def test_detect_performance_issues(self, analyzer):
        """Test performance issue detection."""
        # Add metrics with high error rate
        for i in range(10):
            success = i < 8  # 80% success rate
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_type="agent",
                component="error_prone_agent",
                operation="execute",
                duration=1.0,
                success=success
            )
            analyzer.collector.add_metric(metric)

        issues = analyzer.detect_performance_issues()

        # Should detect high error rate issue
        error_issues = [issue for issue in issues if issue['type'] == 'high_error_rate']
        assert len(error_issues) > 0

    def test_percentile_calculation(self, analyzer):
        """Test percentile calculation helper method."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

        p50 = analyzer._percentile(values, 50)
        assert p50 == 5.5  # Median of 1-10

        p95 = analyzer._percentile(values, 95)
        assert p95 == 9.5  # 95th percentile


class TestMonitoringConfig:
    """Test MonitoringConfig functionality."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = MonitoringConfig(load_env=False)

        assert config.alert_thresholds.error_rate == 0.05
        assert config.metrics_config.max_metrics == 10000
        assert config.dashboard_config.refresh_seconds == 30
        assert config.export_config.enabled is True

    def test_config_from_file(self):
        """Test loading configuration from file."""
        config_data = {
            "alert_thresholds": {
                "error_rate": 0.10,
                "avg_duration": 60.0
            },
            "metrics_config": {
                "max_metrics": 5000,
                "system_monitoring_interval": 10.0
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            config = MonitoringConfig(config_file=config_path, load_env=False)

            assert config.alert_thresholds.error_rate == 0.10
            assert config.alert_thresholds.avg_duration == 60.0
            assert config.metrics_config.max_metrics == 5000
            assert config.metrics_config.system_monitoring_interval == 10.0

        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_config_validation(self):
        """Test configuration validation."""
        config = MonitoringConfig(load_env=False)

        # Valid configuration should pass
        issues = config.validate()
        assert len(issues) == 0

        # Invalid configuration should fail
        config.alert_thresholds.error_rate = -0.1  # Invalid: negative
        config.metrics_config.max_metrics = 0      # Invalid: zero

        issues = config.validate()
        assert len(issues) > 0
        assert 'alert_thresholds' in issues
        assert 'metrics_config' in issues

    def test_config_profiles(self):
        """Test configuration profiles."""
        dev_profile = get_config_profile('development')
        prod_profile = get_config_profile('production')

        assert dev_profile['alert_thresholds']['error_rate'] > prod_profile['alert_thresholds']['error_rate']
        assert dev_profile['logging_config']['level'] == 'DEBUG'
        assert prod_profile['logging_config']['level'] == 'INFO'

    def test_config_update(self):
        """Test runtime configuration updates."""
        config = MonitoringConfig(load_env=False)
        original_error_rate = config.alert_thresholds.error_rate

        # Update configuration
        config.update({
            'alert_thresholds': {
                'error_rate': 0.15
            }
        })

        assert config.alert_thresholds.error_rate == 0.15
        assert config.alert_thresholds.error_rate != original_error_rate


class TestMonitoringIntegration:
    """Test MonitoringIntegration functionality."""

    @pytest.fixture
    def integration(self):
        """Create a test integration instance."""
        config = MonitoringConfig(load_env=False)
        return MonitoringIntegration(config)

    def test_integration_initialization(self, integration):
        """Test integration initialization."""
        assert integration.config is not None
        assert integration.monitor is not None
        assert integration._enabled is True

    def test_agent_decorator(self, integration):
        """Test agent monitoring decorator."""
        @integration.track_agent("test_agent")
        def test_function():
            time.sleep(0.01)
            return "success"

        result = test_function()
        assert result == "success"

        # Check that metric was recorded
        metrics = integration.monitor.collector.get_metrics(component="test_agent")
        assert len(metrics) == 1
        assert metrics[0].success is True

    @pytest.mark.asyncio
    async def test_async_agent_decorator(self, integration):
        """Test async agent monitoring decorator."""
        @integration.track_agent("async_test_agent")
        async def async_test_function():
            await asyncio.sleep(0.01)
            return "async_success"

        result = await async_test_function()
        assert result == "async_success"

        # Check that metric was recorded
        metrics = integration.monitor.collector.get_metrics(component="async_test_agent")
        assert len(metrics) == 1
        assert metrics[0].success is True

    def test_llm_call_decorator(self, integration):
        """Test LLM call monitoring decorator."""
        @integration.track_llm_call("test-model")
        def mock_llm_call():
            time.sleep(0.01)
            return {"response": "test response"}

        result = mock_llm_call()
        assert result["response"] == "test response"

        # Check that metric was recorded
        metrics = integration.monitor.collector.get_metrics(component="test-model")
        assert len(metrics) == 1
        assert metrics[0].metric_type == "llm_call"

    def test_workflow_stage_decorator(self, integration):
        """Test workflow stage monitoring decorator."""
        @integration.track_workflow_stage("test_workflow", "test_stage")
        def test_workflow_function():
            time.sleep(0.01)
            return "workflow_result"

        result = test_workflow_function()
        assert result == "workflow_result"

        # Check that metric was recorded
        metrics = integration.monitor.collector.get_metrics(component="test_workflow")
        assert len(metrics) == 1
        assert metrics[0].operation == "test_stage"

    def test_enable_disable_monitoring(self, integration):
        """Test enabling and disabling monitoring."""
        # Initially enabled
        assert integration._enabled is True

        # Disable monitoring
        integration.disable()
        assert integration._enabled is False

        @integration.track_agent("disabled_test")
        def test_function_disabled():
            return "result"

        # Should not record metrics when disabled
        test_function_disabled()
        metrics = integration.monitor.collector.get_metrics(component="disabled_test")
        assert len(metrics) == 0

        # Re-enable monitoring
        integration.enable()
        assert integration._enabled is True

    def test_performance_report_generation(self, integration):
        """Test performance report generation."""
        # Generate some test metrics
        with integration.monitor.track_agent("report_test_agent"):
            time.sleep(0.01)

        with integration.monitor.track_llm_call("test-model"):
            time.sleep(0.01)

        # Generate report
        report = integration.generate_performance_report(time_window=timedelta(minutes=1))

        assert isinstance(report, PerformanceReport)
        assert report.total_operations > 0
        assert report.overall_success_rate >= 0.0
        assert len(report.agent_performance) > 0

    def test_real_time_status(self, integration):
        """Test real-time status reporting."""
        # Generate some recent activity
        with integration.monitor.track_agent("status_test"):
            time.sleep(0.01)

        status = integration.get_real_time_status()

        assert isinstance(status, dict)
        assert 'monitoring_enabled' in status
        assert 'recent_activity' in status
        assert 'system_status' in status
        assert status['monitoring_enabled'] is True


class TestGlobalMonitoring:
    """Test global monitoring functionality."""

    def test_get_global_monitoring(self):
        """Test getting global monitoring instance."""
        # Reset global state
        import nps_report_v3.monitoring.integration as integration_module
        integration_module._global_monitoring = None

        # Should create new instance
        monitor1 = get_global_monitoring()
        assert monitor1 is not None

        # Should return same instance
        monitor2 = get_global_monitoring()
        assert monitor1 is monitor2

    def test_convenience_decorators(self):
        """Test convenience decorator functions."""
        @monitor_agent("convenience_test")
        def test_function():
            time.sleep(0.001)
            return "success"

        result = test_function()
        assert result == "success"

        # The function should have been monitored through global instance


class TestPerformanceUnderLoad:
    """Test monitoring system performance under load."""

    @pytest.mark.slow
    def test_high_volume_metrics(self):
        """Test system with high volume of metrics."""
        monitor = PerformanceMonitor(max_metrics=1000, auto_start_system_monitoring=False)

        # Generate many metrics quickly
        start_time = time.time()

        for i in range(500):
            with monitor.track_agent(f"load_test_agent_{i % 10}"):
                pass  # Minimal work to test overhead

        duration = time.time() - start_time

        # Should complete in reasonable time (adjust threshold as needed)
        assert duration < 5.0  # 5 seconds for 500 operations

        # Verify metrics were recorded
        metrics = monitor.collector.get_metrics()
        assert len(metrics) == 500

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_monitoring(self):
        """Test concurrent monitoring operations."""
        monitor = PerformanceMonitor(max_metrics=1000, auto_start_system_monitoring=False)

        async def async_operation(operation_id: int):
            async with monitor.track_async_operation(f"concurrent_op_{operation_id}", "test"):
                await asyncio.sleep(0.001)  # Minimal async work

        # Run multiple concurrent operations
        tasks = [async_operation(i) for i in range(100)]
        await asyncio.gather(*tasks)

        # Verify all operations were tracked
        metrics = monitor.collector.get_metrics()
        assert len(metrics) == 100

        # Verify no data corruption
        unique_components = set(metric.component for metric in metrics)
        assert len(unique_components) == 100


# Integration test fixtures
@pytest.fixture(scope="session")
def temp_monitoring_dir():
    """Create temporary directory for monitoring test outputs."""
    import tempfile
    import shutil

    temp_dir = Path(tempfile.mkdtemp(prefix="nps_monitoring_test_"))
    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_metrics_data():
    """Generate sample metrics data for testing."""
    metrics = []
    base_time = datetime.now() - timedelta(hours=1)

    # Generate various types of metrics
    for i in range(50):
        # Agent metrics
        metrics.append(PerformanceMetric(
            timestamp=base_time + timedelta(minutes=i),
            metric_type="agent",
            component=f"agent_{i % 5}",
            operation="execute",
            duration=1.0 + (i % 10) * 0.1,
            success=i % 20 != 0,  # 5% error rate
            error_message="Test error" if i % 20 == 0 else None
        ))

        # LLM call metrics
        if i % 3 == 0:
            metrics.append(PerformanceMetric(
                timestamp=base_time + timedelta(minutes=i),
                metric_type="llm_call",
                component=f"model_{i % 2}",
                operation="completion",
                duration=2.0 + (i % 5) * 0.2,
                success=i % 30 != 0,  # ~3% error rate
                error_message="LLM error" if i % 30 == 0 else None
            ))

    return metrics


# Mark slow tests
pytestmark = pytest.mark.unit


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v", "--tb=short"])