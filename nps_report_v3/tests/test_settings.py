"""Unit tests for configuration management"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import os

from nps_report_v3.config.settings import (
    Settings, Environment, LLMProvider, LogLevel,
    ConfigLoader, get_settings, reload_settings
)


class TestSettings:
    """Test Settings class"""

    def test_default_settings(self):
        """Test default settings initialization"""
        settings = Settings()

        assert settings.environment == Environment.DEVELOPMENT
        assert settings.api_port == 8000
        assert settings.primary_llm_provider == LLMProvider.AZURE
        assert settings.llm_temperature == 0.1
        assert settings.llm_max_tokens == 4000
        assert settings.log_level == LogLevel.INFO

    def test_environment_validation(self):
        """Test environment string validation"""
        settings = Settings(environment="PRODUCTION")
        assert settings.environment == Environment.PRODUCTION

        settings = Settings(environment="development")
        assert settings.environment == Environment.DEVELOPMENT

    @patch.dict(os.environ, {
        'AZURE_OPENAI_API_KEY': 'test-azure-key',
        'AZURE_OPENAI_ENDPOINT': 'https://test.azure.com',
        'YILI_APP_KEY': 'test-yili-key',
        'OPENAI_API_KEY': 'test-openai-key'
    })
    def test_env_variable_loading(self):
        """Test loading from environment variables"""
        settings = Settings()

        assert settings.azure_openai_api_key == 'test-azure-key'
        assert settings.azure_openai_endpoint == 'https://test.azure.com'
        assert settings.yili_app_key == 'test-yili-key'
        assert settings.openai_api_key == 'test-openai-key'

    def test_llm_temperature_validation(self):
        """Test LLM temperature validation"""
        # Valid temperature
        settings = Settings(llm_temperature=0.5)
        assert settings.llm_temperature == 0.5

        # Invalid temperatures should raise validation error
        with pytest.raises(ValueError):
            Settings(llm_temperature=-0.1)

        with pytest.raises(ValueError):
            Settings(llm_temperature=2.1)

    def test_llm_max_tokens_validation(self):
        """Test LLM max tokens validation"""
        # Valid tokens
        settings = Settings(llm_max_tokens=2000)
        assert settings.llm_max_tokens == 2000

        # Invalid tokens should raise validation error
        with pytest.raises(ValueError):
            Settings(llm_max_tokens=0)

        with pytest.raises(ValueError):
            Settings(llm_max_tokens=32001)

    def test_get_llm_config_azure(self):
        """Test getting Azure LLM configuration"""
        settings = Settings(
            azure_openai_api_key="azure-key",
            azure_openai_endpoint="https://azure.com",
            azure_openai_model="gpt-4"
        )

        config = settings.get_llm_config(LLMProvider.AZURE)

        assert config["api_key"] == "azure-key"
        assert config["endpoint"] == "https://azure.com"
        assert config["model"] == "gpt-4"
        assert config["temperature"] == 0.1
        assert config["max_tokens"] == 4000

    def test_get_llm_config_yili(self):
        """Test getting Yili LLM configuration"""
        settings = Settings(
            yili_app_key="yili-key",
            yili_gateway_url="http://yili.com",
            yili_model="custom-model"
        )

        config = settings.get_llm_config(LLMProvider.YILI)

        assert config["api_key"] == "yili-key"
        assert config["gateway_url"] == "http://yili.com"
        assert config["model"] == "custom-model"

    def test_get_llm_config_openai(self):
        """Test getting OpenAI LLM configuration"""
        settings = Settings(
            openai_api_key="openai-key",
            openai_model="gpt-4-turbo"
        )

        config = settings.get_llm_config(LLMProvider.OPENAI)

        assert config["api_key"] == "openai-key"
        assert config["model"] == "gpt-4-turbo"

    def test_get_llm_config_invalid_provider(self):
        """Test getting config for invalid provider"""
        settings = Settings()

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            settings.get_llm_config("invalid_provider")

    def test_get_memory_limits(self):
        """Test getting memory limits"""
        settings = Settings(
            pass1_memory_limit_mb=256,
            pass2_memory_limit_mb=512,
            pass3_memory_limit_mb=384,
            max_memory_mb=1024
        )

        limits = settings.get_memory_limits()

        assert limits["pass1"] == 256
        assert limits["pass2"] == 512
        assert limits["pass3"] == 384
        assert limits["total"] == 1024

    def test_is_production(self):
        """Test production environment check"""
        settings = Settings(environment=Environment.PRODUCTION)
        assert settings.is_production() is True
        assert settings.is_development() is False

    def test_is_development(self):
        """Test development environment check"""
        settings = Settings(environment=Environment.DEVELOPMENT)
        assert settings.is_development() is True
        assert settings.is_production() is False

    def test_get_log_config(self):
        """Test getting log configuration"""
        settings = Settings(
            log_level=LogLevel.DEBUG,
            log_file="/tmp/test.log",
            log_max_size=1000000,
            log_backup_count=3
        )

        config = settings.get_log_config()

        assert config["level"] == "DEBUG"
        assert config["file"] == "/tmp/test.log"
        assert config["max_size"] == 1000000
        assert config["backup_count"] == 3

    def test_to_dict_with_secrets(self):
        """Test converting to dict with secrets"""
        settings = Settings(
            azure_openai_api_key="secret-key",
            database_url="postgresql://user:pass@host/db"
        )

        # Include secrets
        data = settings.to_dict(exclude_secrets=False)
        assert data["azure_openai_api_key"] == "secret-key"
        assert data["database_url"] == "postgresql://user:pass@host/db"

    def test_to_dict_without_secrets(self):
        """Test converting to dict without secrets"""
        settings = Settings(
            azure_openai_api_key="secret-key",
            database_url="postgresql://user:pass@host/db"
        )

        # Exclude secrets
        data = settings.to_dict(exclude_secrets=True)
        assert data["azure_openai_api_key"] == "***"
        assert data["database_url"] == "***"

    def test_checkpoint_dir_creation(self):
        """Test checkpoint directory creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = Path(tmpdir) / "test_checkpoints"
            settings = Settings(checkpoint_dir=str(checkpoint_dir))

            assert checkpoint_dir.exists()
            assert checkpoint_dir.is_dir()

    def test_log_file_dir_creation(self):
        """Test log file directory creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "logs" / "test.log"
            settings = Settings(log_file=str(log_file))

            assert log_file.parent.exists()
            assert log_file.parent.is_dir()


class TestConfigLoader:
    """Test ConfigLoader class"""

    def test_load_default_settings(self):
        """Test loading default settings"""
        loader = ConfigLoader()
        settings = loader.load()

        assert settings.environment == Environment.DEVELOPMENT
        assert isinstance(settings, Settings)

    def test_load_with_environment(self):
        """Test loading with specific environment"""
        loader = ConfigLoader()
        settings = loader.load(environment="production")

        assert settings.environment == Environment.PRODUCTION

    def test_load_with_config_file(self):
        """Test loading with environment config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create a development.json config file
            config_file = config_dir / "development.json"
            config_data = {
                "api_port": 9000,
                "llm_temperature": 0.5,
                "log_level": "DEBUG"
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            loader = ConfigLoader(config_dir=str(config_dir))
            settings = loader.load(environment="development")

            assert settings.api_port == 9000
            assert settings.llm_temperature == 0.5
            assert settings.log_level == LogLevel.DEBUG

    def test_settings_property(self):
        """Test settings property with lazy loading"""
        loader = ConfigLoader()

        # First access should load settings
        settings1 = loader.settings
        assert isinstance(settings1, Settings)

        # Second access should return same instance
        settings2 = loader.settings
        assert settings1 is settings2


class TestSingletonFunctions:
    """Test singleton functions"""

    def test_get_settings(self):
        """Test get_settings singleton"""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
        assert isinstance(settings1, Settings)

    def test_reload_settings(self):
        """Test reloading settings"""
        # Get initial settings
        settings1 = get_settings()

        # Reload with different environment
        settings2 = reload_settings(environment="production")

        assert settings2.environment == Environment.PRODUCTION

        # Subsequent get_settings should return reloaded instance
        settings3 = get_settings()
        assert settings3 is settings2
        assert settings3.environment == Environment.PRODUCTION

        # Cleanup - reload with development
        reload_settings(environment="development")


class TestFeatureFlags:
    """Test feature flags"""

    def test_feature_flags(self):
        """Test feature flag settings"""
        settings = Settings(
            enable_v3_api=True,
            enable_html_reports=False,
            enable_chinese_nlp=True,
            enable_confidence_constraints=False
        )

        assert settings.enable_v3_api is True
        assert settings.enable_html_reports is False
        assert settings.enable_chinese_nlp is True
        assert settings.enable_confidence_constraints is False


class TestSecuritySettings:
    """Test security-related settings"""

    def test_cors_origins(self):
        """Test CORS origins configuration"""
        settings = Settings(
            allowed_cors_origins=["http://localhost:3000", "https://example.com"]
        )

        assert len(settings.allowed_cors_origins) == 2
        assert "http://localhost:3000" in settings.allowed_cors_origins
        assert "https://example.com" in settings.allowed_cors_origins

    def test_api_key_header(self):
        """Test API key header configuration"""
        settings = Settings(api_key_header="Authorization")

        assert settings.api_key_header == "Authorization"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])