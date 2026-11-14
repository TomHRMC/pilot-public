"""phase_4_7_enum_to_text_customer_type_task1

Revision ID: 6b15b78db845
Revises: 3454bbfb10c6
Create Date: 2026-04-03 16:24:37.312182+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6b15b78db845"
down_revision: str | None = "3454bbfb10c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Convert customer.type from PostgreSQL ENUM to TEXT with CHECK constraint.

    Pre-migration validation (already run):
    - SELECT id, type, COUNT(*) FROM customer WHERE type NOT IN ('person', 'company') GROUP BY id, type;
    - Result: 0 rows (all data is valid)
    - SELECT type, COUNT(*) FROM customer GROUP BY type;
    - Result: 13 'person', 11 'company' (24 total records)
    """
    # Step 1: Drop existing CHECK constraint that references ENUM type
    op.drop_constraint("customer_type_chk", "customer", type_="check")

    # Step 2: Convert column from ENUM to TEXT
    op.alter_column(
        "customer",
        "type",
        existing_type=postgresql.ENUM("person", "company", name="customertype"),
        type_=sa.Text(),
        existing_nullable=False,
        postgresql_using="type::text",
    )

    # Step 3: Drop the ENUM type (CASCADE to handle any dependencies)
    op.execute("DROP TYPE IF EXISTS public.customertype CASCADE")

    # Step 4: Re-add CHECK constraint with TEXT values
    op.create_check_constraint(
        "customer_type_chk", "customer", "type IN ('person', 'company')"
    )


def downgrade() -> None:
    """
    Revert customer.type from TEXT back to PostgreSQL ENUM.

    WARNING: This will fail if any new type values were added beyond 'person', 'company'.
    """
    # Step 1: Drop the CHECK constraint
    op.drop_constraint("customer_type_chk", "customer", type_="check")

    # Step 2: Recreate the ENUM type
    op.execute("CREATE TYPE public.customertype AS ENUM ('person', 'company')")

    # Step 3: Convert column from TEXT back to ENUM
    op.alter_column(
        "customer",
        "type",
        existing_type=sa.Text(),
        type_=postgresql.ENUM("person", "company", name="customertype"),
        existing_nullable=False,
        postgresql_using="type::public.customertype",
    )

    # Step 4: Re-add CHECK constraint with ENUM values
    op.create_check_constraint(
        "customer_type_chk",
        "customer",
        "type = ANY (ARRAY['person'::customertype, 'company'::customertype])",
    )
