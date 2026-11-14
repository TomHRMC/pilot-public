"""dlc1_create_tenant_10dlc_profile

Revision ID: 7b15dc3a8a40
Revises: 9b3f7ea49606
Create Date: 2026-07-05 19:00:00.000000

DLC-1: Creates tenant_10dlc_profile table — one row per tenant capturing
business registration data needed to provision Telnyx sub-brand per tenant
for SMS campaign registration (10DLC compliance).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7b15dc3a8a40"
down_revision = "9b3f7ea49606"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE tenant_10dlc_profile (
            created_at          TIMESTAMPTZ NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL,
            created_by          UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by          UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            tenant_id           UUID PRIMARY KEY REFERENCES tenant(id) ON DELETE RESTRICT,
            legal_business_name TEXT NOT NULL,
            dba_name            TEXT,
            ein                 TEXT,
            hq_address_line1    TEXT,
            hq_address_line2    TEXT,
            hq_city             TEXT,
            hq_state            TEXT,
            hq_postal_code      TEXT,
            hq_country          TEXT NOT NULL DEFAULT 'US',
            support_email       TEXT,
            support_phone       TEXT
        )
    """)
    op.execute("""
        CREATE TRIGGER set_updated_at_tenant_10dlc_profile
            BEFORE UPDATE ON tenant_10dlc_profile
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_10dlc_profile CASCADE")
