"""LLM provider factory.

Provides ``get_llm_provider()`` which selects the appropriate LLM
provider implementation based on the ``LLM_PROVIDER`` environment
variable configured in application settings.
"""

from app.core.config import LLMProviderType, Settings
from app.providers.base import LLMProvider
from app.providers.anthropic import AnthropicProvider
from app.providers.openai import OpenAIProvider


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Create and return the configured LLM provider.

    Selects the provider based on ``settings.llm_provider`` and
    configures it with the corresponding API key and model from
    environment variables.

    Args:
        settings: Application settings containing LLM configuration.

    Returns:
        A concrete ``LLMProvider`` instance ready for use.

    Raises:
        ValueError: If no LLM provider is configured, the provider
            type is unrecognized, or the required API key is missing.
    """
    if settings.llm_provider is None:
        raise ValueError(
            "LLM_PROVIDER environment variable is not set. "
            "Set it to 'openai' or 'anthropic' to enable the About Me Bot."
        )

    if settings.llm_provider == LLMProviderType.OPENAI:
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required "
                "when LLM_PROVIDER is set to 'openai'."
            )
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model or "gpt-4o",
        )

    if settings.llm_provider == LLMProviderType.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required "
                "when LLM_PROVIDER is set to 'anthropic'."
            )
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model or "claude-sonnet-4-20250514",
        )

    raise ValueError(
        f"Unsupported LLM provider: {settings.llm_provider}. "
        "Supported values are 'openai' and 'anthropic'."
    )
