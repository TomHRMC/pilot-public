"""phase_fe_1_batch_b21_drop_legacy_notification_pref_tables

Revision ID: a05f647b21fa
Revises: f3829ae33fef
Create Date: 2026-05-18 22:04:28.000000

FIND-080: Drop legacy notification preference tables.
These three tables were superseded by the NotificationPreference model
introduced in a later batch. They have zero rows, zero active consumers
in api/, services/, or tasks/, and no FK dependencies from other tables.

Tables dropped:
  - tenant_notification_default
  - tenant_user_notification_pref
  - contact_notification_pref

Pre-drop MCP verification (2026-05-18):
  - tenant_notification_default: 0 rows
  - tenant_user_notification_pref: 0 rows
  - contact_notification_pref: 0 rows
  - grep api/ services/ tasks/ → zero references
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a05f647b21fa"
down_revision = "f3829ae33fef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_notification_default CASCADE;")
    op.execute("DROP TABLE IF EXISTS tenant_user_notification_pref CASCADE;")
    op.execute("DROP TABLE IF EXISTS contact_notification_pref CASCADE;")


def downgrade() -> None:
    # These tables are legacy/superseded — recreating them on downgrade would
    # require the full original schema. Since they had zero rows and zero
    # consumers, downgrade restores an empty schema for safety.
    op.execute("""
        CREATE TABLE IF NOT EXISTS contact_notification_pref (
            id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            contact_id UUID NOT NULL REFERENCES contact(id),
            notification_type_code VARCHAR NOT NULL REFERENCES notification_type(code),
            allow_sms BOOLEAN NOT NULL DEFAULT false,
            allow_email BOOLEAN NOT NULL DEFAULT true,
            quiet_hours_start TIME,
            quiet_hours_end TIME,
            timezone VARCHAR,
            is_enabled BOOLEAN NOT NULL DEFAULT true,
            PRIMARY KEY (id)
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenant_user_notification_pref (
            id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            user_id UUID NOT NULL REFERENCES "user"(id),
            notification_type_code VARCHAR NOT NULL REFERENCES notification_type(code),
            allow_in_app BOOLEAN NOT NULL DEFAULT true,
            allow_email BOOLEAN NOT NULL DEFAULT false,
            threshold_value NUMERIC(10, 3),
            is_enabled BOOLEAN NOT NULL DEFAULT true,
            PRIMARY KEY (id)
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tenant_user_notif_pref
        ON tenant_user_notification_pref (tenant_id, user_id);
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenant_notification_default (
            id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            notification_type_code VARCHAR NOT NULL REFERENCES notification_type(code),
            default_channels VARCHAR[],
            default_is_enabled BOOLEAN NOT NULL DEFAULT true,
            default_threshold_value NUMERIC(10, 3),
            PRIMARY KEY (id)
        );
    """)
