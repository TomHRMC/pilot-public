"""stripe_connect_1_billing_contact

STRIPE-CONNECT-1-B2 — Tenant billing-contact columns for the public invoice
manual-payment panel.

DDL: two nullable TEXT columns on ``tenant``:
  - billing_contact_phone  — contractor-entered phone shown to customers on the
    public invoice manual-payment panel (null = not entered).
  - billing_contact_email  — contractor-entered email shown to customers on the
    public invoice manual-payment panel (null = not entered).

Both columns are nullable — null is a valid state meaning "the contractor has
not entered a billing contact". The frontend renders a fallback line in that
case (design §G Q9 — no owner-user personal phone/email fallback by design).

No backfill, no NOT NULL constraint, no data changes — pure additive DDL.

See: dev-docs/architecture-design/batch-designs/batch-stripe-connect-1-design.md
     §B.4, §C (A9 row), §G Q9

Revision ID: c8d06a6ffdd2
Revises: d038d647ec41
Create Date: 2026-08-29 18:06:31.557168+00:00

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8d06a6ffdd2"
down_revision = "d038d647ec41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Two nullable TEXT columns — no NOT NULL → no 3-part pattern required.
    # No backfill — null = "contractor hasn't entered it" (design §G Q9).
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("ALTER TABLE tenant ADD COLUMN billing_contact_phone TEXT NULL;")
    op.execute("ALTER TABLE tenant ADD COLUMN billing_contact_email TEXT NULL;")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("ALTER TABLE tenant DROP COLUMN IF EXISTS billing_contact_email;")
    op.execute("ALTER TABLE tenant DROP COLUMN IF EXISTS billing_contact_phone;")
