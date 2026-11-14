"""
PLP-FIX-10 / INV-BUG-17 — Login recording Celery task (A72 session-history wiring).

Design: dev-docs/architecture-design/batch-designs/batch-plp-fix-10-design.md §F/§G.6

The A72 ``_upsert_session_history`` function (in ``api.routes.account_security``)
was built but never connected to a login event — ``user_session_history`` had
zero rows in the deployed environment. This task is enqueued by the Post-Authentication Lambda
on EVERY successful sign-in (new device or not) to upsert the session-history
row (``first_login_at`` / ``last_login_at`` / ``total_session_count``).

Two-layer pattern (inclusions §12):
  - ``_record_user_login_impl(tenant_id, user_id, db)`` — converts str UUIDs,
    calls ``_upsert_session_history``, returns a small result dict. Tested
    directly without Celery.
  - ``record_user_login`` — ``@celery_app.task(bind=True, max_retries=3,
    default_retry_delay=60)`` wrapper. Creates its own session via
    ``next(get_db())``, retries on transient DB errors, and on final failure
    **logs and returns without raising** (login telemetry must never page
    anyone — design §F; the Lambda caller is never-raise).

Sync ``def`` throughout (Rule 21). Parameters use str UUIDs — Celery does not
serialize UUID objects.
"""

import logging
import uuid as _uuid
from typing import Any

from sqlmodel import Session

from api.routes.account_security import _upsert_session_history
from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


def _record_user_login_impl(
    tenant_id: str, user_id: str, db: Session
) -> dict[str, Any]:
    """
    Core implementation — separated for testability (called without ``.delay()``).

    Converts str UUIDs, calls ``_upsert_session_history`` (the A72 upsert that
    was never wired), and returns a small result dict.

    Args:
        tenant_id: The tenant UUID string.
        user_id: The user UUID string.
        db: Database session to use.

    Returns:
        dict with 'status', 'tenant_id', 'user_id', 'total_session_count'.
    """
    tenant_uuid = _uuid.UUID(tenant_id)
    user_uuid = _uuid.UUID(user_id)

    row = _upsert_session_history(db, tenant_uuid, user_uuid)

    return {
        "status": "recorded",
        "tenant_id": str(row.tenant_id),
        "user_id": str(row.user_id),
        "total_session_count": row.total_session_count,
    }


@celery_app.task(
    name="record_user_login",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def record_user_login(self, tenant_id: str, user_id: str) -> dict[str, Any]:
    """
    Celery task: upsert ``user_session_history`` for the authenticated user.

    Enqueued by the Post-Authentication Lambda on every successful sign-in
    (new device or not). Retry posture matches house defaults; gives up
    quietly — login telemetry must never page anyone, and the Lambda caller
    is never-raise (design §F).

    Parameters (str UUIDs — Celery does not serialize UUID objects):
        tenant_id: The tenant UUID string.
        user_id: The user UUID string.

    Returns:
        dict with 'status' key: 'recorded' on success, 'failed' on give-up.
    """
    db: Session = next(get_db())

    try:
        return _record_user_login_impl(tenant_id, user_id, db)

    except self.MaxRetriesExceededError:
        logger.error(
            "record_user_login: max retries exceeded for tenant=%s user=%s",
            tenant_id,
            user_id,
        )
        return {
            "status": "failed",
            "reason": "max_retries_exceeded",
            "tenant_id": tenant_id,
            "user_id": user_id,
        }
    except Exception as exc:
        db.rollback()
        logger.error(
            "record_user_login: error for tenant=%s user=%s: %s",
            tenant_id,
            user_id,
            exc,
            exc_info=True,
        )
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "record_user_login: max retries exceeded (post-retry) for "
                "tenant=%s user=%s",
                tenant_id,
                user_id,
            )
            return {
                "status": "failed",
                "reason": "max_retries_exceeded",
                "tenant_id": tenant_id,
                "user_id": user_id,
            }
    finally:
        db.close()
