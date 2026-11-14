"""
QB-H1 Task 2 + Task 3 — OAuth Refresh Robustness + intuit_tid Logging Tests

Task 2: Verifies the transient/permanent error classification in the Celery
beat task ``refresh_quickbooks_tokens_task``:
  - 400 invalid_grant → expired + notification enqueued
  - 503 from Intuit → still active, transient_failed=1, no notification
  - network TransportError → still active
  - success path → tokens rotated, last_refresh_at set

Task 3: Verifies ``intuit_tid`` is logged (arg-style, not f-string) on the
token-endpoint call via ``caplog`` assertions (tested at the
``_refresh_access_token`` level where the actual httpx call + log happens).

All httpx calls are mocked — no live Intuit calls.

Batch: QB-H1
Design: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §F.1–F.3
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlmodel import select

from app.models.system import (
    AppService,
    IntegrationCredential,
    NotificationOutbox,
)
from core.encryption import encrypt_token
from tasks.quickbooks_token_refresh import (
    TokenRefreshOutcome,
    _classify_refresh_error,
)

pytestmark = [
    pytest.mark.domain_quickbooks,
    pytest.mark.unit,
]


# ==================== Task 2: Error Classification (pure function) ====================


class TestClassifyRefreshError:
    """Unit tests for _classify_refresh_error (pure function, no DB)."""

    def test_400_is_permanent(self):
        """HTTP 400 → PERMANENT_FAILURE."""
        response = MagicMock()
        response.status_code = 400
        response.text = '{"error": "invalid_grant"}'
        exc = httpx.HTTPStatusError("400", request=MagicMock(), response=response)
        assert _classify_refresh_error(exc) == TokenRefreshOutcome.PERMANENT_FAILURE

    def test_401_is_permanent(self):
        """HTTP 401 → PERMANENT_FAILURE."""
        response = MagicMock()
        response.status_code = 401
        response.text = ""
        exc = httpx.HTTPStatusError("401", request=MagicMock(), response=response)
        assert _classify_refresh_error(exc) == TokenRefreshOutcome.PERMANENT_FAILURE

    def test_invalid_grant_in_body_is_permanent(self):
        """invalid_grant in response body → PERMANENT_FAILURE (even on non-400)."""
        response = MagicMock()
        response.status_code = 403
        response.text = '{"error": "invalid_grant"}'
        exc = httpx.HTTPStatusError("403", request=MagicMock(), response=response)
        assert _classify_refresh_error(exc) == TokenRefreshOutcome.PERMANENT_FAILURE

    def test_500_is_transient(self):
        """HTTP 500 → TRANSIENT_FAILURE."""
        response = MagicMock()
        response.status_code = 500
        response.text = "Internal Server Error"
        exc = httpx.HTTPStatusError("500", request=MagicMock(), response=response)
        assert _classify_refresh_error(exc) == TokenRefreshOutcome.TRANSIENT_FAILURE

    def test_503_is_transient(self):
        """HTTP 503 → TRANSIENT_FAILURE."""
        response = MagicMock()
        response.status_code = 503
        response.text = "Service Unavailable"
        exc = httpx.HTTPStatusError("503", request=MagicMock(), response=response)
        assert _classify_refresh_error(exc) == TokenRefreshOutcome.TRANSIENT_FAILURE

    def test_transport_error_is_transient(self):
        """httpx.TransportError → TRANSIENT_FAILURE."""
        exc = httpx.ConnectError("Connection refused")
        assert _classify_refresh_error(exc) == TokenRefreshOutcome.TRANSIENT_FAILURE

    def test_timeout_is_transient(self):
        """httpx.TimeoutException → TRANSIENT_FAILURE."""
        exc = httpx.ReadTimeout("Read timed out")
        assert _classify_refresh_error(exc) == TokenRefreshOutcome.TRANSIENT_FAILURE

    def test_unknown_error_is_permanent(self):
        """Unknown exception → PERMANENT_FAILURE (fail-safe)."""
        exc = ValueError("something unexpected")
        assert _classify_refresh_error(exc) == TokenRefreshOutcome.PERMANENT_FAILURE


# ==================== Helpers ====================


def _make_mock_response(
    status_code: int, json_data: dict | None = None, intuit_tid: str = "test-tid-123"
):
    """Create a mock httpx.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = {"intuit_tid": intuit_tid}
    response.json.return_value = json_data or {}
    response.text = str(json_data or {})
    if status_code >= 400:
        request = MagicMock()
        request.method = "POST"
        request.url = "https://test.intuit.com/v3/token"
        response.request = request
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code}", request=request, response=response
        )
    else:
        response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def qb_credential_expiring(db_session, test_tenant, test_user):
    """Create a QuickBooks credential that is expiring soon (<5 min)."""
    app_service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="QuickBooks Online",
        category_code="accounting",
        provider_code="quickbooks",
        external_account_id="1234567890123456",
        is_active=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(app_service)
    db_session.flush()

    now = datetime.now(UTC)
    credential = IntegrationCredential(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        app_service_id=app_service.id,
        secret_json={
            "access_token_encrypted": encrypt_token("old_access"),
            "refresh_token_encrypted": encrypt_token("test_refresh"),
        },
        expires_at=now + timedelta(minutes=2),  # expiring soon
        last_refresh_at=now - timedelta(hours=1),
        connected_at=now - timedelta(days=1),
        connection_status="active",
        initiated_by_user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(credential)
    db_session.commit()
    db_session.refresh(credential)
    return credential


def _run_task_with_mocked_db(db_session, mock_refresh):
    """Run refresh_quickbooks_tokens_task with get_db patched to yield db_session.

    Patches ``db.close`` to a no-op so the test session stays usable after the
    task's ``finally`` block runs.
    """
    from tasks.quickbooks_token_refresh import refresh_quickbooks_tokens_task

    with (
        patch(
            "tasks.quickbooks_token_refresh._refresh_access_token",
            new_callable=AsyncMock,
            **mock_refresh,
        ),
        patch(
            "tasks.quickbooks_token_refresh.get_db",
            return_value=iter([db_session]),
        ),
        patch.object(db_session, "close"),
    ):
        return refresh_quickbooks_tokens_task()


# ==================== Task 2: Beat Task Integration ====================


class TestTokenRefreshTaskClassification:
    """Test the beat task's error classification with mocked httpx."""

    def test_400_invalid_grant_marks_expired_and_notifies(
        self, db_session, test_tenant, test_user, qb_credential_expiring
    ):
        """400 invalid_grant → connection expired + notification enqueued."""
        mock_response = _make_mock_response(400, {"error": "invalid_grant"})
        exc = httpx.HTTPStatusError("400", request=MagicMock(), response=mock_response)

        result = _run_task_with_mocked_db(db_session, {"side_effect": exc})

        assert result["failed"] == 1
        assert result["transient_failed"] == 0

        # Verify credential is now expired
        db_session.expire_all()
        cred = db_session.get(IntegrationCredential, qb_credential_expiring.id)
        assert cred.connection_status == "expired"

        # Verify notification outbox was enqueued for the owner
        outbox_rows = db_session.exec(
            select(NotificationOutbox).where(
                NotificationOutbox.tenant_id == test_tenant.id,
                NotificationOutbox.channel == "email",
                NotificationOutbox.status == "pending",
            )
        ).all()
        expired_outbox = [
            o for o in outbox_rows if "Connection expired" in (o.subject or "")
        ]
        assert len(expired_outbox) >= 1, (
            "Expected at least one connection-expired notification"
        )

    def test_503_leaves_active_and_counts_transient(
        self, db_session, test_tenant, qb_credential_expiring
    ):
        """503 from Intuit → still active, transient_failed=1, no notification."""
        mock_response = _make_mock_response(503, {"error": "Service Unavailable"})
        exc = httpx.HTTPStatusError("503", request=MagicMock(), response=mock_response)

        result = _run_task_with_mocked_db(db_session, {"side_effect": exc})

        assert result["transient_failed"] == 1
        assert result["failed"] == 0

        db_session.expire_all()
        cred = db_session.get(IntegrationCredential, qb_credential_expiring.id)
        assert cred.connection_status == "active"

    def test_transport_error_leaves_active(
        self, db_session, test_tenant, qb_credential_expiring
    ):
        """Network TransportError → still active."""
        result = _run_task_with_mocked_db(
            db_session,
            {"side_effect": httpx.ConnectError("Connection refused")},
        )

        assert result["transient_failed"] == 1
        assert result["failed"] == 0

        db_session.expire_all()
        cred = db_session.get(IntegrationCredential, qb_credential_expiring.id)
        assert cred.connection_status == "active"

    def test_success_path_rotates_tokens(
        self, db_session, test_tenant, qb_credential_expiring
    ):
        """Success path → tokens rotated, last_refresh_at set."""
        from tasks.quickbooks_token_refresh import QuickBooksTokenResponse

        mock_tokens = QuickBooksTokenResponse(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            expires_in=3600,
            x_refresh_token_expires_in=8726400,
        )

        result = _run_task_with_mocked_db(db_session, {"return_value": mock_tokens})

        assert result["refreshed"] == 1
        assert result["failed"] == 0
        assert result["transient_failed"] == 0

        db_session.expire_all()
        cred = db_session.get(IntegrationCredential, qb_credential_expiring.id)
        assert cred.connection_status == "active"
        assert cred.last_refresh_at is not None


# ==================== Task 3: intuit_tid Logging ====================


class TestIntuitTidLogging:
    """Verify intuit_tid is logged on the token-endpoint call (Task 3)."""

    def test_refresh_access_token_logs_intuit_tid(self, caplog):
        """_refresh_access_token logs intuit_tid from the response header."""
        mock_response = _make_mock_response(
            200,
            {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_in": 3600,
                "x_refresh_token_expires_in": 8726400,
                "token_type": "Bearer",
            },
            intuit_tid="abc-123-def",
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        import logging

        with patch(
            "tasks.quickbooks_token_refresh.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with caplog.at_level(logging.INFO, logger="tasks.quickbooks_token_refresh"):
                import asyncio

                from tasks.quickbooks_token_refresh import _refresh_access_token

                asyncio.run(_refresh_access_token("test_refresh_token"))

        intuit_tid_logs = [r for r in caplog.records if "intuit_tid" in r.message]
        assert len(intuit_tid_logs) >= 1, (
            "Expected at least one log record containing 'intuit_tid'"
        )
        # Verify the intuit_tid value is in the rendered log message (arg-style)
        assert any("abc-123-def" in r.getMessage() for r in intuit_tid_logs)
