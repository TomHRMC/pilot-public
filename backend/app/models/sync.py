"""
app/models/sync.py

SQLModel models for mobile sync infrastructure.

Tables:
    MobileSyncEvent         — append-only sync attempt log (B7a/§15.3)
    MobileDevicePushToken   — canonical push token registry (B8/A51)
    MobileSyncSession       — background sync session telemetry (B8/A51)
    MobilePushRateLimit     — per-device server-side rate limiting (B8/A51)
    MobileSyncEventAudit    — append-only owner resolution audit log (B8/A48)

Design rules:
    - MobileSyncEvent is APPEND-ONLY. Never update existing rows.
    - MobileSyncEventAudit is APPEND-ONLY. Insert on resolution only.
    - MobileSyncSession: completed_at is set via POST /sync-sessions/{id}/complete.
    - MobileDevicePushToken: upsert on (tenant_id, user_id, device_id).
    - MobilePushRateLimit: one row per device_id (UNIQUE constraint).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin


class MobileSyncEvent(AppendOnlyMixin, SQLModel, table=True):
    """
    Append-only log of sync attempts per device per offline operation.

    Never update existing rows. Insert new rows for each status transition.
    Retained for 30 days then archived via cleanup_mobile_sync_events Celery task.

    Status values:   pending | syncing | succeeded | failed | conflict
    Severity values: auto_silent | auto_notice | tech_resolvable | owner_escalation

    operation_type is free-text (no CHECK constraint) — new operation types
    are added at runtime without requiring a schema migration (§F.4).
    """

    __tablename__ = "mobile_sync_event"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'syncing', 'succeeded', 'failed', 'conflict')",
            name="chk_mobile_sync_event_status",
        ),
        CheckConstraint(
            "conflict_severity IS NULL OR conflict_severity IN "
            "('auto_silent', 'auto_notice', 'tech_resolvable', 'owner_escalation')",
            name="chk_mobile_sync_event_conflict_severity",
        ),
        Index(
            "ix_mobile_sync_event_tenant_user_status", "tenant_id", "user_id", "status"
        ),
        Index("ix_mobile_sync_event_created_at", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )

    # Client-reported device identifier (opaque string — no FK, device registry is future)
    device_id: str = Field(sa_column=Column(Text, nullable=False))

    # Operation type: free-text per §F.4 (no CHECK constraint)
    operation_type: str = Field(sa_column=Column(Text, nullable=False))

    # Non-PII summary of the operation (e.g., {'job_id': '...', 'hours': 3.5})
    operation_payload_summary: dict | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Sync status — CHECK constraint enforced (5 valid states)
    status: str = Field(sa_column=Column(Text, nullable=False))

    # Conflict severity — CHECK constraint enforced (4 classes or NULL)
    conflict_severity: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    # Timestamp when tech captured this event on device (required for sync events)
    client_capture_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    # Set when status transitions to 'succeeded'
    synced_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Set when status transitions to 'failed'; structured error info
    error_detail: dict | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Client-generated UUID v4, matches Idempotency-Key header
    idempotency_uuid: uuid.UUID = Field(sa_column=Column(PG_UUID, nullable=False))

    # B7b/A45: Resolution action captured when a conflict is resolved.
    # Set on the resolution-result row (status='succeeded' or status='conflict').
    # NULL on all pre-B7b rows and non-resolved rows.
    resolution_action: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    # created_at inherited from AppendOnlyMixin (server-side insert timestamp)
    # created_by inherited from AppendOnlyMixin (optional author FK)


# ---------------------------------------------------------------------------
# MobileDevicePushToken  — B8/A51: Canonical push token registry
# ---------------------------------------------------------------------------


class MobileDevicePushToken(StandardAuditMixin, SQLModel, table=True):
    """
    Canonical push token registry for mobile devices.

    Upserted on every app launch via POST /api/v1/mobile/push-tokens.
    Referenced by A47/A48 loop-closure push and B11/B14 future surfaces.

    UNIQUE constraint: (tenant_id, user_id, device_id)
    revoked_at is set on logout or invalid-token APNs/FCM response.
    """

    __tablename__ = "mobile_device_push_token"
    __table_args__ = (
        CheckConstraint(
            "platform IN ('ios', 'android')",
            name="mobile_device_push_token_platform_chk",
        ),
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "device_id",
            name="mobile_device_push_token_tenant_user_device_uq",
        ),
        Index(
            "idx_mobile_device_push_token_tenant_user",
            "tenant_id",
            "user_id",
        ),
        Index(
            "idx_mobile_device_push_token_active",
            "tenant_id",
            "user_id",
            "device_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="CASCADE", name="fk_mdpt_tenant"),
            nullable=False,
            index=True,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="CASCADE", name="fk_mdpt_user"),
            nullable=False,
        )
    )
    device_id: uuid.UUID = Field(sa_column=Column(PG_UUID, nullable=False))
    platform: str = Field(sa_column=Column(Text, nullable=False))
    push_token: str = Field(sa_column=Column(Text, nullable=False))
    app_version: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    os_version: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    registered_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )
    last_seen_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )
    notification_permission_granted: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )
    revoked_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Audit FK overrides
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_mdpt_created_by"),
        ),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="SET NULL", name="fk_mdpt_updated_by"),
        ),
    )


# ---------------------------------------------------------------------------
# MobileSyncSession  — B8/A51: Background sync session telemetry
# ---------------------------------------------------------------------------


class MobileSyncSession(SQLModel, table=True):
    """
    Records outcomes of each background sync run per device.

    Inserted by client POST /api/v1/mobile/sync-sessions/{id}/complete.
    Append-only pattern (no updated_at) — but not using AppendOnlyMixin
    because completed_at and outcome are set on the second update call
    (not at insert time). Uses explicit created_at only.
    """

    __tablename__ = "mobile_sync_session"
    __table_args__ = (
        CheckConstraint(
            "triggered_by IN ('silent_push', 'os_opportunistic', 'foreground', 'manual')",
            name="mobile_sync_session_triggered_by_chk",
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('success', 'partial', 'failed', 'throttled')",
            name="mobile_sync_session_outcome_chk",
        ),
        Index(
            "idx_mobile_sync_session_tenant_user_device",
            "tenant_id",
            "user_id",
            "device_id",
        ),
        Index(
            "idx_mobile_sync_session_device_recent",
            "device_id",
        ),
    )

    # FIND-169: renamed from session_id to id (UUID PK convention)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="CASCADE", name="fk_mss_tenant"),
            nullable=False,
            index=True,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="CASCADE", name="fk_mss_user"),
            nullable=False,
        )
    )
    device_id: uuid.UUID = Field(sa_column=Column(PG_UUID, nullable=False))
    triggered_by: str = Field(sa_column=Column(Text, nullable=False))

    started_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )
    completed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    outcome: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    items_attempted: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    items_committed: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    items_deferred: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    items_failed: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    failure_reason: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )


# ---------------------------------------------------------------------------
# MobilePushRateLimit  — B8/A51: Per-device server-side rate limiting
# ---------------------------------------------------------------------------


class MobilePushRateLimit(StandardAuditMixin, SQLModel, table=True):
    """
    Per-device server-side rate limiting table for silent push dispatch.

    One row per device_id (UNIQUE constraint).
    Updated by dispatch_silent_push_for_device() to enforce frequency cap.

    B13b: StandardAuditMixin added — created_by / updated_by columns added via migration.
    Machine-managed by push dispatcher — created_by/updated_by always NULL at runtime.
    """

    __tablename__ = "mobile_push_rate_limit"
    __table_args__ = (
        UniqueConstraint("device_id", name="mobile_push_rate_limit_device_uq"),
        Index("idx_mobile_push_rate_limit_tenant", "tenant_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # created_at, updated_at, created_by, updated_by provided by StandardAuditMixin

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="CASCADE", name="fk_mprl_tenant"),
            nullable=False,
        )
    )
    device_id: uuid.UUID = Field(sa_column=Column(PG_UUID, nullable=False))
    last_push_sent_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )
    push_count_current_window: int = Field(
        default=1,
        sa_column=Column(Integer, server_default=text("1"), nullable=False),
    )
    window_start_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )


# ---------------------------------------------------------------------------
# MobileSyncEventAudit  — B8/A48: Append-only owner resolution audit log
# ---------------------------------------------------------------------------


class MobileSyncEventAudit(AppendOnlyMixin, SQLModel, table=True):
    """
    Append-only audit log for owner resolution of escalated mobile conflicts.

    Inserted by POST /api/v1/owner/mobile-sync-escalations/{id}/resolve.
    FK references mobile_sync_owner_escalation.id (B7b table).
    Never updated — insert only.

    B13b: AppendOnlyMixin added — created_at (backfilled from resolved_at) + created_by added via migration.
    Both created_at and resolved_at coexist (F3 decision).
    """

    __tablename__ = "mobile_sync_event_audit"
    __table_args__ = (
        CheckConstraint(
            "resolution_channel IN ('web', 'voice')",
            name="mobile_sync_event_audit_channel_chk",
        ),
        Index(
            "idx_mobile_sync_event_audit_escalation",
            "escalation_id",
        ),
        Index(
            "idx_mobile_sync_event_audit_tenant_resolver",
            "tenant_id",
            "resolver_user_id",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="CASCADE", name="fk_msea_tenant"),
            nullable=False,
            index=True,
        )
    )
    escalation_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey(
                "mobile_sync_owner_escalation.id",
                ondelete="RESTRICT",
                name="fk_msea_escalation",
            ),
            nullable=False,
        )
    )
    originator_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT", name="fk_msea_originator"),
            nullable=False,
        )
    )
    resolver_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT", name="fk_msea_resolver"),
            nullable=False,
        )
    )
    resolution_action: str = Field(sa_column=Column(Text, nullable=False))
    resolution_channel: str = Field(
        default="web",
        sa_column=Column(Text, server_default=text("'web'"), nullable=False),
    )
    tech_local_snapshot_at_commit: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    server_state_snapshot_at_commit: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    post_commit_state: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    resolved_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=text("now()"), nullable=False
        ),
    )
