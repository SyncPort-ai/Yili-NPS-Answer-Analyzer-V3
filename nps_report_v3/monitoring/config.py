"""
Performance Monitoring Configuration

Configuration management for the NPS V3 performance monitoring system.
Supports environment variable overrides, file-based configuration, and runtime configuration.

Features:
- Environment variable configuration
- JSON configuration file support
- Runtime configuration updates
- Validation and default values
- Configuration profiles for different environments

Usage:
    from nps_report_v3.monitoring.config import MonitoringConfig

    # Load configuration
    config = MonitoringConfig()

    # Create monitor with configuration
    monitor = PerformanceMonitor(**config.get_monitor_config())

    # Update configuration at runtime
    config.update({"alert_thresholds": {"error_rate": 0.10}})
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict


@dataclass
class AlertThresholds:
    """Alert threshold configuration."""

    error_rate: float = 0.05          # 5% error rate threshold
    avg_duration: float = 30.0        # 30 seconds average duration threshold
    cpu_usage: float = 80.0           # 80% CPU usage threshold
    memory_usage: float = 80.0        # 80% memory usage threshold
    disk_usage: float = 90.0          # 90% disk usage threshold
    p95_duration: float = 60.0        # 60 seconds P95 duration threshold
    success_rate: float = 0.95        # 95% minimum success rate
    throughput_minimum: float = 1.0   # 1 call per minute minimum throughput

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertThresholds':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class MetricsConfig:
    """Metrics collection configuration."""

    max_metrics: int = 10000                    # Maximum metrics to keep in memory
    system_monitoring_interval: float = 5.0    # System monitoring interval in seconds
    auto_cleanup_hours: int = 24               # Auto cleanup older than X hours
    cleanup_interval_hours: int = 6           # Run cleanup every X hours
    export_interval_minutes: int = 60         # Export metrics every X minutes
    retention_days: int = 30                  # Keep exported metrics for X days

    def to_dict(self) -> Dict[str, Union[int, float]]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricsConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class DashboardConfig:
    """Dashboard configuration."""

    refresh_seconds: int = 30              # Dashboard refresh interval
    max_components_display: int = 20       # Maximum components to show
    time_window_hours: int = 6             # Default time window for charts
    enable_plotly: bool = True             # Enable Plotly interactive charts
    enable_alerts: bool = True             # Show alerts in dashboard
    show_system_metrics: bool = True       # Show system resource metrics
    chart_height: int = 400                # Chart height in pixels

    def to_dict(self) -> Dict[str, Union[int, bool]]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DashboardConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class ExportConfig:
    """Export configuration."""

    enabled: bool = True                   # Enable metric exports
    format: str = "json"                   # Export format (json, csv)
    output_directory: str = "outputs/monitoring"  # Export directory
    filename_prefix: str = "nps_v3_metrics"       # Filename prefix
    include_system_metrics: bool = True    # Include system metrics in exports
    compress: bool = False                 # Compress exported files
    concurrent_exports: int = 1            # Maximum concurrent exports

    def to_dict(self) -> Dict[str, Union[str, bool, int]]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


@dataclass
class LoggingConfig:
    """Logging configuration for monitoring."""

    level: str = "INFO"                    # Logging level
    enable_performance_logs: bool = True   # Log performance metrics
    enable_alert_logs: bool = True         # Log alerts
    enable_system_logs: bool = False       # Log system metrics (verbose)
    log_file: Optional[str] = None         # Log file path (None for stdout)

    def to_dict(self) -> Dict[str, Union[str, bool]]:
        """Convert to dictionary."""
        result = asdict(self)
        if result["log_file"] is None:
            result["log_file"] = None  # Keep as None instead of converting to string
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoggingConfig':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


class MonitoringConfig:
    """Main monitoring configuration manager."""

    def __init__(self, config_file: Optional[Union[str, Path]] = None, load_env: bool = True):
        """
        Initialize monitoring configuration.

        Args:
            config_file: Optional configuration file path
            load_env: Whether to load configuration from environment variables
        """
        # Initialize with defaults
        self.alert_thresholds = AlertThresholds()
        self.metrics_config = MetricsConfig()
        self.dashboard_config = DashboardConfig()
        self.export_config = ExportConfig()
        self.logging_config = LoggingConfig()

        # Setup logging first
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Load from file if provided
        if config_file:
            self.load_from_file(config_file)

        # Load from environment variables
        if load_env:
            self.load_from_env()

        self.logger.info("Monitoring configuration initialized")

    def load_from_file(self, config_file: Union[str, Path]) -> None:
        """Load configuration from JSON file."""
        config_path = Path(config_file)

        if not config_path.exists():
            self.logger.warning(f"Configuration file not found: {config_path}")
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Update configurations
            if 'alert_thresholds' in data:
                self.alert_thresholds = AlertThresholds.from_dict(data['alert_thresholds'])

            if 'metrics_config' in data:
                self.metrics_config = MetricsConfig.from_dict(data['metrics_config'])

            if 'dashboard_config' in data:
                self.dashboard_config = DashboardConfig.from_dict(data['dashboard_config'])

            if 'export_config' in data:
                self.export_config = ExportConfig.from_dict(data['export_config'])

            if 'logging_config' in data:
                self.logging_config = LoggingConfig.from_dict(data['logging_config'])

            self.logger.info(f"Configuration loaded from: {config_path}")

        except Exception as e:
            self.logger.error(f"Error loading configuration file {config_path}: {e}")
            raise

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""

        # Alert thresholds
        if env_error_rate := os.getenv("NPS_MONITOR_ERROR_RATE_THRESHOLD"):
            self.alert_thresholds.error_rate = float(env_error_rate)

        if env_duration := os.getenv("NPS_MONITOR_DURATION_THRESHOLD"):
            self.alert_thresholds.avg_duration = float(env_duration)

        if env_cpu := os.getenv("NPS_MONITOR_CPU_THRESHOLD"):
            self.alert_thresholds.cpu_usage = float(env_cpu)

        if env_memory := os.getenv("NPS_MONITOR_MEMORY_THRESHOLD"):
            self.alert_thresholds.memory_usage = float(env_memory)

        # Metrics config
        if env_max_metrics := os.getenv("NPS_MONITOR_MAX_METRICS"):
            self.metrics_config.max_metrics = int(env_max_metrics)

        if env_system_interval := os.getenv("NPS_MONITOR_SYSTEM_INTERVAL"):
            self.metrics_config.system_monitoring_interval = float(env_system_interval)

        if env_cleanup_hours := os.getenv("NPS_MONITOR_CLEANUP_HOURS"):
            self.metrics_config.auto_cleanup_hours = int(env_cleanup_hours)

        # Dashboard config
        if env_refresh := os.getenv("NPS_MONITOR_DASHBOARD_REFRESH"):
            self.dashboard_config.refresh_seconds = int(env_refresh)

        if env_time_window := os.getenv("NPS_MONITOR_TIME_WINDOW_HOURS"):
            self.dashboard_config.time_window_hours = int(env_time_window)

        # Export config
        if env_export_enabled := os.getenv("NPS_MONITOR_EXPORT_ENABLED"):
            self.export_config.enabled = env_export_enabled.lower() in ('true', '1', 'yes')

        if env_export_dir := os.getenv("NPS_MONITOR_EXPORT_DIR"):
            self.export_config.output_directory = env_export_dir

        if env_export_format := os.getenv("NPS_MONITOR_EXPORT_FORMAT"):
            self.export_config.format = env_export_format

        # Logging config
        if env_log_level := os.getenv("NPS_MONITOR_LOG_LEVEL"):
            self.logging_config.level = env_log_level.upper()

        if env_log_file := os.getenv("NPS_MONITOR_LOG_FILE"):
            self.logging_config.log_file = env_log_file

        # Configuration loaded from environment variables (logged later)

    def save_to_file(self, config_file: Union[str, Path]) -> None:
        """Save current configuration to JSON file."""
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {
            'alert_thresholds': self.alert_thresholds.to_dict(),
            'metrics_config': self.metrics_config.to_dict(),
            'dashboard_config': self.dashboard_config.to_dict(),
            'export_config': self.export_config.to_dict(),
            'logging_config': self.logging_config.to_dict()
        }

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Configuration saved to: {config_path}")

        except Exception as e:
            self.logger.error(f"Error saving configuration to {config_path}: {e}")
            raise

    def get_monitor_config(self) -> Dict[str, Any]:
        """Get configuration for PerformanceMonitor initialization."""
        return {
            'max_metrics': self.metrics_config.max_metrics,
            'auto_start_system_monitoring': True
        }

    def get_alert_config(self) -> Dict[str, Any]:
        """Get alert manager configuration."""
        return self.alert_thresholds.to_dict()

    def get_dashboard_config(self) -> Dict[str, Any]:
        """Get dashboard generator configuration."""
        return self.dashboard_config.to_dict()

    def get_export_config(self) -> Dict[str, Any]:
        """Get export configuration."""
        return self.export_config.to_dict()

    def update(self, updates: Dict[str, Any]) -> None:
        """Update configuration at runtime."""
        for section, values in updates.items():
            if section == 'alert_thresholds' and hasattr(self, 'alert_thresholds'):
                for key, value in values.items():
                    if hasattr(self.alert_thresholds, key):
                        setattr(self.alert_thresholds, key, value)

            elif section == 'metrics_config' and hasattr(self, 'metrics_config'):
                for key, value in values.items():
                    if hasattr(self.metrics_config, key):
                        setattr(self.metrics_config, key, value)

            elif section == 'dashboard_config' and hasattr(self, 'dashboard_config'):
                for key, value in values.items():
                    if hasattr(self.dashboard_config, key):
                        setattr(self.dashboard_config, key, value)

            elif section == 'export_config' and hasattr(self, 'export_config'):
                for key, value in values.items():
                    if hasattr(self.export_config, key):
                        setattr(self.export_config, key, value)

            elif section == 'logging_config' and hasattr(self, 'logging_config'):
                for key, value in values.items():
                    if hasattr(self.logging_config, key):
                        setattr(self.logging_config, key, value)

        self.logger.info(f"Configuration updated: {updates}")

    def validate(self) -> Dict[str, list]:
        """Validate configuration and return any issues."""
        issues = {}

        # Validate alert thresholds
        alert_issues = []
        if not (0.0 <= self.alert_thresholds.error_rate <= 1.0):
            alert_issues.append("error_rate must be between 0.0 and 1.0")

        if self.alert_thresholds.avg_duration <= 0:
            alert_issues.append("avg_duration must be positive")

        if not (0.0 <= self.alert_thresholds.cpu_usage <= 100.0):
            alert_issues.append("cpu_usage must be between 0.0 and 100.0")

        if not (0.0 <= self.alert_thresholds.memory_usage <= 100.0):
            alert_issues.append("memory_usage must be between 0.0 and 100.0")

        if alert_issues:
            issues['alert_thresholds'] = alert_issues

        # Validate metrics config
        metrics_issues = []
        if self.metrics_config.max_metrics <= 0:
            metrics_issues.append("max_metrics must be positive")

        if self.metrics_config.system_monitoring_interval <= 0:
            metrics_issues.append("system_monitoring_interval must be positive")

        if self.metrics_config.auto_cleanup_hours <= 0:
            metrics_issues.append("auto_cleanup_hours must be positive")

        if metrics_issues:
            issues['metrics_config'] = metrics_issues

        # Validate dashboard config
        dashboard_issues = []
        if self.dashboard_config.refresh_seconds <= 0:
            dashboard_issues.append("refresh_seconds must be positive")

        if self.dashboard_config.time_window_hours <= 0:
            dashboard_issues.append("time_window_hours must be positive")

        if dashboard_issues:
            issues['dashboard_config'] = dashboard_issues

        # Validate export config
        export_issues = []
        if self.export_config.format not in ['json', 'csv']:
            export_issues.append("format must be 'json' or 'csv'")

        if not self.export_config.output_directory:
            export_issues.append("output_directory cannot be empty")

        if export_issues:
            issues['export_config'] = export_issues

        return issues

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire configuration to dictionary."""
        return {
            'alert_thresholds': self.alert_thresholds.to_dict(),
            'metrics_config': self.metrics_config.to_dict(),
            'dashboard_config': self.dashboard_config.to_dict(),
            'export_config': self.export_config.to_dict(),
            'logging_config': self.logging_config.to_dict()
        }

    def _setup_logging(self) -> None:
        """Setup logging based on configuration."""
        log_level = getattr(logging, self.logging_config.level.upper(), logging.INFO)

        # Configure root logger for monitoring
        logger = logging.getLogger("nps_report_v3.monitoring")
        logger.setLevel(log_level)

        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add appropriate handler
        if self.logging_config.log_file:
            handler = logging.FileHandler(self.logging_config.log_file)
        else:
            handler = logging.StreamHandler()

        # Set formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)


# Default configuration profiles
DEVELOPMENT_CONFIG = {
    'alert_thresholds': {
        'error_rate': 0.10,       # More lenient for development
        'avg_duration': 60.0,     # Allow longer durations
        'cpu_usage': 90.0,        # Higher CPU threshold
        'memory_usage': 90.0      # Higher memory threshold
    },
    'metrics_config': {
        'max_metrics': 5000,      # Smaller memory footprint
        'system_monitoring_interval': 10.0,  # Less frequent monitoring
        'auto_cleanup_hours': 12  # More frequent cleanup
    },
    'dashboard_config': {
        'refresh_seconds': 60,    # Less frequent refresh
        'enable_plotly': True,    # Enable interactive charts
        'time_window_hours': 2    # Shorter time window
    },
    'export_config': {
        'enabled': True,
        'format': 'json',
        'output_directory': 'outputs/monitoring/dev'
    },
    'logging_config': {
        'level': 'DEBUG',         # Verbose logging
        'enable_performance_logs': True,
        'enable_alert_logs': True,
        'enable_system_logs': True
    }
}

PRODUCTION_CONFIG = {
    'alert_thresholds': {
        'error_rate': 0.02,       # Strict error rate
        'avg_duration': 15.0,     # Fast response requirements
        'cpu_usage': 70.0,        # Conservative CPU threshold
        'memory_usage': 70.0      # Conservative memory threshold
    },
    'metrics_config': {
        'max_metrics': 50000,     # Larger memory for production
        'system_monitoring_interval': 5.0,   # Frequent monitoring
        'auto_cleanup_hours': 48  # Longer retention
    },
    'dashboard_config': {
        'refresh_seconds': 15,    # Frequent refresh
        'enable_plotly': True,
        'time_window_hours': 12   # Longer time window
    },
    'export_config': {
        'enabled': True,
        'format': 'json',
        'output_directory': '/var/log/nps_v3/monitoring',
        'concurrent_exports': 3
    },
    'logging_config': {
        'level': 'INFO',          # Standard logging
        'enable_performance_logs': True,
        'enable_alert_logs': True,
        'enable_system_logs': False,
        'log_file': '/var/log/nps_v3/monitoring.log'
    }
}


def get_config_profile(profile_name: str) -> Dict[str, Any]:
    """Get a predefined configuration profile."""
    profiles = {
        'development': DEVELOPMENT_CONFIG,
        'dev': DEVELOPMENT_CONFIG,
        'production': PRODUCTION_CONFIG,
        'prod': PRODUCTION_CONFIG
    }

    return profiles.get(profile_name.lower(), {})


def create_config(
    profile: Optional[str] = None,
    config_file: Optional[Union[str, Path]] = None,
    load_env: bool = True
) -> MonitoringConfig:
    """
    Create monitoring configuration with optional profile.

    Args:
        profile: Configuration profile name ('development' or 'production')
        config_file: Optional configuration file path
        load_env: Whether to load from environment variables

    Returns:
        Configured MonitoringConfig instance
    """
    # Create base configuration
    config = MonitoringConfig(config_file=config_file, load_env=load_env)

    # Apply profile if specified
    if profile:
        profile_config = get_config_profile(profile)
        if profile_config:
            config.update(profile_config)

    return config


# Example usage and testing
if __name__ == "__main__":
    print("🔧 Testing NPS V3 Monitoring Configuration")
    print("=" * 50)

    # Test default configuration
    print("\n1. Default Configuration:")
    config = MonitoringConfig(load_env=False)
    print(f"   Error rate threshold: {config.alert_thresholds.error_rate}")
    print(f"   Max metrics: {config.metrics_config.max_metrics}")
    print(f"   Dashboard refresh: {config.dashboard_config.refresh_seconds}s")

    # Test configuration validation
    print("\n2. Configuration Validation:")
    issues = config.validate()
    if issues:
        print(f"   Issues found: {issues}")
    else:
        print("   ✅ Configuration is valid")

    # Test profile loading
    print("\n3. Development Profile:")
    dev_config = create_config(profile='development', load_env=False)
    print(f"   Error rate threshold: {dev_config.alert_thresholds.error_rate}")
    print(f"   Log level: {dev_config.logging_config.level}")

    print("\n4. Production Profile:")
    prod_config = create_config(profile='production', load_env=False)
    print(f"   Error rate threshold: {prod_config.alert_thresholds.error_rate}")
    print(f"   Log level: {prod_config.logging_config.level}")

    # Test configuration file operations
    print("\n5. File Operations:")
    test_config_path = Path("test_monitoring_config.json")

    try:
        config.save_to_file(test_config_path)
        print(f"   ✅ Configuration saved to: {test_config_path}")

        # Load it back
        loaded_config = MonitoringConfig(config_file=test_config_path, load_env=False)
        print(f"   ✅ Configuration loaded from: {test_config_path}")

        # Cleanup
        test_config_path.unlink()
        print(f"   🧹 Cleanup: Removed {test_config_path}")

    except Exception as e:
        print(f"   ❌ File operations error: {e}")

    print("\n🎉 Configuration testing completed!")