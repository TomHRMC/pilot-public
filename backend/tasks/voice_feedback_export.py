"""
Nightly Voice Feedback S3 Export Task.

Established in B2 (A6). Builds the training data pipeline for Llama fine-tuning.

Pattern: §17.1 Periodic Poll Task (no bind, no retry — log errors and move on)
Schedule: Daily at 2:00 AM UTC (added to beat_schedule in celery_app.py)
"""

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from core.celery_app import celery_app
from core.db import get_db

logger = logging.getLogger(__name__)


@celery_app.task(name="export_voice_feedback_to_s3")
def export_voice_feedback_to_s3() -> dict[str, int]:
    """
    Export unexported voice_feedback rows to S3 in model fine-tuning format.

    Format: JSONL — one JSON object per line:
    {"original": "...", "corrected": "...", "intent_misparsed": bool, "corrected_intent": "..."}

    S3 path: s3://pilot-voice-training/feedback/{YYYY}/{MM}/{DD}/{export_uuid}.jsonl

    Returns: {"exported": int, "errors": int}
    """
    db: Session = next(get_db())
    try:
        return _export_voice_feedback_impl(db)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in export_voice_feedback_to_s3: {e}")
        raise
    finally:
        db.close()


def _export_voice_feedback_impl(db: Session) -> dict[str, int]:
    """Inner implementation — separated for testability."""
    import boto3
    from sqlmodel import select

    from app.models.ai import VoiceFeedback
    from core.config import settings

    unexported = db.exec(
        select(VoiceFeedback).where(VoiceFeedback.exported_at.is_(None)).limit(1000)
    ).all()

    if not unexported:
        return {"exported": 0, "errors": 0}

    now_utc = datetime.now(UTC)
    export_uuid = str(uuid.uuid4())
    s3_key = f"feedback/{now_utc.strftime('%Y/%m/%d')}/{export_uuid}.jsonl"

    lines = []
    for row in unexported:
        lines.append(
            json.dumps(
                {
                    "original": row.original_transcription,
                    "corrected": row.corrected_text,
                    "intent_misparsed": row.intent_misparsed,
                    "corrected_intent": row.corrected_intent,
                    "feedback_notes": row.feedback_notes,
                    "tenant_id": str(row.tenant_id),
                    "created_at": row.created_at.isoformat(),
                }
            )
        )

    jsonl_content = "\n".join(lines).encode("utf-8")

    # Check if training bucket is configured
    training_bucket = getattr(settings, "VOICE_TRAINING_BUCKET", None)
    if not training_bucket:
        logger.warning(
            "VOICE_TRAINING_BUCKET env var not set — skipping S3 upload. "
            "Set this in AWS Secrets Manager before production deployment."
        )
        return {"exported": 0, "errors": 0}

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=training_bucket,
            Key=s3_key,
            Body=jsonl_content,
            ContentType="application/jsonl",
        )
    except Exception as e:
        logger.error(f"S3 upload failed for voice feedback export: {e}")
        return {"exported": 0, "errors": len(unexported)}

    # Mark all rows as exported
    for row in unexported:
        row.s3_export_key = s3_key
        row.exported_at = now_utc
        db.add(row)

    db.commit()
    logger.info(
        f"Exported {len(unexported)} voice feedback rows to s3://{training_bucket}/{s3_key}"
    )
    return {"exported": len(unexported), "errors": 0}
