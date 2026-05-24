"""Tests for LLM provider interface, implementations, and factory.

Validates the provider factory selects the correct provider based on
settings, fails fast on invalid configuration, and that each provider
correctly formats API requests and extracts responses.
"""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import LLMProviderType, Settings
from app.providers import get_llm_provider
from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.openai import OpenAIProvider

# Minimal required env vars for a valid Settings instance
REQUIRED_ENV = {
    "NEXUS_MODE": "tracker",
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/nexus_test_db",
    "JWT_SECRET": "test-secret-key",
    "CORS_ORIGINS": "http://localhost:5173",
}


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestGetLLMProvider:
    """Tests for the get_llm_provider factory function."""

    def test_returns_openai_provider(self):
        env = {
            **REQUIRED_ENV,
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-key",
            "OPENAI_MODEL": "gpt-4o",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            provider = get_llm_provider(settings)
            assert isinstance(provider, OpenAIProvider)

    def test_returns_anthropic_provider(self):
        env = {
            **REQUIRED_ENV,
            "LLM_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": "sk-ant-test-key",
            "ANTHROPIC_MODEL": "claude-sonnet-4-20250514",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            provider = get_llm_provider(settings)
            assert isinstance(provider, AnthropicProvider)

    def test_raises_when_no_provider_configured(self):
        with patch.dict(os.environ, REQUIRED_ENV, clear=True):
            settings = Settings()
            with pytest.raises(ValueError, match="LLM_PROVIDER environment variable is not set"):
                get_llm_provider(settings)

    def test_raises_when_openai_key_missing(self):
        env = {**REQUIRED_ENV, "LLM_PROVIDER": "openai"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                get_llm_provider(settings)

    def test_raises_when_anthropic_key_missing(self):
        env = {**REQUIRED_ENV, "LLM_PROVIDER": "anthropic"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                get_llm_provider(settings)

    def test_openai_uses_default_model_when_not_set(self):
        env = {
            **REQUIRED_ENV,
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-key",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            provider = get_llm_provider(settings)
            assert isinstance(provider, OpenAIProvider)
            assert provider._model == "gpt-4o"

    def test_anthropic_uses_default_model_when_not_set(self):
        env = {
            **REQUIRED_ENV,
            "LLM_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": "sk-ant-test-key",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            provider = get_llm_provider(settings)
            assert isinstance(provider, AnthropicProvider)
            assert provider._model == "claude-sonnet-4-20250514"

    def test_all_providers_implement_llm_provider_interface(self):
        """Both concrete providers are subclasses of LLMProvider."""
        assert issubclass(OpenAIProvider, LLMProvider)
        assert issubclass(AnthropicProvider, LLMProvider)


# ---------------------------------------------------------------------------
# OpenAI provider tests
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    """Tests for OpenAIProvider request formatting and response extraction."""

    @pytest.fixture
    def provider(self):
        return OpenAIProvider(api_key="sk-test-key", model="gpt-4o")

    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock httpx.Response matching OpenAI's format."""
        return httpx.Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Hello! I can help with that.",
                        }
                    }
                ]
            },
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )

    async def test_generate_response_returns_content(
        self, provider, mock_openai_response
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_openai_response)

        with patch("app.providers.openai.httpx.AsyncClient", return_value=mock_client):
            result = await provider.generate_response(
                system_prompt="You are a helpful assistant.",
                messages=[{"role": "user", "content": "Hi there"}],
            )

        assert result == "Hello! I can help with that."

    async def test_sends_correct_request_format(self, provider, mock_openai_response):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_openai_response)

        with patch("app.providers.openai.httpx.AsyncClient", return_value=mock_client):
            await provider.generate_response(
                system_prompt="System prompt here.",
                messages=[
                    {"role": "user", "content": "Question 1"},
                    {"role": "assistant", "content": "Answer 1"},
                    {"role": "user", "content": "Question 2"},
                ],
            )

        call_kwargs = mock_client.post.call_args
        assert call_kwargs.args[0] == "https://api.openai.com/v1/chat/completions"

        headers = call_kwargs.kwargs["headers"]
        assert headers["Authorization"] == "Bearer sk-test-key"
        assert headers["Content-Type"] == "application/json"

        body = call_kwargs.kwargs["json"]
        assert body["model"] == "gpt-4o"
        assert body["messages"][0] == {"role": "system", "content": "System prompt here."}
        assert body["messages"][1] == {"role": "user", "content": "Question 1"}
        assert body["messages"][2] == {"role": "assistant", "content": "Answer 1"}
        assert body["messages"][3] == {"role": "user", "content": "Question 2"}
        assert len(body["messages"]) == 4

    async def test_raises_on_http_error(self, provider):
        error_response = httpx.Response(
            status_code=401,
            json={"error": {"message": "Invalid API key"}},
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=error_response)

        with patch("app.providers.openai.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.generate_response(
                    system_prompt="Test",
                    messages=[{"role": "user", "content": "Hi"}],
                )


# ---------------------------------------------------------------------------
# Anthropic provider tests
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    """Tests for AnthropicProvider request formatting and response extraction."""

    @pytest.fixture
    def provider(self):
        return AnthropicProvider(api_key="sk-ant-test-key", model="claude-sonnet-4-20250514")

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create a mock httpx.Response matching Anthropic's format."""
        return httpx.Response(
            status_code=200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": "I'd be happy to help!",
                    }
                ],
                "role": "assistant",
            },
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        )

    async def test_generate_response_returns_content(
        self, provider, mock_anthropic_response
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_anthropic_response)

        with patch("app.providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            result = await provider.generate_response(
                system_prompt="You are a helpful assistant.",
                messages=[{"role": "user", "content": "Hi there"}],
            )

        assert result == "I'd be happy to help!"

    async def test_sends_correct_request_format(self, provider, mock_anthropic_response):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_anthropic_response)

        with patch("app.providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            await provider.generate_response(
                system_prompt="System prompt here.",
                messages=[
                    {"role": "user", "content": "Question 1"},
                    {"role": "assistant", "content": "Answer 1"},
                    {"role": "user", "content": "Question 2"},
                ],
            )

        call_kwargs = mock_client.post.call_args
        assert call_kwargs.args[0] == "https://api.anthropic.com/v1/messages"

        headers = call_kwargs.kwargs["headers"]
        assert headers["x-api-key"] == "sk-ant-test-key"
        assert headers["anthropic-version"] == "2023-06-01"
        assert headers["Content-Type"] == "application/json"

        body = call_kwargs.kwargs["json"]
        assert body["model"] == "claude-sonnet-4-20250514"
        assert body["system"] == "System prompt here."
        assert body["max_tokens"] == 1024
        # Anthropic messages should NOT include system — only user/assistant turns
        assert body["messages"] == [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
        ]

    async def test_raises_on_http_error(self, provider):
        error_response = httpx.Response(
            status_code=401,
            json={"error": {"message": "Invalid API key"}},
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        )
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=error_response)

        with patch("app.providers.anthropic.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.generate_response(
                    system_prompt="Test",
                    messages=[{"role": "user", "content": "Hi"}],
                )
