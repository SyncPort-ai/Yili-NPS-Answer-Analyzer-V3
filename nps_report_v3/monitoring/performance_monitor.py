"""
NPS V3 Performance Monitoring System

Advanced performance monitoring and metrics collection for the NPS V3 multi-agent analysis system.
Tracks execution times, resource usage, error rates, and provides comprehensive analytics.

Features:
- Real-time performance metrics collection
- Agent-level execution monitoring
- LLM call performance tracking
- Memory and resource usage monitoring
- Error rate and failure analysis
- Performance dashboards and alerts
- Historical trend analysis
- Bottleneck identification and optimization suggestions

Usage:
    monitor = PerformanceMonitor()

    # Monitor agent execution
    with monitor.track_agent("B1_promoter_analyst"):
        result = agent.execute(data)

    # Monitor LLM calls
    with monitor.track_llm_call("gpt-4-turbo", "analysis"):
        response = llm_client.call(prompt)

    # Get performance report
    report = monitor.generate_report()
    print(report.to_html())

Components:
- PerformanceMonitor: Main monitoring coordinator
- MetricsCollector: Real-time metrics collection
- PerformanceAnalyzer: Analysis and trend detection
- AlertManager: Performance alerts and notifications
- DashboardGenerator: Performance dashboard creation
"""

import time
import psutil
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from contextlib import contextmanager, asynccontextmanager
from collections import defaultdict, deque
import json
import logging
from pathlib import Path
import statistics
import warnings
from decimal import Decimal, ROUND_HALF_DOWN

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    warnings.warn("Plotly not available. Performance dashboards will use basic HTML output.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    warnings.warn("Pandas not available. Some analytics features will be limited.")


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""

    timestamp: datetime
    metric_type: str  # 'agent', 'llm_call', 'workflow', 'system'
    component: str    # Component name or identifier
    operation: str    # Operation type (execute, call, process, etc.)
    duration: float   # Execution time in seconds
    success: bool     # Whether operation succeeded
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'metric_type': self.metric_type,
            'component': self.component,
            'operation': self.operation,
            'duration': self.duration,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


@dataclass
class SystemMetrics:
    """System resource usage metrics."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_io: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert system metrics to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used_mb': self.memory_used_mb,
            'disk_usage_percent': self.disk_usage_percent,
            'network_io': self.network_io
        }


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""

    component: str
    operation: str
    total_calls: int
    success_rate: float
    avg_duration: float
    min_duration: float
    max_duration: float
    p50_duration: float
    p95_duration: float
    p99_duration: float
    error_rate: float
    throughput_per_minute: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'component': self.component,
            'operation': self.operation,
            'total_calls': self.total_calls,
            'success_rate': self.success_rate,
            'avg_duration': self.avg_duration,
            'min_duration': self.min_duration,
            'max_duration': self.max_duration,
            'p50_duration': self.p50_duration,
            'p95_duration': self.p95_duration,
            'p99_duration': self.p99_duration,
            'error_rate': self.error_rate,
            'throughput_per_minute': self.throughput_per_minute
        }


class MetricsCollector:
    """Real-time metrics collection and storage."""

    def __init__(self, max_metrics: int = 10000):
        """
        Initialize metrics collector.

        Args:
            max_metrics: Maximum number of metrics to keep in memory
        """
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.system_metrics: deque = deque(maxlen=max_metrics)
        self.lock = threading.Lock()
        self._system_monitor_active = False
        self._system_monitor_thread: Optional[threading.Thread] = None

    def add_metric(self, metric: PerformanceMetric):
        """Add a performance metric."""
        with self.lock:
            self.metrics.append(metric)

    def add_system_metric(self, metric: SystemMetrics):
        """Add a system resource metric."""
        with self.lock:
            self.system_metrics.append(metric)

    def get_metrics(
        self,
        metric_type: Optional[str] = None,
        component: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[PerformanceMetric]:
        """Get metrics with optional filtering."""
        with self.lock:
            filtered_metrics = list(self.metrics)

        if metric_type:
            filtered_metrics = [m for m in filtered_metrics if m.metric_type == metric_type]

        if component:
            filtered_metrics = [m for m in filtered_metrics if m.component == component]

        if since:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]

        return filtered_metrics

    def get_system_metrics(self, since: Optional[datetime] = None) -> List[SystemMetrics]:
        """Get system metrics with optional time filtering."""
        with self.lock:
            filtered_metrics = list(self.system_metrics)

        if since:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]

        return filtered_metrics

    def start_system_monitoring(self, interval: float = 5.0):
        """Start background system monitoring."""
        if self._system_monitor_active:
            return

        self._system_monitor_active = True
        self._system_monitor_thread = threading.Thread(
            target=self._system_monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._system_monitor_thread.start()

    def stop_system_monitoring(self):
        """Stop background system monitoring."""
        self._system_monitor_active = False
        if self._system_monitor_thread:
            self._system_monitor_thread.join(timeout=1.0)

    def _system_monitor_loop(self, interval: float):
        """Background system monitoring loop."""
        while self._system_monitor_active:
            try:
                # Collect system metrics
                system_metric = SystemMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=psutil.cpu_percent(interval=1),
                    memory_percent=psutil.virtual_memory().percent,
                    memory_used_mb=psutil.virtual_memory().used / 1024 / 1024,
                    disk_usage_percent=psutil.disk_usage('/').percent,
                    network_io=psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
                )
                self.add_system_metric(system_metric)

                time.sleep(interval)
            except Exception as e:
                logging.error(f"System monitoring error: {e}")
                time.sleep(interval)


class PerformanceAnalyzer:
    """Performance analysis and trend detection."""

    def __init__(self, collector: MetricsCollector):
        """Initialize analyzer with metrics collector."""
        self.collector = collector

    def calculate_stats(
        self,
        component: str,
        operation: str = "execute",
        time_window: Optional[timedelta] = None
    ) -> Optional[PerformanceStats]:
        """Calculate performance statistics for a component."""
        since = datetime.now() - time_window if time_window else None
        metrics = self.collector.get_metrics(component=component, since=since)

        if not metrics:
            return None

        # Filter by operation
        operation_metrics = [m for m in metrics if m.operation == operation]

        if not operation_metrics:
            return None

        durations = [m.duration for m in operation_metrics]
        successes = [m.success for m in operation_metrics]

        total_calls = len(operation_metrics)
        success_rate = sum(successes) / total_calls if total_calls > 0 else 0.0
        error_rate = 1.0 - success_rate

        # Calculate duration statistics
        avg_duration = statistics.mean(durations) if durations else 0.0
        min_duration = min(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        sorted_durations = sorted(durations)
        p50_duration = self._percentile(sorted_durations, 50) if durations else 0.0
        p95_duration = self._percentile(sorted_durations, 95) if durations else 0.0
        p99_duration = self._percentile(sorted_durations, 99) if durations else 0.0

        # Calculate throughput
        if time_window and operation_metrics:
            time_span_minutes = time_window.total_seconds() / 60
            throughput_per_minute = total_calls / time_span_minutes if time_span_minutes > 0 else 0.0
        else:
            throughput_per_minute = 0.0

        return PerformanceStats(
            component=component,
            operation=operation,
            total_calls=total_calls,
            success_rate=success_rate,
            avg_duration=avg_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            p50_duration=p50_duration,
            p95_duration=p95_duration,
            p99_duration=p99_duration,
            error_rate=error_rate,
            throughput_per_minute=throughput_per_minute
        )

    def detect_performance_issues(self) -> List[Dict[str, Any]]:
        """Detect potential performance issues."""
        issues = []

        # Get recent metrics (last hour)
        recent_window = timedelta(hours=1)
        recent_metrics = self.collector.get_metrics(since=datetime.now() - recent_window)

        if not recent_metrics:
            return issues

        # Group metrics by component
        component_metrics = defaultdict(list)
        for metric in recent_metrics:
            component_metrics[metric.component].append(metric)

        for component, metrics in component_metrics.items():
            # Check error rate
            error_rate = sum(1 for m in metrics if not m.success) / len(metrics)
            if error_rate > 0.05:  # More than 5% error rate
                issues.append({
                    'type': 'high_error_rate',
                    'component': component,
                    'severity': 'high' if error_rate > 0.10 else 'medium',
                    'details': f'Error rate: {error_rate:.2%}',
                    'suggestion': 'Review recent errors and implement error handling improvements'
                })

            # Check slow operations
            durations = [m.duration for m in metrics if m.success]
            if durations:
                avg_duration = statistics.mean(durations)
                if avg_duration > 30.0:  # More than 30 seconds average
                    issues.append({
                        'type': 'slow_performance',
                        'component': component,
                        'severity': 'high' if avg_duration > 60.0 else 'medium',
                        'details': f'Average duration: {avg_duration:.2f}s',
                        'suggestion': 'Optimize component logic or consider caching'
                    })

        # Check system resource usage
        recent_system_metrics = self.collector.get_system_metrics(
            since=datetime.now() - recent_window
        )

        if recent_system_metrics:
            avg_cpu = statistics.mean(m.cpu_percent for m in recent_system_metrics)
            avg_memory = statistics.mean(m.memory_percent for m in recent_system_metrics)

            if avg_cpu > 80.0:
                issues.append({
                    'type': 'high_cpu_usage',
                    'component': 'system',
                    'severity': 'high' if avg_cpu > 90.0 else 'medium',
                    'details': f'Average CPU usage: {avg_cpu:.1f}%',
                    'suggestion': 'Consider scaling or optimizing CPU-intensive operations'
                })

            if avg_memory > 80.0:
                issues.append({
                    'type': 'high_memory_usage',
                    'component': 'system',
                    'severity': 'high' if avg_memory > 90.0 else 'medium',
                    'details': f'Average memory usage: {avg_memory:.1f}%',
                    'suggestion': 'Review memory usage and implement cleanup strategies'
                })

        return issues

    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = (percentile / 100.0) * (len(sorted_values) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)

        if lower_index == upper_index:
            return sorted_values[lower_index]

        weight = index - lower_index
        interpolated = sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
        return float(Decimal(interpolated).quantize(Decimal("0.1"), rounding=ROUND_HALF_DOWN))


class AlertManager:
    """Performance alerts and notifications."""

    def __init__(self, analyzer: PerformanceAnalyzer):
        """Initialize alert manager."""
        self.analyzer = analyzer
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            'error_rate': 0.05,
            'avg_duration': 30.0,
            'cpu_usage': 80.0,
            'memory_usage': 80.0
        }

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance alerts."""
        issues = self.analyzer.detect_performance_issues()
        new_alerts = []

        current_time = datetime.now()

        for issue in issues:
            alert = {
                'timestamp': current_time,
                'type': issue['type'],
                'component': issue['component'],
                'severity': issue['severity'],
                'message': issue['details'],
                'suggestion': issue['suggestion'],
                'acknowledged': False
            }

            new_alerts.append(alert)
            self.alert_history.append(alert)

        return new_alerts

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active (unacknowledged) alerts."""
        return [alert for alert in self.alert_history if not alert.get('acknowledged', False)]

    def acknowledge_alert(self, alert_index: int) -> bool:
        """Acknowledge an alert."""
        if 0 <= alert_index < len(self.alert_history):
            self.alert_history[alert_index]['acknowledged'] = True
            return True
        return False


class DashboardGenerator:
    """Performance dashboard creation."""

    def __init__(self, analyzer: PerformanceAnalyzer, alert_manager: AlertManager):
        """Initialize dashboard generator."""
        self.analyzer = analyzer
        self.alert_manager = alert_manager

    def generate_html_dashboard(self) -> str:
        """Generate HTML performance dashboard."""
        # Get recent performance data
        recent_window = timedelta(hours=1)
        recent_metrics = self.analyzer.collector.get_metrics(
            since=datetime.now() - recent_window
        )

        # Get component statistics
        components = set(m.component for m in recent_metrics)
        component_stats = {}

        for component in components:
            stats = self.analyzer.calculate_stats(component, time_window=recent_window)
            if stats:
                component_stats[component] = stats

        # Get system metrics
        system_metrics = self.analyzer.collector.get_system_metrics(
            since=datetime.now() - recent_window
        )

        # Get active alerts
        active_alerts = self.alert_manager.get_active_alerts()

        # Generate HTML dashboard
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NPS V3 Performance Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .dashboard {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #2c3e50; margin-bottom: 10px; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .metric-title {{ font-weight: bold; color: #34495e; margin-bottom: 10px; font-size: 18px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; margin: 5px 0; }}
                .metric-good {{ color: #27ae60; }}
                .metric-warning {{ color: #f39c12; }}
                .metric-error {{ color: #e74c3c; }}
                .alerts {{ margin-bottom: 30px; }}
                .alert {{ padding: 15px; border-radius: 5px; margin-bottom: 10px; }}
                .alert-high {{ background-color: #fee; border-left: 4px solid #e74c3c; }}
                .alert-medium {{ background-color: #fff3cd; border-left: 4px solid #f39c12; }}
                .chart-container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="dashboard">
                <div class="header">
                    <h1>🚀 NPS V3 Performance Dashboard</h1>
                    <p class="timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
        """

        # Active alerts section
        if active_alerts:
            html_content += """
                <div class="alerts">
                    <h2>🚨 Active Alerts</h2>
            """

            for alert in active_alerts[:5]:  # Show top 5 alerts
                alert_class = f"alert-{alert['severity']}"
                html_content += f"""
                    <div class="alert {alert_class}">
                        <strong>{alert['type'].replace('_', ' ').title()}</strong> - {alert['component']}<br>
                        {alert['message']}<br>
                        <em>Suggestion: {alert['suggestion']}</em>
                    </div>
                """

            html_content += "</div>"

        # System metrics overview
        if system_metrics:
            latest_system = system_metrics[-1]
            html_content += f"""
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-title">System CPU Usage</div>
                        <div class="metric-value {'metric-error' if latest_system.cpu_percent > 80 else 'metric-warning' if latest_system.cpu_percent > 60 else 'metric-good'}">
                            {latest_system.cpu_percent:.1f}%
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">System Memory Usage</div>
                        <div class="metric-value {'metric-error' if latest_system.memory_percent > 80 else 'metric-warning' if latest_system.memory_percent > 60 else 'metric-good'}">
                            {latest_system.memory_percent:.1f}%
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Memory Used</div>
                        <div class="metric-value">
                            {latest_system.memory_used_mb:.0f} MB
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Disk Usage</div>
                        <div class="metric-value {'metric-error' if latest_system.disk_usage_percent > 90 else 'metric-warning' if latest_system.disk_usage_percent > 80 else 'metric-good'}">
                            {latest_system.disk_usage_percent:.1f}%
                        </div>
                    </div>
                </div>
            """

        # Component performance table
        if component_stats:
            html_content += """
                <div class="chart-container">
                    <h2>Component Performance Statistics</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Component</th>
                                <th>Total Calls</th>
                                <th>Success Rate</th>
                                <th>Avg Duration</th>
                                <th>P95 Duration</th>
                                <th>Error Rate</th>
                            </tr>
                        </thead>
                        <tbody>
            """

            for component, stats in component_stats.items():
                success_color = 'metric-good' if stats.success_rate > 0.95 else 'metric-warning' if stats.success_rate > 0.90 else 'metric-error'
                duration_color = 'metric-good' if stats.avg_duration < 10 else 'metric-warning' if stats.avg_duration < 30 else 'metric-error'

                html_content += f"""
                    <tr>
                        <td><strong>{component}</strong></td>
                        <td>{stats.total_calls}</td>
                        <td class="{success_color}">{stats.success_rate:.1%}</td>
                        <td class="{duration_color}">{stats.avg_duration:.2f}s</td>
                        <td>{stats.p95_duration:.2f}s</td>
                        <td class="{'metric-error' if stats.error_rate > 0.05 else 'metric-warning' if stats.error_rate > 0.01 else 'metric-good'}">{stats.error_rate:.1%}</td>
                    </tr>
                """

            html_content += """
                        </tbody>
                    </table>
                </div>
            """

        html_content += """
            </div>
        </body>
        </html>
        """

        return html_content

    def generate_plotly_dashboard(self) -> Optional[str]:
        """Generate interactive Plotly dashboard (if available)."""
        if not PLOTLY_AVAILABLE:
            return None

        # Get recent metrics for plotting
        recent_window = timedelta(hours=6)
        recent_metrics = self.analyzer.collector.get_metrics(
            since=datetime.now() - recent_window
        )

        if not recent_metrics:
            return None

        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=['Response Times by Component', 'Success Rate Over Time',
                          'System CPU Usage', 'System Memory Usage',
                          'Error Distribution', 'Throughput Over Time'],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )

        # Response times by component
        components = set(m.component for m in recent_metrics if m.success)
        for component in components:
            component_metrics = [m for m in recent_metrics if m.component == component and m.success]
            if component_metrics:
                durations = [m.duration for m in component_metrics]
                fig.add_trace(
                    go.Box(y=durations, name=component, boxmean=True),
                    row=1, col=1
                )

        # Success rate over time
        success_over_time = defaultdict(list)
        for metric in recent_metrics:
            hour_bucket = metric.timestamp.replace(minute=0, second=0, microsecond=0)
            success_over_time[hour_bucket].append(metric.success)

        timestamps = sorted(success_over_time.keys())
        success_rates = [sum(success_over_time[ts]) / len(success_over_time[ts]) for ts in timestamps]

        fig.add_trace(
            go.Scatter(x=timestamps, y=success_rates, mode='lines+markers', name='Success Rate'),
            row=1, col=2
        )

        # System metrics
        system_metrics = self.analyzer.collector.get_system_metrics(
            since=datetime.now() - recent_window
        )

        if system_metrics:
            system_times = [m.timestamp for m in system_metrics]
            cpu_values = [m.cpu_percent for m in system_metrics]
            memory_values = [m.memory_percent for m in system_metrics]

            fig.add_trace(
                go.Scatter(x=system_times, y=cpu_values, mode='lines', name='CPU %'),
                row=2, col=1
            )

            fig.add_trace(
                go.Scatter(x=system_times, y=memory_values, mode='lines', name='Memory %'),
                row=2, col=2
            )

        # Error distribution
        error_metrics = [m for m in recent_metrics if not m.success]
        error_components = [m.component for m in error_metrics]

        if error_components:
            from collections import Counter
            error_counts = Counter(error_components)

            fig.add_trace(
                go.Bar(x=list(error_counts.keys()), y=list(error_counts.values()), name='Errors'),
                row=3, col=1
            )

        # Update layout
        fig.update_layout(
            height=1200,
            title_text="NPS V3 Performance Dashboard",
            showlegend=True
        )

        return fig.to_html()


class PerformanceMonitor:
    """Main performance monitoring coordinator."""

    def __init__(self, max_metrics: int = 10000, auto_start_system_monitoring: bool = True):
        """
        Initialize performance monitor.

        Args:
            max_metrics: Maximum number of metrics to keep in memory
            auto_start_system_monitoring: Whether to start system monitoring automatically
        """
        self.collector = MetricsCollector(max_metrics)
        self.analyzer = PerformanceAnalyzer(self.collector)
        self.alert_manager = AlertManager(self.analyzer)
        self.dashboard_generator = DashboardGenerator(self.analyzer, self.alert_manager)

        if auto_start_system_monitoring:
            self.collector.start_system_monitoring()

    @contextmanager
    def track_agent(self, agent_id: str, operation: str = "execute", metadata: Optional[Dict[str, Any]] = None):
        """Context manager for tracking agent execution."""
        start_time = time.time()
        start_timestamp = datetime.now()
        error_occurred = False
        error_message = None

        try:
            yield
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time

            metric = PerformanceMetric(
                timestamp=start_timestamp,
                metric_type="agent",
                component=agent_id,
                operation=operation,
                duration=duration,
                success=not error_occurred,
                error_message=error_message,
                metadata=metadata or {}
            )

            self.collector.add_metric(metric)

    @contextmanager
    def track_llm_call(self, model: str, call_type: str = "completion", metadata: Optional[Dict[str, Any]] = None):
        """Context manager for tracking LLM API calls."""
        start_time = time.time()
        start_timestamp = datetime.now()
        error_occurred = False
        error_message = None

        try:
            yield
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time

            metric = PerformanceMetric(
                timestamp=start_timestamp,
                metric_type="llm_call",
                component=model,
                operation=call_type,
                duration=duration,
                success=not error_occurred,
                error_message=error_message,
                metadata=metadata or {}
            )

            self.collector.add_metric(metric)

    @contextmanager
    def track_workflow(self, workflow_name: str, stage: str = "execute", metadata: Optional[Dict[str, Any]] = None):
        """Context manager for tracking workflow execution."""
        start_time = time.time()
        start_timestamp = datetime.now()
        error_occurred = False
        error_message = None

        try:
            yield
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time

            metric = PerformanceMetric(
                timestamp=start_timestamp,
                metric_type="workflow",
                component=workflow_name,
                operation=stage,
                duration=duration,
                success=not error_occurred,
                error_message=error_message,
                metadata=metadata or {}
            )

            self.collector.add_metric(metric)

    @asynccontextmanager
    async def track_async_operation(self, component: str, operation: str = "execute", metadata: Optional[Dict[str, Any]] = None):
        """Async context manager for tracking async operations."""
        start_time = time.time()
        start_timestamp = datetime.now()
        error_occurred = False
        error_message = None

        try:
            yield
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time

            metric = PerformanceMetric(
                timestamp=start_timestamp,
                metric_type="async_operation",
                component=component,
                operation=operation,
                duration=duration,
                success=not error_occurred,
                error_message=error_message,
                metadata=metadata or {}
            )

            self.collector.add_metric(metric)

    def get_component_stats(self, component: str, time_window: Optional[timedelta] = None) -> Optional[PerformanceStats]:
        """Get performance statistics for a component."""
        return self.analyzer.calculate_stats(component, time_window=time_window)

    def get_performance_issues(self) -> List[Dict[str, Any]]:
        """Get current performance issues."""
        return self.analyzer.detect_performance_issues()

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active performance alerts."""
        return self.alert_manager.get_active_alerts()

    def generate_dashboard_html(self) -> str:
        """Generate HTML performance dashboard."""
        return self.dashboard_generator.generate_html_dashboard()

    def generate_dashboard_plotly(self) -> Optional[str]:
        """Generate interactive Plotly dashboard."""
        return self.dashboard_generator.generate_plotly_dashboard()

    def export_metrics(self, filepath: Union[str, Path], format: str = "json") -> None:
        """Export metrics to file."""
        filepath = Path(filepath)

        # Get all metrics
        all_metrics = self.collector.get_metrics()
        all_system_metrics = self.collector.get_system_metrics()

        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'performance_metrics': [m.to_dict() for m in all_metrics],
            'system_metrics': [m.to_dict() for m in all_system_metrics],
            'total_performance_metrics': len(all_metrics),
            'total_system_metrics': len(all_system_metrics)
        }

        if format.lower() == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        elif format.lower() == "csv" and PANDAS_AVAILABLE:
            # Export performance metrics as CSV
            if all_metrics:
                df = pd.DataFrame([m.to_dict() for m in all_metrics])
                df.to_csv(filepath, index=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def cleanup_old_metrics(self, older_than: timedelta) -> int:
        """Remove metrics older than specified time."""
        cutoff_time = datetime.now() - older_than

        with self.collector.lock:
            # Performance metrics
            original_count = len(self.collector.metrics)
            self.collector.metrics = deque(
                (m for m in self.collector.metrics if m.timestamp >= cutoff_time),
                maxlen=self.collector.max_metrics
            )

            # System metrics
            original_system_count = len(self.collector.system_metrics)
            self.collector.system_metrics = deque(
                (m for m in self.collector.system_metrics if m.timestamp >= cutoff_time),
                maxlen=self.collector.max_metrics
            )

            removed_count = original_count - len(self.collector.metrics) + original_system_count - len(self.collector.system_metrics)

        return removed_count

    def stop(self):
        """Stop the performance monitor and cleanup resources."""
        self.collector.stop_system_monitoring()
        logging.info("Performance monitor stopped")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    import random

    async def demo_performance_monitoring():
        """Demonstrate performance monitoring capabilities."""

        # Initialize monitor
        monitor = PerformanceMonitor()

        print("🚀 Starting NPS V3 Performance Monitoring Demo")
        print("=" * 60)

        # Simulate some agent executions
        agents = ["B1_promoter_analyst", "B2_passive_analyst", "B3_detractor_analyst", "C1_strategy_consultant"]

        for i in range(20):
            agent = random.choice(agents)

            # Simulate agent execution
            with monitor.track_agent(agent, metadata={"iteration": i}):
                # Simulate work
                await asyncio.sleep(random.uniform(0.1, 2.0))

                # Simulate occasional failures
                if random.random() < 0.05:
                    raise Exception(f"Simulated error in {agent}")

        # Simulate LLM calls
        models = ["gpt-4-turbo", "gpt-4o-mini"]

        for i in range(15):
            model = random.choice(models)

            with monitor.track_llm_call(model, "completion", metadata={"tokens": random.randint(100, 2000)}):
                await asyncio.sleep(random.uniform(0.5, 3.0))

                if random.random() < 0.03:
                    raise Exception(f"LLM API error for {model}")

        # Wait a bit for system metrics to collect
        await asyncio.sleep(2)

        # Generate performance report
        print("\n📊 Performance Statistics:")
        print("-" * 40)

        for agent in agents:
            stats = monitor.get_component_stats(agent)
            if stats:
                print(f"\n{agent}:")
                print(f"  Total calls: {stats.total_calls}")
                print(f"  Success rate: {stats.success_rate:.1%}")
                print(f"  Avg duration: {stats.avg_duration:.2f}s")
                print(f"  P95 duration: {stats.p95_duration:.2f}s")
                print(f"  Error rate: {stats.error_rate:.1%}")

        # Check for performance issues
        issues = monitor.get_performance_issues()
        if issues:
            print(f"\n⚠️  Performance Issues Detected ({len(issues)}):")
            print("-" * 40)
            for issue in issues:
                print(f"  • {issue['type']} in {issue['component']}")
                print(f"    Severity: {issue['severity']}")
                print(f"    Details: {issue['details']}")
                print(f"    Suggestion: {issue['suggestion']}")
                print()

        # Generate dashboard
        print("\n📈 Generating Performance Dashboard...")
        dashboard_html = monitor.generate_dashboard_html()

        # Save dashboard
        dashboard_path = Path("performance_dashboard.html")
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)

        print(f"✅ Dashboard saved to: {dashboard_path.absolute()}")

        # Export metrics
        metrics_path = Path("performance_metrics.json")
        monitor.export_metrics(metrics_path)
        print(f"✅ Metrics exported to: {metrics_path.absolute()}")

        # Cleanup
        monitor.stop()

        print("\n🎉 Performance monitoring demo completed!")
        print(f"Check the generated dashboard: {dashboard_path.absolute()}")

    # Run demo
    try:
        asyncio.run(demo_performance_monitoring())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
