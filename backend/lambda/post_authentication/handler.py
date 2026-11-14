"""
PLATFORM-SMS-B2 — Cognito Post-Authentication Lambda handler (new-device alert).

Design: dev-docs/architecture-design/batch-designs/batch-platform-sms-b2-design.md §F.3
ADR-0013 (three-pathway SMS model / Pathway C).

This handler fires on EVERY successful Cognito authentication
(triggerSource = "PostAuthentication_Authentication") — only after the full
auth flow (including MFA challenges) completes. It never fires on failed
logins or silent token refresh.

Gate: it enqueues a platform SMS (Sample 3 — new-device sign-in alert) ONLY
when ``event["request"]["newDeviceUsed"]`` is True. That field is populated
only because device tracking is set to "Always remember" (DevOps Part 2 enables
it). When the field is absent or False, the handler returns immediately.

On a new-device sign-in, the handler enqueues the existing B1 task
(``send_platform_account_notification_sms``) once per active tenant the user
belongs to, via a minimal Celery producer that writes directly to the Redis
broker (kombu transport). The task fans out to all verified+opted-in owner
endpoints of each tenant (the TCPA consent gate — design §G-7).

⚠️  The handler MUST NEVER raise to Cognito. An unhandled exception makes
    Cognito treat the authentication as failed — blocking the user's sign-in.
    Every path is wrapped so that any error is logged and swallowed
    (``return event``).

Identity join key: ``user.email`` (citext → case-insensitive). MCP-verified
2026-08-14: the ``user`` table has NO ``cognito_sub`` column; the
Post-Confirmation Lambda already joins by email — same pattern (design §G-9).

Resource resolution (mirrors ``post_confirmation/handler.py``):
  - ``_resolve_db_url()`` — env ``DATABASE_URL`` → else ``DB_SECRET_ARN`` via
    Secrets Manager (boto3, pre-bundled in the Lambda runtime), JSON ``url``.
  - ``_resolve_broker_url()`` — env ``CELERY_BROKER_URL`` → else
    ``REDIS_SECRET_ARN`` via Secrets Manager, JSON ``broker_url`` key.
    (Lambda env vars are plain strings — cannot use the ECS-style
    ``${secret_arn}:json_key::`` extraction; same resolution pattern as the
    DB URL. The ``broker_url`` key name is verified in
    ``infrastructure/terraform/modules/compute/main.tf`` line 222.)
  - ``_get_producer()`` — lazy minimal ``Celery("pilot_lambda_producer",
    broker=...)`` created once per warm start. Does NOT import
    ``core.celery_app`` (which would drag FastAPI/config into the Lambda
    package).

ORM imports only: ``User`` from ``app.models.core``, ``TenantUser`` from
``app.models.auth`` — no FastAPI/route/service imports.

Packaging deps (DevOps Part 2): ``psycopg2-binary``, ``sqlalchemy``,
``sqlmodel``, ``celery`` (kombu arrives transitively). ``boto3``/``botocore``
are NOT packaged — pre-bundled in the AWS Lambda Python runtime, imported
lazily by the resolve functions only when the env vars are unset (i.e. in
Lambda, not local dev/tests).
"""

import logging
import os
import uuid
from contextlib import contextmanager

from celery import Celery
from sqlmodel import Session, create_engine, select

from app.models.auth import TenantUser
from app.models.core import User

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Module-level caches for Lambda warm-start reuse.
_engine = None
_producer = None

# The Celery task name (registered in core.celery_app; enqueued by name here
# so this package does NOT import core.celery_app).
_TASK_NAME = "send_platform_account_notification_sms"

# PLP-FIX-10/INV-BUG-17: the login-recording task name (A72 session-history).
_LOGIN_TASK_NAME = "record_user_login"

# The notification type code for Sample 3 (campaign CXXXXXX).
_TYPE_CODE = "platform_security_new_device"


# ==================== RESOURCE RESOLUTION ====================


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
            "configure the RDS connection for the Post-Authentication Lambda."
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


def _resolve_broker_url() -> str:
    """
    Resolve the Celery/Redis broker URL.

    Resolution order (mirrors ``_resolve_db_url`` — Lambda env vars are plain
    strings, cannot use the ECS-style ``${secret_arn}:json_key::`` extraction):
      1. ``CELERY_BROKER_URL`` env var if set (local dev / tests / explicit
         override — the same key the ECS worker task consumes).
      2. Else fetch the Redis secret from AWS Secrets Manager via
         ``REDIS_SECRET_ARN`` at runtime using the Lambda execution role and
         read its ``broker_url`` field (key name verified in
         ``compute/main.tf`` line 222).

    Never logs the URL — it may embed the Redis password.
    """
    broker_url = os.environ.get("CELERY_BROKER_URL")
    if broker_url:
        return broker_url

    secret_arn = os.environ.get("REDIS_SECRET_ARN")
    if not secret_arn:
        raise RuntimeError(
            "Neither CELERY_BROKER_URL nor REDIS_SECRET_ARN is set — DevOps "
            "must configure the Redis broker for the Post-Authentication Lambda."
        )

    import json

    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_arn)
    except ClientError:
        logger.exception("Failed to fetch Redis secret from Secrets Manager")
        raise
    secret = response.get("SecretString")
    if not secret:
        raise RuntimeError(f"Redis secret {secret_arn} has no SecretString")
    try:
        payload = json.loads(secret)
    except (ValueError, TypeError):
        raise RuntimeError(f"Redis secret {secret_arn} is not valid JSON")
    broker_url = payload.get("broker_url")
    if not broker_url:
        raise RuntimeError(
            f"Redis secret {secret_arn} has no 'broker_url' field — "
            "DevOps must populate it"
        )
    return broker_url


def _get_engine():
    """Lazily create and cache the SQLAlchemy engine (warm-start reuse)."""
    global _engine
    if _engine is None:
        _engine = create_engine(_resolve_db_url(), pool_pre_ping=True)
    return _engine


def _get_producer() -> Celery:
    """
    Lazily create and cache a minimal Celery producer (warm-start reuse).

    Uses the kombu transport (no worker, no app import). Does NOT import
    ``core.celery_app`` — that would drag FastAPI/config into the Lambda
    package. The producer only needs to serialize a task message to the broker.
    """
    global _producer
    if _producer is None:
        _producer = Celery("pilot_lambda_producer", broker=_resolve_broker_url())
    return _producer


@contextmanager
def _session_scope():
    """Yield a Session and ensure it is closed."""
    session = Session(_get_engine())
    try:
        yield session
    finally:
        session.close()


# ==================== ENTRY POINT ====================


def handler(event: dict, context) -> dict:
    """
    Cognito Post Authentication trigger entry point
    (triggerSource = "PostAuthentication_Authentication").

    Fires only after FULLY successful auth (incl. MFA) — never on failed
    logins, never on silent token refresh.

    PLP-FIX-10/INV-BUG-17: login recording (``record_user_login``) fires on
    EVERY successful authentication — new device or not. Device alerts
    (Sample 3) are still gated on ``newDeviceUsed=True``.

    ⚠️  NEVER raises: any exception is logged and ``event`` is returned — an
        unhandled raise would fail the user's sign-in.

    Returns the ``event`` dict so Cognito completes the auth flow.
    """
    try:
        # 1. Extract the email (identity join key — §G-9). Needed for both
        #    login recording and device alerts, so it comes first (before the
        #    newDeviceUsed gate).
        try:
            email = event["request"]["userAttributes"]["email"]
        except (KeyError, TypeError):
            logger.warning(
                "Post-Authentication: no email in userAttributes — "
                "returning event unchanged"
            )
            return event
        if not email or not isinstance(email, str):
            logger.warning(
                "Post-Authentication: empty/non-string email — returning "
                "event unchanged"
            )
            return event
        email = email.strip().lower()

        new_device_used = event.get("request", {}).get("newDeviceUsed") is True

        # 2–5. Resolve user, fan out per active tenant, enqueue.
        with _session_scope() as db:
            _process_authentication(db, email, new_device_used)
    except Exception:
        logger.exception(
            "Post-Authentication handler error (swallowed, returning event)"
        )
    return event


def _process_authentication(db: Session, email: str, new_device_used: bool) -> None:
    """
    Resolve the user by email, then:
      - ALWAYS enqueue ``record_user_login`` per active tenant (INV-BUG-17).
      - If ``new_device_used``: also enqueue device alerts per tenant.

    Both enqueues ride the never-raise posture of the handler entry point.
    """
    user = _resolve_user(db, email)
    if user is None:
        return

    tenant_ids = _resolve_tenant_ids(db, user.id)
    if not tenant_ids:
        logger.info(
            "Post-Authentication: user %s has no active tenants — no "
            "login recording or alert",
            email,
        )
        return

    producer = _get_producer()

    # PLP-FIX-10/INV-BUG-17: login recording fires on EVERY successful auth.
    _enqueue_login_recording(producer, tenant_ids, user.id, email)

    # Device alerts are gated on newDeviceUsed (unchanged behavior).
    if new_device_used:
        _enqueue_new_device_alerts(producer, tenant_ids, user.id, email)


def _resolve_user(db: Session, email: str) -> User | None:
    """Resolve the user by email (citext → case-insensitive)."""
    user = db.exec(
        select(User).where(User.email == email, User.is_active == True)
    ).first()
    if user is None:
        logger.info(
            "Post-Authentication: no active user for email=%s — no alert", email
        )
    return user


def _resolve_tenant_ids(db: Session, user_id: uuid.UUID) -> list:
    """Resolve all active tenant_ids for this user (multi-tenant fan-out)."""
    return db.exec(
        select(TenantUser.tenant_id).where(
            TenantUser.user_id == user_id,
            TenantUser.is_active == True,
        )
    ).all()


def _enqueue_login_recording(
    producer: Celery,
    tenant_ids: list,
    user_id: uuid.UUID,
    email: str,
) -> None:
    """Enqueue ``record_user_login`` per resolved tenant (INV-BUG-17).

    Login recording fires on EVERY successful authentication — new device or
    not. Each tenant gets its own task carrying the same user id (multi-tenant
    fan-out preserved).
    """
    for tid in tenant_ids:
        producer.send_task(
            _LOGIN_TASK_NAME,
            kwargs={
                "tenant_id": str(tid),
                "user_id": str(user_id),
            },
        )
        logger.info(
            "Post-Authentication: enqueued %s for tenant=%s user=%s",
            _LOGIN_TASK_NAME,
            tid,
            email,
        )


def _enqueue_new_device_alerts(
    producer: Celery,
    tenant_ids: list,
    user_id: uuid.UUID,
    email: str,
) -> None:
    """
    Enqueue one Sample 3 (new-device alert) task per active tenant.

    No ``template_context`` — Sample 3 is static. No explicit queue — the
    worker consumes the default ``celery`` queue (design §G-6).

    Each task carries the authenticated user's id so the worker resolves the
    user's own endpoints (PLP-FIX-8 / INV-BUG-4), not the tenant owner's.
    """
    for tid in tenant_ids:
        producer.send_task(
            _TASK_NAME,
            kwargs={
                "tenant_id": str(tid),
                "type_code": _TYPE_CODE,
                "recipient_user_id": str(user_id),
            },
        )
        logger.info(
            "Post-Authentication: enqueued %s for tenant=%s user=%s "
            "recipient_user_id=%s",
            _TASK_NAME,
            tid,
            email,
            user_id,
        )
