"""phase_6_0_1_task_7_fk_audit_integration

Revision ID: d50835eb4ab1
Revises: 47a3ff6f3f8b
Create Date: 2026-04-13 22:27:12.467635+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d50835eb4ab1"
down_revision: str | None = "47a3ff6f3f8b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # For tables with BOTH created_by and updated_by
    for table_name in [
        "connector_config",
        "integration_credential",
        "integration_sync_mapping",
        "integration_sync_conflict",
    ]:
        op.create_foreign_key(
            f"fk_{table_name}_created_by",
            table_name,
            "user",
            ["created_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            f"fk_{table_name}_updated_by",
            table_name,
            "user",
            ["updated_by"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    # Drop FK constraints in reverse order
    for table_name in [
        "connector_config",
        "integration_credential",
        "integration_sync_mapping",
        "integration_sync_conflict",
    ]:
        op.drop_constraint(
            f"fk_{table_name}_updated_by", table_name, type_="foreignkey"
        )
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )
