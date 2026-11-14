import uuid
from datetime import UTC, datetime
from typing import Any

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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin, MachineLogMixin, StandardAuditMixin


# --- Tenant RBAC & Membership ---
class TenantUserRole(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "tenant_user_role"

    code: str = Field(primary_key=True)
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    permissions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
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


class TenantUserStatus(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "tenant_user_status"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_tenant_user_status_tenant_code"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenant.id")
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
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


class TenantUser(StandardAuditMixin, SQLModel, table=True):
    """Note: Uses a composite primary key consisting of tenant_id and user_id"""

    __tablename__ = "tenant_user"

    tenant_id: uuid.UUID = Field(primary_key=True, foreign_key="tenant.id")
    user_id: uuid.UUID = Field(primary_key=True, foreign_key="user.id", index=True)

    role_code: str = Field(
        foreign_key="tenant_user_role.code", nullable=False, index=True
    )
    status_id: uuid.UUID = Field(
        foreign_key="tenant_user_status.id", nullable=False, index=True
    )

    invited_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    joined_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    suspended_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    suspended_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )

    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # FIND-066 (B18): Technician profile columns — all nullable; code wiring in B20
    # skill_level_code: per-tenant skill tier (apprentice/journeyman/master/foreman)
    # No CHECK constraint — skill tiers are tenant-configurable in Phase 2
    skill_level_code: str | None = Field(default=None)
    # employee_number: optional HR/payroll reference ID
    employee_number: str | None = Field(default=None)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class TenantDomain(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "tenant_domain"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "domain", name="uq_tenant_domain_tenant_id_domain"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    domain: str = Field(sa_column=Column(CITEXT, nullable=False))
    verified_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
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


# --- Invitations ---
class TenantUserInvite(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "tenant_user_invite"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "email", name="uq_tenant_user_invite_tenant_id_email"
        ),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="tenant_user_invite_email_format_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    email: str = Field(sa_column=Column(CITEXT, nullable=False))
    token_hash: str = Field(nullable=False, index=True)

    # TEAM-INVITE-1: role assigned at invite time; applied to tenant_user at
    # acceptance (Lambda Path 2). NULL = pre-TEAM-INVITE-1 rows → technician
    # fallback (design §F.3).
    role_code: str | None = Field(default=None, foreign_key="tenant_user_role.code")

    expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    accepted_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    invited_by: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class ContactPortalInvite(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "contact_portal_invite"
    __table_args__ = (
        UniqueConstraint("contact_id", name="uq_contact_portal_invite_contact_id"),
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="contact_portal_invite_email_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    contact_id: uuid.UUID = Field(foreign_key="contact.id", nullable=False)
    email: str = Field(sa_column=Column(CITEXT, nullable=False))
    token_hash: str = Field(nullable=False, index=True)

    expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    accepted_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    invited_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- Security & Auth Tokens ---
class AuthRefreshToken(MachineLogMixin, SQLModel, table=True):
    """Tokens themselves are append-only logs, updated via revocation."""

    __tablename__ = "auth_refresh_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )

    jti: str = Field(nullable=False)
    rotated_from_jti: str | None = Field(default=None)

    issued_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    revoked_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    revoked_reason: str | None = Field(default=None)

    ip: str | None = Field(default=None, sa_column=Column(INET))
    user_agent: str | None = Field(default=None)

    # B13/A70: FK → user_session_metadata.session_id. NULL for tokens issued before B13.
    session_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("user_session_metadata.session_id"),
            nullable=True,
        ),
    )


class AuthPasswordReset(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "auth_password_reset"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)
    contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contact.id", index=True
    )

    token_hash: str = Field(nullable=False, index=True)
    expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    used_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    requested_ip: str | None = Field(default=None, sa_column=Column(INET))

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class AuthEmailVerification(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "auth_email_verification"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)
    contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contact.id", index=True
    )

    token_hash: str = Field(nullable=False, index=True)
    expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    used_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class AuthMfaOtp(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "auth_mfa_otp"
    __table_args__ = (
        CheckConstraint("channel IN ('email', 'sms')", name="auth_mfa_otp_channel_chk"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)
    contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contact.id", index=True
    )
    channel: str = Field(nullable=False)  # 'email' | 'sms'
    user_endpoint_id: uuid.UUID | None = Field(
        default=None, foreign_key="user_endpoint.id", index=True
    )

    destination_masked: str | None = Field(default=None)
    code_hash: str = Field(nullable=False)
    expires_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    consumed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    attempt_count: int = Field(
        default=0,
        sa_column=Column(Integer, server_default=text("0"), nullable=False),
    )
    requested_ip: str | None = Field(default=None, sa_column=Column(INET))

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class AuthPasswordHistory(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "auth_password_history"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)
    contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contact.id", index=True
    )

    password_hash: str = Field(nullable=False)
    changed_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class AuthApiToken(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "auth_api_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)

    name: str = Field(nullable=False)
    token_hash: str = Field(nullable=False)
    scopes: list[str] | None = Field(default=None, sa_column=Column(ARRAY(String)))

    last_used_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    expires_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    revoked_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


# --- SSO Integrations ---
class SsoProvider(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "sso_provider"

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


class UserSsoIdentity(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "user_sso_identity"
    __table_args__ = (
        UniqueConstraint(
            "sso_provider_code",
            "provider_user_id",
            name="uq_user_sso_identity_provider_user",
        ),
        # NEW: Task 3 - SSO login lookup composite index
        Index("idx_user_sso_provider_id", "sso_provider_code", "provider_user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    sso_provider_code: str = Field(foreign_key="sso_provider.code", nullable=False)
    provider_user_id: str = Field(nullable=False)

    # Safely mapping provider_metadata so it doesn't conflict with Pydantic internal metadata
    provider_metadata_: dict[str, Any] | None = Field(
        default=None, sa_column=Column("provider_metadata", JSONB)
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


# --- Security / JSON Web Keys ---
class JwkStatus(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "jwk_status"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(nullable=False)
    name: str = Field(nullable=False)
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    is_signable: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class AuthJwk(AppendOnlyMixin, SQLModel, table=True):
    __tablename__ = "auth_jwk"
    __table_args__ = (
        CheckConstraint(
            "alg IN ('RS256', 'ES256', 'EdDSA')",
            name="auth_jwk_alg_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )
    kid: str = Field(nullable=False, unique=True)
    alg: str = Field(nullable=False)
    public_jwk: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))

    issuer_url: str | None = Field(default=None)
    discovery_url: str | None = Field(default=None)
    jwk_status_id: uuid.UUID = Field(
        foreign_key="jwk_status.id", nullable=False, index=True
    )

    not_before: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    not_after: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # Phase 6.0.1: Override audit field with FK constraint (append-only table)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class PasswordPolicy(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "password_policy"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenant.id", index=True
    )

    min_length: int | None = Field(default=None)
    min_lowercase: int | None = Field(default=None)
    min_uppercase: int | None = Field(default=None)
    min_digits: int | None = Field(default=None)
    min_special: int | None = Field(default=None)

    history_depth: int | None = Field(default=None)
    lockout_threshold: int | None = Field(default=None)
    lockout_window_minutes: int | None = Field(default=None)
    lockout_duration_minutes: int | None = Field(default=None)

    require_mfa: bool | None = Field(default=None)
    rotation_days: int | None = Field(default=None)

    # Phase 6.0.1: Override audit fields with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )
