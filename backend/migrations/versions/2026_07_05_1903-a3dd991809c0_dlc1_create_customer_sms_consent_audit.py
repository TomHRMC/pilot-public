"""dlc1_create_customer_sms_consent_audit

Revision ID: a3dd991809c0
Revises: e5cad108085f
Create Date: 2026-07-05 19:03:30.000000

DLC-1: Creates customer_sms_consent_audit append-only table.
Logs each consent lifecycle event:
  - attested (offline checkbox attestation)
  - double_opt_in_sent (double opt-in SMS dispatched)
  - double_opt_in_confirmed (customer replied YES)
  - opted_out (customer replied STOP)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a3dd991809c0"
down_revision = "e5cad108085f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE customer_sms_consent_audit (
            id                  UUID PRIMARY KEY,
            created_at          TIMESTAMPTZ NOT NULL,
            tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            customer_id         UUID NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
            attested_by         UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            ip_address          TEXT NOT NULL,
            attested_at         TIMESTAMPTZ NOT NULL,
            consent_text_hash   TEXT NOT NULL,
            action              TEXT NOT NULL,
            CONSTRAINT customer_sms_consent_audit_action_chk
                CHECK (action IN ('attested','double_opt_in_sent','double_opt_in_confirmed','opted_out'))
        )
    """)
    op.execute("""
        CREATE INDEX idx_customer_sms_consent_audit_customer
            ON customer_sms_consent_audit(customer_id)
    """)
    op.execute("""
        CREATE INDEX idx_customer_sms_consent_audit_tenant
            ON customer_sms_consent_audit(tenant_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS customer_sms_consent_audit CASCADE")
