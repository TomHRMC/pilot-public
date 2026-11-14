"""
Test Suite: Phase 6.0.1 Task 7 - Integration & Sync Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: phase-6.0-db-schema-sync-11-plan.md - Task 7
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""

    def test_connector_config_created_by_fk_enforcement(
        self, db_session, test_supplier
    ):
        """Test that invalid created_by user ID is rejected"""
        from app.models.system import ConnectorConfig

        invalid_user_id = uuid.uuid4()
        connector = ConnectorConfig(
            supplier_id=test_supplier.id, mode="api", created_by=invalid_user_id
        )
        db_session.add(connector)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_connector_config_created_by" in str(exc_info.value)
        db_session.rollback()


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""

    def test_connector_config_updated_by_fk_enforcement(
        self, db_session, test_supplier, test_user
    ):
        """Test that invalid updated_by user ID is rejected"""
        from app.models.system import ConnectorConfig

        # Create valid record
        connector = ConnectorConfig(
            supplier_id=test_supplier.id, mode="api", created_by=test_user.id
        )
        db_session.add(connector)
        db_session.commit()

        # Attempt to update with invalid user ID
        invalid_user_id = uuid.uuid4()
        connector.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_connector_config_updated_by" in str(exc_info.value)
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""

    def test_user_deletion_blocked_by_connector_config_audit(
        self, db_session, test_supplier
    ):
        """Test ON DELETE RESTRICT behavior"""
        from app.models.core import User
        from app.models.system import ConnectorConfig

        # Create a fresh user with NO other dependencies
        fresh_user = User(
            email="fresh_test_user@example.com",
            auth_provider="local",
            auth_provider_id="local|fresh",
            is_active=True,
        )
        db_session.add(fresh_user)
        db_session.commit()

        # Create record with user audit reference
        connector = ConnectorConfig(
            supplier_id=test_supplier.id, mode="api", created_by=fresh_user.id
        )
        db_session.add(connector)
        db_session.commit()

        # Attempt to delete user (should fail due to RESTRICT)
        db_session.delete(fresh_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_connector_config_created_by" in str(exc_info.value)
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""

    def test_connector_config_null_audit_columns(self, db_session, test_supplier):
        """Test that NULL created_by and updated_by are allowed"""
        from app.models.system import ConnectorConfig

        # Create record with NULL audit columns
        connector = ConnectorConfig(
            supplier_id=test_supplier.id, mode="api", created_by=None, updated_by=None
        )
        db_session.add(connector)
        db_session.commit()  # Should succeed

        assert connector.created_by is None
        assert connector.updated_by is None
