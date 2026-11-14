"""
SIGNUP-GA-1 — Cognito Post-Confirmation Lambda handler (3-path router).

Design: dev-docs/architecture-design/batch-designs/batch-signup-ga-1-design.md §A.2, §F
ADR-0011 (self-sign-up → Lambda) + ADR-0012 (drop tenant-name uniqueness).

This handler fires on EVERY Cognito confirmation in the pool and must ROUTE,
not blindly create a tenant. The 4 user types map to 3 code paths:

  Path 1 — existing/platform user (types i, ii, or a re-fire): a `user` row
           already exists for `email` → NO-OP. Idempotent.
  Path 2 — pending-invite attach (type iv): a pending `tenant_user_invite`
           (accepted_at IS NULL, is_active, not expired) exists → create the
           `user`, attach `tenant_user` to invite.tenant_id, set accepted_at.
           Do NOT create a tenant.
  Path 3 — new-owner create (type iii, self-serve GA): no `user`, no pending
           invite → create `tenant` (placeholder name), owner `user`,
           `tenant_user(owner, joined_at=now)`, owner role/status.

⚠️  The handler MUST NEVER raise to Cognito. An unhandled exception makes
    Cognito treat the confirmation as failed and can strand the user in an
    unconfirmed/limbo state. Every path is wrapped so that any error is
    logged and swallowed (return `event`).

Audit context note: the Lambda has no authenticated app user. It mirrors
`api/routes/auth.py::_signup_impl`, which does NOT call
`set_audit_context_sync()` — so audit_log rows from this handler will have
`actor_id = NULL` (system-initiated). This is the existing behavior for the
dev/test stand-in and is accepted for the prod Lambda. Do not block a
confirmation on audit context.

Dependencies (DevOps packaging): psycopg2-binary, sqlalchemy, sqlmodel.
``boto3``/``botocore`` are NOT packaged — they are pre-bundled in the AWS
Lambda Python runtime and imported lazily by ``_resolve_db_url()`` only when
``DATABASE_URL`` is unset (i.e. in Lambda, not local dev/tests).
The handler imports only the SQLModel ORM classes (lightweight); it does NOT
import the FastAPI app or any route/service modules.
"""

import logging
import os
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlmodel import Session, create_engine, select

from app.models.auth import (
    TenantUser,
    TenantUserInvite,
    TenantUserRole,
    TenantUserStatus,
)
from app.models.core import Tenant, User, UserEndpoint

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Module-level engine cache for Lambda warm-start reuse.
_engine = None


# ==================== DB CONNECTION (production) ====================


def _resolve_db_url() -> str:
    """
    Resolve the SQLAlchemy connection URL.

    Resolution order (secret-management-policy compliant — never hardcode):
      1. ``DATABASE_URL`` env var if set (local dev / tests / explicit override).
      2. Else fetch the RDS secret from AWS Secrets Manager via ``DB_SECRET_ARN``
         at runtime using the Lambda execution role (boto3 is pre-bundled in the
         Lambda runtime — NOT packaged by DevOps) and read its ``url`` field.

    The secret ``pilot/prod/db`` is stored as JSON:
      {"username","password","host","port","dbname","url"}  (see database module).

    Never logs the URL — it embeds the DB password.
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    secret_arn = os.environ.get("DB_SECRET_ARN")
    if not secret_arn:
        raise RuntimeError(
            "Neither DATABASE_URL nor DB_SECRET_ARN is set — DevOps must "
            "configure the RDS connection for the Post-Confirmation Lambda."
        )

    # boto3 is provided by the AWS Lambda Python runtime; import lazily so
    # local dev/tests that do not have boto3 installed are unaffected.
    import json

    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_arn)
    except ClientError:
        logger.exception("Failed to fetch RDS secret from Secrets Manager")
        raise
    secret = response.get("SecretString")
    if not secret:
        raise RuntimeError(f"RDS secret {secret_arn} has no SecretString")
    try:
        payload = json.loads(secret)
    except (ValueError, TypeError):
        raise RuntimeError(f"RDS secret {secret_arn} is not valid JSON")
    db_url = payload.get("url")
    if not db_url:
        raise RuntimeError(
            f"RDS secret {secret_arn} has no 'url' field — DevOps must populate it"
        )
    return db_url


def _get_engine():
    """Lazily create and cache the SQLAlchemy engine (warm-start reuse)."""
    global _engine
    if _engine is None:
        _engine = create_engine(_resolve_db_url(), pool_pre_ping=True)
    return _engine


@contextmanager
def _session_scope():
    """Yield a Session and ensure it is closed."""
    session = Session(_get_engine())
    try:
        yield session
    finally:
        session.close()


# ==================== ENTRY POINT ====================


def handler(event, context):
    """
    Cognito Post-Confirmation trigger entry point.

    Cognito calls ``handler.handler`` (this function). It MUST return the
    ``event`` dict so Cognito completes the confirmation flow. Any exception
    is logged and swallowed — never propagated.
    """
    try:
        email = _extract_email(event)
        if not email:
            logger.warning("No email found in Cognito event; returning event unchanged")
            return event

        with _session_scope() as db:
            _route_confirmation(db, email)
    except Exception:
        logger.exception("Post-Confirmation handler error (swallowed, returning event)")
    return event


# ==================== ROUTER ====================


def _extract_email(event) -> str | None:
    """Extract and normalize the email from the Cognito event dict."""
    try:
        email = event["request"]["userAttributes"]["email"]
        if not email or not isinstance(email, str):
            return None
        return email.strip().lower()
    except (KeyError, TypeError, AttributeError):
        return None


def _route_confirmation(db: Session, email: str) -> None:
    """
    3-path router keyed on ``email`` (design §A.2).

    Routing order:
      1. Path 1 — a ``user`` row already exists → no-op (idempotent).
      2. Path 2 — a pending ``tenant_user_invite`` exists → attach.
      3. Path 3 — neither → new-owner create.
    """
    # Path 1: existing user → no-op
    existing_user = db.exec(select(User).where(User.email == email)).first()
    if existing_user:
        logger.info("Path 1: existing user %s, no-op", email)
        return

    # Path 2: pending invite → attach
    invite = _find_pending_invite(db, email)
    if invite:
        logger.info(
            "Path 2: pending invite for %s, attaching to tenant %s",
            email,
            invite.tenant_id,
        )
        _path2_attach_invite(db, email, invite)
        return

    # Path 3: new owner → create
    logger.info("Path 3: new owner %s, creating tenant", email)
    _path3_create_owner(db, email)


# ==================== PATH 2 — INVITE ATTACH ====================


def _find_pending_invite(db: Session, email: str) -> TenantUserInvite | None:
    """
    Find the most recent pending, active, non-expired invite for ``email``.

    Conditions (design §A.2 Path 2):
      - ``accepted_at IS NULL`` (not yet accepted)
      - ``is_active = true``
      - ``expires_at > now()``
    """
    now = datetime.now(UTC)
    return db.exec(
        select(TenantUserInvite)
        .where(TenantUserInvite.email == email)
        .where(TenantUserInvite.accepted_at.is_(None))
        .where(TenantUserInvite.is_active == True)
        .where(TenantUserInvite.expires_at > now)
        .order_by(TenantUserInvite.expires_at.desc())
    ).first()


def _path2_attach_invite(db: Session, email: str, invite: TenantUserInvite) -> None:
    """
    Path 2: create ``user`` + ``user_endpoint``, attach ``tenant_user`` to
    the invite's tenant, set ``invite.accepted_at``. No tenant created.
    """
    try:
        user = User(email=email)
        db.add(user)
        db.flush()

        endpoint = UserEndpoint(
            user_id=user.id,
            channel="email",
            value=email,
            is_primary=True,
            verification_status="pending",
        )
        db.add(endpoint)

        # TEAM-INVITE-1: role carried on the invite; NULL = pre-TEAM-INVITE-1
        # rows → technician fallback (design §F.3).
        role_code = invite.role_code if invite.role_code else "technician"
        role = _get_or_create_role(db, role_code)
        status = _get_or_create_status(db, "active")

        tenant_user = TenantUser(
            tenant_id=invite.tenant_id,
            user_id=user.id,
            role_code=role.code,
            status_id=status.id,
            joined_at=datetime.now(UTC),
        )
        db.add(tenant_user)

        invite.accepted_at = datetime.now(UTC)
        db.add(invite)

        db.commit()
        logger.info(
            "Path 2 complete: user %s attached to tenant %s",
            email,
            invite.tenant_id,
        )

        # TEAM-INVITE-1: best-effort usage counter (design §F.3, §G.7).
        # Mirrors tier_limit_enforcer.increment_user_count() inline (the
        # Lambda never imports services — packaging constraint). Separate
        # transaction so analytics can never rollback the attach (ADR-0011
        # never-raise invariant). Canonical function:
        # backend/services/tier_limit_enforcer.py:increment_user_count()
        try:
            _increment_user_count_best_effort(db, invite.tenant_id)
        except Exception:
            logger.warning(
                "Usage counter increment failed for tenant %s (non-fatal)",
                invite.tenant_id,
            )
    except Exception:
        db.rollback()
        raise


# ==================== TEAM-INVITE-1: BEST-EFFORT USAGE COUNTER ====================


def _increment_user_count_best_effort(db: Session, tenant_id) -> None:
    """Best-effort usage counter increment (design §F.3, §G.7).

    Mirrors ``tier_limit_enforcer.increment_user_count()`` inline — the
    Lambda never imports services (packaging constraint). Runs in its own
    transaction so analytics can never rollback the attach (ADR-0011).

    Canonical function: backend/services/tier_limit_enforcer.py:increment_user_count()
    """
    from app.models.subscription import TenantSubscriptionUsage

    now = datetime.now(UTC)
    usage = db.exec(
        select(TenantSubscriptionUsage)
        .where(TenantSubscriptionUsage.tenant_id == tenant_id)
        .where(TenantSubscriptionUsage.period_end >= now)
        .order_by(TenantSubscriptionUsage.period_end)
        .limit(1)
    ).first()

    if usage:
        usage.current_user_count = max(0, usage.current_user_count + 1)
        db.add(usage)
        db.commit()
    else:
        # Create initial usage row for current period (monthly aligned)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1)

        new_usage = TenantSubscriptionUsage(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            current_user_count=1,
            current_sms_segment_count=0,
        )
        db.add(new_usage)
        db.commit()


# ==================== PATH 3 — NEW OWNER CREATE ====================


def _path3_create_owner(db: Session, email: str) -> None:
    """
    Path 3: create ``tenant`` (placeholder name) + owner ``user`` +
    ``tenant_user(owner, joined_at=now)`` + role/status.

    The placeholder name ``"{local_part}'s Company"`` is inserted
    UNCONDITIONALLY — no collision check, no UUID suffix (ADR-0012 dropped
    ``tenant_name_key``). The wizard step-1 (``initiate_signup``) overwrites
    it with the real ``business_name``.
    """
    try:
        local_part = email.split("@")[0]
        placeholder_name = f"{local_part}'s Company"

        # Tenant — placeholder name, unconditional (ADR-0012).
        # The before_insert event listener auto-assigns the trial tier.
        tenant = Tenant(name=placeholder_name, is_active=True)
        db.add(tenant)
        db.flush()

        user = User(email=email)
        db.add(user)
        db.flush()

        endpoint = UserEndpoint(
            user_id=user.id,
            channel="email",
            value=email,
            is_primary=True,
            verification_status="pending",
        )
        db.add(endpoint)

        # Role/status resolution mirrors _signup_impl exactly (parity).
        role = _get_or_create_role(db, "owner")
        status = _get_or_create_status(db, "active")

        tenant_user = TenantUser(
            tenant_id=tenant.id,
            user_id=user.id,
            role_code=role.code,
            status_id=status.id,
            joined_at=datetime.now(UTC),
        )
        db.add(tenant_user)

        db.commit()
        logger.info(
            "Path 3 complete: tenant %s + owner %s created",
            tenant.id,
            email,
        )
    except Exception:
        db.rollback()
        raise


# ==================== SHARED HELPERS (mirror _signup_impl) ====================


def _get_or_create_role(db: Session, code: str) -> TenantUserRole:
    """Get or create a TenantUserRole by code (mirrors _signup_impl)."""
    role = db.exec(select(TenantUserRole).where(TenantUserRole.code == code)).first()
    if not role:
        role = TenantUserRole(code=code, name=code.capitalize(), is_default=True)
        db.add(role)
        db.flush()
    return role


def _get_or_create_status(db: Session, code: str) -> TenantUserStatus:
    """Get or create a TenantUserStatus by code (mirrors _signup_impl)."""
    status = db.exec(
        select(TenantUserStatus).where(TenantUserStatus.code == code)
    ).first()
    if not status:
        status = TenantUserStatus(code=code, name=code.capitalize(), is_default=True)
        db.add(status)
        db.flush()
    return status
