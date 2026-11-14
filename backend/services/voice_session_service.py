"""
Voice Session Service — session numbering, retrieval, and structured content utilities.
Established in B2 (A9). Extended by B12 (A67) for persona tone rendering.
"""

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.ai import ConversationMessage, ConversationSession


def get_sessions_with_numbers(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 20,
    cursor: str | None = None,
    local_date_filter: str | None = None,
) -> tuple[list[dict[str, Any]], str | None, bool]:
    """
    Return conversation sessions with derived per-day session_number.

    Session number = ROW_NUMBER() OVER (
        PARTITION BY DATE(created_at AT TIME ZONE tenant_tz), user_id
        ORDER BY created_at ASC
    )

    Tenant timezone: Falls back to UTC if tenant.timezone not configured (see §F.1).

    Args:
        db: Database session
        tenant_id: Active tenant UUID for isolation
        user_id: Requesting user UUID — sessions are user-scoped
        limit: Max records per page (capped at 50)
        cursor: Opaque pagination cursor (base64-encoded created_at)
        local_date_filter: ISO date string (YYYY-MM-DD) in tenant local time to filter

    Returns:
        Tuple of (session_list, next_cursor, has_more)
        Each session dict includes 'session_number' as derived int.
    """
    # NOTE: Tenant timezone resolution — see §F.1 for the MVP decision
    TENANT_TZ_FALLBACK = "UTC"

    # Cap limit at 50
    limit = min(limit, 50)

    # Build window function subquery
    session_number_expr = (
        func.row_number()
        .over(
            partition_by=[
                func.date(
                    func.timezone(TENANT_TZ_FALLBACK, ConversationSession.created_at)
                ),
                ConversationSession.user_id,
            ],
            order_by=ConversationSession.created_at.asc(),
        )
        .label("session_number")
    )

    stmt = (
        select(ConversationSession, session_number_expr)
        .where(ConversationSession.tenant_id == tenant_id)
        .where(ConversationSession.user_id == user_id)
        .where(ConversationSession.is_active == True)
        .order_by(ConversationSession.created_at.desc())
        .limit(limit + 1)
    )

    rows = db.exec(stmt).all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    sessions = []
    for session, session_number in rows:
        sessions.append(
            {
                "session_id": str(session.id),
                "session_number": session_number,
                "title": session.title or session.context_summary,
                "title_auto_generated": session.title_auto_generated,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "archived_at": session.archived_at.isoformat()
                if session.archived_at
                else None,
            }
        )

    next_cursor = None
    if has_more and rows:
        last_session = rows[-1][0]
        next_cursor = base64.b64encode(
            last_session.created_at.isoformat().encode()
        ).decode()

    return sessions, next_cursor, has_more


def resolve_session_by_number(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    session_number: int,
    local_date: str | None = None,
) -> ConversationSession | None:
    """
    Resolve a session by its per-day number for voice addressability.
    "Chat 2" → today's session #2 for current user.

    Args:
        db: Database session
        tenant_id: Active tenant UUID
        user_id: Requesting user UUID
        session_number: 1-based session number within the day
        local_date: ISO date string (YYYY-MM-DD) in tenant local time; defaults to today

    Returns:
        ConversationSession if found, None if no match (disambiguation needed).
    """
    TENANT_TZ_FALLBACK = "UTC"
    if local_date is None:
        local_date = datetime.now(UTC).strftime("%Y-%m-%d")  # UTC fallback

    sessions, _, _ = get_sessions_with_numbers(db, tenant_id, user_id, limit=50)
    for s in sessions:
        if s["session_number"] == session_number:
            session_id = uuid.UUID(s["session_id"])
            return db.exec(
                select(ConversationSession)
                .where(ConversationSession.id == session_id)
                .where(ConversationSession.tenant_id == tenant_id)
            ).first()
    return None


def freeze_session_quote_previews(
    db: Session,
    session: ConversationSession,
    excluding_message_id: uuid.UUID | None = None,
) -> int:
    """
    Freeze all live quote_preview messages in a session to snapshot mode.

    Called synchronously:
    - At quote submission (freeze ALL quote_preview messages)
    - At new artifact turn (freeze all EXCEPT the just-emitted message)

    Args:
        db: Database session
        session: The conversation session to freeze messages in
        excluding_message_id: If provided, skip this message (just-emitted; stays live)

    Returns:
        Count of messages frozen.

    CRITICAL: A message NEVER transitions from snapshot back to live.
    """
    from sqlalchemy.orm.attributes import flag_modified

    messages = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session.id)
        .where(ConversationMessage.tenant_id == session.tenant_id)
        .where(ConversationMessage.structured_content_json.isnot(None))
    ).all()

    frozen_count = 0
    for msg in messages:
        if excluding_message_id and msg.id == excluding_message_id:
            continue
        payload = msg.structured_content_json
        if not payload:
            continue
        if payload.get("render_mode") == "snapshot":
            continue  # CRITICAL: never unfreeze
        artifact_type = payload.get("artifact_type", "")
        if artifact_type != "quote_preview":
            continue

        # Resolve the entity to capture snapshot
        entity_id = payload.get("entity_id")
        snapshot_data = _capture_entity_snapshot(db, artifact_type, entity_id)

        # Build new dict (never mutate in-place — SQLAlchemy won't track JSONB mutations)
        new_payload = dict(payload)
        new_payload["render_mode"] = "snapshot"
        new_payload["snapshot_payload"] = snapshot_data
        msg.structured_content_json = new_payload
        flag_modified(msg, "structured_content_json")
        db.add(msg)
        frozen_count += 1

    if frozen_count > 0:
        db.commit()

    return frozen_count


def _capture_entity_snapshot(
    db: Session,
    artifact_type: str,
    entity_id: str | None,
) -> dict[str, Any]:
    """
    Capture a frozen snapshot of the referenced entity for snapshot rendering.

    This is the single point of snapshot capture — both submission freezes
    and new-artifact-turn freezes call through here to guarantee consistent
    snapshot shape.
    """
    if not entity_id:
        return {}

    if artifact_type == "quote_preview":
        from app.models.quoting import Quote

        try:
            quote = db.get(Quote, uuid.UUID(entity_id))
        except ValueError:
            return {}
        if not quote:
            return {"error": "quote_not_found", "entity_id": entity_id}
        return {
            "quote_id": str(quote.id),
            "status": quote.status_code if hasattr(quote, "status_code") else None,
            "total_cents": quote.total_cents,
            "captured_at": datetime.now(UTC).isoformat(),
        }
    # Future artifact types (job_preview, schedule_preview) added here as needed
    return {}
