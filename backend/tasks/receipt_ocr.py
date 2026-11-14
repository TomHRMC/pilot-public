"""
tasks/receipt_ocr.py

Celery task for receipt OCR processing pipeline (FIND-062/B21/A96).

Task: process_receipt_ocr
  - Triggered on-demand via .delay() from photos.py complete-upload handler
  - Downloads receipt from S3 via RapidOcrService (or MockOcrService in dev)
  - Updates job_expense.cost_cents if OCR result is high-confidence
  - Sets ocr_processed_at + ocr_source on job_expense row

Pattern: §17.2 Event-driven task (triggered by upload completion event).
No Beat entry — triggered exclusively from the complete-upload endpoint.

GPU note: RapidOCR runs on CPU in ECS Fargate app container.
Do NOT route to g4dn.xlarge GPU instance (reserved for Whisper + Ollama).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from core.celery_app import celery_app
from core.db import get_db
from services.ocr_service import get_ocr_service

logger = logging.getLogger(__name__)


@celery_app.task(name="receipt_ocr.process_receipt_ocr", bind=True, max_retries=3)
def process_receipt_ocr(self, attachment_id: str) -> dict:
    """
    Process receipt OCR for a completed photo upload.

    Args:
        attachment_id: UUID string of the job_attachment row whose receipt_object_key
                       should be OCR-processed.

    Returns:
        dict with keys:
          - status: "applied" | "skipped" | "error" | "no_attachment" | "no_receipt_key" | "no_expense"
          - attachment_id: the input attachment_id
          - (optional) total_cents: extracted amount if status="applied"
          - (optional) error: error message if status="error"

    Idempotency:
        Re-processing the same attachment_id is safe — subsequent runs will set
        ocr_processed_at again but will not create duplicate rows.
    """
    import uuid as _uuid

    from sqlmodel import select

    from app.models.fulfillment import JobAttachment, JobExpense

    db = next(get_db())
    try:
        # 1. Look up the job_attachment row
        try:
            attachment_uuid = _uuid.UUID(attachment_id)
        except ValueError:
            logger.error("process_receipt_ocr: invalid attachment_id=%s", attachment_id)
            return {
                "status": "error",
                "attachment_id": attachment_id,
                "error": "invalid UUID",
            }

        attachment = db.exec(
            select(JobAttachment).where(JobAttachment.id == attachment_uuid)
        ).first()

        if not attachment:
            logger.warning(
                "process_receipt_ocr: attachment not found id=%s", attachment_id
            )
            return {"status": "no_attachment", "attachment_id": attachment_id}

        # 2. Find the linked job_expense (via expense_id FK on job_attachment)
        # Only receipt-linked attachments (those with expense_id) need OCR
        if not attachment.expense_id:
            logger.debug(
                "process_receipt_ocr: attachment %s has no expense_id — not a receipt photo",
                attachment_id,
            )
            return {"status": "no_expense", "attachment_id": attachment_id}

        expense = db.exec(
            select(JobExpense)
            .where(JobExpense.id == attachment.expense_id)
            .where(JobExpense.is_active == True)
        ).first()

        if not expense:
            logger.warning(
                "process_receipt_ocr: expense %s not found or inactive for attachment %s",
                attachment.expense_id,
                attachment_id,
            )
            return {"status": "no_expense", "attachment_id": attachment_id}

        # 3. Run OCR — use the attachment's S3 object key (the uploaded photo file)
        ocr = get_ocr_service()
        result = ocr.extract_expense(attachment.object_key)

        now = datetime.now(UTC)

        if result is None:
            # Low confidence or no text — mark processed but don't update cost
            expense.ocr_processed_at = now
            # ocr_source stays None to indicate no usable result
            db.add(expense)
            db.commit()
            logger.info(
                "process_receipt_ocr: OCR returned no result (low confidence) for attachment %s",
                attachment_id,
            )
            return {"status": "skipped", "attachment_id": attachment_id}

        # 4. Apply OCR result to job_expense
        total_cents = result.get("total_cents")
        if total_cents and isinstance(total_cents, int) and total_cents > 0:
            expense.cost_cents = total_cents

        expense.ocr_processed_at = now
        expense.ocr_source = "rapidocr"
        db.add(expense)
        db.commit()

        logger.info(
            "process_receipt_ocr: applied OCR result total_cents=%s for attachment %s expense %s",
            total_cents,
            attachment_id,
            expense.id,
        )
        return {
            "status": "applied",
            "attachment_id": attachment_id,
            "total_cents": total_cents,
        }

    except Exception as exc:
        db.rollback()
        logger.error(
            "process_receipt_ocr: unexpected error for attachment %s: %s",
            attachment_id,
            exc,
            exc_info=True,
        )
        # Retry with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=2**self.request.retries * 30)
        except self.MaxRetriesExceededError:
            return {
                "status": "error",
                "attachment_id": attachment_id,
                "error": str(exc),
            }
    finally:
        db.close()
