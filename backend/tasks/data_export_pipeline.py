"""
Celery task: process a pending data export request — B13/A71.

Registered in core/celery_app.py as event-driven (no Beat schedule).
Enqueued via .delay() from POST /api/v1/users/me/data-exports.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


@celery_app.task(
    name="process_data_export",
    bind=True,
    max_retries=3,
)
def process_data_export(self, export_id: str) -> dict[str, Any]:
    """
    Process a pending data_export_request row.

    Steps:
      1. Load export_request, set status="processing"
      2. Call data_export_compiler.stream_export_to_s3()
      3. Set status="ready", s3_path, signed_url, expires_at
      4. Dispatch email via existing email_service.py
      5. On failure: set status="failed", failure_reason

    Args:
        export_id: UUID string of the data_export_request.

    Retries: up to 3 times with 60-second countdown on transient errors.
    """
    db: Session = next(get_db())

    try:
        result = _process_data_export_impl(export_id, db)
        return result

    except ValueError as e:
        # Don't retry validation errors
        db.rollback()
        logger.error(f"Validation error processing export {export_id}: {e}")
        _mark_failed(export_id, str(e), db)
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing export {export_id}: {e}")
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


def _process_data_export_impl(export_id: str, db: Session) -> dict[str, Any]:
    """Inner implementation — separated for testability without Celery."""
    from app.models.security import DataExportRequest
    from services.data_export_compiler import ExportScopeError, stream_export_to_s3

    export_uuid = UUID(export_id)

    # Step 1: Load and mark as processing
    export = db.exec(
        select(DataExportRequest).where(DataExportRequest.export_id == export_uuid)
    ).first()

    if not export:
        raise ValueError(f"DataExportRequest {export_id} not found")

    if export.status != "pending":
        logger.warning(
            f"Export {export_id} is not pending (status={export.status}), skipping"
        )
        return {"status": export.status, "export_id": export_id}

    export.status = "processing"
    db.add(export)
    db.commit()
    db.refresh(export)

    try:
        # Step 2: Stream to S3
        s3_path, signed_url = stream_export_to_s3(
            db=db,
            tenant_id=export.tenant_id,
            user_id=export.user_id,
            data_scope=export.data_scope,
            export_id=export_uuid,
        )

        # Step 3: Mark as ready
        now = datetime.now(UTC)
        export.status = "ready"
        export.s3_path = s3_path
        export.signed_url = signed_url
        export.expires_at = now + timedelta(days=7)
        db.add(export)
        db.commit()

        # MKT-B11: data_exports feature code deleted — data exports are now unlimited
        # and untracked. Usage ledger write removed entirely. No entitlement check needed.

        # Step 4: Send email notification
        try:
            _send_export_ready_email(export.user_id, export.tenant_id, signed_url, db)
        except Exception as email_err:
            logger.warning(f"Export email failed for {export_id}: {email_err}")

        logger.info(f"Data export {export_id} completed successfully")
        return {"status": "ready", "export_id": export_id, "s3_path": s3_path}

    except ExportScopeError as e:
        _mark_failed(export_id, str(e), db)
        raise ValueError(str(e))
    except Exception as e:
        _mark_failed(export_id, str(e), db)
        raise


def _mark_failed(export_id: str, reason: str, db: Session) -> None:
    """Mark an export as failed with a reason string."""
    from app.models.security import DataExportRequest

    try:
        export = db.exec(
            select(DataExportRequest).where(
                DataExportRequest.export_id == UUID(export_id)
            )
        ).first()
        if export:
            export.status = "failed"
            export.failure_reason = reason[:500]  # cap at 500 chars
            db.add(export)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to mark export {export_id} as failed: {e}")


def _send_export_ready_email(
    user_id: UUID,
    tenant_id: UUID,
    signed_url: str,
    db: Session,
) -> None:
    """Send 'your data export is ready' email via email_service."""
    from app.models.core import User
    from services.email_service import send_email  # type: ignore

    user = db.exec(select(User).where(User.id == user_id)).first()
    if not user:
        return

    send_email(
        to_email=user.email if hasattr(user, "email") else None,
        subject="Your Pilot data export is ready",
        body=(
            f"Your data export is ready for download.\n\n"
            f"Download link (expires in 7 days):\n{signed_url}\n\n"
            "This link will expire in 7 days."
        ),
    )
