"""phase_4_8_replace_user_check_constraints_task1

Revision ID: 3ca8bf106191
Revises: be00bcc02754
Create Date: 2026-04-08 13:13:13.743146+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3ca8bf106191"
down_revision: str | None = "be00bcc02754"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Replace legacy user CHECK constraints with boolean-based logic.

    CRITICAL: Legacy constraints hardcoded obsolete platform role values
    ('staff', 'superadmin') that no longer exist in current seed data.
    This prevented creation of platform users with modern roles
    ('accountant', 'owner', 'support').

    Pre-migration validation: Confirmed no users have legacy role codes.

    Changes:
    1. Drop user_platform_role_chk (legacy: hardcoded role values)
    2. Drop user_platform_mfa_required_chk (legacy: hardcoded role values)
    3. Add user_platform_role_chk (new: boolean logic based on is_platform_user)
    4. Add user_platform_mfa_required_chk (new: all platform users require MFA)

    Reference: dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md
    Authority: dev-docs/db-design/aevofab-db-schema-v2.6h.json
    """
    # Drop legacy constraints with hardcoded role values
    op.drop_constraint("user_platform_role_chk", "user", type_="check")
    op.drop_constraint("user_platform_mfa_required_chk", "user", type_="check")

    # Add new constraints using boolean logic (not hardcoded roles)
    op.create_check_constraint(
        "user_platform_role_chk",
        "user",
        "(is_platform_user = true AND platform_role_code IS NOT NULL) OR (is_platform_user = false AND platform_role_code IS NULL)",
    )
    op.create_check_constraint(
        "user_platform_mfa_required_chk",
        "user",
        "(is_platform_user = false) OR (mfa_enforced = true)",
    )


def downgrade() -> None:
    """
    Rollback: Restore legacy constraints (for testing only).

    WARNING: This restores constraints with hardcoded 'staff', 'superadmin'
    role values that are obsolete and will block platform user creation
    with modern roles.
    """
    # Drop new boolean-based constraints
    op.drop_constraint("user_platform_role_chk", "user", type_="check")
    op.drop_constraint("user_platform_mfa_required_chk", "user", type_="check")

    # Restore legacy constraints with hardcoded role values
    op.create_check_constraint(
        "user_platform_role_chk",
        "user",
        "platform_role_code IS NULL OR platform_role_code IN ('staff', 'superadmin')",
    )
    op.create_check_constraint(
        "user_platform_mfa_required_chk",
        "user",
        "platform_role_code IS NULL OR (platform_role_code IN ('staff', 'superadmin') AND mfa_enforced = true)",
    )
