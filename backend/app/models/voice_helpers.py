"""
Voice AI helper utilities — B19/B20 support.

FIND-168 (B19): Voice Command Entity Link Table
- `_link_voice_to_entity()`: Helper for voice intent handlers to insert entity link rows.
"""

import uuid

from sqlalchemy.orm import Session

from .ai import VoiceCommandEntityLink


def _link_voice_to_entity(
    db: Session,
    tenant_id: uuid.UUID,
    voice_command_log_id: int,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str | None = None,
    created_by: uuid.UUID | None = None,
) -> VoiceCommandEntityLink:
    """
    Link a voice command to an entity it created or mutated.

    Every voice intent handler that successfully creates or mutates an entity
    must call this helper at the end of the handler to create an audit trail.

    **Parameters:**
    - `db`: SQLAlchemy Session
    - `tenant_id`: UUID of the tenant executing the command
    - `voice_command_log_id`: BigInt PK from voice_command_log
    - `entity_type`: String entity type (e.g., 'job_time_entry', 'job', 'quote', 'invoice')
    - `entity_id`: UUID PK of the entity that was changed
    - `action`: Optional action label (e.g., 'clock_in', 'rescheduled', 'created')
    - `created_by`: Optional UUID of the user who executed the voice command

    **Returns:**
    - Created VoiceCommandEntityLink row (NOT yet committed — caller owns transaction)

    **Usage in voice intent handler (B20 pattern):**
    ```python
    # After successfully creating job_time_entry
    link = _link_voice_to_entity(
        db=db,
        tenant_id=tenant_id,
        voice_command_log_id=voice_log.id,
        entity_type='job_time_entry',
        entity_id=entry.id,
        action='clock_in',
        created_by=user_id,
    )
    db.add(link)
    # Transaction commits at endpoint return
    ```

    **Idempotency:**
    - This helper is NOT idempotent — caller is responsible for preventing
      duplicate link rows (e.g., via idempotency_key on voice_command_log).
    - If the same voice command is retried, the caller should detect that
      the entity already exists and skip this helper call.
    """

    link_row = VoiceCommandEntityLink(
        tenant_id=tenant_id,
        voice_command_log_id=voice_command_log_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        created_by=created_by,
    )
    return link_row
