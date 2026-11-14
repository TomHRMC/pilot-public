"""
Scheduling & Dispatch domain models.

Tables:
  - JobTechAssignment       — links a scheduled job to a technician (StandardAuditMixin)
  - TechAvailability        — working hours / PTO / unavailable blocks (StandardAuditMixin)
  - TenantCalendarIntegration — OAuth connection to Google/Outlook calendar (StandardAuditMixin)
  - CalendarSyncLog         — append-only sync event log (AppendOnlyMixin + immutable guard trigger)
  - CalendarSyncConflict    — bi-directional conflicts awaiting owner resolution (StandardAuditMixin)
"""

import uuid
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin

# ---------------------------------------------------------------------------
# JobTechAssignment
# ---------------------------------------------------------------------------


class JobTechAssignment(StandardAuditMixin, SQLModel, table=True):
    """Links a scheduled job to a specific technician.

    Enforces MVP single-tech constraint via partial unique index
    ``uq_job_tech_assignment_active_primary``.
    """

    __tablename__ = "job_tech_assignment"
    __table_args__ = (
        CheckConstraint("role IN ('primary', 'helper')", name="ck_role_valid"),
        CheckConstraint("ordinal >= 1", name="ck_ordinal_positive"),
        # Partial unique indexes are created in the migration via op.execute();
        # SQLAlchemy Index objects are here only for documentation / metadata purposes.
        Index(
            "uq_job_tech_assignment_active_primary",
            "tenant_id",
            "job_id",
            unique=True,
            postgresql_where=text("is_active = true AND role = 'primary'"),
        ),
        Index(
            "uq_job_tech_assignment_active_user",
            "tenant_id",
            "job_id",
            "user_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
        Index(
            "idx_job_tech_assignment_user_active",
            "tenant_id",
            "user_id",
            postgresql_where=text("is_active = true"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT", name="fk_jta_tenant"),
            nullable=False,
            index=True,
        )
    )
    job_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="RESTRICT", name="fk_jta_job"),
            nullable=False,
            index=True,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT", name="fk_jta_user"),
            nullable=False,
        )
    )
    assigned_by_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT", name="fk_jta_assigned_by"),
            nullable=False,
        )
    )
    role: str = Field(
        default="primary",
        sa_column=Column(Text, server_default=text("'primary'"), nullable=False),
    )
    ordinal: int = Field(
        default=1,
        sa_column=Column(Integer, server_default=text("1"), nullable=False),
    )
    assigned_at: AwareDatetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        )
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # B3/A19: Optimistic locking — incremented on every write (including soft-delete)
    version: int = Field(
        default=1,
        sa_column=Column(Integer, server_default=text("1"), nullable=False),
    )

    # Audit FK overrides (SET NULL on cascade)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_jta_created_by"),
        ),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_jta_updated_by"),
        ),
    )


# ---------------------------------------------------------------------------
# TechAvailability
# ---------------------------------------------------------------------------


class TechAvailability(StandardAuditMixin, SQLModel, table=True):
    """Defines tech working hours, PTO, and unavailable blocks."""

    __tablename__ = "tech_availability"
    __table_args__ = (
        CheckConstraint(
            "availability_type IN ('working_hours', 'pto', 'unavailable')",
            name="ck_availability_type",
        ),
        CheckConstraint(
            "(availability_type = 'working_hours' AND recurrence_rrule IS NOT NULL) OR "
            "(availability_type IN ('pto', 'unavailable') AND starts_at IS NOT NULL "
            "AND ends_at IS NOT NULL AND ends_at > starts_at)",
            name="ck_availability_shape",
        ),
        Index(
            "idx_tech_availability_user_active",
            "tenant_id",
            "user_id",
            postgresql_where=text("is_active = true"),
        ),
        # GIST index for time-range overlap queries (created manually in migration)
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT", name="fk_ta_tenant"),
            nullable=False,
            index=True,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT", name="fk_ta_user"),
            nullable=False,
            index=True,
        )
    )
    availability_type: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    starts_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    ends_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    recurrence_rrule: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    notes: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Audit FK overrides
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_ta_created_by"),
        ),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_ta_updated_by"),
        ),
    )


# ---------------------------------------------------------------------------
# TenantCalendarIntegration
# ---------------------------------------------------------------------------


class TenantCalendarIntegration(StandardAuditMixin, SQLModel, table=True):
    """Tenant-scoped connection to an external shared company calendar.

    One row per tenant (enforced by UNIQUE constraint on tenant_id).
    Access/refresh tokens are stored as Fernet-encrypted ``bytea``.
    """

    __tablename__ = "tenant_calendar_integration"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tci_tenant"),
        CheckConstraint(
            "provider_code IN ('google', 'outlook')",
            name="ck_provider_code",
        ),
        CheckConstraint(
            "sync_status IN ('active', 'paused', 'error')",
            name="ck_sync_status",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT", name="fk_tci_tenant"),
            nullable=False,
            index=True,
        )
    )
    provider_code: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    external_calendar_id: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    access_token_encrypted: bytes = Field(
        sa_column=Column(LargeBinary, nullable=False),
    )
    refresh_token_encrypted: bytes = Field(
        sa_column=Column(LargeBinary, nullable=False),
    )
    token_expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    sync_status: str = Field(
        default="active",
        sa_column=Column(Text, server_default=text("'active'"), nullable=False),
    )
    last_sync_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    last_sync_cursor: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    connected_by_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT", name="fk_tci_connected_by"),
            nullable=False,
        )
    )
    connected_at: AwareDatetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        )
    )

    # Audit FK overrides
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_tci_created_by"),
        ),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_tci_updated_by"),
        ),
    )


# ---------------------------------------------------------------------------
# CalendarSyncLog  — AppendOnlyMixin (immutable guard trigger in migration)
# ---------------------------------------------------------------------------


class CalendarSyncLog(AppendOnlyMixin, SQLModel, table=True):
    """Append-only sync event log for the shared calendar.

    IMPORTANT: Although this model uses ``AppendOnlyMixin``, the physical DB
    still has the ``trg_calendar_sync_log_guard_created_immutable`` trigger
    applied in the migration to enforce immutability at the DB layer.
    """

    __tablename__ = "calendar_sync_log"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('push', 'pull')",
            name="ck_direction",
        ),
        CheckConstraint(
            "entity_type IN ('job', 'availability')",
            name="ck_entity_type",
        ),
        CheckConstraint(
            "status IN ('success', 'conflict', 'error')",
            name="ck_status",
        ),
        Index(
            "idx_calendar_sync_log_tenant_recent",
            "tenant_id",
            postgresql_ops={"created_at": "DESC"},
        ),
        Index(
            "idx_calendar_sync_log_entity",
            "tenant_id",
            "entity_type",
            "entity_id",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT", name="fk_csl_tenant"),
            nullable=False,
            index=True,
        )
    )
    direction: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    entity_type: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    entity_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, nullable=False),
    )
    external_event_id: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    status: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    error_detail: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    payload_snapshot: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    # Audit FK override (append-only, only created_by)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_csl_created_by"),
        ),
    )


# ---------------------------------------------------------------------------
# CalendarSyncConflict
# ---------------------------------------------------------------------------


class CalendarSyncConflict(StandardAuditMixin, SQLModel, table=True):
    """Records bi-directional calendar conflicts requiring owner resolution.

    B6/A32: Added conflict_type, base_snapshot, pilot_modified_by_user_id,
    pilot_modified_at, external_modified_at, urgency_score, auto_resolved_stale.
    Resolution constraint expanded to 6 variants.
    """

    __tablename__ = "calendar_sync_conflict"
    __table_args__ = (
        CheckConstraint(
            "resolution IS NULL OR resolution IN ("
            "'accept_local', 'accept_remote', "
            "'restore_from_calendar', 'delete_calendar_too', "
            "'recreate_calendar_event', 'delete_pilot_job')",
            name="ck_resolution",
        ),
        CheckConstraint(
            "conflict_type IN ('modified_modified', 'deleted_modified', 'modified_deleted')",
            name="ck_csc_conflict_type",
        ),
        Index(
            "idx_calendar_sync_conflict_pending",
            "tenant_id",
            "created_at",
            postgresql_where=text("resolution IS NULL"),
        ),
        Index(
            "idx_csc_urgency_pending",
            "tenant_id",
            "urgency_score",
            postgresql_where=text("resolution IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT", name="fk_csc_tenant"),
            nullable=False,
            index=True,
        )
    )
    job_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="RESTRICT", name="fk_csc_job"),
            nullable=False,
            index=True,
        )
    )
    local_snapshot: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
    )
    remote_snapshot: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
    )
    resolution: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    resolved_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_csc_resolved_by"),
            nullable=True,
        ),
    )
    resolved_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # B6/A32: Diff-payload columns
    conflict_type: str = Field(
        default="modified_modified",
        sa_column=Column(
            Text, server_default=text("'modified_modified'"), nullable=False
        ),
    )
    base_snapshot: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    pilot_modified_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_csc_pilot_modified_by"),
            nullable=True,
        ),
    )
    pilot_modified_at: AwareDatetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        )
    )
    external_modified_at: AwareDatetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        )
    )
    urgency_score: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    auto_resolved_stale: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # Audit FK overrides
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_csc_created_by"),
        ),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_csc_updated_by"),
        ),
    )
