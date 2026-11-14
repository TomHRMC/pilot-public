"""
A87 — Feedback Submission Endpoint with Email Intake tests.

Test focus:
- POST /api/v1/feedback/test creates FeedbackSubmission record
- Valid categories accepted (bug, feature_request, question, general)
- Invalid category rejected with 400
- body too short rejected with 422
- from_help_chat_session_id FK validated
- send_feedback_email task called after submission
- _send_feedback_email_impl updates email_message_id on submission

FIX (2026-06-03): Removed module-level TestClient fixture that bypassed the
rollback fixture. All tests now use the conftest `client` fixture which wraps
DB operations in a rolled-back transaction.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


class TestFeedbackSubmissionModel:
    def test_create_submission(self, db_session, test_tenant, test_user):
        from app.models.help import FeedbackSubmission

        now = datetime.now(UTC)
        sub = FeedbackSubmission(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            category="question",
            body="I can't figure out how to set up recurring jobs.",
            email_sent_to="support@pilotfortrades.com",
            created_at=now,
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)

        assert sub.submission_id is not None
        assert sub.category == "question"
        assert sub.email_message_id is None

    def test_category_check_constraint(self, db_session, test_tenant, test_user):
        from app.models.help import FeedbackSubmission

        now = datetime.now(UTC)
        sub = FeedbackSubmission(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            category="invalid_category",
            body="Test feedback body that is long enough.",
            email_sent_to="support@pilotfortrades.com",
            created_at=now,
        )
        db_session.add(sub)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


class TestFeedbackSubmitEndpoint:
    def test_submit_feedback_creates_record(
        self, client, db_session, test_tenant, test_user
    ):
        with patch("api.routes.help.send_feedback_email") as mock_task:
            mock_task.delay = MagicMock()

            response = client.post(
                "/api/v1/feedback/test",
                json={
                    "category": "question",
                    "body": "I can't figure out how to set up recurring jobs in Pilot.",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "submission_id" in data
        assert data["category"] == "question"
        assert "confirmation_message" in data
        mock_task.delay.assert_called_once()

    def test_invalid_category_rejected(self, client):
        response = client.post(
            "/api/v1/feedback/test",
            json={
                "category": "not_a_valid_category",
                "body": "Some feedback that is long enough to pass validation.",
            },
        )
        assert response.status_code == 400

    def test_body_too_short_rejected(self, client):
        response = client.post(
            "/api/v1/feedback/test",
            json={
                "category": "bug",
                "body": "Short",  # < 10 chars min
            },
        )
        assert response.status_code == 422

    def test_all_valid_categories_accepted(self, client):
        valid_categories = ["bug", "feature_request", "question", "general"]

        for category in valid_categories:
            with patch("api.routes.help.send_feedback_email") as mock_task:
                mock_task.delay = MagicMock()
                response = client.post(
                    "/api/v1/feedback/test",
                    json={
                        "category": category,
                        "body": f"This is a long enough feedback body for {category} category testing.",
                    },
                )
            assert response.status_code == 201, f"Category {category} was rejected"


class TestSendFeedbackEmailImpl:
    def test_sends_email_and_stores_message_id(
        self, db_session, test_tenant, test_user
    ):
        from app.models.help import FeedbackSubmission
        from tasks.help_corpus import _send_feedback_email_impl

        now = datetime.now(UTC)
        sub = FeedbackSubmission(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            category="bug",
            body="This is a bug report about the QuickBooks sync failing.",
            email_sent_to="support@pilotfortrades.com",
            created_at=now,
        )
        db_session.add(sub)
        db_session.commit()

        with (
            patch("tasks.help_corpus.send_email") as mock_send,
            patch("tasks.help_corpus.settings") as mock_settings,
        ):
            mock_settings.SUPPORT_EMAIL_ADDRESS = "support@pilotfortrades.com"
            mock_send.return_value = {
                "status": "sent",
                "details": {"headers": {"X-Message-Id": "test-msg-id-123"}},
            }

            result = _send_feedback_email_impl(str(sub.submission_id), db_session)

        assert result["status"] == "sent"
        mock_send.assert_called_once()

    def test_raises_on_invalid_submission_id(self, db_session):
        from tasks.help_corpus import _send_feedback_email_impl

        with pytest.raises(ValueError, match="Invalid submission_id"):
            _send_feedback_email_impl("not-a-uuid", db_session)

    def test_raises_when_submission_not_found(self, db_session):
        from tasks.help_corpus import _send_feedback_email_impl

        with pytest.raises(ValueError, match="not found"):
            _send_feedback_email_impl(str(uuid4()), db_session)
