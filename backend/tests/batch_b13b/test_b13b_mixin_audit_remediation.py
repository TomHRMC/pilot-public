"""
B13b — Mixin Audit Remediation Tests
======================================
Covers all 6 remediation items:

Item 1: customer_communication_message → StandardAuditMixin
  - ORM has created_by, updated_by attributes from mixin
  - DB columns created_by, updated_by exist and are nullable UUID

Item 2: customer_communication_message_read_state → AppendOnlyMixin
  - ORM has created_at, created_by attributes from mixin
  - DB columns created_at, created_by exist; created_at NOT NULL, created_by nullable

Item 3: customer_communication_unrouted → StandardAuditMixin
  - ORM has created_by, updated_by attributes from mixin
  - DB columns created_by, updated_by exist and are nullable UUID

Item 4: sms_quota_period → StandardAuditMixin
  - ORM has created_by, updated_by attributes from mixin
  - DB columns created_by, updated_by exist and are nullable UUID

Item 5: mobile_push_rate_limit → StandardAuditMixin
  - ORM has created_by, updated_by attributes from mixin
  - DB columns created_by, updated_by exist and are nullable UUID

Item 6: mobile_sync_event_audit → AppendOnlyMixin
  - ORM has created_at, created_by attributes from mixin
  - DB columns created_at, created_by exist; created_at NOT NULL, created_by nullable
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import Session

from app.models.mixins import AppendOnlyMixin, StandardAuditMixin
from app.models.sms import (
    CustomerCommunicationMessage,
    CustomerCommunicationMessageReadState,
    CustomerCommunicationUnrouted,
    SmsQuotaPeriod,
)
from app.models.sync import MobilePushRateLimit, MobileSyncEventAudit

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_column_info(db_session: Session, table_name: str, column_name: str) -> dict:
    """Query live DB for column metadata."""
    result = db_session.execute(
        text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = :table AND column_name = :col
        """),
        {"table": table_name, "col": column_name},
    ).fetchone()
    return dict(result._mapping) if result else {}


# ─── Item 1: customer_communication_message ───────────────────────────────────


class TestCustomerCommunicationMessageAuditMixin:
    """B13b Item 1 — Gap Type 1: StandardAuditMixin added."""

    def test_model_inherits_standard_audit_mixin(self):
        """CustomerCommunicationMessage must inherit StandardAuditMixin."""
        assert issubclass(CustomerCommunicationMessage, StandardAuditMixin)

    def test_model_has_created_by_attribute(self):
        """ORM model must expose created_by from mixin."""
        assert hasattr(CustomerCommunicationMessage, "created_by")

    def test_model_has_updated_by_attribute(self):
        """ORM model must expose updated_by from mixin."""
        assert hasattr(CustomerCommunicationMessage, "updated_by")

    def test_model_has_standard_timestamps(self):
        """ORM model must still have created_at and updated_at from mixin."""
        assert hasattr(CustomerCommunicationMessage, "created_at")
        assert hasattr(CustomerCommunicationMessage, "updated_at")

    def test_db_column_created_by_exists_and_is_nullable(self, db_session):
        """DB column created_by must be UUID and nullable."""
        col = _get_column_info(
            db_session, "customer_communication_message", "created_by"
        )
        assert col, "created_by column not found in customer_communication_message"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_column_updated_by_exists_and_is_nullable(self, db_session):
        """DB column updated_by must be UUID and nullable."""
        col = _get_column_info(
            db_session, "customer_communication_message", "updated_by"
        )
        assert col, "updated_by column not found in customer_communication_message"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_existing_timestamps_still_present(self, db_session):
        """Pre-existing created_at and updated_at must still be present after migration."""
        for col_name in ("created_at", "updated_at"):
            col = _get_column_info(
                db_session, "customer_communication_message", col_name
            )
            assert col, f"{col_name} column missing from customer_communication_message"
            assert col["data_type"] == "timestamp with time zone"


# ─── Item 2: customer_communication_message_read_state ────────────────────────


class TestCustomerCommunicationMessageReadStateAuditMixin:
    """B13b Item 2 — Gap Type 2: AppendOnlyMixin added (full set)."""

    def test_model_inherits_append_only_mixin(self):
        """CustomerCommunicationMessageReadState must inherit AppendOnlyMixin."""
        assert issubclass(CustomerCommunicationMessageReadState, AppendOnlyMixin)

    def test_model_has_created_at_attribute(self):
        """ORM model must expose created_at from AppendOnlyMixin."""
        assert hasattr(CustomerCommunicationMessageReadState, "created_at")

    def test_model_has_created_by_attribute(self):
        """ORM model must expose created_by from AppendOnlyMixin."""
        assert hasattr(CustomerCommunicationMessageReadState, "created_by")

    def test_model_does_not_have_updated_by(self):
        """AppendOnly tables must NOT have updated_by."""
        # updated_by should not be added by AppendOnlyMixin
        assert not hasattr(CustomerCommunicationMessageReadState, "updated_by")

    def test_db_column_created_at_exists_not_null(self, db_session):
        """DB column created_at must be TIMESTAMPTZ NOT NULL."""
        col = _get_column_info(
            db_session, "customer_communication_message_read_state", "created_at"
        )
        assert col, (
            "created_at column not found in customer_communication_message_read_state"
        )
        assert col["data_type"] == "timestamp with time zone"
        assert col["is_nullable"] == "NO"

    def test_db_column_created_by_exists_and_is_nullable(self, db_session):
        """DB column created_by must be UUID and nullable."""
        col = _get_column_info(
            db_session, "customer_communication_message_read_state", "created_by"
        )
        assert col, (
            "created_by column not found in customer_communication_message_read_state"
        )
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_existing_read_at_still_present(self, db_session):
        """Pre-existing read_at domain column must still be present (not renamed)."""
        col = _get_column_info(
            db_session, "customer_communication_message_read_state", "read_at"
        )
        assert col, "read_at column missing — must not be renamed or removed"

    def test_db_guard_trigger_installed(self, db_session):
        """guard_created_fields_immutable trigger must be installed for AppendOnly."""
        result = db_session.execute(
            text("""
                SELECT trigger_name FROM information_schema.triggers
                WHERE event_object_table = 'customer_communication_message_read_state'
                AND trigger_name = 'trg_customer_communication_message_read_state_guard_created_immutable'
            """)
        ).fetchone()
        assert result is not None, "guard_created_immutable trigger missing"

    def test_db_audit_trigger_installed(self, db_session):
        """audit.log_changes trigger must be installed for AppendOnly."""
        result = db_session.execute(
            text("""
                SELECT trigger_name FROM information_schema.triggers
                WHERE event_object_table = 'customer_communication_message_read_state'
                AND trigger_name = 'audit_customer_communication_message_read_state_changes'
            """)
        ).fetchone()
        assert result is not None, "audit_changes trigger missing"


# ─── Item 3: customer_communication_unrouted ──────────────────────────────────


class TestCustomerCommunicationUnroutedAuditMixin:
    """B13b Item 3 — Gap Type 1: StandardAuditMixin added."""

    def test_model_inherits_standard_audit_mixin(self):
        assert issubclass(CustomerCommunicationUnrouted, StandardAuditMixin)

    def test_model_has_created_by_attribute(self):
        assert hasattr(CustomerCommunicationUnrouted, "created_by")

    def test_model_has_updated_by_attribute(self):
        assert hasattr(CustomerCommunicationUnrouted, "updated_by")

    def test_db_column_created_by_exists_and_is_nullable(self, db_session):
        col = _get_column_info(
            db_session, "customer_communication_unrouted", "created_by"
        )
        assert col, "created_by column not found in customer_communication_unrouted"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_column_updated_by_exists_and_is_nullable(self, db_session):
        col = _get_column_info(
            db_session, "customer_communication_unrouted", "updated_by"
        )
        assert col, "updated_by column not found in customer_communication_unrouted"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_domain_column_resolved_by_still_present(self, db_session):
        """resolved_by domain column must not be confused with or replaced by created_by."""
        col = _get_column_info(
            db_session, "customer_communication_unrouted", "resolved_by"
        )
        assert col, "resolved_by domain column missing — must not be removed"


# ─── Item 4: sms_quota_period ─────────────────────────────────────────────────


class TestSmsQuotaPeriodAuditMixin:
    """B13b Item 4 — Gap Type 1: StandardAuditMixin added."""

    def test_model_inherits_standard_audit_mixin(self):
        assert issubclass(SmsQuotaPeriod, StandardAuditMixin)

    def test_model_has_created_by_attribute(self):
        assert hasattr(SmsQuotaPeriod, "created_by")

    def test_model_has_updated_by_attribute(self):
        assert hasattr(SmsQuotaPeriod, "updated_by")

    def test_db_column_created_by_exists_and_is_nullable(self, db_session):
        col = _get_column_info(db_session, "sms_quota_period", "created_by")
        assert col, "created_by column not found in sms_quota_period"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_column_updated_by_exists_and_is_nullable(self, db_session):
        col = _get_column_info(db_session, "sms_quota_period", "updated_by")
        assert col, "updated_by column not found in sms_quota_period"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_existing_timestamps_still_present(self, db_session):
        """created_at and updated_at must still exist after migration."""
        for col_name in ("created_at", "updated_at"):
            col = _get_column_info(db_session, "sms_quota_period", col_name)
            assert col, f"{col_name} column missing from sms_quota_period"

    def test_created_by_nullable_on_insert(self, db_session, test_tenant):
        """Machine-managed rows can have NULL created_by — must not fail NOT NULL."""
        from datetime import timedelta

        now = datetime.now(UTC)
        period = SmsQuotaPeriod(
            tenant_id=test_tenant.id,
            period_start=now - timedelta(days=1),
            period_end=now + timedelta(days=29),
            included_segments=100,
            used_segments=0,
            cap_policy="soft",
            # created_by intentionally omitted — must be NULL
        )
        db_session.add(period)
        db_session.commit()
        db_session.refresh(period)
        assert period.created_by is None
        assert period.updated_by is None


# ─── Item 5: mobile_push_rate_limit ───────────────────────────────────────────


class TestMobilePushRateLimitAuditMixin:
    """B13b Item 5 — Gap Type 1: StandardAuditMixin added."""

    def test_model_inherits_standard_audit_mixin(self):
        assert issubclass(MobilePushRateLimit, StandardAuditMixin)

    def test_model_has_created_by_attribute(self):
        assert hasattr(MobilePushRateLimit, "created_by")

    def test_model_has_updated_by_attribute(self):
        assert hasattr(MobilePushRateLimit, "updated_by")

    def test_db_column_created_by_exists_and_is_nullable(self, db_session):
        col = _get_column_info(db_session, "mobile_push_rate_limit", "created_by")
        assert col, "created_by column not found in mobile_push_rate_limit"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_column_updated_by_exists_and_is_nullable(self, db_session):
        col = _get_column_info(db_session, "mobile_push_rate_limit", "updated_by")
        assert col, "updated_by column not found in mobile_push_rate_limit"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_existing_timestamps_still_present(self, db_session):
        for col_name in ("created_at", "updated_at"):
            col = _get_column_info(db_session, "mobile_push_rate_limit", col_name)
            assert col, f"{col_name} column missing from mobile_push_rate_limit"

    def test_created_by_nullable_on_insert(self, db_session, test_tenant):
        """Machine-managed rows can have NULL created_by."""
        rate_limit = MobilePushRateLimit(
            tenant_id=test_tenant.id,
            device_id=uuid.uuid4(),
            last_push_sent_at=datetime.now(UTC),
            push_count_current_window=1,
            window_start_at=datetime.now(UTC),
            # created_by intentionally omitted
        )
        db_session.add(rate_limit)
        db_session.commit()
        db_session.refresh(rate_limit)
        assert rate_limit.created_by is None
        assert rate_limit.updated_by is None


# ─── Item 6: mobile_sync_event_audit ─────────────────────────────────────────


class TestMobileSyncEventAuditAuditMixin:
    """B13b Item 6 — Gap Type 2: AppendOnlyMixin added (full set)."""

    def test_model_inherits_append_only_mixin(self):
        assert issubclass(MobileSyncEventAudit, AppendOnlyMixin)

    def test_model_has_created_at_attribute(self):
        assert hasattr(MobileSyncEventAudit, "created_at")

    def test_model_has_created_by_attribute(self):
        assert hasattr(MobileSyncEventAudit, "created_by")

    def test_model_does_not_have_updated_by(self):
        """AppendOnly tables must NOT have updated_by."""
        assert not hasattr(MobileSyncEventAudit, "updated_by")

    def test_db_column_created_at_exists_not_null(self, db_session):
        col = _get_column_info(db_session, "mobile_sync_event_audit", "created_at")
        assert col, "created_at column not found in mobile_sync_event_audit"
        assert col["data_type"] == "timestamp with time zone"
        assert col["is_nullable"] == "NO"

    def test_db_column_created_by_exists_and_is_nullable(self, db_session):
        col = _get_column_info(db_session, "mobile_sync_event_audit", "created_by")
        assert col, "created_by column not found in mobile_sync_event_audit"
        assert col["data_type"] == "uuid"
        assert col["is_nullable"] == "YES"

    def test_db_existing_resolved_at_still_present(self, db_session):
        """resolved_at domain column must not be removed (both coexist per F3 decision)."""
        col = _get_column_info(db_session, "mobile_sync_event_audit", "resolved_at")
        assert col, "resolved_at domain column missing — must coexist with created_at"

    def test_db_guard_trigger_installed(self, db_session):
        result = db_session.execute(
            text("""
                SELECT trigger_name FROM information_schema.triggers
                WHERE event_object_table = 'mobile_sync_event_audit'
                AND trigger_name = 'trg_mobile_sync_event_audit_guard_created_immutable'
            """)
        ).fetchone()
        assert result is not None, (
            "guard_created_immutable trigger missing on mobile_sync_event_audit"
        )

    def test_db_audit_trigger_installed(self, db_session):
        result = db_session.execute(
            text("""
                SELECT trigger_name FROM information_schema.triggers
                WHERE event_object_table = 'mobile_sync_event_audit'
                AND trigger_name = 'audit_mobile_sync_event_audit_changes'
            """)
        ).fetchone()
        assert result is not None, (
            "audit_changes trigger missing on mobile_sync_event_audit"
        )
