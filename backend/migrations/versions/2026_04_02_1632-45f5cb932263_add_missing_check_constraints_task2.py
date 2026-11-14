"""add_missing_check_constraints_task2

Revision ID: 45f5cb932263
Revises: 0575f69cd5db
Create Date: 2026-04-02 16:32:25.385916+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "45f5cb932263"
down_revision: str | None = "0575f69cd5db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add check constraint for platform users MFA requirement
    op.create_check_constraint(
        "user_platform_mfa_required_chk",
        "user",
        "platform_role_code IS NULL OR (platform_role_code IN ('staff', 'superadmin') AND mfa_enforced = true)",
    )

    # Add email format check constraint for contact_portal_invite
    op.create_check_constraint(
        "contact_portal_invite_email_chk",
        "contact_portal_invite",
        "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
    )

    # Add email format check constraint for customer (nullable)
    op.create_check_constraint(
        "customer_email_format_chk",
        "customer",
        "email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
    )

    # Add email format check constraint for tenant_user_invite
    op.create_check_constraint(
        "tenant_user_invite_email_format_chk",
        "tenant_user_invite",
        "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
    )


def downgrade() -> None:
    # Remove check constraints in reverse order
    op.drop_constraint(
        "tenant_user_invite_email_format_chk", "tenant_user_invite", type_="check"
    )
    op.drop_constraint("customer_email_format_chk", "customer", type_="check")
    op.drop_constraint(
        "contact_portal_invite_email_chk", "contact_portal_invite", type_="check"
    )
    op.drop_constraint("user_platform_mfa_required_chk", "user", type_="check")
