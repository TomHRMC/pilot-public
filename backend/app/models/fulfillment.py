import uuid
from datetime import date
from decimal import Decimal

from pydantic import AwareDatetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin


# CLASS-B1: Job classification lookup (platform defaults + tenant overrides)
class JobType(StandardAuditMixin, SQLModel, table=True):
    """Lookup table for job type (kind of work).

    NULL tenant_id = platform default row (shared across all tenants).
    Non-NULL tenant_id = tenant override that shadows the platform row with the same code.
    Partial unique indexes (not declared here — created in migration) enforce:
      - one platform row per code (WHERE tenant_id IS NULL)
      - one tenant row per (tenant_id, code) (WHERE tenant_id IS NOT NULL)
    """

    __tablename__ = "job_type"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    code: str = Field(sa_column=Column(Text, nullable=False))
    label: str = Field(sa_column=Column(Text, nullable=False))
    sort_order: int = Field(
        default=100,
        sa_column=Column(Integer, server_default=text("100"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Override audit FK fields
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class JobStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "job_status"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_job_status_tenant_code"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_terminal: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class JobRecurrenceRule(StandardAuditMixin, SQLModel, table=True):
    """Recurring job rule template — stores the cadence definition.

    B21: Creating a rule immediately creates the first job. Beat task runs
    daily at 06:00 UTC and generates subsequent job instances when due.
    pattern values: daily | weekly | monthly | annually
    """

    __tablename__ = "job_recurrence_rule"
    __table_args__ = (
        CheckConstraint(
            "pattern IN ('daily','weekly','monthly','annually')",
            name="chk_recurrence_pattern",
        ),
        CheckConstraint("interval_count >= 1", name="chk_interval_count_positive"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    customer_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    site_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("site.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    pattern: str = Field(sa_column=Column(String(20), nullable=False))
    interval_count: int = Field(
        default=1,
        sa_column=Column(Integer, server_default=text("1"), nullable=False),
    )
    starts_on: date = Field(sa_column=Column(Date, nullable=False))
    ends_on: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    max_occurrences: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    occurrences_created: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    next_job_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    last_job_created_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    estimated_duration_minutes: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    default_tech_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    notes_template: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Override audit FK fields (Phase 6.0.1 pattern)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class Job(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "job"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    quote_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    quote_version_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_version.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    customer_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("customer.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    site_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("site.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    status_id: uuid.UUID = Field(
        foreign_key="job_status.id", nullable=False, index=True
    )

    scheduled_start_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    scheduled_end_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    estimated_duration_minutes: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    external_calendar_event_id: str | None = Field(
        default=None,
        sa_column=Column("external_calendar_event_id", nullable=True),
    )

    # Cached financials for real-time < 500ms dashboards
    actual_labor_cost_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    actual_material_cost_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    actual_profit_cents: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # B3/A19: Optimistic locking — incremented on every write
    version: int = Field(
        default=1,
        sa_column=Column(Integer, server_default=text("1"), nullable=False),
    )

    # B3/A19 (F3): Variance notification tracking — bundled into migration 2
    variance_owner_notified_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    variance_last_notified_pct: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(5, 1), nullable=True),
    )

    # B19: Human-readable job number — sequential, tenant-scoped (JOB-000001)
    # default_factory generates a UUID-based placeholder so direct Job() construction
    # in tests doesn't hit the NOT NULL constraint. Production code always calls
    # _generate_job_number() to set the canonical sequential format.
    job_number: str = Field(
        default_factory=lambda: f"JOB-{uuid.uuid4().hex[:10].upper()}",
        sa_column=Column(String(30), nullable=False, index=True),
    )

    # B21: Link job back to the recurrence rule that spawned it (NULL = manually created)
    recurrence_rule_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("job_recurrence_rule.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # JOB-UI-B1: Human-readable job title — nullable, optional free-text label
    title: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    # CLASS-B1: Priority (urgency) — TEXT+CHECK, 3-part NOT NULL migration
    priority: str = Field(
        default="standard",
        sa_column=Column(Text, server_default=text("'standard'"), nullable=False),
    )

    # CLASS-B1: Job type (kind of work) — nullable FK to job_type lookup
    job_type_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("job_type.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class JobNotes(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "job_notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    job_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    notes: str = Field(nullable=False)
    audio_object_key: str | None = Field(default=None)
    customer_visible: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # B7a/A37: Offline capture timestamp — NULL means captured online
    client_capture_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # FIND-050: Server receipt timestamp — NULL=online, non-NULL=arrived via offline sync batch
    server_received_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class JobAttachment(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "job_attachment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    job_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )

    file_name: str = Field(nullable=False)
    mime_type: str = Field(nullable=False)
    size_bytes: int = Field(nullable=False)
    object_key: str = Field(nullable=False)
    description: str | None = Field(default=None)

    # B7a/A37: Offline capture timestamp — NULL means captured online
    client_capture_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # FIND-050: Server receipt timestamp — NULL=online, non-NULL=arrived via offline sync batch
    server_received_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # B7a/A39: SHA-256 hash of photo file for natural-key dedup — NULL for legacy rows
    file_hash: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # B7b/A41: S3 multipart upload tracking
    # NULL on pre-B7b rows — treated as 'complete' by application logic
    # Valid values: pending_upload | uploading | complete | failed
    upload_status: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    s3_upload_session_id: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    upload_completed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # Optional FK to job_expense — links photo to expense
    expense_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("job_expense.id", ondelete="SET NULL"), nullable=True
        ),
    )

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class JobTimeEntry(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "job_time_entry"

    __table_args__ = (
        # RENAMED: Standardized index names
        Index("idx_jte_job", "job_id"),
        Index("idx_jte_user", "user_id"),
        # NEW: Missing time-based index
        Index("idx_jte_started_at", text("started_at DESC")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    job_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("job.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)

    started_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    ended_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    hours: float | None = Field(default=None, sa_column=Column(Numeric(10, 3)))
    notes: str | None = Field(default=None)

    # Task 1-C-4: GPS check-in columns for technician on-site presence verification
    check_in_lat: float | None = Field(
        default=None,
        sa_column=Column(Numeric(10, 7), nullable=True),
    )
    check_in_lng: float | None = Field(
        default=None,
        sa_column=Column(Numeric(10, 7), nullable=True),
    )
    gps_variance_meters: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )

    hourly_rate_cents: int = Field(nullable=False)
    total_cost_cents: int = Field(nullable=False)

    # B3/A14: ETC (Estimate-to-Complete) columns
    hours_remaining_estimate: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(6, 2), nullable=True),
    )
    hours_remaining_was_overridden: bool | None = Field(
        default=None,
        sa_column=Column(Boolean, nullable=True),
    )
    override_note: str | None = Field(
        default=None,
        sa_column=Column("override_note", nullable=True),
    )
    quote_line_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("quote_line.id", ondelete="RESTRICT", name="fk_jte_quote_line"),
            nullable=True,
        ),
    )
    # F2 arch addition: captured at clock-out time
    etc_captured_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # B7a/A37: Offline capture timestamp — NULL means captured online
    client_capture_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # FIND-050: Server receipt timestamp — NULL=online, non-NULL=arrived via offline sync batch
    server_received_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class JobExpenseCategory(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "job_expense_category"

    code: str = Field(primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class JobExpense(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "job_expense"

    __table_args__ = (
        # Phase 6.0 Task 2: Partial index for unbilled expenses
        Index(
            "idx_job_expense_unbilled",
            "job_id",
            postgresql_where=text("is_billable = true AND invoice_line_id IS NULL"),
        ),
        # FIND-121 (B18): Natural-key dedup index now includes user_id as first column
        Index(
            "ix_job_expense_natural_key_dedup",
            "user_id",
            "job_id",
            "incurred_at",
            "cost_cents",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        ),
    )
    job_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    # FIND-121 (B18): user who incurred the expense (different from created_by = operator)
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    job_expense_category_code: str = Field(
        foreign_key="job_expense_category.code", nullable=False, index=True
    )

    description: str = Field(nullable=False)
    vendor_name: str | None = Field(default=None)
    incurred_at: AwareDatetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )
    )

    cost_cents: int = Field(nullable=False)
    markup_pct: float = Field(
        default=0,
        sa_column=Column(Numeric(7, 4), nullable=False, server_default=text("0")),
    )
    markup_amt_cents: int | None = Field(default=None)
    billable_cents: int = Field(nullable=False)

    is_billable: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    invoice_line_id: uuid.UUID | None = Field(
        default=None, foreign_key="invoice_line.id", index=True
    )
    receipt_object_key: str | None = Field(default=None)

    # B7a/A37: Offline capture timestamp — NULL means captured online
    client_capture_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # FIND-050: Server receipt timestamp — NULL=online, non-NULL=arrived via offline sync batch
    server_received_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # FIND-062/B21 (A96): Receipt OCR pipeline columns
    ocr_processed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    ocr_source: str | None = Field(default=None)

    # Phase 6.0.1 Task 3: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class LotoConfirmation(AppendOnlyMixin, SQLModel, table=True):
    """LOTO (Lock Out / Tag Out) Confirmation record.

    Mixin: AppendOnlyMixin — LOTO confirmations are immutable safety records;
    they cannot be updated or deleted after creation. Provides created_at + created_by.

    B20/A89: New capability — LOTO confirmation table with configurable voice guard.
    Offline-capable: client_capture_at + server_received_at pattern.
    """

    __tablename__ = "loto_confirmation"

    __table_args__ = (
        # Natural-key dedup — prevents duplicate offline syncs
        Index(
            "uq_loto_confirmation_natural_key",
            "user_id",
            "job_id",
            "confirmed_at",
            unique=True,
        ),
        # One active LOTO record per (job, user) — partial unique index
        Index(
            "uq_loto_confirmation_active_per_job_user",
            "job_id",
            "user_id",
            postgresql_where=text("is_active = true"),
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    job_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    confirmed_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    # A37/FIND-050: Offline capture timestamps
    client_capture_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    server_received_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Override AppendOnlyMixin created_by with FK constraint (Phase 6.0.1 pattern)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class NecCalculationLog(StandardAuditMixin, SQLModel, table=True):
    """NEC 2023 calculation log — persists voltage drop, conduit fill, and ampacity results.

    MOB-B0: New table. REST API: POST /api/v1/nec/calculate.
    Offline-capable: idempotency_key + client_capture_at pattern (same as job_notes/loto).

    StandardAuditMixin provides: created_at, updated_at, created_by, updated_by.
    Triggers: trg_nec_calc_log_updated_at, trg_nec_calc_log_guard_created_immutable,
              audit_nec_calculation_log_changes.
    """

    __tablename__ = "nec_calculation_log"
    __table_args__ = (
        CheckConstraint(
            "calc_type IN ('voltage_drop', 'conduit_fill', 'ampacity')",
            name="ck_nec_calc_type",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    job_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("job.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    calc_type: str = Field(
        sa_column=Column(String(50), nullable=False),
    )
    nec_guide_version: str = Field(
        default="2023",
        sa_column=Column(String(20), nullable=False, server_default=text("'2023'")),
    )
    inputs_json: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'")),
    )
    result_json: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'")),
    )
    is_offline_calc: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )
    idempotency_key: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, nullable=True, unique=True),
    )
    client_capture_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Override StandardAuditMixin created_by/updated_by with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
