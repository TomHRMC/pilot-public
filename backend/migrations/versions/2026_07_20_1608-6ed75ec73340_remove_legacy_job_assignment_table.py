"""remove_legacy_job_assignment_table

Revision ID: 6ed75ec73340
Revises: aaaa1f8d5138
Create Date: 2026-07-20 16:08:00.000000

Legacy job_assignment table had 0 rows and was superseded by job_tech_assignment.
Safe to drop — no active API endpoints reference it.

NOTE: PostgreSQL automatically drops all indexes, constraints, and triggers
when a table is dropped, so we do not need to drop them individually.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "6ed75ec73340"
down_revision = "aaaa1f8d5138"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop table — Postgres automatically drops all associated indexes,
    # constraints (PK, FK, unique), and triggers.
    op.drop_table("job_assignment")


def downgrade() -> None:
    # Recreate table for rollback safety (0 rows were present before upgrade)
    op.create_table(
        "job_assignment",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(), nullable=True),
        sa.Column("updated_by", postgresql.UUID(), nullable=True),
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("job_id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column(
            "is_lead",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"], ondelete="RESTRICT"),
    )
    op.create_unique_constraint(
        "uq_job_assignment_job_user", "job_assignment", ["job_id", "user_id"]
    )
    op.create_index(
        "ix_job_assignment_tenant_id",
        "job_assignment",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "idx_job_assignment_user_active",
        "job_assignment",
        ["user_id", "is_active"],
        unique=False,
    )
