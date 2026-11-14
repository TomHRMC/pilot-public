"""phase_fe_1_batch_b11_customer_sms_columns

Revision ID: 65466ce269db
Revises: a2c82e3c9940
Create Date: 2026-05-02 16:26:48

B11/A59 — Add TCPA SMS consent columns and last_assigned_tech_id to the customer table.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "65466ce269db"
down_revision = "cdadbe97786c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- TCPA SMS opt-out/opt-in columns ---
    op.execute("""
        ALTER TABLE customer ADD COLUMN sms_opted_out       BOOLEAN     NOT NULL DEFAULT FALSE;
        ALTER TABLE customer ADD COLUMN sms_opt_out_at      TIMESTAMPTZ NULL;
        ALTER TABLE customer ADD COLUMN sms_opt_in_consent  BOOLEAN     NOT NULL DEFAULT FALSE;
        ALTER TABLE customer ADD COLUMN sms_opt_in_at       TIMESTAMPTZ NULL;
        ALTER TABLE customer ADD COLUMN sms_opt_in_source   TEXT        NULL;
    """)

    op.execute("""
        ALTER TABLE customer ADD CONSTRAINT customer_sms_opt_in_source_chk
            CHECK (sms_opt_in_source IS NULL OR
                   sms_opt_in_source IN ('explicit_checkbox', 'inbound_initiated', 'verbal_captured'));
    """)

    # --- B11/F4: routing fallback for inbound SMS thread assignment ---
    op.execute("""
        ALTER TABLE customer
            ADD COLUMN last_assigned_tech_id UUID NULL
                REFERENCES "user"(id) ON DELETE SET NULL;
    """)

    op.execute("""
        CREATE INDEX idx_customer_last_assigned_tech_id
            ON customer(last_assigned_tech_id)
            WHERE last_assigned_tech_id IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_customer_last_assigned_tech_id;")
    op.execute("ALTER TABLE customer DROP COLUMN IF EXISTS last_assigned_tech_id;")
    op.execute(
        "ALTER TABLE customer DROP CONSTRAINT IF EXISTS customer_sms_opt_in_source_chk;"
    )
    op.execute("ALTER TABLE customer DROP COLUMN IF EXISTS sms_opted_out;")
    op.execute("ALTER TABLE customer DROP COLUMN IF EXISTS sms_opt_out_at;")
    op.execute("ALTER TABLE customer DROP COLUMN IF EXISTS sms_opt_in_consent;")
    op.execute("ALTER TABLE customer DROP COLUMN IF EXISTS sms_opt_in_at;")
    op.execute("ALTER TABLE customer DROP COLUMN IF EXISTS sms_opt_in_source;")
