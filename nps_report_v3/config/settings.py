"""
Configuration management system for NPS V3 API.
Provides environment-specific configurations with validation.
"""

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
import os
from pathlib import Path
import json


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    """LLM provider options"""
    AZURE = "azure"
    YILI = "yili"
    OPENAI = "openai"


class LogLevel(str, Enum):
    """Log level options"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Main configuration settings with Pydantic validation"""

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Current environment"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of API workers")
    api_reload: bool = Field(default=False, description="Auto-reload for development")

    # LLM Configuration
    primary_llm_provider: LLMProvider = Field(
        default=LLMProvider.AZURE,
        description="Primary LLM provider"
    )
    enable_llm_failover: bool = Field(
        default=True,
        description="Enable automatic LLM failover"
    )

    # Azure OpenAI
    azure_openai_api_key: Optional[str] = Field(
        default=None,
        env="AZURE_OPENAI_API_KEY",
        description="Azure OpenAI API key"
    )
    azure_openai_endpoint: Optional[str] = Field(
        default=None,
        env="AZURE_OPENAI_ENDPOINT",
        description="Azure OpenAI endpoint"
    )
    azure_openai_model: str = Field(
        default="gpt-4-turbo",
        description="Azure OpenAI model name"
    )
    azure_openai_api_version: str = Field(
        default="2024-02-01",
        description="Azure OpenAI API version"
    )

    # Yili Gateway
    yili_app_key: Optional[str] = Field(
        default=None,
        env="YILI_APP_KEY",
        description="Yili gateway app key"
    )
    yili_gateway_url: str = Field(
        default="http://ai-gateway.yili.com/v1/",
        description="Yili gateway URL"
    )
    yili_model: str = Field(
        default="gpt-4-turbo",
        description="Yili gateway model name"
    )

    # OpenAI (Direct)
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4-turbo",
        description="OpenAI model name"
    )

    # LLM Common Settings
    llm_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM temperature"
    )
    llm_max_tokens: int = Field(
        default=4000,
        ge=1,
        le=32000,
        description="Maximum tokens for LLM response"
    )
    llm_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="LLM request timeout in seconds"
    )
    llm_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for LLM calls"
    )

    # Cache Configuration
    enable_cache: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(
        default=3600,
        description="Cache TTL in seconds"
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis URL for distributed caching"
    )

    # Database Configuration
    database_url: Optional[str] = Field(
        default=None,
        description="Database URL for persistence"
    )

    # Monitoring
    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    prometheus_port: int = Field(
        default=9090,
        description="Prometheus metrics port"
    )

    # Logging
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level"
    )
    log_file: Optional[str] = Field(
        default="logs/nps_v3.log",
        description="Log file path"
    )
    log_max_size: int = Field(
        default=10485760,  # 10MB
        description="Maximum log file size in bytes"
    )
    log_backup_count: int = Field(
        default=5,
        description="Number of log file backups"
    )

    # Memory Management
    max_memory_mb: int = Field(
        default=2048,
        description="Maximum memory usage in MB"
    )
    pass1_memory_limit_mb: int = Field(
        default=512,
        description="Pass 1 memory limit in MB"
    )
    pass2_memory_limit_mb: int = Field(
        default=1024,
        description="Pass 2 memory limit in MB"
    )
    pass3_memory_limit_mb: int = Field(
        default=768,
        description="Pass 3 memory limit in MB"
    )

    # Processing Limits
    large_dataset_threshold: int = Field(
        default=1000,
        description="Threshold for large dataset processing"
    )
    chunk_size: int = Field(
        default=200,
        description="Chunk size for batch processing"
    )
    max_concurrent_agents: int = Field(
        default=5,
        description="Maximum concurrent agent executions"
    )

    # Timeout Configuration
    agent_timeout: int = Field(
        default=60,
        description="Default agent timeout in seconds"
    )
    workflow_timeout: int = Field(
        default=300,
        description="Total workflow timeout in seconds"
    )
    checkpoint_timeout: int = Field(
        default=10,
        description="Checkpoint save timeout in seconds"
    )

    # Checkpoint Configuration
    checkpoint_dir: str = Field(
        default="./checkpoints",
        description="Directory for checkpoint storage"
    )
    enable_checkpoint_compression: bool = Field(
        default=True,
        description="Enable checkpoint compression"
    )

    # Feature Flags
    enable_v3_api: bool = Field(default=True, description="Enable V3 API endpoints")
    enable_html_reports: bool = Field(default=True, description="Enable HTML report generation")
    enable_chinese_nlp: bool = Field(default=True, description="Enable Chinese NLP processing")
    enable_confidence_constraints: bool = Field(
        default=True,
        description="Enable confidence-based constraints"
    )

    # Security
    api_key_header: str = Field(
        default="X-API-Key",
        description="API key header name"
    )
    allowed_cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Allow extra fields for compatibility

    @validator("environment", pre=True)
    def validate_environment(cls, v):
        """Validate and convert environment string"""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @validator("log_file")
    def validate_log_file(cls, v):
        """Ensure log directory exists"""
        if v:
            Path(v).parent.mkdir(parents=True, exist_ok=True)
        return v

    @validator("checkpoint_dir")
    def validate_checkpoint_dir(cls, v):
        """Ensure checkpoint directory exists"""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v

    def get_llm_config(self, provider: Optional[LLMProvider] = None) -> Dict[str, Any]:
        """Get LLM configuration for specified provider"""
        provider = provider or self.primary_llm_provider

        if provider == LLMProvider.AZURE:
            return {
                "api_key": self.azure_openai_api_key,
                "endpoint": self.azure_openai_endpoint,
                "model": self.azure_openai_model,
                "api_version": self.azure_openai_api_version,
                "temperature": self.llm_temperature,
                "max_tokens": self.llm_max_tokens,
                "timeout": self.llm_timeout,
                "max_retries": self.llm_max_retries
            }
        elif provider == LLMProvider.YILI:
            return {
                "api_key": self.yili_app_key,
                "gateway_url": self.yili_gateway_url,
                "model": self.yili_model,
                "temperature": self.llm_temperature,
                "max_tokens": self.llm_max_tokens,
                "timeout": self.llm_timeout,
                "max_retries": self.llm_max_retries
            }
        elif provider == LLMProvider.OPENAI:
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "temperature": self.llm_temperature,
                "max_tokens": self.llm_max_tokens,
                "timeout": self.llm_timeout,
                "max_retries": self.llm_max_retries
            }
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def get_memory_limits(self) -> Dict[str, int]:
        """Get memory limits for each pass"""
        return {
            "pass1": self.pass1_memory_limit_mb,
            "pass2": self.pass2_memory_limit_mb,
            "pass3": self.pass3_memory_limit_mb,
            "total": self.max_memory_mb
        }

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT

    def get_log_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "level": self.log_level.value,
            "file": self.log_file,
            "max_size": self.log_max_size,
            "backup_count": self.log_backup_count
        }

    def to_dict(self, exclude_secrets: bool = True) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        data = self.dict()

        if exclude_secrets:
            # Remove sensitive information
            secret_fields = [
                "azure_openai_api_key",
                "yili_app_key",
                "openai_api_key",
                "database_url",
                "redis_url"
            ]
            for field in secret_fields:
                if field in data:
                    data[field] = "***" if data[field] else None

        return data


class ConfigLoader:
    """Configuration loader with environment-specific overrides"""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self._settings = None

    def load(self, environment: Optional[str] = None) -> Settings:
        """Load configuration for specified environment"""
        # Load base settings from environment variables
        settings = Settings()

        # Override with environment-specific config file if exists
        if environment:
            settings.environment = Environment(environment.lower())

        config_file = self.config_dir / f"{settings.environment.value}.json"
        if config_file.exists():
            with open(config_file) as f:
                overrides = json.load(f)
                for key, value in overrides.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)

        self._settings = settings
        return settings

    @property
    def settings(self) -> Settings:
        """Get current settings (load if not already loaded)"""
        if self._settings is None:
            self._settings = self.load()
        return self._settings


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get singleton settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings(environment: Optional[str] = None) -> Settings:
    """Reload settings with optional environment override"""
    global _settings
    loader = ConfigLoader()
    _settings = loader.load(environment)
    return _settings