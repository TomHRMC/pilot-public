"""
Help System Models — Batch B16 (A85, A84, A87, A88)

Tables:
    help_article           — MachineLogMixin (A85)
    help_article_chunk     — MachineLogMixin (A85)
    help_chat_session      — StandardAuditMixin (A84)
    help_chat_message      — AppendOnlyMixin (A84)
    feedback_submission    — AppendOnlyMixin (A87)
    help_training_corpus   — MachineLogMixin (A88)
"""

import uuid
from datetime import date
from typing import Any

from pgvector.sqlalchemy import Vector
from pydantic import AwareDatetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Column, Field, SQLModel

from app.models.mixins import AppendOnlyMixin, MachineLogMixin, StandardAuditMixin

# ──────────────────────────────────────────────────────────────────────────────
# A85 — Corpus tables
# ──────────────────────────────────────────────────────────────────────────────


class HelpArticle(MachineLogMixin, SQLModel, table=True):
    """
    Help article registry — metadata + hash for the embedding pipeline.
    Content lives in S3; this table stores frontmatter and pipeline state.
    Mixin: MachineLogMixin (created_at only — written by embedding pipeline).
    """

    __tablename__ = "help_article"

    # FIND-169: renamed from article_id to code (string PK lookup table convention)
    code: str = Field(
        sa_column=Column(Text, primary_key=True, nullable=False),
    )
    s3_path: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    title: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    category: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
    )
    frontmatter_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    last_content_hash: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    last_processed_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_updated: date = Field(
        sa_column=Column(Date, nullable=False),
    )
    audience: list[str] = Field(
        default_factory=list,
        sa_column=Column(
            ARRAY(Text),
            nullable=False,
            server_default=text("'{}'::text[]"),
        ),
    )
    # created_at is provided by MachineLogMixin


class HelpArticleChunk(MachineLogMixin, SQLModel, table=True):
    """
    Chunked sections of help articles with pgvector embeddings.
    Mixin: MachineLogMixin (created_at only — written by embedding pipeline).
    """

    __tablename__ = "help_article_chunk"

    chunk_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    # FK child column keeps name article_id — references help_article.code (FIND-169)
    article_id: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("help_article.code", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    chunk_order: int = Field(
        sa_column=Column(Integer, nullable=False),
    )
    section_title: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    chunk_text: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    chunk_text_with_metadata: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    embedding: Any | None = Field(
        default=None,
        sa_column=Column(Vector(1536), nullable=False),
    )
    token_count: int = Field(
        sa_column=Column(Integer, nullable=False),
    )
    # created_at is provided by MachineLogMixin


# ──────────────────────────────────────────────────────────────────────────────
# A84 — Chat session tables
# ──────────────────────────────────────────────────────────────────────────────


class HelpChatSession(StandardAuditMixin, SQLModel, table=True):
    """
    A user's help chat session. Updated throughout lifecycle.
    Mixin: StandardAuditMixin (created_at, updated_at, created_by, updated_by).
    """

    __tablename__ = "help_chat_session"

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('resolved', 'escalated', 'abandoned')",
            name="help_chat_session_outcome_chk",
        ),
    )

    # FIND-169: renamed from session_id to id (UUID PK convention)
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    started_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_activity_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    title: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    outcome: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    message_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    anonymized_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    # created_at, updated_at, created_by, updated_by from StandardAuditMixin


class HelpChatMessage(AppendOnlyMixin, SQLModel, table=True):
    """
    Immutable message record within a help chat session.
    Mixin: AppendOnlyMixin (created_at, created_by — never edited).
    """

    __tablename__ = "help_chat_message"

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="help_chat_message_role_chk",
        ),
    )

    message_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    # FK child column keeps name session_id — references help_chat_session.id (FIND-169)
    session_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("help_chat_session.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    role: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    content: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    context_payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    retrieved_chunks: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    voice_used: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )
    # created_at, created_by from AppendOnlyMixin


# ──────────────────────────────────────────────────────────────────────────────
# A87 — Feedback submission
# ──────────────────────────────────────────────────────────────────────────────


class FeedbackSubmission(AppendOnlyMixin, SQLModel, table=True):
    """
    Write-once user feedback record. Never edited after creation.
    Mixin: AppendOnlyMixin (created_at, created_by).
    """

    __tablename__ = "feedback_submission"

    __table_args__ = (
        CheckConstraint(
            "category IN ('bug', 'feature_request', 'question', 'general')",
            name="feedback_submission_category_chk",
        ),
    )

    submission_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    tenant_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("tenant.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID,
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    category: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    body: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    # FK references renamed PK column (FIND-169: session_id → id on help_chat_session)
    from_help_chat_session_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID,
            ForeignKey("help_chat_session.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    email_sent_to: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    email_message_id: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    # created_at, created_by from AppendOnlyMixin


# ──────────────────────────────────────────────────────────────────────────────
# A88 — Training corpus
# ──────────────────────────────────────────────────────────────────────────────


class HelpTrainingCorpus(MachineLogMixin, SQLModel, table=True):
    """
    Anonymized help session data for AI training corpus.
    Written exclusively by the anonymize_help_sessions Celery task.
    Mixin: MachineLogMixin (created_at only — automated system event).
    """

    __tablename__ = "help_training_corpus"

    corpus_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID,
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    original_session_id_hash: str = Field(
        sa_column=Column(Text, nullable=False, index=True),
    )
    anonymized_message_history: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    anonymized_context_payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    category_inferred: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True, index=True),
    )
    outcome: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    anonymized_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    # created_at is provided by MachineLogMixin
