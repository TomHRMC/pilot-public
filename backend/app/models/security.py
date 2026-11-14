"""
B13 Security & Account Models — Account Security & Data Export.

New models (all live here per F1 decision):
  A72: UserSessionHistory
  A68: MfaGracePeriodTracking
  A69: UserMfaMethod, UserMfaRecoveryCode
  A70: UserSessionMetadata
  A71: DataExportRequest

Mixin assignments (per B13-fix §H remediation):
  StandardAuditMixin: UserSessionHistory, MfaGracePeriodTracking, UserMfaMethod,
                      UserSessionMetadata, DataExportRequest
  AppendOnlyMixin:    UserMfaRecoveryCode

TenantSettings (core.py) and AuthRefreshToken (auth.py) receive additive
columns via separate migrations but their ORM classes are updated in-place.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, StandardAuditMixin

# ---------------------------------------------------------------------------
# A72 — Session History (login tracking)
# ---------------------------------------------------------------------------


class UserSessionHistory(StandardAuditMixin, SQLModel, table=True):
    """
    One row per (tenant_id, user_id) pair.
    Upserted on every successful login to track first-login and session count.
    """

    __tablename__ = "user_session_history"
    __table_args__ = (
        PrimaryKeyConstraint("tenant_id", "user_id", name="pk_user_session_history"),
        Index("ix_user_session_history_tenant_id", "tenant_id"),
        Index("ix_user_session_history_user_id", "user_id"),
    )

    tenant_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("tenant.id"), nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id"), nullable=False)
    )
    first_login_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    total_session_count: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    last_login_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


# ---------------------------------------------------------------------------
# A68 — MFA Grace Period Tracking
# ---------------------------------------------------------------------------


class MfaGracePeriodTracking(StandardAuditMixin, SQLModel, table=True):
    """
    One row per (tenant_id, user_id) for users in an MFA grace period.
    Created when the tenant owner activates the MFA requirement.
    Updated when the user enrolls (enrolled_at) or logs in (enforcement_activated_at).
    """

    __tablename__ = "mfa_grace_period_tracking"
    __table_args__ = (
        PrimaryKeyConstraint(
            "tenant_id", "user_id", name="pk_mfa_grace_period_tracking"
        ),
        Index("ix_mfa_grace_period_tracking_tenant_id", "tenant_id"),
        Index("ix_mfa_grace_period_tracking_user_id", "user_id"),
    )

    tenant_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("tenant.id"), nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id"), nullable=False)
    )
    # When the tenant MFA policy was activated (grace period start)
    grace_started_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    # Set when user completes MFA enrollment
    enrolled_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # Set when user logs in mid-grace (enforcement becomes active)
    enforcement_activated_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


# ---------------------------------------------------------------------------
# A69 — MFA Method Enrollment
# ---------------------------------------------------------------------------


class UserMfaMethod(StandardAuditMixin, SQLModel, table=True):
    """
    Persistent enrollment record for a user's MFA method.
    One row per (tenant_id, user_id, method_type) — enforced via unique constraint.
    """

    __tablename__ = "user_mfa_method"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_id",
            "method_type",
            name="uq_user_mfa_method_tenant_user_type",
        ),
        Index("ix_user_mfa_method_tenant_id", "tenant_id"),
        Index("ix_user_mfa_method_user_id", "user_id"),
    )

    mfa_method_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            server_default=text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("tenant.id"), nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id"), nullable=False)
    )
    # 'totp' | 'sms' | 'email'
    method_type: str = Field(sa_column=Column(Text, nullable=False))
    enrolled_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    last_used_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # Cognito's reference ID for this method
    cognito_method_id: str = Field(sa_column=Column(Text, nullable=False))
    # 'verified' | 'needs_reverification'
    verification_status: str = Field(
        default="verified",
        sa_column=Column(Text, server_default=text("'verified'"), nullable=False),
    )
    # Optional metadata, e.g., last 4 digits of phone
    # Field renamed 'method_metadata' — 'metadata' is reserved by SQLAlchemy Declarative API.
    method_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
    )


class UserMfaRecoveryCode(AppendOnlyMixin, SQLModel, table=True):
    """
    PBKDF2-hashed recovery codes for MFA fallback.
    10 codes generated together (grouped by set_id).
    Plaintext is never stored — only shown once at generation time.
    AppendOnlyMixin: codes are generated once; only domain column 'used_at' changes.
    """

    __tablename__ = "user_mfa_recovery_code"
    __table_args__ = (
        Index("ix_user_mfa_recovery_code_tenant_id", "tenant_id"),
        Index("ix_user_mfa_recovery_code_user_id", "user_id"),
        Index("ix_user_mfa_recovery_code_set_id", "set_id"),
    )

    code_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            server_default=text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("tenant.id"), nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id"), nullable=False)
    )
    # PBKDF2-hashed; plaintext never stored
    code_hash: str = Field(sa_column=Column(Text, nullable=False))
    generated_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    # Set on redemption
    used_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # Groups 10 codes generated together
    set_id: uuid.UUID = Field(sa_column=Column(PG_UUID, nullable=False))


# ---------------------------------------------------------------------------
# A70 — Active Session Metadata
# ---------------------------------------------------------------------------


class UserSessionMetadata(StandardAuditMixin, SQLModel, table=True):
    """
    One row per active browser/device session.
    Created on login (after MFA if required).
    Linked to auth_refresh_token via auth_refresh_token.session_id FK (Migration 7).

    StandardAuditMixin provides: created_at, updated_at, created_by, updated_by.
    Note: B13-fix migration skips adding created_at (already exists in DB from original migration).
    """

    __tablename__ = "user_session_metadata"
    __table_args__ = (
        Index("ix_user_session_metadata_tenant_id", "tenant_id"),
        Index("ix_user_session_metadata_user_id", "user_id"),
        Index(
            "ix_user_session_metadata_user_id_revoked_at",
            "user_id",
            "revoked_at",
        ),
    )

    session_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            server_default=text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("tenant.id"), nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id"), nullable=False)
    )
    # User-Agent + characteristics hash
    device_fingerprint: str = Field(sa_column=Column(Text, nullable=False))
    # Human-readable label, e.g., "Chrome on macOS"
    display_label: str = Field(sa_column=Column(Text, nullable=False))
    ip_address: str = Field(sa_column=Column(INET, nullable=False))
    # City/state from IP lookup; NULL = unknown
    geolocation: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # Updated on token refresh
    last_active_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    # Set on revocation; NULL = active session
    revoked_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


# ---------------------------------------------------------------------------
# A71 — Data Export Request
# ---------------------------------------------------------------------------


class DataExportRequest(StandardAuditMixin, SQLModel, table=True):
    """
    Tracks async data export requests.
    Status lifecycle: pending → processing → ready | expired | failed.
    ZIP archive streamed to S3 via tasks/data_export_pipeline.py.
    """

    __tablename__ = "data_export_request"
    __table_args__ = (
        Index("ix_data_export_request_tenant_id", "tenant_id"),
        Index("ix_data_export_request_user_id", "user_id"),
        Index("ix_data_export_request_status", "status"),
    )

    export_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            server_default=text("gen_random_uuid()"),
            nullable=False,
            primary_key=True,
        ),
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("tenant.id"), nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, ForeignKey("user.id"), nullable=False)
    )
    requested_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    # pending | processing | ready | expired | failed
    status: str = Field(
        default="pending",
        sa_column=Column(Text, server_default=text("'pending'"), nullable=False),
    )
    # S3 key — set when status = ready
    s3_path: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # 7-day presigned S3 GET URL — set when status = ready
    signed_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # 7 days after ready; set when status = ready
    expires_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # 'full_tenant' (owner) | 'user_specific' (technician)
    data_scope: str = Field(sa_column=Column(Text, nullable=False))
    # Set on failure
    failure_reason: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
