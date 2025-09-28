"""
错误处理与容错机制
提供分层错误处理、优雅降级、状态保存和重试机制
"""

import logging
import traceback
import json
import os
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import asyncio
import pickle
import functools

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """错误严重级别"""
    CRITICAL = "critical"     # 系统无法继续运行
    HIGH = "high"            # 主要功能失效
    MEDIUM = "medium"        # 部分功能影响
    LOW = "low"             # 轻微影响
    WARNING = "warning"      # 警告信息

class ErrorCategory(Enum):
    """错误分类"""
    DATA_ERROR = "data_error"                 # 数据相关错误
    PROCESSING_ERROR = "processing_error"     # 处理逻辑错误
    AGENT_ERROR = "agent_error"              # 智能体错误
    NETWORK_ERROR = "network_error"          # 网络连接错误
    VALIDATION_ERROR = "validation_error"    # 数据验证错误
    CONFIGURATION_ERROR = "config_error"     # 配置错误
    RESOURCE_ERROR = "resource_error"        # 资源不足错误
    EXTERNAL_SERVICE_ERROR = "external_error" # 外部服务错误

@dataclass
class ErrorContext:
    """错误上下文信息"""
    error_id: str
    timestamp: str
    severity: ErrorSeverity
    category: ErrorCategory
    component: str
    function_name: str
    error_message: str
    stack_trace: str
    input_data: Optional[Dict[str, Any]]
    system_state: Optional[Dict[str, Any]]
    recovery_suggestions: List[str]
    metadata: Dict[str, Any]

class ApplicationError(Exception):
    """应用程序基础异常类"""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.PROCESSING_ERROR, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Dict[str, Any] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()

class DataValidationError(ApplicationError):
    """数据验证错误"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message, ErrorCategory.VALIDATION_ERROR, ErrorSeverity.HIGH)
        self.field = field
        self.value = value

class AgentProcessingError(ApplicationError):
    """智能体处理错误"""
    
    def __init__(self, message: str, agent_name: str, stage: str = None):
        super().__init__(message, ErrorCategory.AGENT_ERROR, ErrorSeverity.MEDIUM)
        self.agent_name = agent_name
        self.stage = stage

class NetworkTimeoutError(ApplicationError):
    """网络超时错误"""
    
    def __init__(self, message: str, service: str, timeout_duration: float):
        super().__init__(message, ErrorCategory.NETWORK_ERROR, ErrorSeverity.MEDIUM)
        self.service = service
        self.timeout_duration = timeout_duration

class ResourceInsufficientError(ApplicationError):
    """资源不足错误"""
    
    def __init__(self, message: str, resource_type: str, required: Any, available: Any):
        super().__init__(message, ErrorCategory.RESOURCE_ERROR, ErrorSeverity.HIGH)
        self.resource_type = resource_type
        self.required = required
        self.available = available

class ErrorHandler:
    """全局错误处理器"""
    
    def __init__(self, checkpoint_dir: str = "checkpoints", max_retry_attempts: int = 3):
        """
        初始化错误处理器
        
        Args:
            checkpoint_dir: 检查点保存目录
            max_retry_attempts: 最大重试次数
        """
        self.checkpoint_dir = checkpoint_dir
        self.max_retry_attempts = max_retry_attempts
        self.error_history: List[ErrorContext] = []
        
        # 确保检查点目录存在
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # 错误恢复策略映射
        self.recovery_strategies = {
            ErrorCategory.DATA_ERROR: self._recover_from_data_error,
            ErrorCategory.PROCESSING_ERROR: self._recover_from_processing_error,
            ErrorCategory.AGENT_ERROR: self._recover_from_agent_error,
            ErrorCategory.NETWORK_ERROR: self._recover_from_network_error,
            ErrorCategory.VALIDATION_ERROR: self._recover_from_validation_error,
            ErrorCategory.RESOURCE_ERROR: self._recover_from_resource_error
        }
        
        # 降级策略
        self.fallback_strategies = {
            "nps_analysis": self._fallback_nps_analysis,
            "question_group_analysis": self._fallback_question_analysis,
            "business_insights": self._fallback_business_insights,
            "report_generation": self._fallback_report_generation
        }
        
        logger.info(f"错误处理器初始化完成，检查点目录: {checkpoint_dir}")
    
    def handle_error(self, error: Exception, component: str, function_name: str, 
                    input_data: Optional[Dict[str, Any]] = None,
                    system_state: Optional[Dict[str, Any]] = None) -> ErrorContext:
        """
        处理错误
        
        Args:
            error: 异常对象
            component: 出错组件名称
            function_name: 出错函数名称
            input_data: 输入数据
            system_state: 系统状态
            
        Returns:
            ErrorContext: 错误上下文
        """
        # 生成错误ID
        error_id = f"{component}_{function_name}_{int(datetime.now().timestamp())}"
        
        # 确定错误类型和严重性
        if isinstance(error, ApplicationError):
            category = error.category
            severity = error.severity
            error_message = str(error)
        else:
            category = self._classify_error(error)
            severity = self._assess_severity(error, component)
            error_message = str(error)
        
        # 创建错误上下文
        error_context = ErrorContext(
            error_id=error_id,
            timestamp=datetime.now().isoformat(),
            severity=severity,
            category=category,
            component=component,
            function_name=function_name,
            error_message=error_message,
            stack_trace=traceback.format_exc(),
            input_data=input_data,
            system_state=system_state,
            recovery_suggestions=self._generate_recovery_suggestions(category, error),
            metadata={
                "error_type": type(error).__name__,
                "component_version": "v2.0",
                "python_version": "3.11+"
            }
        )
        
        # 记录错误
        self._log_error(error_context)
        
        # 添加到错误历史
        self.error_history.append(error_context)
        
        # 保存错误上下文
        self._save_error_context(error_context)
        
        return error_context
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """分类错误"""
        
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # 根据错误类型分类
        if error_type in ['ValueError', 'TypeError', 'KeyError']:
            return ErrorCategory.DATA_ERROR
        elif error_type in ['TimeoutError', 'ConnectionError', 'RequestException']:
            return ErrorCategory.NETWORK_ERROR
        elif 'validation' in error_message or 'invalid' in error_message:
            return ErrorCategory.VALIDATION_ERROR
        elif 'memory' in error_message or 'resource' in error_message:
            return ErrorCategory.RESOURCE_ERROR
        elif error_type in ['ImportError', 'ModuleNotFoundError']:
            return ErrorCategory.CONFIGURATION_ERROR
        else:
            return ErrorCategory.PROCESSING_ERROR
    
    def _assess_severity(self, error: Exception, component: str) -> ErrorSeverity:
        """评估错误严重性"""
        
        # 关键组件的错误更严重
        critical_components = ['parallel_processor', 'nps_calculator']
        if component in critical_components:
            return ErrorSeverity.HIGH
        
        # 根据错误类型评估
        error_type = type(error).__name__
        if error_type in ['SystemExit', 'MemoryError', 'OSError']:
            return ErrorSeverity.CRITICAL
        elif error_type in ['ValueError', 'TypeError', 'AssertionError']:
            return ErrorSeverity.HIGH
        elif error_type in ['Warning', 'UserWarning']:
            return ErrorSeverity.WARNING
        else:
            return ErrorSeverity.MEDIUM
    
    def _generate_recovery_suggestions(self, category: ErrorCategory, error: Exception) -> List[str]:
        """生成恢复建议"""
        
        suggestions = []
        
        if category == ErrorCategory.DATA_ERROR:
            suggestions.extend([
                "检查输入数据格式和完整性",
                "验证数据类型是否正确",
                "考虑使用默认值或备用数据"
            ])
        
        elif category == ErrorCategory.NETWORK_ERROR:
            suggestions.extend([
                "检查网络连接状态",
                "增加重试机制",
                "使用备用服务端点"
            ])
        
        elif category == ErrorCategory.AGENT_ERROR:
            suggestions.extend([
                "检查智能体配置",
                "使用备用分析方法",
                "降级到基础分析功能"
            ])
        
        elif category == ErrorCategory.VALIDATION_ERROR:
            suggestions.extend([
                "检查数据验证规则",
                "放宽验证标准",
                "使用数据清理工具"
            ])
        
        elif category == ErrorCategory.RESOURCE_ERROR:
            suggestions.extend([
                "释放不必要的资源",
                "减少处理批次大小",
                "优化内存使用"
            ])
        
        else:
            suggestions.extend([
                "检查日志获取详细信息",
                "尝试重新启动处理",
                "联系技术支持"
            ])
        
        return suggestions
    
    def _log_error(self, error_context: ErrorContext):
        """记录错误"""
        
        log_level = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING
        }
        
        logger.log(
            log_level[error_context.severity],
            f"[{error_context.error_id}] {error_context.component}.{error_context.function_name}: "
            f"{error_context.error_message}"
        )
        
        if error_context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            logger.error(f"Stack trace:\n{error_context.stack_trace}")
    
    def _save_error_context(self, error_context: ErrorContext):
        """保存错误上下文"""
        
        try:
            error_file = os.path.join(self.checkpoint_dir, f"error_{error_context.error_id}.json")
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(error_context), f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存错误上下文失败: {e}")
    
    async def recover_with_strategy(self, error_context: ErrorContext, 
                                  recovery_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用策略恢复"""
        
        recovery_strategy = self.recovery_strategies.get(error_context.category)
        if recovery_strategy:
            try:
                return await recovery_strategy(error_context, recovery_data)
            except Exception as e:
                logger.error(f"恢复策略执行失败: {e}")
                return {"status": "recovery_failed", "error": str(e)}
        else:
            return {"status": "no_recovery_strategy", "category": error_context.category.value}
    
    async def _recover_from_data_error(self, error_context: ErrorContext, 
                                     recovery_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """从数据错误恢复"""
        
        # 尝试使用备用数据
        if recovery_data and "backup_data" in recovery_data:
            return {
                "status": "recovered_with_backup",
                "data": recovery_data["backup_data"],
                "recovery_method": "backup_data"
            }
        
        # 尝试使用默认值
        if error_context.component == "input_data_processor":
            return {
                "status": "recovered_with_defaults",
                "data": {"default": True, "minimal_data": True},
                "recovery_method": "default_values"
            }
        
        return {"status": "recovery_partial", "recovery_method": "data_error_mitigation"}
    
    async def _recover_from_processing_error(self, error_context: ErrorContext,
                                           recovery_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """从处理错误恢复"""
        
        # 尝试简化处理
        if "simplified_processing" in error_context.recovery_suggestions:
            return {
                "status": "recovered_simplified",
                "processing_mode": "basic",
                "recovery_method": "simplified_processing"
            }
        
        return {"status": "recovery_attempted", "recovery_method": "processing_error_mitigation"}
    
    async def _recover_from_agent_error(self, error_context: ErrorContext,
                                      recovery_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """从智能体错误恢复"""
        
        # 尝试使用备用分析方法
        fallback_method = self.fallback_strategies.get(error_context.component)
        if fallback_method:
            try:
                result = await fallback_method(recovery_data)
                return {
                    "status": "recovered_with_fallback",
                    "result": result,
                    "recovery_method": "agent_fallback"
                }
            except Exception as e:
                logger.error(f"备用方法执行失败: {e}")
        
        return {"status": "recovery_partial", "recovery_method": "agent_error_mitigation"}
    
    async def _recover_from_network_error(self, error_context: ErrorContext,
                                        recovery_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """从网络错误恢复"""
        
        # 实现网络重试机制
        return {
            "status": "retry_recommended",
            "retry_delay": 5,
            "max_retries": 3,
            "recovery_method": "network_retry"
        }
    
    async def _recover_from_validation_error(self, error_context: ErrorContext,
                                           recovery_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """从验证错误恢复"""
        
        # 尝试放宽验证标准
        return {
            "status": "recovered_relaxed_validation",
            "validation_mode": "lenient",
            "recovery_method": "relaxed_validation"
        }
    
    async def _recover_from_resource_error(self, error_context: ErrorContext,
                                         recovery_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """从资源错误恢复"""
        
        # 尝试优化资源使用
        return {
            "status": "recovered_optimized",
            "processing_mode": "low_memory",
            "batch_size": "reduced",
            "recovery_method": "resource_optimization"
        }
    
    async def _fallback_nps_analysis(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """NPS分析备用方法"""
        
        # 基础NPS计算
        if data and "nps_scores" in data:
            scores = data["nps_scores"]
            promoters = sum(1 for score in scores if score >= 9)
            detractors = sum(1 for score in scores if score <= 6)
            nps = ((promoters - detractors) / len(scores)) * 100 if scores else 0
            
            return {
                "nps_score": nps,
                "method": "basic_calculation",
                "confidence": 0.8,
                "fallback": True
            }
        
        return {"nps_score": 0, "method": "default", "fallback": True}
    
    async def _fallback_question_analysis(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """问题分析备用方法"""
        
        return {
            "analysis": "基础文本统计分析",
            "method": "statistical_fallback",
            "confidence": 0.6,
            "fallback": True
        }
    
    async def _fallback_business_insights(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """商业洞察备用方法"""
        
        return {
            "insights": ["基于基础数据的简化洞察"],
            "method": "template_based",
            "confidence": 0.5,
            "fallback": True
        }
    
    async def _fallback_report_generation(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """报告生成备用方法"""
        
        return {
            "report": "简化版报告",
            "format": "basic_text",
            "method": "template_fallback",
            "fallback": True
        }

class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        初始化检查点管理器
        
        Args:
            checkpoint_dir: 检查点保存目录
        """
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
    
    def save_checkpoint(self, checkpoint_id: str, data: Dict[str, Any], 
                       metadata: Optional[Dict[str, Any]] = None):
        """
        保存检查点
        
        Args:
            checkpoint_id: 检查点ID
            data: 要保存的数据
            metadata: 元数据
        """
        try:
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "metadata": metadata or {}
            }
            
            checkpoint_file = os.path.join(self.checkpoint_dir, f"checkpoint_{checkpoint_id}.pkl")
            with open(checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            
            logger.info(f"检查点已保存: {checkpoint_id}")
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        加载检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            检查点数据，如果不存在则返回None
        """
        try:
            checkpoint_file = os.path.join(self.checkpoint_dir, f"checkpoint_{checkpoint_id}.pkl")
            if os.path.exists(checkpoint_file):
                with open(checkpoint_file, 'rb') as f:
                    checkpoint_data = pickle.load(f)
                logger.info(f"检查点已加载: {checkpoint_id}")
                return checkpoint_data
            else:
                logger.warning(f"检查点不存在: {checkpoint_id}")
                return None
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None
    
    def list_checkpoints(self) -> List[str]:
        """列出所有检查点"""
        try:
            checkpoints = []
            for filename in os.listdir(self.checkpoint_dir):
                if filename.startswith("checkpoint_") and filename.endswith(".pkl"):
                    checkpoint_id = filename[11:-4]  # 去掉 "checkpoint_" 和 ".pkl"
                    checkpoints.append(checkpoint_id)
            return sorted(checkpoints)
        except Exception as e:
            logger.error(f"列出检查点失败: {e}")
            return []
    
    def cleanup_old_checkpoints(self, max_age_days: int = 7):
        """清理过期检查点"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (max_age_days * 24 * 60 * 60)
            
            for filename in os.listdir(self.checkpoint_dir):
                if filename.startswith("checkpoint_") and filename.endswith(".pkl"):
                    file_path = os.path.join(self.checkpoint_dir, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"删除过期检查点: {filename}")
        except Exception as e:
            logger.error(f"清理检查点失败: {e}")

class RetryManager:
    """重试管理器"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_factor: float = 2.0):
        """
        初始化重试管理器
        
        Args:
            max_attempts: 最大重试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff_factor: 退避因子
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    async def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        带退避机制的重试
        
        Args:
            func: 要重试的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次尝试的异常
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
                    logger.warning(f"第{attempt + 1}次尝试失败，{delay:.1f}秒后重试: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"所有{self.max_attempts}次尝试都失败了")
        
        raise last_exception

def error_handler_decorator(component: str, fallback_result: Any = None, 
                          save_checkpoint: bool = False):
    """
    错误处理装饰器
    
    Args:
        component: 组件名称
        fallback_result: 备用结果
        save_checkpoint: 是否保存检查点
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            checkpoint_manager = CheckpointManager() if save_checkpoint else None
            
            try:
                # 保存检查点
                if checkpoint_manager:
                    checkpoint_id = f"{component}_{func.__name__}_{int(datetime.now().timestamp())}"
                    checkpoint_manager.save_checkpoint(checkpoint_id, {
                        "args": args,
                        "kwargs": kwargs,
                        "function": func.__name__
                    })
                
                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                return result
                
            except Exception as e:
                # 处理错误
                error_context = error_handler.handle_error(
                    error=e,
                    component=component,
                    function_name=func.__name__,
                    input_data={"args": str(args)[:500], "kwargs": str(kwargs)[:500]}
                )
                
                # 尝试恢复
                if error_context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
                    logger.error(f"严重错误，使用备用结果: {error_context.error_id}")
                    return fallback_result
                else:
                    # 重新抛出异常让上层处理
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 对于同步函数，创建简单的错误处理
            error_handler = ErrorHandler()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = error_handler.handle_error(
                    error=e,
                    component=component,
                    function_name=func.__name__,
                    input_data={"args": str(args)[:500], "kwargs": str(kwargs)[:500]}
                )
                
                if error_context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
                    return fallback_result
                else:
                    raise
        
        # 根据函数类型返回相应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, 
                    exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    失败重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 重试延迟
        exceptions: 需要重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            retry_manager = RetryManager(max_attempts=max_attempts, base_delay=delay)
            
            async def target_func():
                return await func(*args, **kwargs)
            
            try:
                return await retry_manager.retry_with_backoff(target_func)
            except exceptions as e:
                logger.error(f"重试失败: {e}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_attempts - 1:
                        logger.warning(f"第{attempt + 1}次尝试失败，重试中: {e}")
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(f"所有{max_attempts}次尝试都失败了")
                        raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# 使用示例
async def main():
    """主函数示例"""
    error_handler = ErrorHandler()
    checkpoint_manager = CheckpointManager()
    retry_manager = RetryManager()
    
    print("错误处理系统初始化完成")

if __name__ == "__main__":
    asyncio.run(main())