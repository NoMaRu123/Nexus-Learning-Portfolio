"""Tests for app.webhooks.service module.

Validates WebhookService operations including dispatch, retry logic
with exponential backoff, no-op behaviour when unconfigured, and
failure logging.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.webhooks.service import BACKOFF_BASE_SECONDS, MAX_RETRIES, WebhookService


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_settings(
    webhook_url: str | None = "https://hooks.example.com/events",
    webhook_auth_header: str | None = "Bearer test-token-123",
) -> MagicMock:
    """Create a mock Settings object with webhook configuration."""
    settings = MagicMock()
    settings.webhook_url = webhook_url
    settings.webhook_auth_header = webhook_auth_header
    return settings


def _success_response() -> httpx.Response:
    """Create a mock 200 OK response."""
    return httpx.Response(status_code=200, request=httpx.Request("POST", "https://example.com"))


def _error_response(status_code: int = 500) -> httpx.Response:
    """Create a mock error response."""
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://example.com"),
    )


# ---------------------------------------------------------------------------
# dispatch tests
# ---------------------------------------------------------------------------


class TestDispatch:
    """Tests for WebhookService.dispatch()."""

    @pytest.mark.asyncio
    async def test_dispatch_sends_post_with_correct_payload(self):
        """dispatch sends an HTTP POST with event_type and payload in the body."""
        settings = _make_settings()
        service = WebhookService(settings)

        mock_response = _success_response()
        with patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await service.dispatch("project.created", {"project_id": "abc-123"})

            mock_client.post.assert_awaited_once()
            call_kwargs = mock_client.post.call_args
            assert call_kwargs[1]["json"] == {
                "event_type": "project.created",
                "payload": {"project_id": "abc-123"},
            }

    @pytest.mark.asyncio
    async def test_dispatch_includes_auth_header(self):
        """dispatch includes the configured Authorization header."""
        settings = _make_settings(webhook_auth_header="Bearer my-secret")
        service = WebhookService(settings)

        mock_response = _success_response()
        with patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await service.dispatch("skill.updated", {"skill_id": "xyz"})

            call_kwargs = mock_client.post.call_args
            headers = call_kwargs[1]["headers"]
            assert headers["Authorization"] == "Bearer my-secret"
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_dispatch_noop_when_no_webhook_url(self):
        """dispatch is a no-op when no webhook URL is configured."""
        settings = _make_settings(webhook_url=None)
        service = WebhookService(settings)

        with patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls:
            await service.dispatch("project.created", {"id": "123"})

            mock_client_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_noop_when_webhook_url_empty(self):
        """dispatch is a no-op when webhook URL is an empty string (falsy)."""
        settings = _make_settings(webhook_url="")
        service = WebhookService(settings)

        with patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls:
            await service.dispatch("project.created", {"id": "123"})

            mock_client_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_does_not_propagate_exceptions(self):
        """dispatch catches all exceptions and does not raise."""
        settings = _make_settings()
        service = WebhookService(settings)

        with patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            # Should not raise
            await service.dispatch("project.created", {"id": "123"})

    @pytest.mark.asyncio
    async def test_dispatch_without_auth_header(self):
        """dispatch works without an auth header configured."""
        settings = _make_settings(webhook_auth_header=None)
        service = WebhookService(settings)

        mock_response = _success_response()
        with patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await service.dispatch("skill.updated", {"skill_id": "xyz"})

            call_kwargs = mock_client.post.call_args
            headers = call_kwargs[1]["headers"]
            assert "Authorization" not in headers
            assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# _send_with_retry tests
# ---------------------------------------------------------------------------


class TestSendWithRetry:
    """Tests for WebhookService._send_with_retry()."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """_send_with_retry returns immediately on a successful first attempt."""
        settings = _make_settings()
        service = WebhookService(settings)

        mock_response = _success_response()
        with patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await service._send_with_retry(
                "https://hooks.example.com",
                {"event_type": "test"},
                {"Content-Type": "application/json"},
            )

            assert mock_client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_http_error_status(self):
        """_send_with_retry retries up to MAX_RETRIES on HTTP error responses."""
        settings = _make_settings()
        service = WebhookService(settings)

        error_resp = _error_response(500)
        with (
            patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls,
            patch("app.webhooks.service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = error_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(httpx.HTTPStatusError):
                await service._send_with_retry(
                    "https://hooks.example.com",
                    {"event_type": "test"},
                    {"Content-Type": "application/json"},
                )

            assert mock_client.post.await_count == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        """_send_with_retry uses exponential backoff: 1s, 2s between retries."""
        settings = _make_settings()
        service = WebhookService(settings)

        error_resp = _error_response(502)
        with (
            patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls,
            patch("app.webhooks.service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = error_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(httpx.HTTPStatusError):
                await service._send_with_retry(
                    "https://hooks.example.com",
                    {"event_type": "test"},
                    {"Content-Type": "application/json"},
                )

            # Backoff: 1s after attempt 1, 2s after attempt 2, no sleep after attempt 3
            assert mock_sleep.await_count == MAX_RETRIES - 1
            mock_sleep.assert_any_await(BACKOFF_BASE_SECONDS * 1)  # 1s
            mock_sleep.assert_any_await(BACKOFF_BASE_SECONDS * 2)  # 2s

    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self):
        """_send_with_retry succeeds if the second attempt returns 200."""
        settings = _make_settings()
        service = WebhookService(settings)

        error_resp = _error_response(503)
        success_resp = _success_response()

        with (
            patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls,
            patch("app.webhooks.service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_client = AsyncMock()
            mock_client.post.side_effect = [error_resp, success_resp]
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            # Should not raise
            await service._send_with_retry(
                "https://hooks.example.com",
                {"event_type": "test"},
                {"Content-Type": "application/json"},
            )

            assert mock_client.post.await_count == 2
            mock_sleep.assert_awaited_once_with(BACKOFF_BASE_SECONDS * 1)

    @pytest.mark.asyncio
    async def test_retries_on_network_error(self):
        """_send_with_retry retries on network-level errors (ConnectError)."""
        settings = _make_settings()
        service = WebhookService(settings)

        with (
            patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls,
            patch("app.webhooks.service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(httpx.ConnectError):
                await service._send_with_retry(
                    "https://hooks.example.com",
                    {"event_type": "test"},
                    {"Content-Type": "application/json"},
                )

            assert mock_client.post.await_count == MAX_RETRIES


# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------


class TestWebhookLogging:
    """Tests for failure logging in WebhookService."""

    @pytest.mark.asyncio
    async def test_logs_failure_with_status_code_and_payload(self, caplog):
        """Failed webhook delivery logs the HTTP status code and event payload."""
        settings = _make_settings()
        service = WebhookService(settings)

        error_resp = _error_response(500)
        with (
            patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls,
            patch("app.webhooks.service.asyncio.sleep", new_callable=AsyncMock),
            caplog.at_level(logging.WARNING, logger="app.webhooks.service"),
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = error_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await service.dispatch("project.created", {"project_id": "abc"})

            # Check that warning logs contain status code and payload
            warning_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
            assert len(warning_logs) >= 1
            log_text = " ".join(r.message for r in warning_logs)
            assert "500" in log_text
            assert "project_id" in log_text

    @pytest.mark.asyncio
    async def test_logs_final_exception_in_dispatch(self, caplog):
        """dispatch logs the final exception after all retries are exhausted."""
        settings = _make_settings()
        service = WebhookService(settings)

        error_resp = _error_response(502)
        with (
            patch("app.webhooks.service.httpx.AsyncClient") as mock_client_cls,
            patch("app.webhooks.service.asyncio.sleep", new_callable=AsyncMock),
            caplog.at_level(logging.ERROR, logger="app.webhooks.service"),
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = error_resp
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await service.dispatch("skill.updated", {"skill_id": "xyz"})

            error_logs = [r for r in caplog.records if r.levelno == logging.ERROR]
            assert len(error_logs) >= 1
            log_text = " ".join(r.message for r in error_logs)
            assert "skill.updated" in log_text
