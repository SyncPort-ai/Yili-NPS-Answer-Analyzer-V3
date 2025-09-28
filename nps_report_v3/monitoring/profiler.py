"""
Monitoring and profiling infrastructure for NPS V3 API.
Provides memory tracking, execution time profiling, and performance metrics.
"""

import time
import psutil
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
from pathlib import Path
import functools

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionProfile:
    """Execution profile for a function or operation"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    memory_before_mb: Optional[float] = None
    memory_after_mb: Optional[float] = None
    memory_delta_mb: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryMonitor:
    """Monitor memory usage"""

    def __init__(self, threshold_mb: float = 1024):
        self.process = psutil.Process()
        self.threshold_mb = threshold_mb
        self.baseline_mb = self.get_memory_usage_mb()

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / (1024 * 1024)

    def get_memory_percent(self) -> float:
        """Get memory usage as percentage of available memory"""
        return self.process.memory_percent()

    def check_memory_pressure(self) -> bool:
        """Check if memory usage exceeds threshold"""
        current_mb = self.get_memory_usage_mb()
        return current_mb > self.threshold_mb

    def get_memory_delta_mb(self) -> float:
        """Get memory change from baseline"""
        return self.get_memory_usage_mb() - self.baseline_mb

    def reset_baseline(self):
        """Reset memory baseline"""
        self.baseline_mb = self.get_memory_usage_mb()


class ExecutionProfiler:
    """Profile execution time and resources"""

    def __init__(self):
        self.profiles: List[ExecutionProfile] = []
        self.memory_monitor = MemoryMonitor()

    def start_profile(self, name: str, metadata: Optional[Dict] = None) -> ExecutionProfile:
        """Start profiling an operation"""
        profile = ExecutionProfile(
            name=name,
            start_time=time.time(),
            memory_before_mb=self.memory_monitor.get_memory_usage_mb(),
            metadata=metadata or {}
        )
        return profile

    def end_profile(self, profile: ExecutionProfile, error: Optional[str] = None):
        """End profiling and calculate metrics"""
        profile.end_time = time.time()
        profile.duration_ms = (profile.end_time - profile.start_time) * 1000
        profile.memory_after_mb = self.memory_monitor.get_memory_usage_mb()
        profile.memory_delta_mb = profile.memory_after_mb - profile.memory_before_mb
        profile.error = error

        self.profiles.append(profile)

        # Log if execution was slow or used too much memory
        if profile.duration_ms > 5000:  # 5 seconds
            logger.warning(f"Slow execution: {profile.name} took {profile.duration_ms:.2f}ms")
        if profile.memory_delta_mb > 100:  # 100MB
            logger.warning(f"High memory usage: {profile.name} used {profile.memory_delta_mb:.2f}MB")

    def get_summary(self) -> Dict[str, Any]:
        """Get profiling summary"""
        if not self.profiles:
            return {}

        total_duration = sum(p.duration_ms for p in self.profiles if p.duration_ms)
        total_memory = sum(p.memory_delta_mb for p in self.profiles if p.memory_delta_mb)

        return {
            "total_operations": len(self.profiles),
            "total_duration_ms": total_duration,
            "total_memory_mb": total_memory,
            "average_duration_ms": total_duration / len(self.profiles),
            "average_memory_mb": total_memory / len(self.profiles),
            "slowest_operation": max(self.profiles, key=lambda p: p.duration_ms or 0).name,
            "highest_memory_operation": max(self.profiles, key=lambda p: p.memory_delta_mb or 0).name
        }


class MetricsCollector:
    """Collect and aggregate performance metrics"""

    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)

    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict] = None):
        """Increment a counter metric"""
        self.counters[name] += value
        self.metrics.append(PerformanceMetric(
            name=f"counter.{name}",
            value=value,
            unit="count",
            timestamp=datetime.utcnow(),
            tags=tags or {}
        ))

    def set_gauge(self, name: str, value: float, tags: Optional[Dict] = None):
        """Set a gauge metric"""
        self.gauges[name] = value
        self.metrics.append(PerformanceMetric(
            name=f"gauge.{name}",
            value=value,
            unit="value",
            timestamp=datetime.utcnow(),
            tags=tags or {}
        ))

    def record_histogram(self, name: str, value: float, tags: Optional[Dict] = None):
        """Record a histogram metric"""
        self.histograms[name].append(value)
        self.metrics.append(PerformanceMetric(
            name=f"histogram.{name}",
            value=value,
            unit="value",
            timestamp=datetime.utcnow(),
            tags=tags or {}
        ))

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        summary = {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {}
        }

        # Calculate histogram statistics
        for name, values in self.histograms.items():
            if values:
                import statistics
                summary["histograms"][name] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "stdev": statistics.stdev(values) if len(values) > 1 else 0
                }

        return summary

    def export_metrics(self, filepath: str):
        """Export metrics to file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump({
                "summary": self.get_summary(),
                "metrics": [
                    {
                        "name": m.name,
                        "value": m.value,
                        "unit": m.unit,
                        "timestamp": m.timestamp.isoformat(),
                        "tags": m.tags
                    }
                    for m in self.metrics[-1000:]  # Keep last 1000 metrics
                ]
            }, f, indent=2)


class WorkflowProfiler:
    """Profile entire workflow execution"""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.profiler = ExecutionProfiler()
        self.metrics = MetricsCollector()
        self.agent_profiles: Dict[str, ExecutionProfile] = {}

    def profile_agent(self, agent_id: str) -> ExecutionProfile:
        """Start profiling an agent"""
        profile = self.profiler.start_profile(f"agent_{agent_id}", {"agent_id": agent_id})
        self.agent_profiles[agent_id] = profile
        return profile

    def end_agent_profile(self, agent_id: str, success: bool = True, error: Optional[str] = None):
        """End agent profiling"""
        if agent_id in self.agent_profiles:
            profile = self.agent_profiles[agent_id]
            self.profiler.end_profile(profile, error)

            # Record metrics
            self.metrics.increment_counter(f"agent.{agent_id}.executions")
            if success:
                self.metrics.increment_counter(f"agent.{agent_id}.success")
            else:
                self.metrics.increment_counter(f"agent.{agent_id}.failure")

            if profile.duration_ms:
                self.metrics.record_histogram(f"agent.{agent_id}.duration_ms", profile.duration_ms)
            if profile.memory_delta_mb:
                self.metrics.record_histogram(f"agent.{agent_id}.memory_mb", profile.memory_delta_mb)

    def get_report(self) -> Dict[str, Any]:
        """Get comprehensive profiling report"""
        return {
            "workflow_id": self.workflow_id,
            "profiling_summary": self.profiler.get_summary(),
            "metrics_summary": self.metrics.get_summary(),
            "agent_profiles": {
                agent_id: {
                    "duration_ms": profile.duration_ms,
                    "memory_delta_mb": profile.memory_delta_mb,
                    "error": profile.error
                }
                for agent_id, profile in self.agent_profiles.items()
            }
        }


# Decorators for profiling

def profile_async(name: Optional[str] = None):
    """Decorator to profile async functions"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = name or func.__name__
            profiler = ExecutionProfiler()
            profile = profiler.start_profile(func_name)

            try:
                result = await func(*args, **kwargs)
                profiler.end_profile(profile)

                logger.debug(f"Profiled {func_name}: {profile.duration_ms:.2f}ms, {profile.memory_delta_mb:.2f}MB")

                return result
            except Exception as e:
                profiler.end_profile(profile, str(e))
                raise

        return wrapper
    return decorator


def profile_sync(name: Optional[str] = None):
    """Decorator to profile sync functions"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = name or func.__name__
            profiler = ExecutionProfiler()
            profile = profiler.start_profile(func_name)

            try:
                result = func(*args, **kwargs)
                profiler.end_profile(profile)

                logger.debug(f"Profiled {func_name}: {profile.duration_ms:.2f}ms, {profile.memory_delta_mb:.2f}MB")

                return result
            except Exception as e:
                profiler.end_profile(profile, str(e))
                raise

        return wrapper
    return decorator


# Global profiler instance
_global_profiler = None


def get_global_profiler() -> WorkflowProfiler:
    """Get global profiler instance"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = WorkflowProfiler("global")
    return _global_profiler


def reset_global_profiler(workflow_id: str = "global"):
    """Reset global profiler"""
    global _global_profiler
    _global_profiler = WorkflowProfiler(workflow_id)