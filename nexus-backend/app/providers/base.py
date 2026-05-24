"""Abstract LLM provider interface.

Defines the contract for LLM interactions used by the About Me Bot
service. Concrete implementations (OpenAI, Anthropic) implement this
interface and are selected at startup via the LLM_PROVIDER environment
variable.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM provider integrations.

    All LLM providers must implement generate_response to provide a
    consistent interface regardless of the underlying API. This enables
    provider-agnostic bot logic and allows new providers to be added
    by implementing this interface without modifying existing code.
    """

    @abstractmethod
    async def generate_response(self, system_prompt: str, messages: list[dict]) -> str:
        """Generate a response from the LLM.

        Args:
            system_prompt: The system-level instruction providing context
                about the user's profile, skills, and projects.
            messages: Conversation history as a list of message dicts,
                each with "role" ("user" or "assistant") and "content" keys.

        Returns:
            The assistant's response text.

        Raises:
            httpx.HTTPStatusError: If the LLM API returns an error status.
            httpx.TimeoutException: If the request exceeds the timeout.
        """
        ...
