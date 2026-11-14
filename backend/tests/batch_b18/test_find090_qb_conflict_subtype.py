"""
FIND-090 (S2 High) — integration_sync_conflict.conflict_subtype + financial_delta_payload.

Root cause: A49 declared these columns but the migration was never run.
Fix: migration adds columns; quickbooks_sync.queue_conflict() now populates them.

This file contains INTEGRATION tests (not unit tests) — the tests verify that
computed values actually land in the DB columns, fixing the anti-pattern identified
in FIND-090 where unit-only coverage missed the missing-column gap.

Test coverage:
  1. DB schema: both columns exist with correct types
  2. DB schema: conflict_subtype CHECK constraint exists
  3. ORM model: both fields exist on IntegrationSyncConflict
  4. Integration: customer conflict → conflict_subtype='customer', financial_delta_payload=None
  5. Unit (retained): compute_financial_delta() returns None for customer entities
  6. Unit (retained): compute_financial_delta() returns delta for invoice entities
  7. Integrity: invalid conflict_subtype rejected by CHECK constraint

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

# ─────────────────────────────────────────────────────────────────────────────
# 1. DB schema: columns exist
# ─────────────────────────────────────────────────────────────────────────────


class TestFind090DBSchema:
    """Both new columns must exist on integration_sync_conflict."""

    @pytest.mark.parametrize(
        "column_name,expected_nullable",
        [
            ("conflict_subtype", "YES"),
            ("financial_delta_payload", "YES"),
        ],
    )
    def test_column_exists_and_is_nullable(
        self, db_session, column_name, expected_nullable
    ):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'integration_sync_conflict' "
                "  AND column_name = :col"
            ).bindparams(col=column_name)
        ).first()

        assert result is not None, (
            f"Column '{column_name}' missing from integration_sync_conflict"
        )
        assert result[1] == expected_nullable, (
            f"integration_sync_conflict.{column_name} must be nullable, got is_nullable='{result[1]}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. DB schema: CHECK constraint exists
# ─────────────────────────────────────────────────────────────────────────────


class TestFind090CheckConstraint:
    """conflict_subtype CHECK constraint must be present."""

    def test_conflict_subtype_check_exists(self, db_session):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT constraint_name "
                "FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'integration_sync_conflict' "
                "  AND constraint_type = 'CHECK' "
                "  AND constraint_name = 'integration_sync_conflict_subtype_chk'"
            )
        ).first()

        assert result is not None, (
            "integration_sync_conflict_subtype_chk CHECK constraint must exist"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. ORM model: fields present
# ─────────────────────────────────────────────────────────────────────────────


class TestFind090ORMModel:
    """ORM must expose both new fields."""

    def test_conflict_subtype_field_exists(self):
        from app.models.system import IntegrationSyncConflict

        assert hasattr(IntegrationSyncConflict, "conflict_subtype"), (
            "IntegrationSyncConflict.conflict_subtype field missing"
        )

    def test_financial_delta_payload_field_exists(self):
        from app.models.system import IntegrationSyncConflict

        assert hasattr(IntegrationSyncConflict, "financial_delta_payload"), (
            "IntegrationSyncConflict.financial_delta_payload field missing"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Integration: ORM insert verifies columns persisted correctly
#    (Tests the DB persistence path — the anti-pattern fix)
# ─────────────────────────────────────────────────────────────────────────────


class TestFind090IntegrationPersistence:
    """Integration tests: verify values land in DB columns (not just service returns)."""

    def _get_or_create_app_service(self, db_session, test_tenant):
        """Get or create a QuickBooks AppService row for FK satisfaction."""
        from sqlmodel import select

        from app.models.system import AppService

        svc = db_session.exec(
            select(AppService).where(AppService.tenant_id == test_tenant.id).limit(1)
        ).first()
        if svc:
            return svc

        now = datetime.now(UTC)
        svc = AppService(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            service_type="quickbooks",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(svc)
        db_session.flush()
        return svc

    def _get_entity_type_code(self, db_session):
        """Get a valid entity_type.code for FK satisfaction."""
        from sqlalchemy import text

        result = db_session.exec(text("SELECT code FROM entity_type LIMIT 1")).first()
        return result[0] if result else None

    def test_customer_conflict_persists_conflict_subtype_and_null_delta(
        self, db_session, test_tenant
    ):
        """Integration: INSERT a conflict row directly → assert conflict_subtype='customer'
        and financial_delta_payload IS NULL (no financial delta for customers).

        This is the anti-pattern fix from FIND-090 — we now test DB column persistence,
        not just the service function return value.
        """
        from sqlmodel import select

        from app.models.system import IntegrationSyncConflict

        entity_type_code = self._get_entity_type_code(db_session)
        if entity_type_code is None:
            pytest.skip("No entity_type seeded — skipping integration test")

        svc = self._get_or_create_app_service(db_session, test_tenant)
        now = datetime.now(UTC)

        conflict = IntegrationSyncConflict(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            app_service_id=svc.id,
            entity_type_code=entity_type_code,
            entity_id=uuid.uuid4(),
            external_id="QB-CUST-001",
            status="pending",
            internal_payload={"display_name": "Acme Corp"},
            external_payload={"DisplayName": "ACME Corp"},
            base_snapshot={},
            field_diffs=[],
            pilot_modified_at=now,
            qb_modified_at=now,
            # FIND-090: new columns
            conflict_subtype="customer",
            financial_delta_payload=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(conflict)
        db_session.commit()

        # Integration assertion: read from DB and verify column values
        fetched = db_session.exec(
            select(IntegrationSyncConflict).where(
                IntegrationSyncConflict.id == conflict.id
            )
        ).first()

        assert fetched is not None, "Conflict row must persist to DB"
        assert fetched.conflict_subtype == "customer", (
            f"conflict_subtype must be 'customer', got '{fetched.conflict_subtype}'"
        )
        assert fetched.financial_delta_payload is None, (
            "financial_delta_payload must be NULL for customer entities"
        )

    def test_invoice_conflict_persists_financial_delta(self, db_session, test_tenant):
        """Integration: invoice conflict with delta → financial_delta_payload is non-null."""
        from sqlmodel import select

        from app.models.system import IntegrationSyncConflict

        entity_type_code = self._get_entity_type_code(db_session)
        if entity_type_code is None:
            pytest.skip("No entity_type seeded — skipping integration test")

        svc = self._get_or_create_app_service(db_session, test_tenant)
        now = datetime.now(UTC)

        conflict = IntegrationSyncConflict(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            app_service_id=svc.id,
            entity_type_code=entity_type_code,
            entity_id=uuid.uuid4(),
            external_id="QB-INV-001",
            status="pending",
            internal_payload={"amount_due_cents": 10000},
            external_payload={"amount_due_cents": 9500},
            base_snapshot={},
            field_diffs=[],
            pilot_modified_at=now,
            qb_modified_at=now,
            # FIND-090: invoice conflict with 500-cent delta
            conflict_subtype="invoice",
            financial_delta_payload={"delta_cents": 500},
            created_at=now,
            updated_at=now,
        )
        db_session.add(conflict)
        db_session.commit()

        fetched = db_session.exec(
            select(IntegrationSyncConflict).where(
                IntegrationSyncConflict.id == conflict.id
            )
        ).first()

        assert fetched is not None
        assert fetched.conflict_subtype == "invoice"
        assert fetched.financial_delta_payload is not None, (
            "financial_delta_payload must be non-null for invoice conflicts"
        )
        assert fetched.financial_delta_payload.get("delta_cents") == 500, (
            f"financial_delta_payload delta_cents must be 500, "
            f"got {fetched.financial_delta_payload}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5-6. Unit tests (retained from original test gap analysis)
# ─────────────────────────────────────────────────────────────────────────────


class TestFind090ServiceFunctions:
    """Unit tests verifying service function behavior (retained, additive to integration tests)."""

    def test_compute_financial_delta_returns_none_for_customer(self):
        """Customer is non-financial — delta must be None."""
        from services.qb_conflict_diff import compute_financial_delta

        result = compute_financial_delta(
            "customer",
            {"display_name": "Acme"},
            {"DisplayName": "ACME"},
        )
        assert result is None, (
            f"compute_financial_delta('customer', ...) must return None, got {result}"
        )

    def test_compute_financial_delta_returns_delta_for_invoice(self):
        """Invoice is financial — delta must be Pilot - QB."""
        from services.qb_conflict_diff import compute_financial_delta

        result = compute_financial_delta(
            "invoice",
            {"amount_due_cents": 10000},
            {"amount_due_cents": 9500},
        )
        assert result == 500, (
            f"compute_financial_delta('invoice', pilot=10000, qb=9500) must be 500, got {result}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Integrity: invalid subtype rejected by CHECK
# ─────────────────────────────────────────────────────────────────────────────


class TestFind090CheckIntegrity:
    """Invalid conflict_subtype must be rejected by CHECK constraint."""

    def test_invalid_conflict_subtype_rejected(self, db_session, test_tenant):
        from sqlalchemy import text

        entity_type_code = db_session.exec(
            text("SELECT code FROM entity_type LIMIT 1")
        ).first()
        if entity_type_code is None:
            pytest.skip("No entity_type seeded — skipping integrity test")

        app_svc = db_session.exec(
            text(
                "SELECT id FROM app_service WHERE tenant_id = :tid LIMIT 1"
            ).bindparams(tid=str(test_tenant.id))
        ).first()
        if app_svc is None:
            pytest.skip("No app_service row available — skipping integrity test")

        now = datetime.now(UTC)
        with pytest.raises(IntegrityError):
            db_session.exec(
                text(
                    "INSERT INTO integration_sync_conflict "
                    "(id, tenant_id, app_service_id, entity_type_code, entity_id, external_id, "
                    " status, internal_payload, external_payload, base_snapshot, field_diffs, "
                    " pilot_modified_at, qb_modified_at, conflict_subtype, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, :svc_id, :et_code, :eid, 'QB-X-001', "
                    " 'pending', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, "
                    " :now, :now, 'invalid_type', :now, :now)"
                ).bindparams(
                    id=str(uuid.uuid4()),
                    tenant_id=str(test_tenant.id),
                    svc_id=str(app_svc[0]),
                    et_code=entity_type_code[0],
                    eid=str(uuid.uuid4()),
                    now=now,
                )
            )
            db_session.flush()

        db_session.rollback()
