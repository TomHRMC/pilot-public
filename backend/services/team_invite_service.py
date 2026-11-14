"""
TEAM-INVITE-1 — Team invite service.

Handles invite creation, listing, resend, revoke, and public token validation.
All functions are sync ``def`` (rules §21) and use tenant-scoped ``select()``
(rules §4 — ``db.get()`` banned on tenant-scoped models).

Design: dev-docs/architecture-design/batch-designs/batch-team-invite-1-design.md §F
"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.models.auth import TenantUserInvite, TenantUserRole
from app.models.core import Tenant, User
from services.onboarding_service import mark_team_invited
from services.tier_limit_enforcer import check_user_add_allowed

logger = logging.getLogger(__name__)

INVITE_EXPIRY_DAYS = 7


# ── Typed service exceptions (mapped by the route to RFC 7807 codes) ─────────


class TeamInviteError(Exception):
    """Base exception for team invite service errors."""

    def __init__(self, message: str, error_code: str, status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class InvalidRoleError(TeamInviteError):
    def __init__(self, role_code: str):
        super().__init__(
            f"Role '{role_code}' is not a valid active role.",
            error_code="invalid_role",
            status_code=400,
        )


class InviteUserExistsError(TeamInviteError):
    def __init__(self, email: str):
        super().__init__(
            f"A user with email '{email}' already has a Pilot account.",
            error_code="invite_user_exists",
            status_code=409,
        )


class InvitePendingExistsError(TeamInviteError):
    def __init__(self, invite_id: UUID):
        self.invite_id = invite_id
        super().__init__(
            "A pending invite already exists for this email.",
            error_code="invite_pending_exists",
            status_code=409,
        )


class InviteNotFoundError(TeamInviteError):
    def __init__(self):
        super().__init__(
            "Invite not found in this tenant.",
            error_code="invite_not_found",
            status_code=404,
        )


class InviteAlreadyAcceptedError(TeamInviteError):
    def __init__(self):
        super().__init__(
            "This invite has already been accepted.",
            error_code="invite_already_accepted",
            status_code=409,
        )


class InviteRevokedError(TeamInviteError):
    def __init__(self):
        super().__init__(
            "This invite has been revoked.",
            error_code="invite_revoked",
            status_code=409,
        )


# ── Token helper (design §F.2) ─────────────────────────────────────────────────


def _generate_invite_token() -> tuple[str, str]:
    """Generate a raw token and its SHA-256 hash.

    Returns:
        Tuple of (raw_token, token_hash). The raw token leaves the process
        ONLY inside the invite email URL. The DB stores only the hash.
    """
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def _get_web_app_base_url() -> str:
    """Resolve the web app base URL for invite link construction.

    Uses ``settings.FRONTEND_URL`` (defined in core/config.py Settings class).
    Falls back to localhost:3000 for dev.
    """
    from core.config import settings

    base = settings.FRONTEND_URL or "http://localhost:3000"
    return base.rstrip("/")


# ── Public service functions ───────────────────────────────────────────────────


def create_invite(
    db: Session,
    *,
    tenant_id: UUID,
    email: str,
    role_code: str,
    invited_by: UUID,
) -> tuple[TenantUserInvite, str]:
    """Create a new invite and send the invite email.

    Returns:
        Tuple of (invite_row, raw_token). The raw_token is used ONLY to
        build the invite URL in the email — it is never returned by the API.

    Raises:
        InvalidRoleError: role_code is not an active tenant_user_role.
        InviteUserExistsError: a user row already exists for this email.
        InvitePendingExistsError: a pending invite already exists.
    """
    email_lower = email.strip().lower()

    # 1. Validate role is active
    role = db.exec(
        select(TenantUserRole)
        .where(TenantUserRole.code == role_code)
        .where(TenantUserRole.is_active == True)
    ).first()
    if not role:
        raise InvalidRoleError(role_code)

    # 2. Forward-compat seat check (always true — MKT-B11 invariant)
    check_user_add_allowed(db, tenant_id)

    # 3. Check if a user already exists for this email
    existing_user = db.exec(select(User).where(User.email == email_lower)).first()
    if existing_user:
        raise InviteUserExistsError(email_lower)

    # 4. Check for existing invite for this (tenant_id, email)
    # The table has uq_tenant_user_invite_tenant_id_email — only ONE row per
    # (tenant_id, email) pair. So we look for ANY existing row, then decide:
    #   - If it's still pending (active, not accepted, not expired) → 409
    #   - If it's revoked/expired → reactivate it with a new token + role + expiry
    now = datetime.now(UTC)
    existing = db.exec(
        select(TenantUserInvite)
        .where(TenantUserInvite.tenant_id == tenant_id)
        .where(TenantUserInvite.email == email_lower)
    ).first()

    if existing:
        # Check if it's still pending (active, not accepted, not expired)
        is_pending = (
            existing.accepted_at is None
            and existing.is_active
            and existing.expires_at > now
        )
        if is_pending:
            raise InvitePendingExistsError(existing.id)

        # Reactivate the existing row (revoked or expired) with new token + role + expiry
        raw_token, token_hash = _generate_invite_token()
        existing.token_hash = token_hash
        existing.role_code = role_code
        existing.expires_at = now + timedelta(days=INVITE_EXPIRY_DAYS)
        existing.invited_by = invited_by
        existing.is_active = True
        existing.accepted_at = None
        db.add(existing)
        db.commit()
        db.refresh(existing)
        invite = existing
    else:
        # 5. No existing row — generate token + insert new
        raw_token, token_hash = _generate_invite_token()
        expires_at = now + timedelta(days=INVITE_EXPIRY_DAYS)

        invite = TenantUserInvite(
            tenant_id=tenant_id,
            email=email_lower,
            token_hash=token_hash,
            role_code=role_code,
            expires_at=expires_at,
            invited_by=invited_by,
            is_active=True,
        )
        db.add(invite)
        db.commit()
        db.refresh(invite)

    # 6. Send invite email (category=internal → tenant_id=None → Pilot branding)
    _send_invite_email(db, invite, role, raw_token)

    # 7. Mark onboarding checklist (non-fatal)
    try:
        mark_team_invited(db, tenant_id)
    except Exception:
        logger.warning("mark_team_invited failed for tenant %s (non-fatal)", tenant_id)

    return invite, raw_token


def list_invites(db: Session, *, tenant_id: UUID) -> list[TenantUserInvite]:
    """List all invites for a tenant, ordered by created_at DESC."""
    return list(
        db.exec(
            select(TenantUserInvite)
            .where(TenantUserInvite.tenant_id == tenant_id)
            .order_by(TenantUserInvite.created_at.desc())
        ).all()
    )


def resend_invite(
    db: Session,
    *,
    tenant_id: UUID,
    invite_id: UUID,
) -> tuple[TenantUserInvite, str]:
    """Resend an invite: rotate token, reset expiry, resend email.

    Returns:
        Tuple of (invite_row, raw_token).

    Raises:
        InviteNotFoundError: invite not found in this tenant.
        InviteAlreadyAcceptedError: invite was already accepted.
        InviteRevokedError: invite was revoked.
    """
    invite = _get_tenant_invite(db, tenant_id, invite_id)
    if not invite:
        raise InviteNotFoundError()

    if invite.accepted_at is not None:
        raise InviteAlreadyAcceptedError()
    if not invite.is_active:
        raise InviteRevokedError()

    # Rotate token + reset expiry
    raw_token, token_hash = _generate_invite_token()
    invite.token_hash = token_hash
    invite.expires_at = datetime.now(UTC) + timedelta(days=INVITE_EXPIRY_DAYS)
    db.add(invite)
    db.commit()
    db.refresh(invite)

    # Resend email
    role = None
    if invite.role_code:
        role = db.exec(
            select(TenantUserRole).where(TenantUserRole.code == invite.role_code)
        ).first()
    _send_invite_email(db, invite, role, raw_token)

    return invite, raw_token


def revoke_invite(
    db: Session,
    *,
    tenant_id: UUID,
    invite_id: UUID,
) -> TenantUserInvite:
    """Revoke an invite by setting is_active=False.

    Raises:
        InviteNotFoundError: invite not found in this tenant.
        InviteAlreadyAcceptedError: invite was already accepted.
    """
    invite = _get_tenant_invite(db, tenant_id, invite_id)
    if not invite:
        raise InviteNotFoundError()

    if invite.accepted_at is not None:
        raise InviteAlreadyAcceptedError()

    invite.is_active = False
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def validate_invite_token(db: Session, *, raw_token: str) -> TenantUserInvite | None:
    """Validate a raw invite token.

    Returns the invite row if valid (exists, not expired, not accepted,
    not revoked). Returns None for any failure mode (uniform 404 contract,
    design §G.9).
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.now(UTC)

    invite = db.exec(
        select(TenantUserInvite).where(TenantUserInvite.token_hash == token_hash)
    ).first()

    if not invite:
        return None
    if invite.accepted_at is not None:
        return None
    if not invite.is_active:
        return None
    if invite.expires_at <= now:
        return None
    return invite


def get_public_invite_data(db: Session, *, raw_token: str) -> TenantUserInvite | None:
    """Get invite + tenant data for the public landing page.

    Returns the invite row if valid (same conditions as validate_invite_token).
    The route resolves tenant_name from the tenant row.
    """
    return validate_invite_token(db, raw_token=raw_token)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_tenant_invite(
    db: Session, tenant_id: UUID, invite_id: UUID
) -> TenantUserInvite | None:
    """Fetch an invite scoped to a tenant (rules §4 — tenant-scoped select)."""
    return db.exec(
        select(TenantUserInvite)
        .where(TenantUserInvite.id == invite_id)
        .where(TenantUserInvite.tenant_id == tenant_id)
    ).first()


def _send_invite_email(
    db: Session,
    invite: TenantUserInvite,
    role: TenantUserRole | None,
    raw_token: str,
) -> None:
    """Render and send the team_invite email via render_and_send.

    Category=internal → tenant_id=None → Pilot standard branding.
    """
    from services.email_template_renderer import render_and_send

    # Resolve tenant name
    tenant = db.exec(select(Tenant).where(Tenant.id == invite.tenant_id)).first()
    tenant_name = tenant.name if tenant else "Pilot for Trades"

    role_name = role.name if role else "Team Member"

    base_url = _get_web_app_base_url()
    invite_url = f"{base_url}/invite/{raw_token}"

    # Format expiry date for display
    expires_date = invite.expires_at.strftime("%B %d, %Y")

    try:
        render_and_send(
            db,
            "team_invite",
            context={
                "invitee_email": invite.email,
                "tenant_name": tenant_name,
                "role_name": role_name,
                "invite_url": invite_url,
                "expires_date": expires_date,
            },
            to_address=invite.email,
        )
    except Exception:
        logger.exception(
            "Failed to send team_invite email to %s (non-fatal)", invite.email
        )


def compute_invite_status(invite: TenantUserInvite) -> str:
    """Compute the display status for an invite.

    Precedence (design §D2):
        accepted → revoked → expired → pending
    """
    if invite.accepted_at is not None:
        return "accepted"
    if not invite.is_active:
        return "revoked"
    if invite.expires_at <= datetime.now(UTC):
        return "expired"
    return "pending"
