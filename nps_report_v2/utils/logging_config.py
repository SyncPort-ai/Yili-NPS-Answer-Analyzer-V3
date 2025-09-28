"""
详细日志配置系统
支持多级别、多输出、可配置的详细调试日志记录
"""

import logging
import logging.handlers
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

class DetailedLoggingConfig:
    """详细日志配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化日志配置
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认设置
        """
        self.config_file = config_file or "logging_config.json"
        self.config = self._load_config()
        self.loggers = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """加载日志配置"""
        default_config = {
            "enabled": True,
            "level": "INFO",
            "detailed_debug": False,
            "output": {
                "console": True,
                "file": True,
                "detailed_file": True
            },
            "files": {
                "main_log": "logs/app.log",
                "debug_log": "logs/debug.log",
                "error_log": "logs/error.log",
                "v2_workflow_log": "logs/v2_workflow.log",
                "agent_log": "logs/agents.log"
            },
            "rotation": {
                "max_bytes": 10485760,  # 10MB
                "backup_count": 5
            },
            "format": {
                "standard": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                "detailed": "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
                "debug": "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d [%(pathname)s] - %(message)s"
            },
            "modules": {
                "nps_report_v2": "DEBUG",
                "nps_report_v2.parallel_processor": "DEBUG",
                "nps_report_v2.agents": "DEBUG",
                "nps_report_v2.report_generator": "DEBUG",
                "nps_report_v2.utils": "DEBUG",
                "api": "INFO",
                "uvicorn": "WARNING",
                "fastapi": "INFO"
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并配置（loaded覆盖default）
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"Warning: Failed to load logging config from {self.config_file}: {e}")
        
        return default_config
    
    def save_config(self):
        """保存当前配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save logging config: {e}")
    
    def setup_logging(self):
        """设置日志系统"""
        if not self.config.get("enabled", True):
            logging.disable(logging.CRITICAL)
            return
        
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 清除现有的处理器
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 设置根日志级别
        root_level = getattr(logging, self.config.get("level", "INFO").upper())
        root_logger.setLevel(root_level)
        
        # 配置格式器
        standard_formatter = logging.Formatter(self.config["format"]["standard"])
        detailed_formatter = logging.Formatter(self.config["format"]["detailed"])
        debug_formatter = logging.Formatter(self.config["format"]["debug"])
        
        # 控制台输出
        if self.config["output"].get("console", True):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(root_level)
            if self.config.get("detailed_debug", False):
                console_handler.setFormatter(detailed_formatter)
            else:
                console_handler.setFormatter(standard_formatter)
            root_logger.addHandler(console_handler)
        
        # 主日志文件
        if self.config["output"].get("file", True):
            main_handler = logging.handlers.RotatingFileHandler(
                self.config["files"]["main_log"],
                maxBytes=self.config["rotation"]["max_bytes"],
                backupCount=self.config["rotation"]["backup_count"],
                encoding='utf-8'
            )
            main_handler.setLevel(root_level)
            main_handler.setFormatter(standard_formatter)
            root_logger.addHandler(main_handler)
        
        # 详细调试日志文件
        if self.config["output"].get("detailed_file", True) and self.config.get("detailed_debug", False):
            debug_handler = logging.handlers.RotatingFileHandler(
                self.config["files"]["debug_log"],
                maxBytes=self.config["rotation"]["max_bytes"],
                backupCount=self.config["rotation"]["backup_count"],
                encoding='utf-8'
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(debug_formatter)
            root_logger.addHandler(debug_handler)
        
        # 错误日志文件
        error_handler = logging.handlers.RotatingFileHandler(
            self.config["files"]["error_log"],
            maxBytes=self.config["rotation"]["max_bytes"],
            backupCount=self.config["rotation"]["backup_count"],
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # V2工作流专用日志
        if self.config.get("detailed_debug", False):
            v2_handler = logging.handlers.RotatingFileHandler(
                self.config["files"]["v2_workflow_log"],
                maxBytes=self.config["rotation"]["max_bytes"],
                backupCount=self.config["rotation"]["backup_count"],
                encoding='utf-8'
            )
            v2_handler.setLevel(logging.DEBUG)
            v2_handler.setFormatter(debug_formatter)
            
            # 只记录V2相关的日志
            v2_filter = logging.Filter('nps_report_v2')
            v2_handler.addFilter(v2_filter)
            root_logger.addHandler(v2_handler)
            
            # Agent专用日志
            agent_handler = logging.handlers.RotatingFileHandler(
                self.config["files"]["agent_log"],
                maxBytes=self.config["rotation"]["max_bytes"],
                backupCount=self.config["rotation"]["backup_count"],
                encoding='utf-8'
            )
            agent_handler.setLevel(logging.DEBUG)
            agent_handler.setFormatter(debug_formatter)
            
            agent_filter = logging.Filter('nps_report_v2.agents')
            agent_handler.addFilter(agent_filter)
            root_logger.addHandler(agent_handler)
        
        # 配置各模块的日志级别
        for module, level in self.config.get("modules", {}).items():
            logger = logging.getLogger(module)
            logger.setLevel(getattr(logging, level.upper()))
            self.loggers[module] = logger
        
        # 记录日志系统启动信息
        main_logger = logging.getLogger("logging_config")
        main_logger.info("=" * 60)
        main_logger.info("详细日志系统已启动")
        main_logger.info(f"配置文件: {self.config_file}")
        main_logger.info(f"日志级别: {self.config.get('level', 'INFO')}")
        main_logger.info(f"详细调试: {'开启' if self.config.get('detailed_debug', False) else '关闭'}")
        main_logger.info(f"输出方式: {', '.join([k for k, v in self.config['output'].items() if v])}")
        main_logger.info("=" * 60)
    
    def enable_detailed_debug(self):
        """启用详细调试模式"""
        self.config["detailed_debug"] = True
        self.config["level"] = "DEBUG"
        self.save_config()
        self.setup_logging()
        
        logger = logging.getLogger("logging_config")
        logger.info("详细调试模式已启用")
    
    def disable_detailed_debug(self):
        """禁用详细调试模式"""
        self.config["detailed_debug"] = False
        self.config["level"] = "INFO"
        self.save_config()
        self.setup_logging()
        
        logger = logging.getLogger("logging_config")
        logger.info("详细调试模式已禁用")
    
    def set_module_level(self, module: str, level: str):
        """设置特定模块的日志级别"""
        self.config["modules"][module] = level.upper()
        if module in self.loggers:
            self.loggers[module].setLevel(getattr(logging, level.upper()))
        self.save_config()
        
        logger = logging.getLogger("logging_config")
        logger.info(f"模块 {module} 日志级别设置为 {level}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取配置好的logger"""
        return logging.getLogger(name)


# 全局日志配置实例
_logging_config = None

def get_logging_config() -> DetailedLoggingConfig:
    """获取全局日志配置实例"""
    global _logging_config
    if _logging_config is None:
        _logging_config = DetailedLoggingConfig()
    return _logging_config

def setup_detailed_logging(config_file: Optional[str] = None):
    """设置详细日志系统"""
    global _logging_config
    _logging_config = DetailedLoggingConfig(config_file)
    _logging_config.setup_logging()
    return _logging_config

def get_logger(name: str) -> logging.Logger:
    """便捷的获取logger函数"""
    config = get_logging_config()
    return config.get_logger(name)

def enable_debug():
    """启用调试模式"""
    config = get_logging_config()
    config.enable_detailed_debug()

def disable_debug():
    """禁用调试模式"""
    config = get_logging_config()
    config.disable_detailed_debug()

# 调试装饰器
def log_function_call(logger_name: str = None):
    """
    记录函数调用的装饰器
    
    Args:
        logger_name: 使用的logger名称，默认使用模块名
    """
    def decorator(func):
        import functools
        import inspect
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 确定logger名称
            if logger_name:
                logger = get_logger(logger_name)
            else:
                module = inspect.getmodule(func)
                logger = get_logger(module.__name__ if module else 'unknown')
            
            # 记录函数调用
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            
            logger.debug(f"调用函数 {func.__name__}({signature})")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"函数 {func.__name__} 执行成功，返回: {type(result).__name__}")
                return result
            except Exception as e:
                logger.error(f"函数 {func.__name__} 执行失败: {e}")
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 确定logger名称
            if logger_name:
                logger = get_logger(logger_name)
            else:
                module = inspect.getmodule(func)
                logger = get_logger(module.__name__ if module else 'unknown')
            
            # 记录函数调用
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            
            logger.debug(f"调用异步函数 {func.__name__}({signature})")
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"异步函数 {func.__name__} 执行成功，返回: {type(result).__name__}")
                return result
            except Exception as e:
                logger.error(f"异步函数 {func.__name__} 执行失败: {e}")
                raise
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator

# 使用示例和测试
if __name__ == "__main__":
    # 设置详细日志
    config = setup_detailed_logging()
    
    # 测试各种日志级别
    logger = get_logger("test")
    logger.debug("这是调试信息")
    logger.info("这是一般信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    
    # 启用详细调试
    enable_debug()
    logger.debug("详细调试模式下的调试信息")
    
    # 测试装饰器
    @log_function_call()
    def test_function(x, y):
        return x + y
    
    result = test_function(1, 2)
    print(f"测试结果: {result}")