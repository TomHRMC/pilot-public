"""dlc1_add_customer_sms_consent_columns

Revision ID: e5cad108085f
Revises: 7b15dc3a8a40
Create Date: 2026-07-05 19:03:00.000000

DLC-1: Adds 4 new nullable columns to customer for offline consent attestation
audit trail and double opt-in state tracking.
  - sms_consent_attested_by  (FK → user)
  - sms_consent_attested_at  (TIMESTAMPTZ)
  - sms_consent_ip_address   (TEXT)
  - sms_verification_status  (TEXT, CHECK, default 'unverified')
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5cad108085f"
down_revision = "7b15dc3a8a40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All columns nullable — no 3-part pattern required
    op.execute("""
        ALTER TABLE customer
            ADD COLUMN IF NOT EXISTS sms_consent_attested_by UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            ADD COLUMN IF NOT EXISTS sms_consent_attested_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS sms_consent_ip_address  TEXT,
            ADD COLUMN IF NOT EXISTS sms_verification_status TEXT
                DEFAULT 'unverified'
                CHECK (sms_verification_status IN ('unverified','pending_verification','verified','opted_out'))
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE customer
            DROP COLUMN IF EXISTS sms_consent_attested_by,
            DROP COLUMN IF EXISTS sms_consent_attested_at,
            DROP COLUMN IF EXISTS sms_consent_ip_address,
            DROP COLUMN IF EXISTS sms_verification_status
    """)
