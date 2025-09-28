"""
NPS V3 Performance Monitoring Integration

Integration utilities for seamlessly integrating performance monitoring into the existing
NPS V3 analysis system. Provides decorators, middleware, and utility functions for
monitoring agents, workflows, and LLM calls.

Features:
- Agent execution monitoring decorators
- LLM call tracking middleware
- Workflow stage monitoring
- Automatic error tracking and analysis
- Performance regression detection
- Integration with existing logging systems

Usage:
    from nps_report_v3.monitoring.integration import MonitoringIntegration

    # Initialize monitoring
    monitor = MonitoringIntegration()

    # Use decorators
    @monitor.track_agent()
    def my_agent_function():
        return "result"

    # Use context managers
    async with monitor.track_llm_call("gpt-4-turbo"):
        result = await llm_client.call(prompt)

    # Generate reports
    report = monitor.generate_performance_report()
"""

import functools
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Union, List, Tuple
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass
import inspect

from .performance_monitor import PerformanceMonitor
from .config import MonitoringConfig, create_config


@dataclass
class PerformanceReport:
    """Comprehensive performance analysis report."""

    report_id: str
    generated_at: datetime
    time_window: timedelta

    # Summary metrics
    total_operations: int
    overall_success_rate: float
    average_response_time: float

    # Component breakdown
    agent_performance: Dict[str, Dict[str, Any]]
    llm_performance: Dict[str, Dict[str, Any]]
    workflow_performance: Dict[str, Dict[str, Any]]

    # System metrics
    resource_usage: Dict[str, Any]

    # Issues and recommendations
    performance_issues: List[Dict[str, Any]]
    recommendations: List[str]

    # Trends and insights
    trend_analysis: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for serialization."""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'time_window_hours': self.time_window.total_seconds() / 3600,
            'summary': {
                'total_operations': self.total_operations,
                'overall_success_rate': self.overall_success_rate,
                'average_response_time': self.average_response_time
            },
            'component_performance': {
                'agents': self.agent_performance,
                'llm': self.llm_performance,
                'workflows': self.workflow_performance
            },
            'system_metrics': self.resource_usage,
            'issues': self.performance_issues,
            'recommendations': self.recommendations,
            'trends': self.trend_analysis
        }


class MonitoringIntegration:
    """Main integration class for NPS V3 performance monitoring."""

    def __init__(self, config: Optional[MonitoringConfig] = None):
        """
        Initialize monitoring integration.

        Args:
            config: Optional monitoring configuration
        """
        self.config = config or create_config()
        self.monitor = PerformanceMonitor(**self.config.get_monitor_config())
        self.logger = logging.getLogger(__name__)

        # Integration state
        self._enabled = True
        self._component_registry: Dict[str, Dict[str, Any]] = {}

        self.logger.info("Monitoring integration initialized")

    def enable(self) -> None:
        """Enable monitoring."""
        self._enabled = True
        self.logger.info("Monitoring enabled")

    def disable(self) -> None:
        """Disable monitoring."""
        self._enabled = False
        self.logger.info("Monitoring disabled")

    def register_component(
        self,
        component_name: str,
        component_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a component for monitoring."""
        self._component_registry[component_name] = {
            'type': component_type,
            'registered_at': datetime.now(),
            'metadata': metadata or {}
        }
        self.logger.debug(f"Registered component: {component_name} ({component_type})")

    def track_agent(
        self,
        agent_id: Optional[str] = None,
        operation: str = "execute",
        track_errors: bool = True,
        include_args: bool = False
    ):
        """
        Decorator for tracking agent execution performance.

        Args:
            agent_id: Optional agent identifier (auto-detected if not provided)
            operation: Operation type being performed
            track_errors: Whether to track and log errors
            include_args: Whether to include function arguments in metadata

        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            # Auto-detect agent_id from function name or class if not provided
            actual_agent_id = agent_id or self._extract_agent_id(func)

            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    if not self._enabled:
                        return await func(*args, **kwargs)

                    metadata = {}
                    if include_args:
                        metadata.update({
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        })

                    try:
                        async with self.monitor.track_async_operation(
                            component=actual_agent_id,
                            operation=operation,
                            metadata=metadata
                        ):
                            result = await func(*args, **kwargs)
                            return result

                    except Exception as e:
                        if track_errors:
                            self.logger.error(f"Agent {actual_agent_id} error in {operation}: {e}")
                        raise

                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    if not self._enabled:
                        return func(*args, **kwargs)

                    metadata = {}
                    if include_args:
                        metadata.update({
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        })

                    try:
                        with self.monitor.track_agent(
                            agent_id=actual_agent_id,
                            operation=operation,
                            metadata=metadata
                        ):
                            result = func(*args, **kwargs)
                            return result

                    except Exception as e:
                        if track_errors:
                            self.logger.error(f"Agent {actual_agent_id} error in {operation}: {e}")
                        raise

                return sync_wrapper

        return decorator

    def track_llm_call(
        self,
        model: Optional[str] = None,
        call_type: str = "completion",
        track_tokens: bool = True
    ):
        """
        Decorator for tracking LLM API calls.

        Args:
            model: LLM model name (auto-detected if not provided)
            call_type: Type of LLM call (completion, embedding, etc.)
            track_tokens: Whether to track token usage in metadata

        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            actual_model = model or "auto-detected"

            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    if not self._enabled:
                        return await func(*args, **kwargs)

                    metadata = {}
                    if track_tokens and 'max_tokens' in kwargs:
                        metadata['max_tokens'] = kwargs['max_tokens']

                    try:
                        with self.monitor.track_llm_call(
                            model=actual_model,
                            call_type=call_type,
                            metadata=metadata
                        ):
                            result = await func(*args, **kwargs)

                            # Try to extract token usage from result
                            if track_tokens and hasattr(result, 'usage'):
                                metadata.update({
                                    'prompt_tokens': getattr(result.usage, 'prompt_tokens', 0),
                                    'completion_tokens': getattr(result.usage, 'completion_tokens', 0),
                                    'total_tokens': getattr(result.usage, 'total_tokens', 0)
                                })

                            return result

                    except Exception as e:
                        self.logger.error(f"LLM call error for {actual_model}: {e}")
                        raise

                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    if not self._enabled:
                        return func(*args, **kwargs)

                    metadata = {}
                    if track_tokens and 'max_tokens' in kwargs:
                        metadata['max_tokens'] = kwargs['max_tokens']

                    try:
                        with self.monitor.track_llm_call(
                            model=actual_model,
                            call_type=call_type,
                            metadata=metadata
                        ):
                            result = func(*args, **kwargs)

                            # Try to extract token usage from result
                            if track_tokens and hasattr(result, 'usage'):
                                metadata.update({
                                    'prompt_tokens': getattr(result.usage, 'prompt_tokens', 0),
                                    'completion_tokens': getattr(result.usage, 'completion_tokens', 0),
                                    'total_tokens': getattr(result.usage, 'total_tokens', 0)
                                })

                            return result

                    except Exception as e:
                        self.logger.error(f"LLM call error for {actual_model}: {e}")
                        raise

                return sync_wrapper

        return decorator

    def track_workflow_stage(self, workflow_name: str, stage: str):
        """
        Decorator for tracking workflow stage execution.

        Args:
            workflow_name: Name of the workflow
            stage: Stage name within the workflow

        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            if inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    if not self._enabled:
                        return await func(*args, **kwargs)

                    with self.monitor.track_workflow(
                        workflow_name=workflow_name,
                        stage=stage
                    ):
                        return await func(*args, **kwargs)

                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    if not self._enabled:
                        return func(*args, **kwargs)

                    with self.monitor.track_workflow(
                        workflow_name=workflow_name,
                        stage=stage
                    ):
                        return func(*args, **kwargs)

                return sync_wrapper

        return decorator

    @contextmanager
    def track_custom_operation(
        self,
        component: str,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Context manager for tracking custom operations."""
        if not self._enabled:
            yield
            return

        with self.monitor.track_agent(agent_id=component, operation=operation, metadata=metadata):
            yield

    @asynccontextmanager
    async def track_async_custom_operation(
        self,
        component: str,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Async context manager for tracking custom operations."""
        if not self._enabled:
            yield
            return

        async with self.monitor.track_async_operation(
            component=component,
            operation=operation,
            metadata=metadata
        ):
            yield

    def generate_performance_report(
        self,
        time_window: Optional[timedelta] = None
    ) -> PerformanceReport:
        """Generate comprehensive performance analysis report."""
        if time_window is None:
            time_window = timedelta(hours=6)

        report_id = f"nps_v3_perf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Get metrics for the time window
        since = datetime.now() - time_window
        recent_metrics = self.monitor.collector.get_metrics(since=since)
        system_metrics = self.monitor.collector.get_system_metrics(since=since)

        # Calculate summary statistics
        total_operations = len(recent_metrics)
        successful_operations = len([m for m in recent_metrics if m.success])
        overall_success_rate = successful_operations / total_operations if total_operations > 0 else 0.0

        durations = [m.duration for m in recent_metrics if m.success]
        average_response_time = sum(durations) / len(durations) if durations else 0.0

        # Analyze component performance
        agent_performance = self._analyze_component_performance(recent_metrics, "agent")
        llm_performance = self._analyze_component_performance(recent_metrics, "llm_call")
        workflow_performance = self._analyze_component_performance(recent_metrics, "workflow")

        # Analyze system resource usage
        resource_usage = self._analyze_system_metrics(system_metrics)

        # Detect performance issues
        performance_issues = self.monitor.get_performance_issues()

        # Generate recommendations
        recommendations = self._generate_recommendations(recent_metrics, performance_issues)

        # Perform trend analysis
        trend_analysis = self._analyze_trends(recent_metrics, time_window)

        return PerformanceReport(
            report_id=report_id,
            generated_at=datetime.now(),
            time_window=time_window,
            total_operations=total_operations,
            overall_success_rate=overall_success_rate,
            average_response_time=average_response_time,
            agent_performance=agent_performance,
            llm_performance=llm_performance,
            workflow_performance=workflow_performance,
            resource_usage=resource_usage,
            performance_issues=performance_issues,
            recommendations=recommendations,
            trend_analysis=trend_analysis
        )

    def get_real_time_status(self) -> Dict[str, Any]:
        """Get real-time monitoring status."""
        # Get recent metrics (last 10 minutes)
        recent = datetime.now() - timedelta(minutes=10)
        recent_metrics = self.monitor.collector.get_metrics(since=recent)

        # Get latest system metrics
        system_metrics = self.monitor.collector.get_system_metrics(since=recent)
        latest_system = system_metrics[-1] if system_metrics else None

        # Calculate real-time statistics
        total_recent = len(recent_metrics)
        successful_recent = len([m for m in recent_metrics if m.success])
        recent_success_rate = successful_recent / total_recent if total_recent > 0 else 0.0

        # Active components
        active_components = set(m.component for m in recent_metrics)

        # Current alerts
        active_alerts = self.monitor.get_active_alerts()

        return {
            'monitoring_enabled': self._enabled,
            'timestamp': datetime.now().isoformat(),
            'recent_activity': {
                'total_operations_10min': total_recent,
                'success_rate_10min': recent_success_rate,
                'active_components': list(active_components),
                'operations_per_minute': total_recent / 10.0 if total_recent > 0 else 0.0
            },
            'system_status': {
                'cpu_percent': latest_system.cpu_percent if latest_system else 0.0,
                'memory_percent': latest_system.memory_percent if latest_system else 0.0,
                'memory_used_mb': latest_system.memory_used_mb if latest_system else 0.0
            } if latest_system else {},
            'alerts': {
                'total_active_alerts': len(active_alerts),
                'high_severity_alerts': len([a for a in active_alerts if a.get('severity') == 'high']),
                'latest_alerts': active_alerts[:3]  # Show 3 most recent
            },
            'registered_components': len(self._component_registry)
        }

    def export_performance_data(
        self,
        filepath: str,
        format: str = "json",
        time_window: Optional[timedelta] = None
    ) -> None:
        """Export performance data to file."""
        if time_window:
            # Clean up old metrics first
            older_than = datetime.now() - time_window
            self.monitor.cleanup_old_metrics(timedelta(seconds=(datetime.now() - older_than).total_seconds()))

        self.monitor.export_metrics(filepath, format)
        self.logger.info(f"Performance data exported to: {filepath}")

    def get_dashboard_html(self) -> str:
        """Get HTML performance dashboard."""
        return self.monitor.generate_dashboard_html()

    def _extract_agent_id(self, func: Callable) -> str:
        """Extract agent ID from function or class name."""
        # Try to get class name if it's a method
        if hasattr(func, '__self__'):
            class_name = func.__self__.__class__.__name__
            if 'Agent' in class_name:
                return class_name

        # Fall back to function name
        func_name = func.__name__
        if 'agent' in func_name.lower():
            return func_name

        return f"unknown_agent_{func_name}"

    def _analyze_component_performance(
        self,
        metrics: List,
        component_type: str
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze performance for components of a specific type."""
        type_metrics = [m for m in metrics if m.metric_type == component_type]

        # Group by component
        component_groups = {}
        for metric in type_metrics:
            if metric.component not in component_groups:
                component_groups[metric.component] = []
            component_groups[metric.component].append(metric)

        # Calculate statistics for each component
        component_stats = {}
        for component, comp_metrics in component_groups.items():
            if not comp_metrics:
                continue

            durations = [m.duration for m in comp_metrics]
            successes = [m.success for m in comp_metrics]

            component_stats[component] = {
                'total_calls': len(comp_metrics),
                'success_rate': sum(successes) / len(successes) if successes else 0.0,
                'avg_duration': sum(durations) / len(durations) if durations else 0.0,
                'min_duration': min(durations) if durations else 0.0,
                'max_duration': max(durations) if durations else 0.0,
                'error_count': len([m for m in comp_metrics if not m.success]),
                'last_execution': max(m.timestamp for m in comp_metrics).isoformat()
            }

        return component_stats

    def _analyze_system_metrics(self, system_metrics: List) -> Dict[str, Any]:
        """Analyze system resource usage metrics."""
        if not system_metrics:
            return {}

        cpu_values = [m.cpu_percent for m in system_metrics]
        memory_values = [m.memory_percent for m in system_metrics]
        memory_mb_values = [m.memory_used_mb for m in system_metrics]

        return {
            'cpu_usage': {
                'avg': sum(cpu_values) / len(cpu_values),
                'min': min(cpu_values),
                'max': max(cpu_values),
                'current': cpu_values[-1] if cpu_values else 0.0
            },
            'memory_usage': {
                'avg_percent': sum(memory_values) / len(memory_values),
                'min_percent': min(memory_values),
                'max_percent': max(memory_values),
                'current_percent': memory_values[-1] if memory_values else 0.0,
                'avg_mb': sum(memory_mb_values) / len(memory_mb_values),
                'current_mb': memory_mb_values[-1] if memory_mb_values else 0.0
            },
            'data_points': len(system_metrics),
            'monitoring_duration_minutes':
                (system_metrics[-1].timestamp - system_metrics[0].timestamp).total_seconds() / 60
                if len(system_metrics) > 1 else 0.0
        }

    def _generate_recommendations(
        self,
        metrics: List,
        issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Analyze error patterns
        error_metrics = [m for m in metrics if not m.success]
        if error_metrics:
            error_rate = len(error_metrics) / len(metrics) if metrics else 0.0
            if error_rate > 0.05:
                recommendations.append(
                    f"High error rate detected ({error_rate:.1%}). "
                    "Review error handling and implement retry mechanisms."
                )

        # Analyze slow operations
        slow_operations = [m for m in metrics if m.success and m.duration > 30.0]
        if slow_operations:
            slow_rate = len(slow_operations) / len(metrics) if metrics else 0.0
            if slow_rate > 0.10:
                recommendations.append(
                    f"Slow operations detected ({slow_rate:.1%} taking >30s). "
                    "Consider implementing caching or optimizing bottleneck operations."
                )

        # Analyze component-specific issues
        component_durations = {}
        for metric in metrics:
            if metric.success:
                if metric.component not in component_durations:
                    component_durations[metric.component] = []
                component_durations[metric.component].append(metric.duration)

        for component, durations in component_durations.items():
            if durations:
                avg_duration = sum(durations) / len(durations)
                if avg_duration > 20.0:
                    recommendations.append(
                        f"Component '{component}' has high average duration ({avg_duration:.1f}s). "
                        "Consider optimization or parallel processing."
                    )

        # Based on system issues
        for issue in issues:
            if issue['type'] == 'high_cpu_usage':
                recommendations.append(
                    "High CPU usage detected. Consider implementing CPU-intensive operation batching "
                    "or offloading to background tasks."
                )
            elif issue['type'] == 'high_memory_usage':
                recommendations.append(
                    "High memory usage detected. Review memory cleanup patterns and consider "
                    "implementing more aggressive garbage collection."
                )

        # Default recommendations if no specific issues found
        if not recommendations and metrics:
            recommendations.append(
                "System appears to be performing well. Continue monitoring for trend analysis."
            )

        return recommendations

    def _analyze_trends(
        self,
        metrics: List,
        time_window: timedelta
    ) -> Dict[str, Any]:
        """Analyze performance trends over the time window."""
        if len(metrics) < 10:  # Not enough data for trend analysis
            return {
                'trend_available': False,
                'reason': 'Insufficient data points for trend analysis'
            }

        # Sort metrics by timestamp
        sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)

        # Split into time buckets for trend analysis
        bucket_count = min(10, len(sorted_metrics) // 2)  # Up to 10 buckets
        bucket_size = len(sorted_metrics) // bucket_count

        trend_data = []
        for i in range(bucket_count):
            start_idx = i * bucket_size
            end_idx = start_idx + bucket_size if i < bucket_count - 1 else len(sorted_metrics)
            bucket_metrics = sorted_metrics[start_idx:end_idx]

            if bucket_metrics:
                bucket_durations = [m.duration for m in bucket_metrics if m.success]
                bucket_success_rate = sum(1 for m in bucket_metrics if m.success) / len(bucket_metrics)

                trend_data.append({
                    'timestamp': bucket_metrics[0].timestamp.isoformat(),
                    'avg_duration': sum(bucket_durations) / len(bucket_durations) if bucket_durations else 0.0,
                    'success_rate': bucket_success_rate,
                    'operation_count': len(bucket_metrics)
                })

        # Simple trend detection
        if len(trend_data) >= 3:
            recent_duration = sum(bucket['avg_duration'] for bucket in trend_data[-3:]) / 3
            early_duration = sum(bucket['avg_duration'] for bucket in trend_data[:3]) / 3

            duration_trend = "improving" if recent_duration < early_duration else "degrading" if recent_duration > early_duration else "stable"

            recent_success = sum(bucket['success_rate'] for bucket in trend_data[-3:]) / 3
            early_success = sum(bucket['success_rate'] for bucket in trend_data[:3]) / 3

            success_trend = "improving" if recent_success > early_success else "degrading" if recent_success < early_success else "stable"
        else:
            duration_trend = "insufficient_data"
            success_trend = "insufficient_data"

        return {
            'trend_available': True,
            'time_buckets': trend_data,
            'duration_trend': duration_trend,
            'success_rate_trend': success_trend,
            'analysis_period_hours': time_window.total_seconds() / 3600
        }


# Utility functions for easy integration
def monitor_agent(agent_id: Optional[str] = None, **kwargs):
    """Convenience function to create agent monitoring decorator."""
    integration = MonitoringIntegration()
    return integration.track_agent(agent_id=agent_id, **kwargs)


def monitor_llm_call(model: Optional[str] = None, **kwargs):
    """Convenience function to create LLM call monitoring decorator."""
    integration = MonitoringIntegration()
    return integration.track_llm_call(model=model, **kwargs)


def monitor_workflow_stage(workflow_name: str, stage: str):
    """Convenience function to create workflow stage monitoring decorator."""
    integration = MonitoringIntegration()
    return integration.track_workflow_stage(workflow_name=workflow_name, stage=stage)


# Global monitoring instance for easy access
_global_monitoring: Optional[MonitoringIntegration] = None


def get_global_monitoring() -> MonitoringIntegration:
    """Get or create global monitoring instance."""
    global _global_monitoring
    if _global_monitoring is None:
        _global_monitoring = MonitoringIntegration()
    return _global_monitoring


def setup_global_monitoring(config: Optional[MonitoringConfig] = None) -> MonitoringIntegration:
    """Setup global monitoring with custom configuration."""
    global _global_monitoring
    _global_monitoring = MonitoringIntegration(config=config)
    return _global_monitoring


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    import random

    async def demo_monitoring_integration():
        """Demonstrate monitoring integration capabilities."""

        print("🔗 Starting NPS V3 Monitoring Integration Demo")
        print("=" * 60)

        # Setup monitoring
        integration = MonitoringIntegration()

        # Example agent function with monitoring
        @integration.track_agent("demo_agent")
        async def analyze_feedback(feedback_text: str) -> Dict[str, Any]:
            await asyncio.sleep(random.uniform(0.5, 2.0))  # Simulate processing

            if random.random() < 0.05:  # 5% error rate
                raise Exception("Simulated analysis error")

            return {
                "sentiment": random.choice(["positive", "negative", "neutral"]),
                "confidence": random.uniform(0.7, 1.0),
                "key_phrases": ["quality", "taste", "packaging"]
            }

        # Example LLM call with monitoring
        @integration.track_llm_call("gpt-4-turbo")
        async def generate_insights(data: Dict[str, Any]) -> str:
            await asyncio.sleep(random.uniform(1.0, 3.0))  # Simulate API call

            if random.random() < 0.02:  # 2% error rate
                raise Exception("LLM API error")

            return f"Generated insights for {data['sentiment']} feedback"

        # Example workflow stage monitoring
        @integration.track_workflow_stage("nps_analysis", "preprocessing")
        async def preprocess_data(raw_data: List[str]) -> List[Dict[str, Any]]:
            await asyncio.sleep(0.5)
            return [{"text": text, "processed": True} for text in raw_data]

        print("\n🚀 Running simulated operations...")

        # Simulate operations
        sample_feedback = [
            "伊利安慕希酸奶味道很好",
            "包装设计需要改进",
            "价格有点高但质量不错",
            "希望有更多口味选择",
            "物流速度很快，满意"
        ]

        # Preprocessing
        processed_data = await preprocess_data(sample_feedback)
        print(f"   ✅ Preprocessed {len(processed_data)} items")

        # Analysis operations
        for i, item in enumerate(processed_data):
            try:
                # Analyze feedback
                result = await analyze_feedback(item['text'])

                # Generate insights
                insights = await generate_insights(result)

                print(f"   ✅ Processed item {i+1}: {result['sentiment']}")

            except Exception as e:
                print(f"   ❌ Error processing item {i+1}: {e}")

        # Wait for metrics collection
        await asyncio.sleep(2)

        # Generate performance report
        print("\n📊 Generating Performance Report...")
        report = integration.generate_performance_report(time_window=timedelta(minutes=5))

        print(f"   Report ID: {report.report_id}")
        print(f"   Total Operations: {report.total_operations}")
        print(f"   Overall Success Rate: {report.overall_success_rate:.1%}")
        print(f"   Average Response Time: {report.average_response_time:.2f}s")

        # Show component performance
        print(f"\n   Agent Performance:")
        for agent, stats in report.agent_performance.items():
            print(f"     {agent}: {stats['success_rate']:.1%} success, {stats['avg_duration']:.2f}s avg")

        print(f"\n   LLM Performance:")
        for model, stats in report.llm_performance.items():
            print(f"     {model}: {stats['success_rate']:.1%} success, {stats['avg_duration']:.2f}s avg")

        # Show real-time status
        print(f"\n📈 Real-time Status:")
        status = integration.get_real_time_status()
        print(f"   Operations (10min): {status['recent_activity']['total_operations_10min']}")
        print(f"   Success Rate (10min): {status['recent_activity']['success_rate_10min']:.1%}")
        print(f"   Active Components: {len(status['recent_activity']['active_components'])}")

        # Export data
        print(f"\n💾 Exporting Performance Data...")
        integration.export_performance_data("demo_performance_metrics.json", time_window=timedelta(hours=1))
        print(f"   ✅ Data exported successfully")

        # Generate dashboard
        print(f"\n📈 Generating Dashboard...")
        dashboard_html = integration.get_dashboard_html()

        with open("demo_monitoring_dashboard.html", 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
        print(f"   ✅ Dashboard saved to: demo_monitoring_dashboard.html")

        print(f"\n🎉 Monitoring integration demo completed!")
        print(f"📊 Check the generated dashboard and exported metrics for detailed analysis.")

    # Run the demo
    try:
        asyncio.run(demo_monitoring_integration())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()