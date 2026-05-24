"""OpenAI LLM provider implementation.

Uses httpx async client to communicate with the OpenAI Chat Completions
API. Provider is selected when LLM_PROVIDER=openai.
"""

import httpx

from app.providers.base import LLMProvider

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
REQUEST_TIMEOUT = 30.0


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API.

    Args:
        api_key: OpenAI API key for authentication.
        model: Model identifier (e.g. "gpt-4o", "gpt-3.5-turbo").
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def generate_response(self, system_prompt: str, messages: list[dict]) -> str:
        """Send a chat completion request to OpenAI and return the response.

        Constructs the messages array with the system prompt followed by
        the conversation history, then extracts the assistant's reply.

        Args:
            system_prompt: System-level instruction for the model.
            messages: Conversation history with "role" and "content" keys.

        Returns:
            The assistant's response text.

        Raises:
            httpx.HTTPStatusError: If the API returns a non-2xx status.
            httpx.TimeoutException: If the request exceeds 30 seconds.
        """
        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(
            {"role": msg["role"], "content": msg["content"]} for msg in messages
        )

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                OPENAI_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": openai_messages,
                },
            )
            response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]
