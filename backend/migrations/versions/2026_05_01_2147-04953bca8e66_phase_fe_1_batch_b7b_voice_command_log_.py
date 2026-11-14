"""phase_fe_1_batch_b7b_voice_command_log_offline_columns

Revision ID: 04953bca8e66
Revises: cbb6b7c41735
Create Date: 2026-05-01 21:47:14

B7b / A42 — Voice Command Offline Capture & Deferred Processing
Adds 7 new columns to voice_command_log for offline voice capture pipeline.

Design doc §F.1: audio_object_key does NOT pre-exist (verified live DB).
All columns are nullable (backwards-compatible with existing synchronous rows).
No updated_at trigger needed — voice_command_log is effectively append-only.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "04953bca8e66"
down_revision = "cbb6b7c41735"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Add nullable columns (backwards-compatible)                       #
    # ------------------------------------------------------------------ #

    # S3 key for stored audio file (NULL for synchronous commands)
    op.add_column(
        "voice_command_log", sa.Column("audio_object_key", sa.Text(), nullable=True)
    )

    # Client-side capture timestamp for offline commands
    op.add_column(
        "voice_command_log",
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
    )

    # When audio reached server
    op.add_column(
        "voice_command_log",
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # When Whisper completed
    op.add_column(
        "voice_command_log",
        sa.Column("transcribed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # When Llama completed intent parse
    op.add_column(
        "voice_command_log",
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Processing pipeline status (NULL for synchronous commands)
    op.add_column(
        "voice_command_log", sa.Column("processing_status", sa.Text(), nullable=True)
    )
    op.execute("""
        ALTER TABLE public.voice_command_log
        ADD CONSTRAINT chk_voice_command_log_processing_status
        CHECK (processing_status IS NULL OR processing_status IN
            ('pending_upload', 'uploading', 'transcribing', 'parsing', 'completed', 'failed'));
    """)

    # Client-generated UUID v4 for safe offline retry (NULL for synchronous commands)
    op.add_column(
        "voice_command_log", sa.Column("idempotency_uuid", sa.UUID(), nullable=True)
    )

    # ------------------------------------------------------------------ #
    # 2. Indexes                                                           #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE UNIQUE INDEX ix_voice_command_log_idempotency_uuid
        ON public.voice_command_log (idempotency_uuid)
        WHERE idempotency_uuid IS NOT NULL;
    """)

    op.execute("""
        CREATE INDEX ix_voice_command_log_processing_status
        ON public.voice_command_log (tenant_id, processing_status)
        WHERE processing_status NOT IN ('completed', 'failed');
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_voice_command_log_processing_status;")
    op.execute("DROP INDEX IF EXISTS public.ix_voice_command_log_idempotency_uuid;")
    op.execute(
        "ALTER TABLE public.voice_command_log DROP CONSTRAINT IF EXISTS chk_voice_command_log_processing_status;"
    )
    op.drop_column("voice_command_log", "idempotency_uuid")
    op.drop_column("voice_command_log", "processing_status")
    op.drop_column("voice_command_log", "parsed_at")
    op.drop_column("voice_command_log", "transcribed_at")
    op.drop_column("voice_command_log", "uploaded_at")
    op.drop_column("voice_command_log", "captured_at")
    op.drop_column("voice_command_log", "audio_object_key")
