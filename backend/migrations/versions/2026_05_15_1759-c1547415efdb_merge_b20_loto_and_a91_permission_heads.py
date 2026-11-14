"""merge_b20_loto_and_a91_permission_heads

Revision ID: c1547415efdb
Revises: 798dcad549eb, de31bbfd899c
Create Date: 2026-05-15 17:59:51.464615+00:00

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "c1547415efdb"
down_revision: str | None = ("798dcad549eb", "de31bbfd899c")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
