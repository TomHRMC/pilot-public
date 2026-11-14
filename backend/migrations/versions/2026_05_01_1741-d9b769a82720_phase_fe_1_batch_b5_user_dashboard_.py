"""phase_fe_1_batch_b5_user_dashboard_widget

Revision ID: d9b769a82720
Revises: 7644915569b3
Create Date: 2026-05-01 17:41:00.000000

Creates the user_dashboard_widget table for B5/A5 — Reports & Dashboard.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9b769a82720"
down_revision: str | None = "7644915569b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_dashboard_widget (
            id              UUID        NOT NULL DEFAULT gen_random_uuid(),
            user_id         UUID        NOT NULL,
            tenant_id       UUID        NOT NULL,
            widget_type     VARCHAR(64) NOT NULL,
            widget_config_json JSONB    NOT NULL DEFAULT '{}'::jsonb,
            position_x      INTEGER     NOT NULL DEFAULT 0,
            position_y      INTEGER     NOT NULL DEFAULT 0,
            width           INTEGER     NOT NULL DEFAULT 2,
            height          INTEGER     NOT NULL DEFAULT 2,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by      UUID,
            updated_by      UUID,
            CONSTRAINT pk_user_dashboard_widget PRIMARY KEY (id),
            CONSTRAINT fk_user_dashboard_widget_user_id
                FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT fk_user_dashboard_widget_tenant_id
                FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT,
            CONSTRAINT fk_user_dashboard_widget_created_by
                FOREIGN KEY (created_by) REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT fk_user_dashboard_widget_updated_by
                FOREIGN KEY (updated_by) REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT ck_widget_width   CHECK (width  BETWEEN 1 AND 12),
            CONSTRAINT ck_widget_height  CHECK (height BETWEEN 1 AND 8),
            CONSTRAINT ck_widget_position_x CHECK (position_x >= 0),
            CONSTRAINT ck_widget_position_y CHECK (position_y >= 0)
        )
    """)

    op.execute("""
        CREATE INDEX ix_user_dashboard_widget_user_id
            ON user_dashboard_widget (user_id)
    """)

    op.execute("""
        CREATE INDEX ix_user_dashboard_widget_tenant_id
            ON user_dashboard_widget (tenant_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_dashboard_widget_tenant_id")
    op.execute("DROP INDEX IF EXISTS ix_user_dashboard_widget_user_id")
    op.execute("DROP TABLE IF EXISTS user_dashboard_widget")
