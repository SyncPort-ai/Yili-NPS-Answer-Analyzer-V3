"""
NPS V3 Performance Monitoring Module

Comprehensive performance monitoring and analytics for the NPS V3 multi-agent analysis system.
Provides real-time metrics collection, performance analysis, alerting, and dashboard generation.

Key Features:
- Real-time performance metrics collection
- Agent-level execution monitoring
- LLM call performance tracking
- System resource usage monitoring
- Error rate and failure analysis
- Performance dashboards and alerts
- Historical trend analysis
- Bottleneck identification and optimization suggestions

Main Components:
- PerformanceMonitor: Main monitoring coordinator
- MetricsCollector: Real-time metrics collection
- PerformanceAnalyzer: Analysis and trend detection
- AlertManager: Performance alerts and notifications
- DashboardGenerator: Performance dashboard creation

Usage:
    from nps_report_v3.monitoring import PerformanceMonitor

    # Initialize monitor
    monitor = PerformanceMonitor()

    # Track agent execution
    with monitor.track_agent("B1_promoter_analyst"):
        result = agent.execute(data)

    # Track LLM calls
    with monitor.track_llm_call("gpt-4-turbo", "analysis"):
        response = llm_client.call(prompt)

    # Generate dashboard
    dashboard_html = monitor.generate_dashboard_html()
"""

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

# Version information
__version__ = "1.0.0"
__author__ = "NPS V3 Development Team"

# Export main classes
__all__ = [
    "PerformanceMonitor",
    "PerformanceMetric",
    "SystemMetrics",
    "PerformanceStats",
    "MetricsCollector",
    "PerformanceAnalyzer",
    "AlertManager",
    "DashboardGenerator"
]

# Module configuration
DEFAULT_CONFIG = {
    "max_metrics": 10000,
    "system_monitoring_interval": 5.0,
    "alert_thresholds": {
        "error_rate": 0.05,
        "avg_duration": 30.0,
        "cpu_usage": 80.0,
        "memory_usage": 80.0
    },
    "auto_cleanup_hours": 24,
    "dashboard_refresh_seconds": 30
}


def create_monitor(config: dict = None) -> PerformanceMonitor:
    """
    Create a configured performance monitor instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured PerformanceMonitor instance
    """
    if config is None:
        config = DEFAULT_CONFIG

    return PerformanceMonitor(
        max_metrics=config.get("max_metrics", DEFAULT_CONFIG["max_metrics"]),
        auto_start_system_monitoring=config.get("auto_start_system_monitoring", True)
    )