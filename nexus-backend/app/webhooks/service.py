"""Outbound webhook dispatch service.

Sends HTTP POST notifications to a configured webhook URL when
platform events occur (e.g. project creation, skill proficiency
change). Includes retry logic with exponential backoff and
configurable authentication headers.

All failures are logged — they never propagate to the caller so
that webhook delivery cannot block primary operations.
"""

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES: int = 3
BACKOFF_BASE_SECONDS: float = 1.0  # 1s, 2s, 4s


class WebhookService:
    """Dispatches outbound webhook notifications.

    Loads the target URL and auth header from application settings.
    If no webhook URL is configured, all dispatch calls are no-ops.

    Args:
        settings: Application settings containing webhook configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._webhook_url: str | None = settings.webhook_url
        self._auth_header: str | None = settings.webhook_auth_header

    async def dispatch(self, event_type: str, payload: dict[str, Any]) -> None:
        """Send a webhook notification for a platform event.

        This method is fire-and-forget safe: it catches all exceptions
        and logs them rather than propagating, ensuring webhook delivery
        never blocks the primary operation.

        Args:
            event_type: The type of event (e.g. ``"project.created"``).
            payload: A JSON-serialisable dict describing the event.
        """
        if not self._webhook_url:
            return

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._auth_header:
            headers["Authorization"] = self._auth_header

        body: dict[str, Any] = {
            "event_type": event_type,
            "payload": payload,
        }

        try:
            await self._send_with_retry(self._webhook_url, body, headers)
        except Exception:
            # Final safety net — ensure nothing escapes to the caller.
            logger.exception(
                "Webhook dispatch failed for event_type=%s payload=%s",
                event_type,
                payload,
            )

    async def _send_with_retry(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        """Send an HTTP POST with up to 3 retries and exponential backoff.

        Backoff delays: 1 s, 2 s, 4 s (``BACKOFF_BASE_SECONDS * 2**attempt``).

        On each failed attempt the error is logged with the event payload
        and HTTP status code (when available). After all retries are
        exhausted the last exception is re-raised so the caller can
        handle final logging.

        Args:
            url: The webhook target URL.
            payload: The JSON body to send.
            headers: HTTP headers including auth and content-type.

        Raises:
            httpx.HTTPStatusError: If the server returns a non-2xx status
                after all retries.
            httpx.HTTPError: For network-level failures after all retries.
        """
        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    return  # Success — exit immediately.
            except httpx.HTTPStatusError as exc:
                last_exception = exc
                status_code = exc.response.status_code
                logger.warning(
                    "Webhook delivery attempt %d/%d failed: "
                    "status=%d url=%s payload=%s",
                    attempt + 1,
                    MAX_RETRIES,
                    status_code,
                    url,
                    payload,
                )
            except httpx.HTTPError as exc:
                last_exception = exc
                logger.warning(
                    "Webhook delivery attempt %d/%d failed: "
                    "error=%s url=%s payload=%s",
                    attempt + 1,
                    MAX_RETRIES,
                    exc,
                    url,
                    payload,
                )

            # Exponential backoff: 1s, 2s, 4s
            if attempt < MAX_RETRIES - 1:
                delay = BACKOFF_BASE_SECONDS * (2**attempt)
                await asyncio.sleep(delay)

        # All retries exhausted — re-raise so dispatch() can log it.
        if last_exception is not None:
            raise last_exception
