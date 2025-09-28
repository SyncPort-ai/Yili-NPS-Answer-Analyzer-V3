"""
Comprehensive Error Handling and Resilience Patterns for NPS V3 Analysis System

Implements robust error handling patterns including circuit breakers, retry mechanisms,
graceful degradation, and recovery strategies for a production-ready multi-agent system.
"""

import asyncio
import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Union, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from functools import wraps
import uuid
import json

# Type variables for generic error handling
T = TypeVar('T')
F = TypeVar('F', bound=Callable)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    AGENT_FAILURE = "agent_failure"
    LLM_API_FAILURE = "llm_api_failure"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    RESOURCE_ERROR = "resource_error"
    DATA_ERROR = "data_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryAction(Enum):
    """Available recovery actions."""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    FAIL_FAST = "fail_fast"
    DEGRADE_GRACEFULLY = "degrade_gracefully"
    ESCALATE = "escalate"


@dataclass
class ErrorContext:
    """Comprehensive error context information."""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    error_type: str = ""
    error_message: str = ""
    category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    component: str = ""
    operation: str = ""
    workflow_id: Optional[str] = None
    agent_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    recovery_action: Optional[RecoveryAction] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    upstream_errors: List[str] = field(default_factory=list)


class NPSSystemException(Exception):
    """Base exception for NPS analysis system."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        component: str = "",
        context_data: Optional[Dict[str, Any]] = None,
        recovery_action: Optional[RecoveryAction] = None
    ):
        super().__init__(message)
        self.error_context = ErrorContext(
            error_type=self.__class__.__name__,
            error_message=message,
            category=category,
            severity=severity,
            component=component,
            context_data=context_data or {},
            recovery_action=recovery_action
        )


class AgentExecutionError(NPSSystemException):
    """Error during agent execution."""
    def __init__(self, agent_id: str, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AGENT_FAILURE,
            component=f"agent_{agent_id}",
            **kwargs
        )
        self.error_context.agent_id = agent_id


class LLMAPIError(NPSSystemException):
    """Error with LLM API calls."""
    def __init__(self, message: str, api_endpoint: str = "", **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.LLM_API_FAILURE,
            component="llm_client",
            **kwargs
        )
        self.error_context.context_data["api_endpoint"] = api_endpoint


class WorkflowTimeoutError(NPSSystemException):
    """Workflow execution timeout."""
    def __init__(self, workflow_id: str, timeout_seconds: float, **kwargs):
        super().__init__(
            f"Workflow {workflow_id} timed out after {timeout_seconds} seconds",
            category=ErrorCategory.TIMEOUT_ERROR,
            component="workflow_orchestrator",
            **kwargs
        )
        self.error_context.workflow_id = workflow_id
        self.error_context.context_data["timeout_seconds"] = timeout_seconds


class DataValidationError(NPSSystemException):
    """Data validation failure."""
    def __init__(self, field: str, value: Any, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION_ERROR,
            component="data_validator",
            **kwargs
        )
        self.error_context.context_data.update({
            "field": field,
            "value": str(value)[:100]  # Limit value length
        })


class ResourceExhaustionError(NPSSystemException):
    """System resource exhaustion."""
    def __init__(self, resource_type: str, current_usage: str, **kwargs):
        super().__init__(
            f"Resource exhaustion: {resource_type} - {current_usage}",
            category=ErrorCategory.RESOURCE_ERROR,
            severity=ErrorSeverity.HIGH,
            component="resource_manager",
            **kwargs
        )
        self.error_context.context_data.update({
            "resource_type": resource_type,
            "current_usage": current_usage
        })


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception_types: tuple = (Exception,)
    success_threshold: int = 3  # for half-open to closed transition


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Calls fail fast, no execution
    - HALF_OPEN: Limited calls to test recovery
    """

    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker."""
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = threading.RLock()

    def __call__(self, func: F) -> F:
        """Decorator for applying circuit breaker to functions."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        with self.lock:
            if self._should_reject_call():
                raise NPSSystemException(
                    f"Circuit breaker OPEN for {func.__name__}",
                    category=ErrorCategory.NETWORK_ERROR,
                    severity=ErrorSeverity.HIGH,
                    component="circuit_breaker",
                    recovery_action=RecoveryAction.FALLBACK
                )

        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            self._record_success()
            return result

        except Exception as e:
            # Check if this is an expected exception type
            if isinstance(e, self.config.expected_exception_types):
                self._record_failure()
            raise

    def _should_reject_call(self) -> bool:
        """Determine if call should be rejected."""
        if self.state == CircuitBreakerState.CLOSED:
            return False

        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and
                time.time() - self.last_failure_time >= self.config.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return False
            return True

        if self.state == CircuitBreakerState.HALF_OPEN:
            return False

        return False

    def _record_failure(self) -> None:
        """Record a failure and update circuit breaker state."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.success_count = 0

            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def _record_success(self) -> None:
        """Record a success and update circuit breaker state."""
        with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    logger.info("Circuit breaker closed after successful recovery")
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on successful calls
                self.failure_count = max(0, self.failure_count - 1)

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }


class RetryStrategy(ABC):
    """Abstract base class for retry strategies."""

    @abstractmethod
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if retry should be attempted."""
        pass

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Get delay before next retry attempt."""
        pass


class ExponentialBackoffRetry(RetryStrategy):
    """Exponential backoff retry strategy."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Check if should retry based on attempt count and exception type."""
        if attempt >= self.max_retries:
            return False

        # Don't retry validation errors
        if isinstance(exception, DataValidationError):
            return False

        # Don't retry critical errors
        if isinstance(exception, NPSSystemException):
            if exception.error_context.severity == ErrorSeverity.CRITICAL:
                return False

        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with optional jitter."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay

        return delay


class LinearBackoffRetry(RetryStrategy):
    """Linear backoff retry strategy."""

    def __init__(self, max_retries: int = 3, delay: float = 1.0):
        self.max_retries = max_retries
        self.delay = delay

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        return attempt < self.max_retries and not isinstance(exception, DataValidationError)

    def get_delay(self, attempt: int) -> float:
        return self.delay * (attempt + 1)


def with_retry(strategy: RetryStrategy):
    """Decorator for adding retry logic to functions."""
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None

            while True:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    if not strategy.should_retry(attempt, e):
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                        raise

                    delay = strategy.get_delay(attempt)
                    logger.warning(f"Retry attempt {attempt + 1} for {func.__name__} after {delay}s delay: {e}")

                    await asyncio.sleep(delay)
                    attempt += 1

        return wrapper
    return decorator


class ErrorHandler:
    """Centralized error handling and recovery system."""

    def __init__(self):
        """Initialize error handler."""
        self.error_log: List[ErrorContext] = []
        self.error_handlers: Dict[ErrorCategory, List[Callable]] = {}
        self.fallback_strategies: Dict[str, Callable] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.lock = threading.RLock()

    def register_error_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorContext], RecoveryAction]
    ) -> None:
        """Register error handler for specific category."""
        if category not in self.error_handlers:
            self.error_handlers[category] = []
        self.error_handlers[category].append(handler)

    def register_fallback_strategy(self, component: str, fallback: Callable) -> None:
        """Register fallback strategy for component."""
        self.fallback_strategies[component] = fallback

    def register_circuit_breaker(self, component: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Register circuit breaker for component."""
        circuit_breaker = CircuitBreaker(config)
        self.circuit_breakers[component] = circuit_breaker
        return circuit_breaker

    async def handle_error(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> Any:
        """Handle error with appropriate recovery strategy."""
        # Create error context
        if isinstance(exception, NPSSystemException):
            error_context = exception.error_context
        else:
            error_context = ErrorContext(
                error_type=type(exception).__name__,
                error_message=str(exception),
                context_data=context or {}
            )

        # Add to error log
        with self.lock:
            self.error_log.append(error_context)

        # Log error
        logger.error(
            f"Error in {error_context.component}.{error_context.operation}: "
            f"{error_context.error_message} (ID: {error_context.error_id})"
        )

        # Determine recovery action
        recovery_action = await self._determine_recovery_action(error_context)
        error_context.recovery_action = recovery_action

        # Execute recovery action
        return await self._execute_recovery_action(error_context, exception)

    async def _determine_recovery_action(self, error_context: ErrorContext) -> RecoveryAction:
        """Determine appropriate recovery action for error."""
        # Check registered handlers
        if error_context.category in self.error_handlers:
            for handler in self.error_handlers[error_context.category]:
                try:
                    action = handler(error_context)
                    if action:
                        return action
                except Exception as e:
                    logger.warning(f"Error handler failed: {e}")

        # Default recovery strategies by category
        default_strategies = {
            ErrorCategory.AGENT_FAILURE: RecoveryAction.RETRY,
            ErrorCategory.LLM_API_FAILURE: RecoveryAction.RETRY,
            ErrorCategory.NETWORK_ERROR: RecoveryAction.RETRY,
            ErrorCategory.TIMEOUT_ERROR: RecoveryAction.RETRY,
            ErrorCategory.VALIDATION_ERROR: RecoveryAction.FAIL_FAST,
            ErrorCategory.RESOURCE_ERROR: RecoveryAction.DEGRADE_GRACEFULLY,
            ErrorCategory.DATA_ERROR: RecoveryAction.FALLBACK,
            ErrorCategory.CONFIGURATION_ERROR: RecoveryAction.FAIL_FAST,
            ErrorCategory.UNKNOWN_ERROR: RecoveryAction.ESCALATE
        }

        # Consider severity for strategy adjustment
        base_action = default_strategies.get(error_context.category, RecoveryAction.ESCALATE)

        if error_context.severity == ErrorSeverity.CRITICAL:
            return RecoveryAction.FAIL_FAST
        elif error_context.severity == ErrorSeverity.HIGH:
            if base_action == RecoveryAction.RETRY and error_context.retry_count >= 2:
                return RecoveryAction.ESCALATE

        return base_action

    async def _execute_recovery_action(
        self,
        error_context: ErrorContext,
        original_exception: Exception
    ) -> Any:
        """Execute the determined recovery action."""
        action = error_context.recovery_action

        if action == RecoveryAction.RETRY:
            if error_context.retry_count < error_context.max_retries:
                error_context.retry_count += 1
                logger.info(f"Retrying operation (attempt {error_context.retry_count})")
                # In real implementation, would re-execute the operation
                return None
            else:
                logger.error("Max retries exceeded, escalating")
                return await self._execute_recovery_action(
                    error_context._replace(recovery_action=RecoveryAction.ESCALATE),
                    original_exception
                )

        elif action == RecoveryAction.FALLBACK:
            if error_context.component in self.fallback_strategies:
                try:
                    fallback = self.fallback_strategies[error_context.component]
                    logger.info(f"Executing fallback strategy for {error_context.component}")
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(error_context)
                    else:
                        return fallback(error_context)
                except Exception as e:
                    logger.error(f"Fallback strategy failed: {e}")
                    raise original_exception
            else:
                logger.warning(f"No fallback strategy for {error_context.component}")
                raise original_exception

        elif action == RecoveryAction.SKIP:
            logger.info(f"Skipping operation due to error: {error_context.error_message}")
            return None

        elif action == RecoveryAction.DEGRADE_GRACEFULLY:
            logger.info("Gracefully degrading service")
            # Return minimal/default response
            return self._create_degraded_response(error_context)

        elif action == RecoveryAction.FAIL_FAST:
            logger.error("Failing fast due to unrecoverable error")
            raise original_exception

        elif action == RecoveryAction.ESCALATE:
            logger.error("Escalating error to higher level")
            # In real implementation, would notify operators/administrators
            raise NPSSystemException(
                f"Escalated error: {error_context.error_message}",
                category=error_context.category,
                severity=ErrorSeverity.CRITICAL,
                component=error_context.component,
                context_data=error_context.context_data
            )

        return None

    def _create_degraded_response(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Create degraded response for graceful degradation."""
        return {
            "status": "degraded",
            "error_id": error_context.error_id,
            "message": "服务降级响应",
            "component": error_context.component,
            "timestamp": error_context.timestamp.isoformat(),
            "partial_data": True
        }

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        with self.lock:
            if not self.error_log:
                return {"total_errors": 0}

            # Analyze errors
            category_counts = {}
            severity_counts = {}
            component_counts = {}
            recent_errors = 0
            one_hour_ago = datetime.now() - timedelta(hours=1)

            for error in self.error_log:
                # Category stats
                category = error.category.value
                category_counts[category] = category_counts.get(category, 0) + 1

                # Severity stats
                severity = error.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

                # Component stats
                component = error.component
                component_counts[component] = component_counts.get(component, 0) + 1

                # Recent errors
                if error.timestamp >= one_hour_ago:
                    recent_errors += 1

            return {
                "total_errors": len(self.error_log),
                "recent_errors_1h": recent_errors,
                "error_rate_1h": recent_errors / 60,  # per minute
                "category_distribution": category_counts,
                "severity_distribution": severity_counts,
                "component_distribution": component_counts,
                "circuit_breaker_states": {
                    name: cb.get_state() for name, cb in self.circuit_breakers.items()
                }
            }

    def clear_error_log(self) -> None:
        """Clear error log (for testing/maintenance)."""
        with self.lock:
            self.error_log.clear()

    def export_error_log(self, output_file: str) -> None:
        """Export error log for analysis."""
        with self.lock:
            data = {
                "export_time": datetime.now().isoformat(),
                "total_errors": len(self.error_log),
                "errors": [
                    {
                        "error_id": error.error_id,
                        "timestamp": error.timestamp.isoformat(),
                        "category": error.category.value,
                        "severity": error.severity.value,
                        "component": error.component,
                        "operation": error.operation,
                        "error_type": error.error_type,
                        "error_message": error.error_message,
                        "retry_count": error.retry_count,
                        "recovery_action": error.recovery_action.value if error.recovery_action else None,
                        "context_data": error.context_data
                    }
                    for error in self.error_log
                ]
            }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Error log exported to: {output_file}")


# Global error handler instance
global_error_handler = ErrorHandler()


# Convenience decorators
def resilient(
    max_retries: int = 3,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
):
    """Comprehensive resilience decorator combining multiple patterns."""
    def decorator(func: F) -> F:
        # Create retry strategy
        retry_strategy = ExponentialBackoffRetry(max_retries=max_retries)

        # Create circuit breaker if config provided
        circuit_breaker = None
        if circuit_breaker_config:
            component_name = f"{func.__module__}.{func.__name__}"
            circuit_breaker = global_error_handler.register_circuit_breaker(
                component_name, circuit_breaker_config
            )

        # Register fallback if provided
        if fallback:
            component_name = f"{func.__module__}.{func.__name__}"
            global_error_handler.register_fallback_strategy(component_name, fallback)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    # Apply circuit breaker if configured
                    if circuit_breaker:
                        return await circuit_breaker.call(func, *args, **kwargs)
                    else:
                        if asyncio.iscoroutinefunction(func):
                            return await func(*args, **kwargs)
                        else:
                            return func(*args, **kwargs)

                except Exception as e:
                    # Handle error through global handler
                    if not retry_strategy.should_retry(attempt, e):
                        try:
                            return await global_error_handler.handle_error(
                                e, {"function": func.__name__, "attempt": attempt}
                            )
                        except Exception:
                            # If error handling fails, re-raise original
                            raise e

                    # Retry with backoff
                    delay = retry_strategy.get_delay(attempt)
                    logger.warning(f"Retrying {func.__name__} after {delay}s (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(delay)
                    attempt += 1

        return wrapper
    return decorator


def fallback_strategy(component: str):
    """Decorator to register a function as a fallback strategy."""
    def decorator(func: F) -> F:
        global_error_handler.register_fallback_strategy(component, func)
        return func
    return decorator


def error_handler(category: ErrorCategory):
    """Decorator to register a function as an error handler."""
    def decorator(func: F) -> F:
        global_error_handler.register_error_handler(category, func)
        return func
    return decorator


# Example error handlers
@error_handler(ErrorCategory.LLM_API_FAILURE)
def handle_llm_api_failure(error_context: ErrorContext) -> RecoveryAction:
    """Handle LLM API failures with specific logic."""
    # Check error message for specific failure types
    error_msg = error_context.error_message.lower()

    if "rate limit" in error_msg or "quota" in error_msg:
        return RecoveryAction.RETRY  # Retry with backoff
    elif "authentication" in error_msg or "unauthorized" in error_msg:
        return RecoveryAction.FAIL_FAST  # Don't retry auth errors
    elif "timeout" in error_msg:
        return RecoveryAction.RETRY  # Retry timeouts
    else:
        return RecoveryAction.FALLBACK  # Use fallback for other API errors


@error_handler(ErrorCategory.AGENT_FAILURE)
def handle_agent_failure(error_context: ErrorContext) -> RecoveryAction:
    """Handle agent execution failures."""
    # Critical agents should not be skipped
    critical_agents = ["A0", "A1", "C5"]  # Data cleaner, NPS calculator, Executive synthesizer

    if error_context.agent_id in critical_agents:
        return RecoveryAction.RETRY if error_context.retry_count < 2 else RecoveryAction.FAIL_FAST
    else:
        # Non-critical agents can be skipped in degraded mode
        return RecoveryAction.SKIP if error_context.retry_count >= 1 else RecoveryAction.RETRY


# Example fallback strategies
@fallback_strategy("llm_client")
async def llm_fallback_response(error_context: ErrorContext) -> Dict[str, Any]:
    """Fallback response for LLM failures."""
    logger.info("Using LLM fallback response")
    return {
        "response": "无法获取AI分析结果，请稍后重试。",
        "confidence": 0.1,
        "fallback": True,
        "error_id": error_context.error_id
    }


@fallback_strategy("agent_B4")  # Text clustering agent
async def text_clustering_fallback(error_context: ErrorContext) -> Dict[str, Any]:
    """Fallback for text clustering agent."""
    logger.info("Using basic text clustering fallback")
    return {
        "clusters": [
            {"theme": "一般反馈", "keywords": ["反馈", "意见"], "count": 1}
        ],
        "fallback": True,
        "error_id": error_context.error_id
    }


# Health check utilities
class SystemHealthChecker:
    """System health monitoring and reporting."""

    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler

    async def check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check."""
        health_status = {
            "overall_status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {},
            "error_statistics": self.error_handler.get_error_statistics(),
            "circuit_breakers": {},
            "recommendations": []
        }

        # Check circuit breaker states
        for name, cb in self.error_handler.circuit_breakers.items():
            state_info = cb.get_state()
            health_status["circuit_breakers"][name] = state_info

            if state_info["state"] == "open":
                health_status["overall_status"] = "degraded"
                health_status["recommendations"].append(
                    f"Circuit breaker {name} is open - service degraded"
                )

        # Analyze error patterns
        error_stats = health_status["error_statistics"]
        recent_errors = error_stats.get("recent_errors_1h", 0)
        error_rate = error_stats.get("error_rate_1h", 0)

        if error_rate > 5:  # More than 5 errors per minute
            health_status["overall_status"] = "unhealthy"
            health_status["recommendations"].append(
                f"High error rate detected: {error_rate:.1f} errors/minute"
            )
        elif error_rate > 1:
            health_status["overall_status"] = "degraded"
            health_status["recommendations"].append(
                f"Elevated error rate: {error_rate:.1f} errors/minute"
            )

        # Check for critical errors
        severity_stats = error_stats.get("severity_distribution", {})
        critical_errors = severity_stats.get("critical", 0)

        if critical_errors > 0:
            health_status["overall_status"] = "critical"
            health_status["recommendations"].append(
                f"{critical_errors} critical errors detected - immediate attention required"
            )

        return health_status

    def get_health_summary(self) -> str:
        """Get concise health summary."""
        # This would be called synchronously for quick checks
        error_stats = self.error_handler.get_error_statistics()
        total_errors = error_stats.get("total_errors", 0)
        recent_errors = error_stats.get("recent_errors_1h", 0)

        if recent_errors == 0:
            return "✅ System healthy - no recent errors"
        elif recent_errors < 5:
            return f"⚠️ System stable - {recent_errors} recent errors"
        else:
            return f"❌ System degraded - {recent_errors} errors in last hour"


# Create global health checker
system_health = SystemHealthChecker(global_error_handler)