"""team_invite_1_tenant_user_invite_role_code

Revision ID: 3da9abdfb2f2
Revises: ec2df153a859
Create Date: 2026-09-03 14:27:08.868749+00:00

TEAM-INVITE-1: Add nullable ``role_code`` column to ``tenant_user_invite``
so the inviter can specify the role at invite time. The Post-Confirmation
Lambda Path 2 reads this column to assign the role at acceptance; NULL =
pre-TEAM-INVITE-1 rows → technician fallback (design §F.3).

DDL-only (ADR-0016) — no data INSERTs. Nullable add: no backfill, no lock.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3da9abdfb2f2"
down_revision: str | None = "ec2df153a859"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_user_invite",
        sa.Column("role_code", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tenant_user_invite_role_code",
        "tenant_user_invite",
        "tenant_user_role",
        ["role_code"],
        ["code"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tenant_user_invite_role_code",
        "tenant_user_invite",
        type_="foreignkey",
    )
    op.drop_column("tenant_user_invite", "role_code")
