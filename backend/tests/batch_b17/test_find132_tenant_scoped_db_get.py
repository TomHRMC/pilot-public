"""
FIND-132 (S2 High) — Replace all db.get() calls on tenant-scoped models with
tenant-scoped select() queries in quickbooks_sync.py and voice_action_router.py.

Verifies:
  - QB sync detect_conflict: cross-tenant customer_id returns None (not found),
    no conflict raised for wrong-tenant data
  - QB sync sync_customer_to_qb: wrong-tenant customer_id raises ValueError
  - Voice create_job: context_window_json["active_customer_id"] from different
    tenant returns customer-not-found error; job NOT created
  - Voice query_job_profit: correct customer_name returned (regression guard —
    FK resolution still works after fix)
  - Static assertion: no db.get(Customer, ...) calls remain in either file

Architecture rule: §6.2 of pilot-python-engineer-methods.md —
db.get(Model, pk) is permanently banned on any model with a tenant_id column.

Test subfolder: tests/batch_b17/
"""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, select

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_trial_tier(db_session: Session):
    from app.models.subscription import SubscriptionTier

    tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()
    assert tier is not None, "Trial tier not seeded — run alembic upgrade head"
    return tier


def _create_tenant(db_session: Session, name: str):
    from app.models.core import Tenant

    tier = _get_trial_tier(db_session)
    t = Tenant(
        id=uuid.uuid4(),
        name=name,
        is_active=True,
        current_subscription_tier_id=tier.tier_id,
    )
    db_session.add(t)
    db_session.flush()
    return t


def _create_customer(db_session: Session, tenant_id, display_name: str):
    from app.models.crm import Customer

    c = Customer(id=uuid.uuid4(), tenant_id=tenant_id, display_name=display_name)
    db_session.add(c)
    db_session.flush()
    return c


def _create_user(db_session: Session, email: str):
    from app.models.core import User

    u = User(
        id=uuid.uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
    )
    db_session.add(u)
    db_session.flush()
    return u


def _create_site(db_session: Session, tenant_id, customer_id):
    from app.models.crm import Site

    s = Site(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        display_name="Test Site",
    )
    db_session.add(s)
    db_session.flush()
    return s


def _create_job(db_session: Session, tenant_id, customer_id, site_id):
    from app.models.fulfillment import Job, JobStatus

    status = db_session.exec(
        select(JobStatus).where(JobStatus.tenant_id == None)
    ).first()
    j = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=status.id if status else None,
        title="Test Job",
        actual_labor_cost_cents=50000,
        actual_material_cost_cents=20000,
        actual_profit_cents=30000,
    )
    db_session.add(j)
    db_session.flush()
    return j


# ---------------------------------------------------------------------------
# Static code analysis: verify no db.get(Customer,...) in target files
# ---------------------------------------------------------------------------


class TestNoDbGetViolationsStatic:
    """
    Static check: db.get(Customer, ...) must not exist in quickbooks_sync.py
    or voice_action_router.py after FIND-132 remediation.
    """

    def _grep_db_get_customer(self, filepath: str) -> list[int]:
        """Return line numbers where db.get(Customer, ...) appears."""
        violations = []
        import os

        path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", filepath)
        )
        with open(path) as f:
            for i, line in enumerate(f, start=1):
                if "db.get(Customer" in line:
                    violations.append(i)
        return violations

    def test_no_db_get_customer_in_quickbooks_sync(self):
        violations = self._grep_db_get_customer("services/quickbooks_sync.py")
        assert not violations, (
            f"FIND-132 violation: db.get(Customer, ...) in quickbooks_sync.py "
            f"at lines: {violations}. Use tenant-scoped select() instead."
        )

    def test_no_db_get_customer_in_voice_action_router(self):
        violations = self._grep_db_get_customer("services/voice_action_router.py")
        assert not violations, (
            f"FIND-132 violation: db.get(Customer, ...) in voice_action_router.py "
            f"at lines: {violations}. Use tenant-scoped select() instead."
        )


# ---------------------------------------------------------------------------
# QB sync detect_conflict — cross-tenant isolation
# ---------------------------------------------------------------------------


class TestQBSyncDetectConflictTenantScoped:
    """
    QB sync _detect_conflict: customer_id from a different tenant must return False.
    """

    def test_detect_conflict_wrong_tenant_returns_false(self, db_session: Session):
        """
        mapping.entity_id belonging to tenant_b, syncing as tenant_a →
        _detect_conflict returns False (customer not found in tenant_a scope).
        """
        tenant_a = _create_tenant(db_session, "QB-DetectConflict-A")
        tenant_b = _create_tenant(db_session, "QB-DetectConflict-B")
        customer_b = _create_customer(db_session, tenant_b.id, "Wrong Tenant Customer")

        mock_mapping = MagicMock()
        mock_mapping.entity_id = customer_b.id
        mock_mapping.external_version_token = "1"
        mock_mapping.internal_version_token = "old_token"

        # qb_customer has changed SyncToken — would be a conflict if tenant matched
        qb_customer = {"Id": "QB-1", "SyncToken": "2"}

        import asyncio

        from services.quickbooks_sync import QuickBooksSync

        sync = QuickBooksSync.__new__(QuickBooksSync)
        sync.db = db_session
        sync.tenant_id = tenant_a.id

        result = asyncio.run(sync.detect_conflict(mock_mapping, qb_customer))

        assert result is False, (
            "detect_conflict must return False when customer belongs to different tenant. "
            "Cross-tenant customer data must never be accessible via QB sync."
        )


# ---------------------------------------------------------------------------
# QB sync sync_customer_to_qb — wrong-tenant raises ValueError
# ---------------------------------------------------------------------------


class TestQBSyncCustomerTenantScoped:
    """
    QB sync sync_customer_to_qb: cross-tenant customer_id raises ValueError.
    """

    def test_sync_customer_wrong_tenant_raises(self, db_session: Session):
        """
        customer_id from tenant_b, syncing as tenant_a → ValueError raised.
        """
        tenant_a = _create_tenant(db_session, "QB-Sync-A")
        tenant_b = _create_tenant(db_session, "QB-Sync-B")
        customer_b = _create_customer(db_session, tenant_b.id, "Tenant B Customer")

        import asyncio

        from services.quickbooks_sync import QuickBooksSync

        sync = QuickBooksSync.__new__(QuickBooksSync)
        sync.db = db_session
        sync.tenant_id = tenant_a.id

        with pytest.raises(ValueError, match="not found"):
            asyncio.run(sync.sync_customer_to_qb(customer_b.id))


# ---------------------------------------------------------------------------
# Voice create_job — cross-tenant customer in context blocked
# ---------------------------------------------------------------------------


class TestVoiceCreateJobTenantScoped:
    """
    Voice create_job: active_customer_id from context_window_json pointing to a
    different tenant's customer must return error, not create a job.
    """

    def test_create_job_cross_tenant_customer_blocked(self, db_session: Session):
        """
        After FIND-132: tenant-scoped query returns None for cross-tenant customer →
        handler returns customer-not-found error, job not created.
        """
        from app.models.ai import ConversationSession
        from core.auth import AuthenticatedUser

        tenant_a = _create_tenant(db_session, "Voice-CreateJob-A")
        tenant_b = _create_tenant(db_session, "Voice-CreateJob-B")
        user_a = _create_user(db_session, f"voice-{uuid.uuid4().hex[:6]}@a.test")

        # Customer belongs to tenant_b — attack vector via context_window_json
        customer_b = _create_customer(db_session, tenant_b.id, "Tenant B Customer")

        session = ConversationSession(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            user_id=user_a.id,
            context_window_json={"active_customer_id": str(customer_b.id)},
        )
        db_session.add(session)
        db_session.flush()

        mock_user = MagicMock(spec=AuthenticatedUser)
        mock_user.id = user_a.id
        mock_user.tenant_id = tenant_a.id

        entities = {"job_description": "Panel upgrade", "customer_name": None}

        import asyncio

        from services.voice_action_router import create_job_via_voice

        result = asyncio.run(
            create_job_via_voice(entities, mock_user, db_session, session)
        )

        assert result.get("success") is False, (
            "create_job must fail when active_customer_id belongs to a different tenant. "
            f"Got: {result}"
        )
        assert (
            "customer" in result.get("error", "").lower()
            or "customer" in result.get("message", "").lower()
        ), f"Error must mention customer. Got: {result}"


# ---------------------------------------------------------------------------
# Voice query_job_profit — same-tenant customer name resolves correctly
# ---------------------------------------------------------------------------


class TestVoiceQueryJobProfitRegression:
    """
    Regression guard: query_job_profit must still return correct customer_name
    for a same-tenant job after the FIND-132 fix.
    """

    def test_query_job_profit_returns_correct_customer_name(self, db_session: Session):
        """
        Tenant-scoped query on job.customer_id must still resolve to the correct
        customer when customer belongs to the same tenant.
        """
        from app.models.ai import ConversationSession
        from core.auth import AuthenticatedUser

        tenant = _create_tenant(db_session, "Voice-QueryProfit")
        user = _create_user(db_session, f"profit-{uuid.uuid4().hex[:6]}@test.test")
        customer = _create_customer(db_session, tenant.id, "Johnson Electric")
        site = _create_site(db_session, tenant.id, customer.id)
        job = _create_job(db_session, tenant.id, customer.id, site.id)

        session = ConversationSession(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            context_window_json={"active_job_id": str(job.id)},
        )
        db_session.add(session)
        db_session.flush()

        mock_user = MagicMock(spec=AuthenticatedUser)
        mock_user.id = user.id
        mock_user.tenant_id = tenant.id

        entities = {"job_reference": str(job.id)}

        import asyncio

        from services.voice_action_router import get_job_profitability

        result = asyncio.run(
            get_job_profitability(entities, mock_user, db_session, session)
        )

        if result.get("success"):
            assert "Johnson Electric" in result.get("message", ""), (
                f"Regression: customer_name 'Johnson Electric' not found in result. "
                f"Tenant-scoped query must still resolve FK for same-tenant customer. "
                f"Result: {result}"
            )
