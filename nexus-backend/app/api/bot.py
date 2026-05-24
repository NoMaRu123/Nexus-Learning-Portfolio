"""About Me Bot API endpoint.

Provides a public chat endpoint for the About Me Bot with rate limiting.
No authentication required — this is a public-facing Portfolio Mode feature.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import UserAccount
from app.providers import get_llm_provider
from app.services.bot import BotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bot", tags=["bot"])

# Rate limiter keyed by visitor IP address.
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Pydantic schemas (inline per task spec)
# ---------------------------------------------------------------------------


class MessageDict(BaseModel):
    """A single message in the conversation history."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content text")


class ChatRequest(BaseModel):
    """Request body for the bot chat endpoint."""

    query: str = Field(..., description="The user's chat message")
    session_history: list[MessageDict] = Field(
        default_factory=list,
        description="Prior conversation messages for context continuity",
    )


class ChatResponse(BaseModel):
    """Response body from the bot chat endpoint."""

    response: str = Field(..., description="The bot's reply")
    is_fallback: bool = Field(
        ...,
        description="True if the response is a fallback (no LLM call made)",
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/10minutes")
async def bot_chat(
    request: Request,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Send a message to the About Me Bot and receive a response.

    This is a public endpoint — no authentication required.
    Rate limited to 30 requests per IP per 10-minute window.

    The bot classifies the query as relevant or unrelated:
    - Relevant queries fetch user context from the DB and call the LLM.
    - Unrelated queries return a humorous fallback with a Google search link.

    If the LLM service is unavailable, a friendly error message is returned.
    """
    settings = get_settings()

    # Resolve the portfolio owner (first user in the database).
    result = await db.execute(
        select(UserAccount).order_by(UserAccount.created_at.asc()).limit(1)
    )
    owner = result.scalar_one_or_none()

    if owner is None:
        return ChatResponse(
            response="The portfolio is not set up yet. Please check back later!",
            is_fallback=True,
        )

    # Obtain the LLM provider — return friendly message if unavailable.
    try:
        llm_provider = get_llm_provider(settings)
    except ValueError:
        logger.warning("LLM provider is not configured; returning friendly error.")
        return ChatResponse(
            response=(
                "I'm sorry, the chat service is temporarily unavailable. "
                "Please try again later!"
            ),
            is_fallback=True,
        )

    # Build the BotService and handle the message.
    bot_service = BotService(llm=llm_provider, db=db, user_id=owner.id)

    session_history = [msg.model_dump() for msg in body.session_history]

    try:
        result_dict = await bot_service.handle_message(
            query=body.query,
            session_history=session_history,
        )
    except (httpx.HTTPError, httpx.TimeoutException):
        logger.exception("LLM provider HTTP error during bot chat.")
        return ChatResponse(
            response=(
                "I'm sorry, the chat service is temporarily unavailable. "
                "Please try again later!"
            ),
            is_fallback=True,
        )

    return ChatResponse(
        response=result_dict["response"],
        is_fallback=result_dict["is_fallback"],
    )
