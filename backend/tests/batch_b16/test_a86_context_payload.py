"""
A86 — Contextual Help Anchor Metadata tests.

Test focus:
- HelpContextPayload schema accepts all optional fields
- HelpContextPayload schema validates correctly
- context_payload stored on help_chat_message correctly
- pii_anonymizer.anonymize_context_payload strips PII appropriately
"""

from api.schemas.help import HelpContextPayload


class TestHelpContextPayloadSchema:
    def test_all_fields_optional(self):
        """HelpContextPayload with no fields should be valid."""
        payload = HelpContextPayload()
        assert payload.route is None
        assert payload.entity_type is None
        assert payload.recent_actions is None
        assert payload.user_role is None
        assert payload.tenant_metadata is None

    def test_full_payload_valid(self):
        payload = HelpContextPayload(
            route="/settings/integrations/quickbooks",
            entity_type=None,
            recent_actions=["opened_settings", "viewed_qb_conflict"],
            user_role="owner",
            tenant_metadata={"size": "small", "trade": "electrical"},
        )
        assert payload.route == "/settings/integrations/quickbooks"
        assert "owner" == payload.user_role
        assert len(payload.recent_actions) == 2

    def test_serializes_to_dict(self):
        payload = HelpContextPayload(
            route="/jobs",
            user_role="technician",
        )
        d = payload.model_dump(exclude_none=True)
        assert d["route"] == "/jobs"
        assert d["user_role"] == "technician"
        assert "entity_type" not in d


class TestContextPayloadAnonymizer:
    def test_anonymize_context_payload_strips_query_params(self):
        from services.pii_anonymizer import anonymize_context_payload

        payload = {
            "route": "/jobs/abc123?token=supersecret",
            "user_role": "owner",
        }
        result = anonymize_context_payload(payload)
        assert "supersecret" not in result["route"]
        assert result["route"] == "/jobs/abc123"

    def test_anonymize_context_payload_retains_safe_tenant_metadata(self):
        from services.pii_anonymizer import anonymize_context_payload

        payload = {
            "route": "/settings",
            "tenant_metadata": {
                "size": "small",
                "trade": "electrical",
                "owner_email": "mike@example.com",  # PII — should be stripped
            },
        }
        result = anonymize_context_payload(payload)
        assert "size" in result["tenant_metadata"]
        assert "trade" in result["tenant_metadata"]
        assert "owner_email" not in result["tenant_metadata"]

    def test_anonymize_context_payload_handles_none(self):
        from services.pii_anonymizer import anonymize_context_payload

        result = anonymize_context_payload(None)
        assert result is None

    def test_anonymize_context_payload_handles_empty(self):
        from services.pii_anonymizer import anonymize_context_payload

        result = anonymize_context_payload({})
        assert result == {}


class TestContextPayloadStoredOnMessage:
    def test_context_payload_persisted_on_user_message(
        self, db_session, test_tenant, test_user
    ):
        from datetime import UTC, datetime

        from app.models.help import HelpChatMessage, HelpChatSession

        now = datetime.now(UTC)
        session = HelpChatSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            started_at=now,
            last_activity_at=now,
            message_count=0,
            created_at=now,
            updated_at=now,
        )
        db_session.add(session)
        db_session.flush()

        context = {
            "route": "/settings/integrations/quickbooks",
            "user_role": "owner",
            "recent_actions": ["opened_settings"],
        }

        msg = HelpChatMessage(
            # FIND-169: session.session_id → session.id
            session_id=session.id,
            tenant_id=test_tenant.id,
            role="user",
            content="How do I connect QuickBooks?",
            context_payload=context,
            voice_used=False,
            created_at=now,
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.context_payload is not None
        assert msg.context_payload["route"] == "/settings/integrations/quickbooks"
        assert msg.context_payload["user_role"] == "owner"
