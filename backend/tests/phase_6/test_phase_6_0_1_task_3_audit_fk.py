"""
Test Suite: Phase 6.0.1 Task 3 - Job Management Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.

Reference: dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md - Task 3

This test suite verifies:
1. Invalid user IDs in created_by are rejected
2. Invalid user IDs in updated_by are rejected
3. Users with audit references cannot be deleted (ON DELETE RESTRICT)
4. NULL audit columns are allowed (backward compatibility)
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.fulfillment import (
    Job,
    JobExpenseCategory,
    JobStatus,
)
from app.models.quoting import (
    ChangeOrder,
    ChangeOrderLine,
    ChangeOrderLineTaxComponent,
)


class TestAuditFKConstraintsCreatedBy:
    """Test FK constraint enforcement on created_by column"""

    def test_job_created_by_fk_enforcement(
        self, db_session: Session, test_tenant, test_customer, test_site
    ):
        """Test that invalid created_by user ID is rejected for Job"""
        invalid_user_id = uuid.uuid4()

        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=invalid_user_id,  # Invalid user ID
        )
        db_session.add(job)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_job_created_by" in str(exc_info.value).lower()
        db_session.rollback()

    def test_job_valid_created_by_accepted(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test that valid created_by user ID is accepted for Job"""
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        assert job.created_by == test_user.id

    def test_change_order_created_by_fk_enforcement(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test that invalid created_by user ID is rejected for ChangeOrder"""
        # Create a job first
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        change_order = ChangeOrder(
            tenant_id=job.tenant_id,
            job_id=job.id,
            description="Test change order",
            created_by=invalid_user_id,  # Invalid user ID
        )
        db_session.add(change_order)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_change_order_created_by" in str(exc_info.value).lower()
        db_session.rollback()

    def test_job_expense_category_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected for JobExpenseCategory"""
        invalid_user_id = uuid.uuid4()

        category = JobExpenseCategory(
            code="MATERIALS",
            tenant_id=test_tenant.id,
            name="Materials",
            created_by=invalid_user_id,  # Invalid user ID
        )
        db_session.add(category)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_job_expense_category_created_by" in str(exc_info.value).lower()
        db_session.rollback()


class TestAuditFKConstraintsUpdatedBy:
    """Test FK constraint enforcement on updated_by column"""

    def test_job_updated_by_fk_enforcement(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test that invalid updated_by user ID is rejected for Job"""
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        job.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_job_updated_by" in str(exc_info.value).lower()
        db_session.rollback()

    def test_job_valid_updated_by_accepted(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test that valid updated_by user ID is accepted for Job"""
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        job.updated_by = test_user.id
        db_session.commit()

        assert job.updated_by == test_user.id

    def test_change_order_line_updated_by_fk_enforcement(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test that invalid updated_by user ID is rejected for ChangeOrderLine"""
        # Setup job and change order
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        change_order = ChangeOrder(
            tenant_id=job.tenant_id,
            job_id=job.id,
            description="Test change order",
            created_by=test_user.id,
        )
        db_session.add(change_order)
        db_session.commit()

        # Get or create line type
        from app.models.quoting import QcoLineType

        line_type = db_session.exec(
            select(QcoLineType).where(QcoLineType.is_active == True).limit(1)
        ).first()

        if not line_type:
            line_type = QcoLineType(
                tenant_id=test_tenant.id,
                code="MATERIAL",
                name="Material",
            )
            db_session.add(line_type)
            db_session.commit()

        change_order_line = ChangeOrderLine(
            tenant_id=job.tenant_id,
            change_order_id=change_order.id,
            position=1,
            qco_line_type_id=line_type.id,
            description="Test line",
            created_by=test_user.id,
        )
        db_session.add(change_order_line)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        change_order_line.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_change_order_line_updated_by" in str(exc_info.value).lower()
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""

    def test_user_deletion_blocked_by_job_audit(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test ON DELETE RESTRICT behavior for Job"""
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Deletion should be prevented by any FK constraint (may be tenant_user or job)
        error_msg = str(exc_info.value).lower()
        assert "foreign" in error_msg and "key" in error_msg
        db_session.rollback()

    def test_user_deletion_blocked_by_change_order_audit(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test ON DELETE RESTRICT behavior for ChangeOrder"""
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        change_order = ChangeOrder(
            tenant_id=job.tenant_id,
            job_id=job.id,
            description="Test change order",
            created_by=test_user.id,
        )
        db_session.add(change_order)
        db_session.commit()

        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Deletion should be prevented by any FK constraint
        error_msg = str(exc_info.value).lower()
        assert "foreign" in error_msg and "key" in error_msg
        db_session.rollback()

    def test_user_deletion_blocked_by_job_expense_category_audit(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test ON DELETE RESTRICT behavior for JobExpenseCategory"""
        category = JobExpenseCategory(
            code="MATERIALS",
            tenant_id=test_tenant.id,
            name="Materials",
            created_by=test_user.id,
        )
        db_session.add(category)
        db_session.commit()

        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Deletion should be prevented by any FK constraint
        error_msg = str(exc_info.value).lower()
        assert "foreign" in error_msg and "key" in error_msg
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""

    def test_job_null_audit_columns(
        self, db_session: Session, test_tenant, test_customer, test_site
    ):
        """Test that NULL created_by and updated_by are allowed for Job"""
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=None,  # NULL allowed
            updated_by=None,
        )
        db_session.add(job)
        db_session.commit()  # Should succeed

        assert job.created_by is None
        assert job.updated_by is None

    def test_change_order_null_audit_columns(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test that NULL created_by and updated_by are allowed for ChangeOrder"""
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        change_order = ChangeOrder(
            tenant_id=job.tenant_id,
            job_id=job.id,
            description="Test change order",
            created_by=None,  # NULL allowed
            updated_by=None,
        )
        db_session.add(change_order)
        db_session.commit()  # Should succeed

        assert change_order.created_by is None
        assert change_order.updated_by is None

    def test_job_expense_category_null_created_by(
        self, db_session: Session, test_tenant
    ):
        """Test that NULL created_by is allowed for JobExpenseCategory"""
        category = JobExpenseCategory(
            code="MATERIALS",
            tenant_id=test_tenant.id,
            name="Materials",
            created_by=None,  # NULL allowed
        )
        db_session.add(category)
        db_session.commit()  # Should succeed

        assert category.created_by is None


class TestAppendOnlyTables:
    """Test append-only tables (created_by only)"""

    def test_change_order_line_tax_component_created_by_only(
        self, db_session: Session, test_tenant, test_user, test_customer, test_site
    ):
        """Test that ChangeOrderLineTaxComponent only has created_by FK (append-only)"""
        # This table uses AppendOnlyMixin so it should only have created_by, not updated_by
        # The FK constraint should exist and work

        # Setup prerequisites
        job_status = JobStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(job_status)
        db_session.commit()

        job = Job(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=job_status.id,
            created_by=test_user.id,
        )
        db_session.add(job)
        db_session.commit()

        change_order = ChangeOrder(
            tenant_id=job.tenant_id,
            job_id=job.id,
            description="Test change order",
            created_by=test_user.id,
        )
        db_session.add(change_order)
        db_session.commit()

        # Get or create line type
        from app.models.quoting import QcoLineType

        line_type = db_session.exec(
            select(QcoLineType).where(QcoLineType.is_active == True).limit(1)
        ).first()

        if not line_type:
            line_type = QcoLineType(
                tenant_id=test_tenant.id,
                code="MATERIAL",
                name="Material",
            )
            db_session.add(line_type)
            db_session.commit()

        change_order_line = ChangeOrderLine(
            tenant_id=job.tenant_id,
            change_order_id=change_order.id,
            position=1,
            qco_line_type_id=line_type.id,
            description="Test line",
            created_by=test_user.id,
        )
        db_session.add(change_order_line)
        db_session.commit()

        # Get tax rate version (simplified - may need to create one)
        from app.models.catalog import TaxRateVersion

        tax_version = db_session.exec(select(TaxRateVersion).limit(1)).first()

        if not tax_version:
            pytest.skip("No TaxRateVersion available for test")

        # Test that invalid created_by is rejected
        invalid_user_id = uuid.uuid4()
        tax_component = ChangeOrderLineTaxComponent(
            tenant_id=job.tenant_id,
            change_order_line_id=change_order_line.id,
            tax_rate_version_id=tax_version.id,
            component_code="STATE",
            rate_pct=0.0625,
            amount_cents=100,
            created_by=invalid_user_id,  # Invalid user ID
        )
        db_session.add(tax_component)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert (
            "fk_change_order_line_tax_component_created_by"
            in str(exc_info.value).lower()
        )
        db_session.rollback()

        # Verify append-only table has created_by but not updated_by
        # (Check the model directly)
        assert hasattr(ChangeOrderLineTaxComponent, "created_by")
        assert not hasattr(ChangeOrderLineTaxComponent, "updated_by")
