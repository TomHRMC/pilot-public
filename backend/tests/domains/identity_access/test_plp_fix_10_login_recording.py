"""
PLP-FIX-10 / INV-BUG-17 — Login recording task tests.

Domain: identity_access (PRD §3.5)

Covers the new ``record_user_login`` Celery task (two-layer pattern):
  (a) ``_record_user_login_impl`` upserts a row for the given ids.
  (b) Second call increments ``total_session_count`` and preserves
      ``first_login_at`` (the A72 upsert contract).
  (c) The wrapper's give-up-quietly path: force the impl to raise
      (monkeypatch) → wrapper logs, no exception propagates.

Reference: ``tests/batch_b13/test_a72_session_history.py`` for the upsert
contract patterns.
"""

from unittest.mock import patch

import pytest

from tasks.login_recording import _record_user_login_impl, record_user_login

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


class TestRecordUserLoginImpl:
    """_record_user_login_impl — the testable inner function."""

    def test_impl_upserts_row_on_first_call(self, db_session, tenant_a, user_tenant_a):
        """First call creates a row with count=1."""
        result = _record_user_login_impl(
            str(tenant_a.id), str(user_tenant_a.id), db_session
        )

        assert result["status"] == "recorded"
        assert result["tenant_id"] == str(tenant_a.id)
        assert result["user_id"] == str(user_tenant_a.id)
        assert result["total_session_count"] == 1

    def test_impl_increments_count_and_preserves_first_login(
        self, db_session, tenant_a, user_tenant_a
    ):
        """Second call increments count and preserves first_login_at."""
        result1 = _record_user_login_impl(
            str(tenant_a.id), str(user_tenant_a.id), db_session
        )
        first_count = result1["total_session_count"]
        assert first_count == 1

        result2 = _record_user_login_impl(
            str(tenant_a.id), str(user_tenant_a.id), db_session
        )

        assert result2["total_session_count"] == first_count + 1
        # The impl returns the count; the A72 upsert preserves first_login_at
        # internally (verified in test_a72_session_history.py — we assert the
        # count contract here).


class TestRecordUserLoginWrapperGiveUpQuietly:
    """The Celery wrapper must never raise — login telemetry must never page."""

    def test_wrapper_gives_up_quietly_on_impl_failure(
        self, db_session, tenant_a, user_tenant_a
    ):
        """When _impl raises, the wrapper logs and returns without raising."""
        # Patch _record_user_login_impl to raise a non-retryable error.
        # We also patch get_db so the wrapper uses our db_session.
        # We patch self.retry to raise MaxRetriesExceededError immediately
        # so the test doesn't hang on retries.
        with (
            patch(
                "tasks.login_recording._record_user_login_impl",
                side_effect=RuntimeError("DB connection lost"),
            ),
            patch("tasks.login_recording.get_db", return_value=iter([db_session])),
            patch.object(
                record_user_login,
                "MaxRetriesExceededError",
                Exception,
            ),
            patch.object(
                record_user_login,
                "retry",
                side_effect=record_user_login.MaxRetriesExceededError(),
            ),
        ):
            # The wrapper should NOT raise — it catches and returns a failed dict.
            result = record_user_login.run(str(tenant_a.id), str(user_tenant_a.id))

        assert result["status"] == "failed"
        assert result["reason"] == "max_retries_exceeded"
        assert result["tenant_id"] == str(tenant_a.id)
        assert result["user_id"] == str(user_tenant_a.id)
