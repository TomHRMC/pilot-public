"""phase_fe_1_batch_b7b_tenant_settings_offline_photo

Revision ID: cbb6b7c41735
Revises: 91bf9dafe0e5
Create Date: 2026-05-01 21:18:38

B7b / A41 + A42 — Offline and photo-related tenant settings.
Adds four new columns to tenant_settings:
  - photo_upload_wifi_only (BOOLEAN NOT NULL DEFAULT TRUE)
  - photo_local_retention_days (INTEGER NOT NULL DEFAULT 7)
  - offline_hard_limit_hours (INTEGER NULL DEFAULT 72)
  - voice_offline_audio_storage_limit_mb (INTEGER NOT NULL DEFAULT 500)

Design doc §F.7: A44's server contribution is offline_hard_limit_hours — no separate migration needed.
Design doc §F.3: Direct columns on tenant_settings (not a new table). B9/A53 adds resolver on top later.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cbb6b7c41735"
down_revision = "91bf9dafe0e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # photo_upload_wifi_only — NOT NULL, server_default TRUE
    op.add_column(
        "tenant_settings",
        sa.Column(
            "photo_upload_wifi_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # photo_local_retention_days — NOT NULL, server_default 7
    op.add_column(
        "tenant_settings",
        sa.Column(
            "photo_local_retention_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("7"),
        ),
    )

    # offline_hard_limit_hours — NULLABLE, no server_default (app default 72 is documented)
    op.add_column(
        "tenant_settings",
        sa.Column(
            "offline_hard_limit_hours",
            sa.Integer(),
            nullable=True,
        ),
    )

    # voice_offline_audio_storage_limit_mb — NOT NULL, server_default 500
    op.add_column(
        "tenant_settings",
        sa.Column(
            "voice_offline_audio_storage_limit_mb",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("500"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_settings", "voice_offline_audio_storage_limit_mb")
    op.drop_column("tenant_settings", "offline_hard_limit_hours")
    op.drop_column("tenant_settings", "photo_local_retention_days")
    op.drop_column("tenant_settings", "photo_upload_wifi_only")
