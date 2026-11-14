"""phase_fe_1_batch_b15_payment_stripe_columns

Revision ID: 5026cc474168
Revises: 394278063c7b
Create Date: 2026-05-03 14:22:50.000000

B15/A81: Add 4 Stripe Payment Intent columns to payment table.
Also seeds a system-level payment_method record ('stripe'/'one_time_public_link')
per design doc §F8, so Stripe one-time payments have a valid NOT NULL payment_method_id.

Columns added:
  - stripe_payment_intent_id TEXT UNIQUE (Stripe pi_... ID; webhook reconciliation anchor)
  - customer_payment_comment TEXT NULL
  - amount_variance_cents INTEGER NULL (amount_paid - invoice_total; neg=underpay; pos=overpay)
  - paid_via TEXT NULL CHECK: stripe | check | bank_transfer | other

All 4 are nullable additions — simple op.add_column, no backfill required.
"""

import uuid as _uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5026cc474168"
down_revision = "394278063c7b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 4 new columns ─────────────────────────────────────────────────────────
    op.add_column(
        "payment", sa.Column("stripe_payment_intent_id", sa.Text(), nullable=True)
    )
    op.add_column(
        "payment", sa.Column("customer_payment_comment", sa.Text(), nullable=True)
    )
    op.add_column(
        "payment", sa.Column("amount_variance_cents", sa.Integer(), nullable=True)
    )
    op.add_column("payment", sa.Column("paid_via", sa.Text(), nullable=True))

    # Unique constraint + index for stripe_payment_intent_id (webhook lookup)
    op.create_unique_constraint(
        "uq_payment_stripe_payment_intent_id", "payment", ["stripe_payment_intent_id"]
    )
    op.create_index(
        "ix_payment_stripe_payment_intent_id", "payment", ["stripe_payment_intent_id"]
    )

    # Check constraint for paid_via
    op.create_check_constraint(
        "payment_paid_via_chk",
        "payment",
        "paid_via IN ('stripe', 'check', 'bank_transfer', 'other')",
    )

    # ── Seed system payment_method for Stripe one-time payments (§F8) ─────────
    # payment_method has UUID `id` PK — audit.log_changes() works fine on INSERT.
    # BEFORE UPDATE triggers (guard_created_immutable, set_updated_at) don't fire
    # on INSERT. No session_replication_role bypass needed on RDS.
    # Use a fixed UUID so this is idempotent across re-runs
    system_pm_id = str(_uuid.UUID("00000000-b15a-4c00-8000-000000000001"))

    op.execute(f"""
        INSERT INTO payment_method (id, tenant_id, payment_type_id, psp_provider, psp_payment_method_id,
                                    brand, created_at, updated_at)
        SELECT
            '{system_pm_id}'::uuid,
            t.id,
            pt.id,
            'stripe',
            'one_time_public_link',
            'Stripe One-Time (Public Link)',
            NOW(),
            NOW()
        FROM tenant t
        CROSS JOIN (SELECT id FROM payment_type LIMIT 1) pt
        LIMIT 1
        ON CONFLICT (tenant_id, psp_provider, psp_payment_method_id) DO NOTHING
    """)


def downgrade() -> None:
    # Remove seeded system payment_method
    op.execute(
        "DELETE FROM payment_method WHERE psp_payment_method_id = 'one_time_public_link' AND psp_provider = 'stripe'"
    )

    op.drop_constraint("payment_paid_via_chk", "payment", type_="check")
    op.drop_index("ix_payment_stripe_payment_intent_id", table_name="payment")
    op.drop_constraint("uq_payment_stripe_payment_intent_id", "payment", type_="unique")
    op.drop_column("payment", "paid_via")
    op.drop_column("payment", "amount_variance_cents")
    op.drop_column("payment", "customer_payment_comment")
    op.drop_column("payment", "stripe_payment_intent_id")
