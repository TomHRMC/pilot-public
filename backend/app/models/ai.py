import uuid
from datetime import UTC, datetime
from typing import Any

# Import Vector type from pgvector
from pgvector.sqlalchemy import Vector
from pydantic import AwareDatetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from .mixins import AppendOnlyMixin


class ConversationSession(SQLModel, table=True):
    __tablename__ = "conversation_session"

    __table_args__ = (
        # FIND-112 (B18): Added 'expired' and 'archived' to status set
        CheckConstraint(
            "status IN ('active', 'ended', 'abandoned', 'expired', 'archived')",
            name="conv_session_status_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)

    status: str = Field(
        default="active",
        sa_column=Column(String, server_default=text("'active'"), nullable=False),
    )
    context_summary: str | None = Field(default=None)

    # A11: Ollama-generated or user-set session title
    title: str | None = Field(default=None)
    title_auto_generated: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )

    # 1024 dimensions - adjust if your Ollama model outputs a different size
    context_embedding: Any | None = Field(default=None, sa_column=Column(Vector(1024)))
    # FIND-113 (B18): NOT NULL + DEFAULT '{}' — never NULL; zero context = empty dict
    context_window_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )

    expires_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    # A11: Archive timestamp for >30 days inactive sessions
    archived_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # Audit Columns explicitly defined
    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Phase 6.0.1: Audit trail columns with FK constraints
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
        description="User who created this conversation session",
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
        description="User who last updated this conversation session",
    )


class ConversationMessage(SQLModel, table=True):
    __tablename__ = "conversation_message"

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="conv_msg_role_chk",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False, index=True)
    session_id: uuid.UUID = Field(
        foreign_key="conversation_session.id", nullable=False, index=True
    )

    role: str = Field(nullable=False)  # user|assistant|system
    content_text: str = Field(nullable=False)
    audio_object_key: str | None = Field(default=None)

    # A12: Structured content payload for artifact messages (quotes, jobs, etc.)
    structured_content_json: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )

    embedding: Any | None = Field(default=None, sa_column=Column(Vector(1024)))

    created_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")

    # Audit Columns explicitly defined
    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class VoiceFeedback(SQLModel, table=True):
    """
    Voice AI feedback loop for Whisper/Llama training data capture.
    AppendOnly — rows are never updated after creation except by Celery export task.
    Established in B2 (A6). Strategic moat: builds fine-tuning dataset.
    """

    __tablename__ = "voice_feedback"

    __table_args__ = (
        Index("ix_voice_feedback_tenant_id", "tenant_id"),
        Index("ix_voice_feedback_user_id", "user_id"),
        Index(
            "ix_voice_feedback_unexported",
            "exported_at",
            postgresql_where=text("exported_at IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"), nullable=False
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
        )
    )
    voice_command_log_id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("voice_command_log.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    original_transcription: str = Field(nullable=False)
    corrected_text: str | None = Field(default=None)
    intent_misparsed: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
    corrected_intent: str | None = Field(default=None)
    feedback_notes: str | None = Field(default=None)

    # Written by nightly Celery task — not by user
    s3_export_key: str | None = Field(default=None)
    exported_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # AppendOnly audit fields
    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT")),
    )


class VoiceCommandLog(SQLModel, table=True):
    __tablename__ = "voice_command_log"

    __table_args__ = (
        # RENAMED & NEW: Standardized index names
        Index("idx_voice_log_tenant_time", "tenant_id", text("created_at DESC")),
        Index("idx_voice_log_intent", "intent_detected"),
        Index("idx_voice_log_latency", "total_latency_ms"),
    )

    # Bigserial for high-throughput telemetry
    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    message_id: uuid.UUID | None = Field(
        default=None, foreign_key="conversation_message.id", index=True
    )

    intent_detected: str | None = Field(default=None)
    entities_extracted: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    action_executed: str | None = Field(default=None)

    whisper_latency_ms: int | None = Field(default=None)
    ollama_latency_ms: int | None = Field(default=None)
    total_latency_ms: int | None = Field(default=None)

    is_successful: bool = Field(
        default=True,
        sa_column=Column(Boolean, server_default=text("true"), nullable=False),
    )

    # B7b/A42: Offline voice capture tracking columns
    # NULL for synchronous (non-offline) commands
    audio_object_key: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    captured_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    uploaded_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    transcribed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    parsed_at: AwareDatetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # Valid values: pending_upload|uploading|transcribing|parsing|completed|failed
    # NULL for synchronous commands (backwards-compatible)
    processing_status: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    # Client-generated UUID v4 for safe offline retry. NULL for synchronous commands.
    idempotency_uuid: uuid.UUID | None = Field(
        default=None, sa_column=Column(PG_UUID, nullable=True)
    )

    # Audit Columns explicitly defined
    created_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class VoiceCommandEntityLink(AppendOnlyMixin, SQLModel, table=True):
    """
    Junction/link table linking voice_command_log rows to the entities they created or mutated.
    Enables platform-wide voice-to-entity audit trail for: owner re-listen, dispute resolution,
    training data audit, and support debugging.

    AppendOnly — rows are never updated after creation. Immutable audit record.
    Established in B19 (A95) — foundation for B20 voice intent handlers.
    """

    __tablename__ = "voice_command_entity_link"

    __table_args__ = (
        Index("ix_vcel_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_vcel_voice_log", "voice_command_log_id"),
    )

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )  # BigInt PK — high-volume write table; consistent with voice_command_log.id type
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )
    voice_command_log_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("voice_command_log.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    entity_type: str = Field(
        nullable=False
    )  # e.g. 'job_time_entry', 'job', 'quote', 'invoice'
    entity_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID, nullable=False)
    )  # UUID PK of the changed entity — all voice-actionable entities use UUID PKs
    action: str | None = Field(
        default=None
    )  # e.g. 'clock_in', 'rescheduled', 'created'

    # AppendOnlyMixin provides created_at + created_by (the tech who spoke the command)
