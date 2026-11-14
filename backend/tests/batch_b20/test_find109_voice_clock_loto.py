"""
Test Suite: FIND-109 — Voice Handlers for Clock In/Out and LOTO Confirmation
==============================================================================

Implements voice intents for hands-free time tracking:
  1. clock_in_via_voice: Tech says "Clock in on the Johnson job" → creates open JobTimeEntry
  2. clock_out_via_voice: Tech says "Clock out" → finds open entry, computes hours/cost
  3. confirm_loto_via_voice: Tech says "Confirm LOTO" → writes LotoConfirmation, sets flag
  4. log_time_entry_via_voice rate fix: replaces hardcoded 5000 with LaborRateVersion catalog

Test coverage:
  1. clock_in → JobTimeEntry created with started_at set, ended_at=NULL, resolved rate
  2. clock_out → open entry found, ended_at set, hours computed, total_cost_cents calculated
  3. clock_out with no open entry → error response
  4. confirm_loto → LotoConfirmation row created, context safety_loto_verified flag set
  5. log_time_entry rate → catalog lookup (not hardcoded 5000) with burden_pct
  6. Fallback: when no skill_level_code or no LaborRateVersion, use default_labor_rate_cents

Note: voice_command_entity_link wiring deferred to FIND-168 implementation.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from api.schemas.voice import ContextWindowSchema
from app.models.ai import ConversationSession
from app.models.auth import TenantUser
from app.models.catalog import LaborRateVersion
from app.models.core import Tenant, User
from app.models.crm import Customer
from app.models.fulfillment import (
    Job,
    JobStatus,
    JobTimeEntry,
    LotoConfirmation,
)
from core.auth import AuthenticatedUser
from services.voice_action_router import (
    clock_in_via_voice,
    clock_out_via_voice,
    confirm_loto_via_voice,
    log_time_entry_via_voice,
)
from tests.conftest import UTC

# ==================== FIXTURES ====================


@pytest.fixture
def test_tenant_find109(db_session):
    """Create a test tenant for FIND-109."""
    tenant = Tenant(
        id=uuid.UUID("00000000-0000-0000-0000-000000000109"),
        name="FIND-109 Test Tenant",
        is_active=True,
        created_by=None,
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_user_find109(db_session, test_tenant_find109):
    """Create a test user with skill_level_code set."""
    from app.models.auth import TenantUserStatus

    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000f09"),
        email="tech@find109.test",
        is_active=True,
        created_by=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create a default status for the tenant
    status = db_session.exec(
        select(TenantUserStatus).where(
            TenantUserStatus.tenant_id == test_tenant_find109.id,
            TenantUserStatus.is_default == True,
        )
    ).first()

    if not status:
        status = TenantUserStatus(
            tenant_id=test_tenant_find109.id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
            created_by=None,
        )
        db_session.add(status)
        db_session.commit()
        db_session.refresh(status)

    # Add TenantUser mapping with skill_level_code
    tenant_user = TenantUser(
        tenant_id=test_tenant_find109.id,
        user_id=user.id,
        role_code="technician",
        status_id=status.id,
        skill_level_code="journeyman",
        created_by=None,
    )
    db_session.add(tenant_user)
    db_session.commit()

    return user


@pytest.fixture
def test_customer_find109(db_session, test_tenant_find109):
    """Create a test customer."""
    customer = Customer(
        id=uuid.UUID("00000000-0000-0000-0000-000000000c09"),
        tenant_id=test_tenant_find109.id,
        display_name="Johnson Electric",
        created_by=None,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def test_job_find109(db_session, test_tenant_find109, test_customer_find109):
    """Create a test job."""
    from app.models.crm import Site

    # Create site first
    site = Site(
        id=uuid.UUID("00000000-0000-0000-0000-000000000a09"),
        tenant_id=test_tenant_find109.id,
        customer_id=test_customer_find109.id,
        name="Test Site",
        created_by=None,
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)

    job_status = db_session.exec(
        select(JobStatus).where(JobStatus.code == "unscheduled")
    ).first()
    if not job_status:
        job_status = JobStatus(
            tenant_id=test_tenant_find109.id,
            code="unscheduled",
            name="Unscheduled",
            is_default=True,
            is_terminal=False,
            created_by=None,
        )
        db_session.add(job_status)
        db_session.commit()
        db_session.refresh(job_status)

    job = Job(
        id=uuid.UUID("00000000-0000-0000-0000-000000000b09"),
        tenant_id=test_tenant_find109.id,
        customer_id=test_customer_find109.id,
        site_id=site.id,
        status_id=job_status.id,
        created_by=None,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def test_labor_rate_find109(db_session, test_tenant_find109):
    """Create a LaborRateVersion for journeyman."""
    rate = LaborRateVersion(
        tenant_id=test_tenant_find109.id,
        skill_level_code="journeyman",
        hourly_rate_cents=8500,  # $85/hr
        burden_pct=Decimal("0.3000"),  # 30% burden
        created_by=None,
    )
    db_session.add(rate)
    db_session.commit()
    db_session.refresh(rate)
    return rate


@pytest.fixture
def test_conversation_session_find109(
    db_session, test_tenant_find109, test_user_find109, test_job_find109
):
    """Create a conversation session with active job context."""
    ctx = ContextWindowSchema(
        tenant_id=str(test_tenant_find109.id),
        user_id=str(test_user_find109.id),
        active_job_id=str(test_job_find109.id),
    )
    session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=test_tenant_find109.id,
        user_id=test_user_find109.id,
        context_window_json=ctx.to_jsonb(),
        created_by=None,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def authenticated_user_find109(test_user_find109, test_tenant_find109):
    """Create an AuthenticatedUser context."""
    return AuthenticatedUser(
        user=test_user_find109,
        tenant_id=test_tenant_find109.id,
        role_code="technician",
        permissions=["jobs.view", "jobs.update", "time_entries.create"],
    )


# ==================== CLOCK IN TESTS ====================


class TestClockInViaVoice:
    """Test clock_in_via_voice handler."""

    @pytest.mark.asyncio
    async def test_clock_in_creates_open_entry(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
        test_job_find109,
        test_labor_rate_find109,
    ):
        """Clock in with active job → creates JobTimeEntry with started_at, ended_at=NULL."""
        result = await clock_in_via_voice(
            entities={},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True
        assert result["action"] == "clock_in"
        assert "started_at" in result["data"]

        # Verify JobTimeEntry was created
        entry = (
            db_session.execute(
                select(JobTimeEntry)
                .where(JobTimeEntry.user_id == authenticated_user_find109.id)
                .where(JobTimeEntry.job_id == test_job_find109.id)
                .order_by(JobTimeEntry.created_at.desc())
            )
            .scalars()
            .first()
        )

        assert entry is not None
        assert entry.started_at is not None
        assert entry.ended_at is None  # Open entry
        assert entry.hours is None
        assert entry.total_cost_cents == 0
        # Burdened rate: 8500 * (1 + 0.3) = 11050 cents ($110.50/hr)
        assert entry.hourly_rate_cents == 11050

    @pytest.mark.asyncio
    async def test_clock_in_with_job_reference(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
        test_customer_find109,
        test_labor_rate_find109,
    ):
        """Clock in with job_reference entity → finds job by customer name."""
        result = await clock_in_via_voice(
            entities={"job_reference": "Johnson"},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_clock_in_no_active_job_no_reference(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
    ):
        """Clock in without active job or reference → error."""
        # Clear active_job_id from context
        ctx = ContextWindowSchema.from_jsonb(
            test_conversation_session_find109.context_window_json
        )
        ctx.active_job_id = None
        test_conversation_session_find109.context_window_json = ctx.to_jsonb()
        db_session.add(test_conversation_session_find109)
        db_session.commit()

        result = await clock_in_via_voice(
            entities={},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is False
        assert result["error"] == "No job specified"

    @pytest.mark.asyncio
    async def test_clock_in_fallback_to_default_rate(
        self,
        db_session,
        test_tenant_find109,
        test_user_find109,
        test_conversation_session_find109,
        test_job_find109,
    ):
        """Clock in with no skill_level_code → uses default_labor_rate_cents."""
        # Clear skill_level_code by deleting and recreating TenantUser
        db_session.execute(
            text(
                f"DELETE FROM tenant_user WHERE tenant_id = '{test_tenant_find109.id}' AND user_id = '{test_user_find109.id}'"
            )
        )
        db_session.commit()

        # Recreate TenantUser without skill level
        from app.models.auth import TenantUserStatus

        status = (
            db_session.execute(
                select(TenantUserStatus)
                .where(TenantUserStatus.tenant_id == test_tenant_find109.id)
                .where(TenantUserStatus.is_default == True)
            )
            .scalars()
            .first()
        )
        if not status:
            status = TenantUserStatus(
                tenant_id=test_tenant_find109.id,
                code="active",
                name="Active",
                is_default=True,
                is_active=True,
                created_by=None,
            )
            db_session.add(status)
            db_session.commit()
            db_session.refresh(status)

        tenant_user = TenantUser(
            tenant_id=test_tenant_find109.id,
            user_id=test_user_find109.id,
            role_code="technician",
            status_id=status.id,
            skill_level_code=None,
            created_by=None,
        )
        db_session.add(tenant_user)
        db_session.commit()

        # Also clear any LaborRateVersion for this tenant
        db_session.execute(
            text(
                f"DELETE FROM labor_rate_version WHERE tenant_id = '{test_tenant_find109.id}'"
            )
        )
        db_session.commit()

        auth_user = AuthenticatedUser(
            user=test_user_find109,
            tenant_id=test_tenant_find109.id,
            role_code="technician",
            permissions=["jobs.view", "jobs.update", "time_entries.create"],
        )

        result = await clock_in_via_voice(
            entities={},
            current_user=auth_user,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True
        # Verify rate falls back to default (8500 cents = $85/hr, the system default)
        entry = (
            db_session.execute(
                select(JobTimeEntry)
                .where(JobTimeEntry.user_id == auth_user.id)
                .where(JobTimeEntry.job_id == test_job_find109.id)
            )
            .scalars()
            .first()
        )
        assert entry.hourly_rate_cents == 8500


# ==================== CLOCK OUT TESTS ====================


class TestClockOutViaVoice:
    """Test clock_out_via_voice handler."""

    @pytest.mark.asyncio
    async def test_clock_out_closes_entry(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
        test_job_find109,
        test_labor_rate_find109,
    ):
        """Clock out → finds open entry, sets ended_at, computes hours/cost."""
        # Create manual entry 1 minute in the past (to avoid sleeping)
        now = datetime.now(UTC)
        started = now - timedelta(minutes=1)

        entry = JobTimeEntry(
            tenant_id=authenticated_user_find109.tenant_id,
            job_id=test_job_find109.id,
            user_id=authenticated_user_find109.id,
            started_at=started,
            ended_at=None,
            hours=None,
            hourly_rate_cents=8500,  # Burdened rate from catalog
            total_cost_cents=0,
            created_by=authenticated_user_find109.id,
        )
        db_session.add(entry)
        db_session.commit()

        # Now clock out
        result = await clock_out_via_voice(
            entities={},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True
        assert result["action"] == "clock_out"
        assert result["data"]["hours"] > 0
        assert result["data"]["cost_cents"] > 0

        # Verify entry was closed
        entry = (
            db_session.execute(
                select(JobTimeEntry)
                .where(JobTimeEntry.user_id == authenticated_user_find109.id)
                .where(JobTimeEntry.job_id == test_job_find109.id)
                .order_by(JobTimeEntry.created_at.desc())
            )
            .scalars()
            .first()
        )

        assert entry.ended_at is not None
        assert entry.hours is not None
        assert entry.total_cost_cents > 0

    @pytest.mark.asyncio
    async def test_clock_out_no_open_entry(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
    ):
        """Clock out with no open entry → error."""
        result = await clock_out_via_voice(
            entities={},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is False
        assert result["error"] == "No open clock-in"

    @pytest.mark.asyncio
    async def test_clock_out_hours_calculation(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
        test_job_find109,
    ):
        """Clock out → hours=(ended_at-started_at)/3600 calculated correctly."""
        # Create manual entry 2 hours in the past
        now = datetime.now(UTC)
        started = now - timedelta(hours=2)

        entry = JobTimeEntry(
            tenant_id=authenticated_user_find109.tenant_id,
            job_id=test_job_find109.id,
            user_id=authenticated_user_find109.id,
            started_at=started,
            ended_at=None,
            hours=None,
            hourly_rate_cents=5000,
            total_cost_cents=0,
            created_by=authenticated_user_find109.id,
        )
        db_session.add(entry)
        db_session.commit()

        result = await clock_out_via_voice(
            entities={},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True
        # Allow for small timing variance (±0.1 hours)
        assert 1.9 < result["data"]["hours"] < 2.1


# ==================== LOTO CONFIRMATION TESTS ====================


class TestConfirmLotoViaVoice:
    """Test confirm_loto_via_voice handler."""

    @pytest.mark.asyncio
    async def test_confirm_loto_creates_record_and_sets_flag(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
        test_job_find109,
    ):
        """Confirm LOTO → creates LotoConfirmation, sets safety_loto_verified=True."""
        result = await confirm_loto_via_voice(
            entities={},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True
        assert result["action"] == "confirm_loto"

        # Verify LotoConfirmation was created
        loto = (
            db_session.execute(
                select(LotoConfirmation)
                .where(LotoConfirmation.job_id == test_job_find109.id)
                .where(LotoConfirmation.user_id == authenticated_user_find109.id)
                .order_by(LotoConfirmation.created_at.desc())
            )
            .scalars()
            .first()
        )

        assert loto is not None
        assert loto.is_active is True

        # Verify context flag was set
        db_session.refresh(test_conversation_session_find109)
        ctx = ContextWindowSchema.from_jsonb(
            test_conversation_session_find109.context_window_json
        )
        assert ctx.safety_loto_verified is True

    @pytest.mark.asyncio
    async def test_confirm_loto_idempotent(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
        test_job_find109,
    ):
        """Confirm LOTO twice → only one record created."""
        # First confirm
        await confirm_loto_via_voice(
            entities={},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        # Second confirm
        result = await confirm_loto_via_voice(
            entities={},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True

        # Verify only one LOTO record exists
        lotos = db_session.exec(
            select(LotoConfirmation)
            .where(LotoConfirmation.job_id == test_job_find109.id)
            .where(LotoConfirmation.user_id == authenticated_user_find109.id)
            .where(LotoConfirmation.is_active == True)
        ).all()

        assert len(lotos) == 1


# ==================== LOG TIME ENTRY RATE FIX TESTS ====================


class TestLogTimeEntryRateFix:
    """Test that log_time_entry_via_voice uses catalog rate (not hardcoded 5000)."""

    @pytest.mark.asyncio
    async def test_log_time_entry_uses_catalog_rate(
        self,
        db_session,
        authenticated_user_find109,
        test_conversation_session_find109,
        test_job_find109,
        test_labor_rate_find109,
    ):
        """Log time entry → uses LaborRateVersion catalog (not hardcoded 5000)."""
        result = await log_time_entry_via_voice(
            entities={"hours": 3},
            current_user=authenticated_user_find109,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True
        assert result["action"] == "log_time_entry"

        # Verify entry uses burdened rate from catalog
        entry = (
            db_session.execute(
                select(JobTimeEntry)
                .where(JobTimeEntry.user_id == authenticated_user_find109.id)
                .where(JobTimeEntry.job_id == test_job_find109.id)
                .order_by(JobTimeEntry.created_at.desc())
            )
            .scalars()
            .first()
        )

        # Burdened rate: 8500 * (1 + 0.3) = 11050 cents
        assert entry.hourly_rate_cents == 11050
        # Total cost: 3 hours * 11050 cents/hr = 33150 cents
        assert entry.total_cost_cents == 33150

    @pytest.mark.asyncio
    async def test_log_time_entry_fallback_to_default_rate(
        self,
        db_session,
        test_tenant_find109,
        test_user_find109,
        test_conversation_session_find109,
        test_job_find109,
    ):
        """Log time entry with no skill level or catalog rate → uses default_labor_rate_cents."""
        # Clear skill_level_code by deleting and recreating TenantUser
        db_session.execute(
            text(
                f"DELETE FROM tenant_user WHERE tenant_id = '{test_tenant_find109.id}' AND user_id = '{test_user_find109.id}'"
            )
        )
        db_session.commit()

        # Recreate TenantUser without skill level
        from app.models.auth import TenantUserStatus

        status = (
            db_session.execute(
                select(TenantUserStatus)
                .where(TenantUserStatus.tenant_id == test_tenant_find109.id)
                .where(TenantUserStatus.is_default == True)
            )
            .scalars()
            .first()
        )
        if not status:
            status = TenantUserStatus(
                tenant_id=test_tenant_find109.id,
                code="active",
                name="Active",
                is_default=True,
                is_active=True,
                created_by=None,
            )
            db_session.add(status)
            db_session.commit()
            db_session.refresh(status)

        tenant_user = TenantUser(
            tenant_id=test_tenant_find109.id,
            user_id=test_user_find109.id,
            role_code="technician",
            status_id=status.id,
            skill_level_code=None,
            created_by=None,
        )
        db_session.add(tenant_user)
        db_session.commit()

        # Clear rates
        db_session.execute(
            text(
                f"DELETE FROM labor_rate_version WHERE tenant_id = '{test_tenant_find109.id}'"
            )
        )
        db_session.commit()

        auth_user = AuthenticatedUser(
            user=test_user_find109,
            tenant_id=test_tenant_find109.id,
            role_code="technician",
            permissions=["jobs.view", "jobs.update", "time_entries.create"],
        )

        result = await log_time_entry_via_voice(
            entities={"hours": 2},
            current_user=auth_user,
            db=db_session,
            session=test_conversation_session_find109,
        )

        assert result["success"] is True

        entry = (
            db_session.execute(
                select(JobTimeEntry)
                .where(JobTimeEntry.user_id == auth_user.id)
                .where(JobTimeEntry.job_id == test_job_find109.id)
            )
            .scalars()
            .first()
        )

        # Default rate: 8500 cents/hr (system default)
        assert entry.hourly_rate_cents == 8500
        # Total: 2 hours * 8500 = 17000 cents
        assert entry.total_cost_cents == 17000


# ==================== REGRESSION: NO VOICE_COMMAND_LOG_ID COLUMN ====================


class TestNoVoiceCommandLogIdColumn:
    """Regression guard: verify voice_command_log_id does NOT exist on job_time_entry."""

    def test_job_time_entry_no_voice_command_log_id_column(self, db_session):
        """Verify job_time_entry table does NOT have voice_command_log_id column."""
        result = db_session.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'job_time_entry'
                AND column_name = 'voice_command_log_id'
            """
            )
        ).fetchone()

        assert result is None, (
            "job_time_entry.voice_command_log_id column should NOT exist (FIND-168 handles linking)"
        )
