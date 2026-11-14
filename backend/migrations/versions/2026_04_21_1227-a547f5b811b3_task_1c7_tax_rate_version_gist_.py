"""task_1c7_tax_rate_version_gist_constraint_hardening

Revision ID: a547f5b811b3
Revises: 8f6a759a2a32
Create Date: 2026-04-21 12:27:00.000000

Task 1-C-7: tax_rate_version GiST Constraint Hardening
=======================================================
Adds `taxability_code` VARCHAR column to `tax_rate_version` with a Foreign Key,
and replaces the existing 2-column GiST exclusion constraint with a 3-column version
that includes `taxability_code` as a second discriminator:

  Old: EXCLUDE USING GIST (jurisdiction_code WITH =, valid_period WITH &&)
  New: EXCLUDE USING GIST (jurisdiction_code WITH =, taxability_code WITH =, valid_period WITH &&)

This allows a single jurisdiction to legally hold simultaneous different rates
for labor vs. materials.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a547f5b811b3"
down_revision = "8f6a759a2a32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Part 1: Add taxability_code column as NULLABLE first
    # -----------------------------------------------------------------------
    op.add_column(
        "tax_rate_version",
        sa.Column(
            "taxability_code",
            sa.String(),
            nullable=True,
        ),
    )

    # -----------------------------------------------------------------------
    # Part 2: Backfill all existing rows with the default 'taxable' code.
    # -----------------------------------------------------------------------
    op.execute("""
        UPDATE tax_rate_version
        SET taxability_code = 'taxable'
        WHERE taxability_code IS NULL
    """)

    # -----------------------------------------------------------------------
    # Part 3: Lock down to NOT NULL with server default for future inserts
    # -----------------------------------------------------------------------
    op.alter_column(
        "tax_rate_version",
        "taxability_code",
        nullable=False,
        server_default="taxable",
    )

    # -----------------------------------------------------------------------
    # Part 4: Add the Foreign Key to the taxability_code lookup table
    # -----------------------------------------------------------------------
    op.create_foreign_key(
        "fk_tax_rate_version_taxability_code",
        "tax_rate_version",
        "taxability_code",
        ["taxability_code"],
        ["code"],
        ondelete="RESTRICT",
    )

    # -----------------------------------------------------------------------
    # Part 5: Drop the old 2-column GiST exclusion constraint and replace
    # it with the hardened 3-column version that includes taxability_code.
    # -----------------------------------------------------------------------
    op.execute("""
        ALTER TABLE tax_rate_version
        DROP CONSTRAINT IF EXISTS tax_rate_version_no_overlap
    """)

    op.execute("""
        ALTER TABLE tax_rate_version
        ADD CONSTRAINT tax_rate_version_no_overlap
        EXCLUDE USING GIST (
            jurisdiction_code WITH =,
            taxability_code   WITH =,
            valid_period      WITH &&
        )
    """)


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # Reverse Part 5: Drop the hardened 3-column GiST and restore the
    # original 2-column constraint.
    # NOTE: If overlapping valid_periods were added for different taxability
    # codes while this migration was active, this downgrade will fail until
    # those overlapping rows are manually resolved.
    # -----------------------------------------------------------------------
    op.execute("""
        ALTER TABLE tax_rate_version
        DROP CONSTRAINT IF EXISTS tax_rate_version_no_overlap
    """)

    op.execute("""
        ALTER TABLE tax_rate_version
        ADD CONSTRAINT tax_rate_version_no_overlap
        EXCLUDE USING GIST (
            jurisdiction_code WITH =,
            valid_period      WITH &&
        )
    """)

    # -----------------------------------------------------------------------
    # Reverse Part 4: Drop the Foreign Key
    # -----------------------------------------------------------------------
    op.drop_constraint(
        "fk_tax_rate_version_taxability_code",
        "tax_rate_version",
        type_="foreignkey",
    )

    # -----------------------------------------------------------------------
    # Reverse Parts 1-3: Drop the taxability_code column entirely
    # -----------------------------------------------------------------------
    op.drop_column("tax_rate_version", "taxability_code")
