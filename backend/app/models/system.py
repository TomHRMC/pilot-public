import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import AwareDatetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    desc,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, MachineLogMixin, StandardAuditMixin


# --- Webhooks ---
class WebhookEndpoint(MachineLogMixin, SQLModel, table=True):
    __tablename__ = "webhook_endpoint"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    url: str = Field(nullable=False)

    # Array of strings mapped to postgres

    event_filter: list[str] | None = Field(
        default=None, sa_column=Column(ARRAY(String))
    )

    secret: str | None = Field(default=None)
    enabled: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    disabled_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )


class WebhookEvent(MachineLogMixin, SQLModel, table=True):
    __tablename__ = "webhook_event"

    __table_args__ = (
        # Tenant dashboard query optimization
        Index("idx_webhook_event_tenant_time", "tenant_id", desc("created_at")),
        # Entity lookup query optimization
        Index(
            "idx_webhook_event_entity",
            "entity_type_code",
            "entity_id",
            desc("created_at"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )

    # QuickBooks webhook fields (Task #19 - Gap #27)
    source_app: str | None = Field(default=None, index=True)  # "quickbooks"
    event_type: str | None = Field(
        default=None
    )  # "com.intuit.quickbooks.customer.create"
    event_id: str | None = Field(
        default=None, index=True
    )  # CloudEvents ID (idempotency)

    # Legacy fields (kept for backward compatibility)
    event_type_code: str | None = Field(
        default=None, foreign_key="webhook_event_type.code", index=True
    )
    entity_type_code: str | None = Field(default=None, foreign_key="entity_type.code")
    entity_id: uuid.UUID | None = Field(default=None)

    # Payload and processing
    payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    signature_valid: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    processed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    error_message: str | None = Field(default=None)


# --- B10: Notification Category Registry ---


class NotificationCategory(StandardAuditMixin, SQLModel, table=True):
    """
    Platform-defined notification category registry (B10/A56).

    Lookup table — categories are seeded by migration, not user-created.
    Soft-delete not applicable (platform-defined; use is_active on preferences instead).
    """

    __tablename__ = "notification_category"

    # FIND-169: renamed from category_id to code (string PK lookup table convention)
    code: str = Field(primary_key=True)
    display_label: str = Field(nullable=False)
    description: str = Field(nullable=False)
    category_group_id: str | None = Field(default=None)  # Phase 2 forward-compat
    display_order: int = Field(nullable=False)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class NotificationCategorySubTrigger(StandardAuditMixin, SQLModel, table=True):
    """
    Sub-trigger registry with forced-minimum push semantics (B10/A56).

    forced_minimum_push_uniform: override to True for ALL recipients (critical alerts).
    forced_minimum_push_recipient_only: override to True ONLY when the recipient is
        the originating user on the outbox row.
    """

    __tablename__ = "notification_category_sub_trigger"
    __table_args__ = (Index("ix_notif_sub_trigger_category_id", "category_id"),)

    # FIND-169: renamed from sub_trigger_id to code (string PK lookup table convention)
    code: str = Field(primary_key=True)
    # FK child column category_id references notification_category.code (FIND-169)
    category_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("notification_category.code", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    display_label: str | None = Field(default=None)
    forced_minimum_push_uniform: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    forced_minimum_push_recipient_only: bool | None = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=True),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class NotificationDefaultPolicy(StandardAuditMixin, SQLModel, table=True):
    """
    System and tenant-level notification default policies (B10/A56).

    NULL tenant_id = system default.
    Non-NULL tenant_id = tenant override.

    Uniqueness enforced via partial unique indexes (NULL != NULL in standard UNIQUE).
    See migration for uq_notif_default_policy_system and uq_notif_default_policy_tenant.
    """

    __tablename__ = "notification_default_policy"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('push', 'email', 'in_app')",
            name="chk_notif_default_policy_channel",
        ),
        Index("ix_notif_default_policy_tenant_id", "tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    # FK child column category_id references notification_category.code (FIND-169)
    category_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("notification_category.code", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    channel: str = Field(nullable=False)  # push|email|in_app
    enabled: bool = Field(nullable=False)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- B10/A57: User Preference Matrix + In-App Notifications ---


class NotificationPreference(StandardAuditMixin, SQLModel, table=True):
    """
    User/tenant-level notification preference overrides (B10/A57).

    NULL user_id = tenant-level override.
    Non-NULL user_id = user-level override.

    Resolution order (three-tier):
      User override → Tenant override → notification_default_policy (tenant) →
      notification_default_policy (system) → False

    Uniqueness enforced via partial unique indexes (NULL != NULL in standard UNIQUE).
    See migration for uq_notif_pref_tenant_level and uq_notif_pref_user_level.
    """

    __tablename__ = "notification_preference"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('push', 'email', 'in_app')",
            name="chk_notif_pref_channel",
        ),
        Index("ix_notif_pref_tenant_user", "tenant_id", "user_id"),
        Index("ix_notif_pref_category_channel", "category_id", "channel"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        )
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    # FK child column category_id references notification_category.code (FIND-169)
    category_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("notification_category.code", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    channel: str = Field(nullable=False)  # push|email|in_app
    enabled: bool = Field(nullable=False)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class InAppNotification(AppendOnlyMixin, SQLModel, table=True):
    """
    In-app notification bell panel records (B10/A57).

    AppendOnlyMixin — notifications are immutable after creation.
    read_at is set when user marks notification as read.
    SSE delivery: after db.commit(), emit_to_user() pushes the row to the
    user's open SSE connection.
    """

    __tablename__ = "in_app_notification"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('standard', 'critical')",
            name="chk_in_app_notif_priority",
        ),
        # Partial index for unread count queries
        Index(
            "ix_in_app_notif_user_unread",
            "tenant_id",
            "user_id",
            "created_at",
            postgresql_where=text("read_at IS NULL"),
        ),
        # Bell panel recent-50 query index
        Index(
            "ix_in_app_notif_user_created",
            "tenant_id",
            "user_id",
            "created_at",
        ),
    )

    # FIND-169: renamed from notification_id to id (UUID PK convention)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
        )
    )
    # FK child column category_id references notification_category.code (FIND-169)
    category_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("notification_category.code", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    body: str = Field(nullable=False)
    deep_link_target: str = Field(nullable=False)
    priority: str = Field(
        default="standard",
        sa_column=Column(String, nullable=False, server_default=text("'standard'")),
    )
    read_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # AppendOnlyMixin provides created_at + created_by; override created_by FK
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Notifications ---
class NotificationOutbox(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        # FIND-077 (B18): notification_outbox_channel_chk dropped — replaced by FK to notification_channel.code
        CheckConstraint(
            "(recipient_contact_id IS NOT NULL OR recipient_user_id IS NOT NULL OR to_address IS NOT NULL)",
            name="notification_outbox_recipient_presence_chk",
        ),
        CheckConstraint(
            "((recipient_contact_id IS NOT NULL)::int + (recipient_user_id IS NOT NULL)::int + (to_address IS NOT NULL)::int) = 1",
            name="notification_outbox_recipient_exclusive_chk",
        ),
        CheckConstraint(
            "(channel <> 'in_app') OR (recipient_user_id IS NOT NULL)",
            name="notification_outbox_inapp_requires_user_chk",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'canceled', 'suppressed_by_preferences')",
            name="notification_outbox_status_chk",
        ),
        # B10/A56: index on category_id for preference gate queries
        Index("ix_notif_outbox_category_id", "category_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    notification_event_id: uuid.UUID = Field(
        foreign_key="notification_event.id", nullable=False, index=True
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)

    recipient_contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contact.id", index=True
    )
    recipient_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    # FIND-077 (B18): FK to notification_channel.code replaces old CHECK constraint
    channel: str = Field(foreign_key="notification_channel.code", nullable=False)

    contact_endpoint_id: uuid.UUID | None = Field(
        default=None, foreign_key="contact_endpoint.id", index=True
    )
    user_endpoint_id: uuid.UUID | None = Field(
        default=None, foreign_key="user_endpoint.id", index=True
    )

    to_address: str | None = Field(default=None)
    subject: str | None = Field(default=None)
    body: str = Field(nullable=False)

    scheduled_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    status: Literal[
        "pending", "sent", "failed", "canceled", "suppressed_by_preferences"
    ] = Field(
        default="pending",
        sa_column=Column(String, nullable=False, server_default="pending"),
    )
    provider_message_id: str | None = Field(default=None)
    idempotency_key: str | None = Field(default=None, index=True)

    attempt_count: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    next_attempt_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    last_error: str | None = Field(default=None)
    priority: int = Field(
        default=5, sa_column=Column(Integer, server_default=text("5"), nullable=False)
    )

    # Safely renamed from metadata
    contextdata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # B10/A56: Notification category and sub-trigger classification
    # Index is defined in __table_args__ (ix_notif_outbox_category_id)
    # FK child columns reference renamed PK columns (FIND-169)
    category_id: str | None = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("notification_category.code"),
            nullable=True,
        ),
    )
    sub_trigger_id: str | None = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("notification_category_sub_trigger.code"),
            nullable=True,
        ),
    )
    # originating recipient for forced-minimum-push-recipient-only logic (A58)
    recipient_user_id_originating: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, nullable=True),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class NotificationDeliveryAttempt(MachineLogMixin, SQLModel, table=True):
    __tablename__ = "notification_delivery_attempt"

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','delivered','bounced','rejected','throttled','error')",
            name="notification_delivery_attempt_status_chk",
        ),
        # NEW: Composite index for performance
        Index(
            "idx_notif_attempt_outbox_time",
            "notification_outbox_id",
            text("attempted_at DESC"),
        ),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    notification_outbox_id: uuid.UUID = Field(
        foreign_key="notification_outbox.id", nullable=False, index=True
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)

    attempt_no: int = Field(nullable=False)
    status: str = Field(nullable=False)  # sent|failed|retrying
    provider: str = Field(
        nullable=False
    )  # sendgrid|telnyx|mock (B11/A59: SMS carrier adapter)

    # RENAMED from provider_response to details in Phase 5.3 migration
    details: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Provider-specific response payload (renamed from provider_response)",
    )

    # NEW COLUMNS added in Phase 5.3 migration:
    provider_code: str | None = Field(
        default=None,
        description="Provider-specific message/transaction ID (e.g., Twilio SID)",
    )
    duration_ms: int | None = Field(
        default=None,
        description="Time taken for delivery attempt in milliseconds",
    )
    created_by: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        description="User who initiated this delivery attempt",
    )

    error_message: str | None = Field(default=None)
    http_status: int | None = Field(default=None)
    retryable: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
        description="Set false for hard bounces/4xx-not-retryable.",
    )

    attempted_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    completed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    next_attempt_after: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # FIXED: Override MachineLogMixin created_at to use server_default
    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )


# --- Integrations & Connectors ---
class IntegrationSyncLog(MachineLogMixin, SQLModel, table=True):
    __tablename__ = "integration_sync_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failed', 'partial_success')",
            name="isl_status_chk",
        ),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    app_service_id: uuid.UUID = Field(
        foreign_key="app_service.id", nullable=False, index=True
    )

    status: str = Field(nullable=False)  # success|failed|partial_success
    started_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    finished_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    records_processed: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    records_failed: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    error_message: str | None = Field(default=None)

    # Safely renamed from metadata
    contextdata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")


class ConnectorConfig(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "connector_config"

    __table_args__ = (
        CheckConstraint(
            "mode IN ('api','scrape','manual')",
            name="connector_config_mode_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    supplier_id: uuid.UUID = Field(
        foreign_key="supplier.id", nullable=False, unique=True
    )
    mode: str = Field(
        default="api",
        sa_column=Column(String, server_default=text("'api'"), nullable=False),
    )
    schedule_cron: str | None = Field(default=None)

    enabled: bool = Field(
        default=True,
        sa_column=Column(
            Boolean, server_default=text("true"), nullable=False, index=True
        ),
    )
    last_success_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    failure_count: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )

    # Safely renamed from metadata
    contextdata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ConnectorRunLog(MachineLogMixin, SQLModel, table=True):
    __tablename__ = "connector_run_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'failed')",
            name="connector_run_log_status_chk",
        ),
        # NEW: Task 3 - Supplier sync history composite indexes
        Index(
            "idx_connector_run_supplier_started", "supplier_id", text("started_at DESC")
        ),
        Index(
            "idx_connector_run_supplier_status",
            "supplier_id",
            "status",
            text("started_at DESC"),
        ),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    supplier_id: uuid.UUID = Field(foreign_key="supplier.id", nullable=False)

    started_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    finished_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    status: Literal["running", "success", "failed"] = Field(
        default="running",
        sa_column=Column(String, nullable=False, server_default=text("'running'")),
    )
    items_fetched: int = Field(
        default=0, sa_column=Column(Integer, server_default=text("0"), nullable=False)
    )
    error: str | None = Field(default=None)

    # Safely renamed from metadata
    contextdata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))


# --- Global Audit Ledger ---
class AuditEvent(SQLModel, table=True):
    """
    Master system ledger. Note: This uses __table_args__ to put it in the 'audit'
    PostgreSQL schema instead of the default 'public' schema.
    """

    __tablename__ = "event"
    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('system', 'user', 'platform', 'external_webhook')",
            name="audit_event_actor_type_chk",
        ),
        {"schema": "audit"},
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    occurred_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
    )

    tenant_id: uuid.UUID | None = Field(default=None)
    user_id: uuid.UUID | None = Field(default=None)
    actor_type: str = Field(default="system", nullable=False)
    user_role: str | None = Field(default=None)

    ip: str | None = Field(default=None, sa_column=Column(INET))
    user_agent: str | None = Field(default=None)
    request_id: str | None = Field(default=None, index=True)
    correlation_id: str | None = Field(default=None)
    idempotency_key: str | None = Field(default=None, index=True)

    entity_name: str = Field(nullable=False)
    entity_id: str = Field(nullable=False)
    action: str = Field(nullable=False)

    old_values: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    new_values: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    reason: str | None = Field(default=None)

    # Safely renamed from metadata
    contextdata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    prev_hash: str | None = Field(default=None)
    self_hash: str | None = Field(default=None)
    hashed_at: AwareDatetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )


# --- Add to app/models/system.py ---


class AppServiceCategory(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "app_service_category"

    code: str = Field(primary_key=True)
    description: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class AppServiceProvider(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "app_service_provider"

    code: str = Field(primary_key=True)
    description: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class AppService(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "app_service"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    name: str = Field(nullable=False)

    category_code: str = Field(
        foreign_key="app_service_category.code", nullable=False, index=True
    )
    provider_code: str = Field(
        foreign_key="app_service_provider.code", nullable=False, index=True
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Task #16 - QuickBooks OAuth 2.0 Flow & Hybrid Schema Refactoring
    external_account_id: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True, index=True),
        description="QuickBooks realm_id (Company ID). Indexed for fast webhook routing.",
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class IntegrationCredential(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "integration_credential"

    __table_args__ = (
        CheckConstraint(
            "connection_status IN ('pending', 'active', 'disconnected', 'expired', 'revoked')",
            name="ck_integration_credential_status",
        ),
        # Phase 6.0 Task 2: Partial index for credential expiration checks
        Index(
            "idx_integration_cred_expires",
            "expires_at",
            postgresql_where=text("expires_at IS NOT NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    app_service_id: uuid.UUID = Field(
        foreign_key="app_service.id", nullable=False, index=True
    )

    secret_json: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
        description="Encrypted tokens only: access_token_encrypted, refresh_token_encrypted, state_token",
    )

    # Task #16 - QuickBooks OAuth 2.0 Flow & Hybrid Schema Refactoring
    # Explicit timestamp columns for queryable lifecycle tracking (v2.6h "Double-Lock" standard)
    expires_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When the OAuth access token expires (typically 1 hour from issue)",
    )

    last_refresh_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Most recent token rotation timestamp",
    )

    connected_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Initial authorization timestamp (OAuth callback completion)",
    )

    disconnected_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When user revoked access or connection was terminated",
    )

    initiated_by_user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        index=True,
        description="User who authorized the QuickBooks connection",
    )

    connection_status: str = Field(
        default="pending",
        sa_column=Column(
            String, server_default=text("'pending'"), nullable=False, index=True
        ),
    )

    # Existing field - Keep for backward compatibility
    rotated_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class IntegrationSyncMapping(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "integration_sync_mapping"
    __table_args__ = (
        UniqueConstraint(
            "app_service_id",
            "entity_type_code",
            "entity_id",
            name="uq_integration_sync_mapping_internal",
        ),
        UniqueConstraint(
            "app_service_id",
            "entity_type_code",
            "external_id",
            name="uq_integration_sync_mapping_external",
        ),
        CheckConstraint(
            "sync_preference IN ('pilot_master', 'external_master', 'bi_directional')",
            name="sync_preference_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    app_service_id: uuid.UUID = Field(foreign_key="app_service.id", nullable=False)

    entity_type_code: str = Field(foreign_key="entity_type.code", nullable=False)
    entity_id: uuid.UUID = Field(nullable=False)
    external_id: str = Field(nullable=False)

    external_version_token: str | None = Field(default=None)
    internal_version_token: str | None = Field(default=None)
    sync_preference: str = Field(
        default="pilot_master",
        sa_column=Column(String, server_default=text("'pilot_master'"), nullable=False),
    )
    last_synced_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class IntegrationSyncConflict(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "integration_sync_conflict"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'resolved_keep_internal', 'resolved_keep_external')",
            name="integration_sync_conflict_status_chk",
        ),
        # FIND-090 (B18): conflict_subtype for entity-type-aware display
        CheckConstraint(
            "conflict_subtype IS NULL OR conflict_subtype IN "
            "('customer','quote','invoice','expense','deletion_local','deletion_remote')",
            name="integration_sync_conflict_subtype_chk",
        ),
        Index(
            "idx_integration_sync_conflict_auto_expire",
            "tenant_id",
            "auto_expire_at",
            postgresql_where=text("status = 'pending' AND auto_expire_at IS NOT NULL"),
        ),
        Index(
            "idx_integration_sync_conflict_pre_warning",
            "tenant_id",
            "pre_warning_at",
            postgresql_where=text("status = 'pending' AND pre_warning_at IS NOT NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    app_service_id: uuid.UUID = Field(
        foreign_key="app_service.id", nullable=False, index=True
    )

    entity_type_code: str = Field(
        foreign_key="entity_type.code", nullable=False, index=True
    )
    entity_id: uuid.UUID = Field(nullable=False)
    external_id: str = Field(nullable=False)
    status: str = Field(
        default="pending",
        sa_column=Column(String, server_default=text("'pending'"), nullable=False),
    )

    internal_payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    external_payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))

    resolved_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    resolved_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )

    # B8/A49: Diff/staleness columns for QB conflict display
    base_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    field_diffs: list = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    pilot_modified_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )
    pilot_modified_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
        ),
    )
    qb_modified_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )
    qb_modified_by_external_user_label: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    auto_expire_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    pre_warning_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # FIND-090 (B18): Entity-type-aware conflict display columns — A49 schema deferred columns
    conflict_subtype: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    financial_delta_payload: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class NotificationChannel(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "notification_channel"
    code: str = Field(primary_key=True)
    name: str = Field(nullable=False)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class NotificationType(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "notification_type"
    __table_args__ = (
        CheckConstraint(
            "audience IN ('tenant','customer')",
            name="notification_type_audience_chk",
        ),
    )

    code: str = Field(primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    audience: str = Field(nullable=False)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# ContactNotificationPref, TenantUserNotificationPref, TenantNotificationDefault
# removed in FIND-080 / B21 (2026-05-18) — legacy tables superseded by
# NotificationPreference; migration: phase_fe_1_batch_b21_drop_legacy_notification_pref_tables


class NotificationTemplate(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "notification_template"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    notification_type_code: str = Field(
        foreign_key="notification_type.code", nullable=False, index=True
    )

    channel: str = Field(nullable=False)
    locale: str = Field(nullable=False)
    subject: str | None = Field(default=None)
    body: str = Field(nullable=False)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class NotificationEvent(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "notification_event"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    notification_type_code: str = Field(
        foreign_key="notification_type.code", nullable=False, index=True
    )
    entity_type_code: str = Field(
        foreign_key="entity_type.code", nullable=False, index=True
    )
    entity_id: str = Field(nullable=False)

    occurred_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    payload: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class WebhookEventType(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "webhook_event_type"
    code: str = Field(primary_key=True)
    name: str = Field(nullable=False)
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class WebhookDeliveryAttempt(MachineLogMixin, SQLModel, table=True):
    __tablename__ = "webhook_delivery_attempt"
    __table_args__ = (
        # Worker queue query optimization
        Index("idx_webhook_delivery_pending", "status", "next_attempt_after"),
        CheckConstraint(
            "status IN ('pending', 'success', 'failed', 'giving_up')",
            name="webhook_delivery_attempt_status_chk",
        ),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    webhook_event_id: uuid.UUID = Field(
        foreign_key="webhook_event.id", nullable=False, index=True
    )
    webhook_endpoint_id: uuid.UUID = Field(
        foreign_key="webhook_endpoint.id", nullable=False, index=True
    )

    attempt_no: int = Field(
        default=1, sa_column=Column(Integer, server_default=text("1"), nullable=False)
    )
    status: Literal["pending", "success", "failed", "giving_up"] = Field(
        default="pending",
        sa_column=Column(String, nullable=False, server_default=text("'pending'")),
    )
    http_status: int | None = Field(default=None)
    error: str | None = Field(default=None)

    request_header: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    response_body: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    requested_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    completed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    next_attempt_after: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )


class IdempotencyKey(MachineLogMixin, SQLModel, table=True):
    __tablename__ = "idempotency_key"

    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress','succeeded','failed')",
            name="idempotency_key_status_chk",
        ),
    )

    key: str = Field(primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)

    first_seen_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    status: str = Field(
        default="in_progress",
        sa_column=Column(String, server_default=text("'in_progress'"), nullable=False),
    )
    request_hash: str | None = Field(default=None)
    response_hash: str | None = Field(default=None)
    response_body: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    locked_until: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


# --- B7b: Offline Conflict Engine ---


class SyncConflictClassificationMatrix(StandardAuditMixin, SQLModel, table=True):
    """
    Data-driven conflict severity classification engine (B7b/A40).

    Platform-default rows have tenant_id = NULL.
    Tenant-specific override rows have tenant_id = <UUID>.

    Classification logic in services/mobile_sync_conflict.py resolves:
        1. Tenant override row (tenant_id matches, is_active=True)
        2. Platform default row (tenant_id IS NULL, is_active=True)
        3. Fallback: 'tech_resolvable' with generic reason

    Four-Class Severity (§16.6):
        auto_silent | auto_notice | tech_resolvable | owner_escalation
    """

    __tablename__ = "sync_conflict_classification_matrix"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('auto_silent', 'auto_notice', 'tech_resolvable', 'owner_escalation')",
            name="chk_sync_conflict_matrix_severity",
        ),
        Index(
            "ix_sync_conflict_matrix_tenant_op",
            "tenant_id",
            "operation_type",
        ),
        Index(
            "ix_sync_conflict_matrix_active",
            "operation_type",
            "trigger_condition",
            postgresql_where=text("is_active = TRUE"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Classification keys
    operation_type: str = Field(sa_column=Column(String, nullable=False))
    trigger_condition: str = Field(sa_column=Column(String, nullable=False))

    # Classification output
    severity: str = Field(sa_column=Column(String, nullable=False))
    classification_reason: str = Field(sa_column=Column(String, nullable=False))

    # NULL = platform default; non-NULL = tenant override (§F.8)
    tenant_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=True
        ),
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Override audit FK constraints (Phase 6.0.1 pattern)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class MobileSyncOwnerEscalation(StandardAuditMixin, SQLModel, table=True):
    """
    Owner escalation routing table for mobile sync conflicts (B7b/A46).

    Created when A45 resolve endpoint receives escalate_to_owner.
    Resolved by owner via POST /api/v1/owner/mobile-sync-escalations/{id}/resolve.

    Pattern: §16.11 Mobile-to-Web Escalation Pattern (first implementation).
    Loop-closure: notification_outbox entries sent to tech on resolution.
    """

    __tablename__ = "mobile_sync_owner_escalation"
    __table_args__ = (
        CheckConstraint(
            "escalation_reason IN ('auto_severity', 'tech_chose')",
            name="chk_mobile_sync_escalation_reason",
        ),
        CheckConstraint(
            "status IN ('pending', 'resolved', 'rejected', 'auto_recovered', 'stale')",
            name="chk_mobile_sync_escalation_status",
        ),
        CheckConstraint(
            "resolution_action IS NULL OR resolution_action IN ("
            "'used_local', 'used_server', 'manual_edit', 'rejected',"
            "'use_tech', 'use_server', 'restore_and_accept',"
            "'override_with_tech', 'discard_tech',"
            "'accept_authorized_at_capture', 'reject_unauthorized'"
            ")",
            name="chk_mobile_sync_escalation_resolution_action",
        ),
        Index(
            "ix_mobile_sync_owner_escalation_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_mobile_sync_owner_escalation_originating_user",
            "originating_user_id",
        ),
        Index(
            "ix_mobile_sync_owner_escalation_conflict_id",
            "conflict_id",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        )
    )

    # The tech who triggered the escalation
    originating_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
        )
    )

    # FK to mobile_sync_event row with status='conflict'
    conflict_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("mobile_sync_event.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )

    escalated_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    escalation_reason: str = Field(sa_column=Column(String, nullable=False))
    escalation_reason_explainer: str = Field(sa_column=Column(String, nullable=False))

    status: str = Field(
        default="pending",
        sa_column=Column(String, server_default=text("'pending'"), nullable=False),
    )

    # Set when owner resolves
    resolved_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    resolved_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    resolution_action: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    resolution_payload: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Override audit FK constraints (Phase 6.0.1 pattern)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
