"""Anthropic LLM provider implementation.

Uses httpx async client to communicate with the Anthropic Messages API.
Provider is selected when LLM_PROVIDER=anthropic.
"""

import httpx

from app.providers.base import LLMProvider

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
REQUEST_TIMEOUT = 30.0
MAX_TOKENS = 1024


class AnthropicProvider(LLMProvider):
    """LLM provider backed by the Anthropic Messages API.

    Args:
        api_key: Anthropic API key for authentication.
        model: Model identifier (e.g. "claude-sonnet-4-20250514").
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def generate_response(self, system_prompt: str, messages: list[dict]) -> str:
        """Send a message request to Anthropic and return the response.

        Uses Anthropic's API format where the system prompt is a top-level
        parameter and messages contain only user/assistant turns.

        Args:
            system_prompt: System-level instruction for the model.
            messages: Conversation history with "role" and "content" keys.

        Returns:
            The assistant's response text.

        Raises:
            httpx.HTTPStatusError: If the API returns a non-2xx status.
            httpx.TimeoutException: If the request exceeds 30 seconds.
        """
        anthropic_messages = [
            {"role": msg["role"], "content": msg["content"]} for msg in messages
        ]

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                ANTHROPIC_MESSAGES_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": ANTHROPIC_API_VERSION,
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": MAX_TOKENS,
                    "system": system_prompt,
                    "messages": anthropic_messages,
                },
            )
            response.raise_for_status()

        data = response.json()
        return data["content"][0]["text"]
