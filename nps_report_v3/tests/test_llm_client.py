"""Unit tests for LLM client abstraction layer"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

from nps_report_v3.llm.client import (
    LLMConfig, LLMResponse, LLMClient,
    AzureOpenAIClient, YiliGatewayClient,
    LLMClientWithFailover, create_llm_client
)


class MockLLMClient(LLMClient):
    """Mock LLM client for testing"""

    def __init__(self, config: LLMConfig, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        self.call_count += 1

        if self.should_fail:
            raise Exception("Mock generation failure")

        return LLMResponse(
            content=f"Mock response to: {prompt}",
            model=self.config.model_name,
            usage={
                'prompt_tokens': 10,
                'completion_tokens': 20,
                'total_tokens': 30
            },
            latency_ms=100
        )

    async def embed(self, text: str):
        if self.should_fail:
            raise Exception("Mock embedding failure")
        return [0.1] * 1536  # Mock embedding vector


class TestLLMConfig:
    """Test LLMConfig dataclass"""

    def test_config_creation(self):
        config = LLMConfig(
            model_name="gpt-4",
            api_key="test-key",
            api_base="https://api.example.com"
        )

        assert config.model_name == "gpt-4"
        assert config.api_key == "test-key"
        assert config.api_base == "https://api.example.com"
        assert config.temperature == 0.1  # Default
        assert config.max_tokens == 4000  # Default
        assert config.timeout == 30  # Default
        assert config.max_retries == 3  # Default


class TestLLMResponse:
    """Test LLMResponse dataclass"""

    def test_response_creation(self):
        response = LLMResponse(
            content="Test response",
            model="gpt-4",
            usage={'total_tokens': 50},
            latency_ms=150
        )

        assert response.content == "Test response"
        assert response.model == "gpt-4"
        assert response.usage['total_tokens'] == 50
        assert response.latency_ms == 150
        assert response.cached is False  # Default
        assert response.metadata is None  # Default


class TestLLMClient:
    """Test base LLMClient functionality"""

    def test_cache_key_generation(self):
        config = LLMConfig("test", "key", "base")
        client = MockLLMClient(config)

        key1 = client._get_cache_key("Hello world")
        key2 = client._get_cache_key("Hello world")
        key3 = client._get_cache_key("Different prompt")

        assert key1 == key2  # Same prompt should generate same key
        assert key1 != key3  # Different prompts should have different keys

    def test_cache_save_and_retrieve(self):
        config = LLMConfig("test", "key", "base")
        client = MockLLMClient(config)

        prompt = "Test prompt"
        response = LLMResponse(
            content="Test response",
            model="test",
            usage={},
            latency_ms=100
        )

        # Save to cache
        client._save_to_cache(prompt, response, ttl_seconds=3600)

        # Retrieve from cache
        cached = client._get_from_cache(prompt)

        assert cached is not None
        assert cached.content == "Test response"
        assert cached.cached is True

    def test_cache_expiration(self):
        config = LLMConfig("test", "key", "base")
        client = MockLLMClient(config)

        prompt = "Test prompt"
        response = LLMResponse(
            content="Test response",
            model="test",
            usage={},
            latency_ms=100
        )

        # Save with immediate expiration
        client._save_to_cache(prompt, response, ttl_seconds=0)

        # Should not retrieve expired item
        cached = client._get_from_cache(prompt)
        assert cached is None

    @pytest.mark.asyncio
    async def test_generate_with_retry_success(self):
        config = LLMConfig("test", "key", "base")
        client = MockLLMClient(config)

        response = await client.generate_with_retry("Test prompt")

        assert response.content == "Mock response to: Test prompt"
        assert client.call_count == 1
        assert client.total_tokens == 30

    @pytest.mark.asyncio
    async def test_generate_with_retry_cached(self):
        config = LLMConfig("test", "key", "base")
        client = MockLLMClient(config)

        # First call
        response1 = await client.generate_with_retry("Test prompt")
        assert client.call_count == 1

        # Second call should use cache
        response2 = await client.generate_with_retry("Test prompt")
        assert client.call_count == 1  # No additional call
        assert response2.cached is True

    @pytest.mark.asyncio
    async def test_generate_with_retry_failure(self):
        config = LLMConfig("test", "key", "base", max_retries=2, retry_delay=0.1)
        client = MockLLMClient(config, should_fail=True)

        with pytest.raises(Exception, match="LLM call failed after 2 attempts"):
            await client.generate_with_retry("Test prompt")

        assert client.call_count == 2


class TestAzureOpenAIClient:
    """Test Azure OpenAI client"""

    @pytest.mark.asyncio
    async def test_azure_generate(self):
        config = LLMConfig("gpt-4", "test-key", "https://test.openai.azure.com")

        with patch('nps_report_v3.llm.client.AsyncAzureOpenAI') as mock_azure:
            mock_client = AsyncMock()
            mock_azure.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Azure response"
            mock_response.model = "gpt-4"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30

            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            client = AzureOpenAIClient(config)
            response = await client.generate("Test prompt")

            assert response.content == "Azure response"
            assert response.model == "gpt-4"
            assert response.usage['total_tokens'] == 30

    @pytest.mark.asyncio
    async def test_azure_embed(self):
        config = LLMConfig("gpt-4", "test-key", "https://test.openai.azure.com")

        with patch('nps_report_v3.llm.client.AsyncAzureOpenAI') as mock_azure:
            mock_client = AsyncMock()
            mock_azure.return_value = mock_client

            mock_response = MagicMock()
            mock_response.data = [MagicMock()]
            mock_response.data[0].embedding = [0.1] * 1536

            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            client = AzureOpenAIClient(config)
            embedding = await client.embed("Test text")

            assert len(embedding) == 1536
            assert embedding[0] == 0.1


class TestYiliGatewayClient:
    """Test Yili Gateway client"""

    @pytest.mark.asyncio
    async def test_yili_generate(self):
        config = LLMConfig("gpt-4", "test-key", "http://gateway.yili.com")

        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Yili response'}}],
                'model': 'gpt-4',
                'usage': {
                    'prompt_tokens': 10,
                    'completion_tokens': 20,
                    'total_tokens': 30
                }
            }

            mock_client.post = AsyncMock(return_value=mock_response)

            client = YiliGatewayClient(config)
            response = await client.generate("Test prompt")

            assert response.content == "Yili response"
            assert response.model == "gpt-4"
            assert response.usage['total_tokens'] == 30


class TestLLMClientWithFailover:
    """Test failover LLM client"""

    @pytest.mark.asyncio
    async def test_failover_primary_success(self):
        primary_config = LLMConfig("primary", "key", "base")
        backup_config = LLMConfig("backup", "key", "base")

        primary = MockLLMClient(primary_config, should_fail=False)
        backup = MockLLMClient(backup_config, should_fail=False)

        client = LLMClientWithFailover(primary, backup)

        response = await client.generate("Test prompt")

        assert response.content == "Mock response to: Test prompt"
        assert primary.call_count == 1
        assert backup.call_count == 0

    @pytest.mark.asyncio
    async def test_failover_to_backup(self):
        primary_config = LLMConfig("primary", "key", "base")
        backup_config = LLMConfig("backup", "key", "base")

        primary = MockLLMClient(primary_config, should_fail=True)
        backup = MockLLMClient(backup_config, should_fail=False)

        client = LLMClientWithFailover(primary, backup)

        response = await client.generate("Test prompt")

        assert response.content == "Mock response to: Test prompt"
        assert primary.call_count == 1
        assert backup.call_count == 1

    @pytest.mark.asyncio
    async def test_failover_both_fail(self):
        primary_config = LLMConfig("primary", "key", "base")
        backup_config = LLMConfig("backup", "key", "base")

        primary = MockLLMClient(primary_config, should_fail=True)
        backup = MockLLMClient(backup_config, should_fail=True)

        client = LLMClientWithFailover(primary, backup)

        with pytest.raises(Exception, match="Backup client also failed"):
            await client.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_embed_failover(self):
        primary_config = LLMConfig("primary", "key", "base")
        backup_config = LLMConfig("backup", "key", "base")

        primary = MockLLMClient(primary_config, should_fail=True)
        backup = MockLLMClient(backup_config, should_fail=False)

        client = LLMClientWithFailover(primary, backup)

        embedding = await client.embed("Test text")

        assert len(embedding) == 1536
        assert embedding[0] == 0.1


class TestCreateLLMClient:
    """Test factory function"""

    @patch.dict('os.environ', {
        'AZURE_OPENAI_API_KEY': 'azure-key',
        'AZURE_OPENAI_ENDPOINT': 'https://azure.openai.com',
        'YILI_APP_KEY': 'yili-key',
        'YILI_GATEWAY_URL': 'http://yili.gateway.com'
    })
    def test_create_azure_primary(self):
        with patch('nps_report_v3.llm.client.AzureOpenAIClient') as mock_azure:
            with patch('nps_report_v3.llm.client.YiliGatewayClient') as mock_yili:
                client = create_llm_client(primary="azure", enable_failover=True)

                # Should create both clients for failover
                assert mock_azure.called
                assert mock_yili.called
                assert isinstance(client, LLMClientWithFailover)

    @patch.dict('os.environ', {
        'AZURE_OPENAI_API_KEY': 'azure-key',
        'AZURE_OPENAI_ENDPOINT': 'https://azure.openai.com',
    })
    def test_create_no_failover(self):
        with patch('nps_report_v3.llm.client.AzureOpenAIClient') as mock_azure:
            client = create_llm_client(primary="azure", enable_failover=False)

            # Should only create primary client
            assert mock_azure.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])