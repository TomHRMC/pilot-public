"""Phase 6.0.1 Task 9: FK constraints for auth security tables

Revision ID: 942e0e011328
Revises: 58bb3299550a
Create Date: 2026-04-13 23:29:31.010825+00:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "942e0e011328"
down_revision: str | None = "58bb3299550a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    # For append-only tables (created_by only)
    for table_name in [
        "auth_api_token",
        "auth_email_verification",
        "auth_password_reset",
        "auth_password_history",
        "auth_mfa_otp",
        "auth_jwk",
    ]:
        op.create_foreign_key(
            f"fk_{table_name}_created_by",
            table_name,
            "user",
            ["created_by"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade():
    # Drop FK constraints in reverse order
    for table_name in [
        "auth_jwk",
        "auth_mfa_otp",
        "auth_password_history",
        "auth_password_reset",
        "auth_email_verification",
        "auth_api_token",
    ]:
        op.drop_constraint(
            f"fk_{table_name}_created_by", table_name, type_="foreignkey"
        )
