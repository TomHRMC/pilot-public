"""signup_ga1_drop_tenant_name_unique_add_owner_email

SIGNUP-GA-1 — Post-Confirmation Lambda Router + Self-Serve Signup Backend.

Two schema changes (design §B, ADR-0012):
  1. Drop the `tenant_name_key` UNIQUE index on `tenant(name)` — tenant.name is
     display-only; nothing FKs off it (MCP-verified). Removing it eliminates the
     only collision path that could throw inside the Post-Confirmation Lambda
     and strand a Cognito confirmation.
  2. Add nullable `owner_email` / `owner_first_name` / `owner_last_name` columns
     to `tenant_signup` so the wizard step-1 resolve-or-attach logic can persist
     owner identity (previously dropped by initiate_signup()).

MCP-verified (2026-07-29): `tenant_name_key` is a UNIQUE **index** (not a
table constraint) — `CREATE UNIQUE INDEX tenant_name_key ON public.tenant
USING btree (name)`. Therefore `op.drop_index()` / `op.create_index(...,
unique=True)` is the correct API (not `op.drop_constraint`).

Revision ID: 44b3427a0e57
Revises: 2dba31137096
Create Date: 2026-07-29 22:04:16.160938+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "44b3427a0e57"
down_revision: str | None = "2dba31137096"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADR-0012 — tenant.name is display-only; nothing FKs off it (MCP-verified).
    # MCP-verified (2026-07-29): `tenant_name_key` is a UNIQUE **constraint**
    # (pg_constraint.contype='u', def='UNIQUE (name)') whose backing index
    # shares the same name. Dropping the index directly fails with
    # DependentObjectsStillExist; the constraint must be dropped instead.
    op.drop_constraint("tenant_name_key", "tenant", type_="unique")

    # Persist owner identity on the signup record (previously dropped by
    # initiate_signup). All nullable — no backfill, no NOT NULL pattern.
    op.add_column("tenant_signup", sa.Column("owner_email", sa.Text(), nullable=True))
    op.add_column(
        "tenant_signup", sa.Column("owner_first_name", sa.Text(), nullable=True)
    )
    op.add_column(
        "tenant_signup", sa.Column("owner_last_name", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    # Exact reverse of upgrade().
    op.drop_column("tenant_signup", "owner_last_name")
    op.drop_column("tenant_signup", "owner_first_name")
    op.drop_column("tenant_signup", "owner_email")

    # NOTE: re-adding uniqueness will FAIL if duplicate tenant names now exist
    # (accepted one-way door per ADR-0012). Recreated as a UNIQUE constraint
    # to match the original object type (MCP-verified contype='u').
    op.create_unique_constraint("tenant_name_key", "tenant", ["name"])
