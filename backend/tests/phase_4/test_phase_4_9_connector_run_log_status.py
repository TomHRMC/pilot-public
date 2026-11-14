"""
Test Suite: Phase 4.9 Task 1 - Normalize connector_run_log Status Values
Tests CHECK constraint value alignment with JSON schema

Reference: phase-4.9-db-schema-sync-5-plan.md
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.system import ConnectorRunLog


class TestConnectorRunLogStatusConstraint:
    """Test updated connector_run_log CHECK constraint"""

    def test_connector_run_log_valid_statuses(self, db_session: Session, test_supplier):
        """Verify all JSON-defined status values are accepted"""
        # Test all valid statuses from JSON schema
        for status in ["running", "success", "failed"]:
            obj = ConnectorRunLog(supplier_id=test_supplier.id, status=status)
            db_session.add(obj)
            db_session.commit()

            # Verify it was saved with correct status
            assert obj.status == status

            # Clean up
            db_session.delete(obj)
            db_session.commit()

    def test_connector_run_log_rejects_legacy_statuses(
        self, db_session: Session, test_supplier
    ):
        """Verify legacy status values are rejected"""
        # Capture supplier_id before the loop to avoid stale object issues after rollback
        supplier_id = test_supplier.id

        # Test legacy statuses are rejected
        for legacy_status in ["completed", "cancelled"]:
            obj = ConnectorRunLog(
                supplier_id=supplier_id,
                status=legacy_status,  # type: ignore
            )
            with pytest.raises(IntegrityError) as exc_info:
                db_session.add(obj)
                db_session.commit()
            assert "connector_run_log_status_chk" in str(exc_info.value).lower()
            db_session.rollback()

    def test_connector_run_log_default_status(self, db_session: Session, test_supplier):
        """Verify default status value"""
        obj = ConnectorRunLog(
            supplier_id=test_supplier.id,
            # Don't set status - let default apply
        )
        db_session.add(obj)
        db_session.commit()

        assert obj.status == "running"
