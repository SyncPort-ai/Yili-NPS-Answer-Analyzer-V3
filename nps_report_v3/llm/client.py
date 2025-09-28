"""
LLM client abstraction layer for NPS V3 API.
Provides unified interface for Azure OpenAI and Yili Gateway with automatic failover.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio
import logging
import time
import hashlib
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM clients"""
    model_name: str
    api_key: str
    api_base: str
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 2


@dataclass
class LLMResponse:
    """Standard response format from LLM"""
    content: str
    model: str
    usage: Dict[str, int]
    latency_ms: int
    cached: bool = False
    metadata: Optional[Dict] = None


class LLMClient(ABC):
    """Abstract base class for LLM clients"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.call_count = 0
        self.total_tokens = 0
        self.cache = {}  # Simple in-memory cache

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response from LLM"""
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text"""
        pass

    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key for prompt"""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _get_from_cache(self, prompt: str) -> Optional[LLMResponse]:
        """Get response from cache if available"""
        key = self._get_cache_key(prompt)
        if key in self.cache:
            cached_item = self.cache[key]
            if cached_item['expires_at'] > datetime.utcnow():
                logger.debug(f"Cache hit for prompt hash: {key[:8]}...")
                response = cached_item['response']
                response.cached = True
                return response
        return None

    def _save_to_cache(self, prompt: str, response: LLMResponse, ttl_seconds: int = 3600):
        """Save response to cache"""
        key = self._get_cache_key(prompt)
        self.cache[key] = {
            'response': response,
            'expires_at': datetime.utcnow() + timedelta(seconds=ttl_seconds)
        }
        logger.debug(f"Cached response for prompt hash: {key[:8]}...")

    async def generate_with_retry(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response with retry logic"""
        # Check cache first
        cached_response = self._get_from_cache(prompt)
        if cached_response:
            return cached_response

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                start_time = time.time()
                response = await self.generate(prompt, **kwargs)
                response.latency_ms = int((time.time() - start_time) * 1000)

                # Update statistics
                self.call_count += 1
                self.total_tokens += response.usage.get('total_tokens', 0)

                # Cache the response
                self._save_to_cache(prompt, response)

                return response

            except Exception as e:
                last_error = e
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")

                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying after {delay} seconds...")
                    await asyncio.sleep(delay)

        raise Exception(f"LLM call failed after {self.config.max_retries} attempts: {last_error}")


class AzureOpenAIClient(LLMClient):
    """Azure OpenAI client implementation"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # Lazy import to avoid dependency if not used
        from openai import AsyncAzureOpenAI
        self.client = AsyncAzureOpenAI(
            api_key=config.api_key,
            api_version="2024-02-01",
            azure_endpoint=config.api_base
        )

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using Azure OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.config.temperature),
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                timeout=self.config.timeout
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                latency_ms=0  # Will be set by generate_with_retry
            )

        except Exception as e:
            logger.error(f"Azure OpenAI generation error: {e}")
            raise

    async def embed(self, text: str) -> List[float]:
        """Generate embedding using Azure OpenAI"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text,
                timeout=self.config.timeout
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Azure OpenAI embedding error: {e}")
            raise


class YiliGatewayClient(LLMClient):
    """Yili corporate gateway client implementation"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # Use httpx for async HTTP requests
        import httpx
        self.client = httpx.AsyncClient(
            base_url=config.api_base,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            },
            timeout=config.timeout
        )

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using Yili Gateway"""
        try:
            payload = {
                "model": self.config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get('temperature', self.config.temperature),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens)
            }

            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            data = response.json()

            return LLMResponse(
                content=data['choices'][0]['message']['content'],
                model=data.get('model', self.config.model_name),
                usage=data.get('usage', {
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0
                }),
                latency_ms=0  # Will be set by generate_with_retry
            )

        except Exception as e:
            logger.error(f"Yili Gateway generation error: {e}")
            raise

    async def embed(self, text: str) -> List[float]:
        """Generate embedding using Yili Gateway"""
        try:
            payload = {
                "model": "text-embedding-ada-002",
                "input": text
            }

            response = await self.client.post("/embeddings", json=payload)
            response.raise_for_status()

            data = response.json()
            return data['data'][0]['embedding']

        except Exception as e:
            logger.error(f"Yili Gateway embedding error: {e}")
            raise


class LLMClientWithFailover(LLMClient):
    """LLM client with automatic failover between primary and backup"""

    def __init__(self, primary_client: LLMClient, backup_client: Optional[LLMClient] = None):
        # Use primary client's config
        super().__init__(primary_client.config)
        self.primary_client = primary_client
        self.backup_client = backup_client
        self.use_primary = True

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate with automatic failover"""
        # Try primary client first
        if self.use_primary:
            try:
                logger.debug("Using primary LLM client")
                return await self.primary_client.generate(prompt, **kwargs)
            except Exception as e:
                logger.warning(f"Primary client failed: {e}")
                if self.backup_client:
                    logger.info("Failing over to backup client")
                    self.use_primary = False
                else:
                    raise

        # Use backup client
        if self.backup_client and not self.use_primary:
            try:
                logger.debug("Using backup LLM client")
                response = await self.backup_client.generate(prompt, **kwargs)

                # Try to restore primary after successful backup call
                asyncio.create_task(self._try_restore_primary())

                return response
            except Exception as e:
                logger.error(f"Backup client also failed: {e}")
                raise

        raise Exception("No available LLM client")

    async def embed(self, text: str) -> List[float]:
        """Generate embedding with automatic failover"""
        if self.use_primary:
            try:
                return await self.primary_client.embed(text)
            except Exception as e:
                logger.warning(f"Primary client embedding failed: {e}")
                if self.backup_client:
                    self.use_primary = False
                else:
                    raise

        if self.backup_client and not self.use_primary:
            return await self.backup_client.embed(text)

        raise Exception("No available LLM client for embedding")

    async def _try_restore_primary(self):
        """Try to restore primary client after delay"""
        await asyncio.sleep(60)  # Wait 1 minute before trying
        try:
            # Test with simple prompt
            await self.primary_client.generate("test", max_tokens=10)
            self.use_primary = True
            logger.info("Primary client restored")
        except:
            pass  # Keep using backup

    async def generate_with_retry(self, prompt: str, **kwargs) -> LLMResponse:
        """Override to use failover logic"""
        # Check cache first
        cached_response = self._get_from_cache(prompt)
        if cached_response:
            return cached_response

        # Use failover generation
        response = await self.generate(prompt, **kwargs)

        # Cache the response
        self._save_to_cache(prompt, response)

        return response


def create_llm_client(primary: str = "azure", enable_failover: bool = True) -> LLMClient:
    """
    Factory function to create LLM client

    Args:
        primary: Primary client type ('azure' or 'yili')
        enable_failover: Whether to enable automatic failover

    Returns:
        Configured LLM client
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Create primary client
    if primary == "azure":
        azure_config = LLMConfig(
            model_name=os.getenv("AZURE_OPENAI_MODEL", "gpt-4-turbo"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_base=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        )
        primary_client = AzureOpenAIClient(azure_config)
    else:
        yili_config = LLMConfig(
            model_name=os.getenv("YILI_MODEL", "gpt-4-turbo"),
            api_key=os.getenv("YILI_APP_KEY", ""),
            api_base=os.getenv("YILI_GATEWAY_URL", "http://ai-gateway.yili.com/v1/"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        )
        primary_client = YiliGatewayClient(yili_config)

    if not enable_failover:
        return primary_client

    # Create backup client (opposite of primary)
    if primary == "azure":
        yili_config = LLMConfig(
            model_name=os.getenv("YILI_MODEL", "gpt-4-turbo"),
            api_key=os.getenv("YILI_APP_KEY", ""),
            api_base=os.getenv("YILI_GATEWAY_URL", "http://ai-gateway.yili.com/v1/"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        )
        backup_client = YiliGatewayClient(yili_config)
    else:
        azure_config = LLMConfig(
            model_name=os.getenv("AZURE_OPENAI_MODEL", "gpt-4-turbo"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_base=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        )
        backup_client = AzureOpenAIClient(azure_config)

    return LLMClientWithFailover(primary_client, backup_client)


# Alias for backward compatibility
get_llm_client = create_llm_client