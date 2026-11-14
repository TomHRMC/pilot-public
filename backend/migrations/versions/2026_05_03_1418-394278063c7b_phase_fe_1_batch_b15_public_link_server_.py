"""phase_fe_1_batch_b15_public_link_server_defaults

Revision ID: 394278063c7b
Revises: 27e787ad52bd
Create Date: 2026-05-03 14:18:47.000000

B15/A80 fix: Add server_default to signed_token on quote_public_link and
invoice_public_link so that legacy INSERT statements (tests, old send_invoice route)
that omit signed_token don't violate the NOT NULL constraint.

Also add server_default to expires_at on invoice_public_link (was nullable before B15,
now NOT NULL after B15 tightening — same issue).

This does NOT change the constraint (columns remain NOT NULL); it only adds a
safe fallback default so rows without an explicit signed_token get the placeholder.
The B15 public-link endpoints always provide a real signed_token; only legacy paths
need the default.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "394278063c7b"
down_revision = "27e787ad52bd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add server_default to quote_public_link.signed_token
    op.alter_column(
        "quote_public_link",
        "signed_token",
        server_default=sa.text("'legacy.placeholder'"),
        nullable=False,
    )
    # Add server_default to quote_public_link.expires_at (already NOT NULL, just add default)
    op.alter_column(
        "quote_public_link",
        "expires_at",
        server_default=sa.text("NOW() + INTERVAL '90 days'"),
        nullable=False,
    )

    # Add server_default to invoice_public_link.signed_token
    op.alter_column(
        "invoice_public_link",
        "signed_token",
        server_default=sa.text("'legacy.placeholder'"),
        nullable=False,
    )
    # Add server_default to invoice_public_link.expires_at
    op.alter_column(
        "invoice_public_link",
        "expires_at",
        server_default=sa.text("NOW() + INTERVAL '90 days'"),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "invoice_public_link", "expires_at", server_default=None, nullable=True
    )
    op.alter_column(
        "invoice_public_link", "signed_token", server_default=None, nullable=True
    )
    op.alter_column(
        "quote_public_link", "expires_at", server_default=None, nullable=True
    )
    op.alter_column(
        "quote_public_link", "signed_token", server_default=None, nullable=True
    )
