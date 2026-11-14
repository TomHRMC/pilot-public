"""phase_fe_1_batch_b5_rbac_dashboard_manage

Revision ID: ed3d99abe247
Revises: d9b769a82720
Create Date: 2026-05-01 17:51:00.000000

Adds 'dashboard.manage' permission to owner and office_staff roles.
- owner already has '*' (wildcard), so this is additive documentation-only for owner.
- office_staff and technician get 'dashboard.manage' so they can manage their own widgets.
- accountant gets 'dashboard.manage' (read-only widgets for their financial views).

B5/A5: Required for dashboard widget CRUD endpoints.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ed3d99abe247"
down_revision: str | None = "d9b769a82720"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add dashboard.manage to all roles that have reports.view or need dashboard access.
    # owner already has '*' wildcard — no change needed.
    # office_staff, technician, accountant all get dashboard.manage.
    op.execute("""
        UPDATE tenant_user_role
        SET permissions = permissions || '["dashboard.manage"]'::jsonb,
            updated_at = NOW()
        WHERE code IN ('office_staff', 'technician', 'accountant')
          AND NOT (permissions @> '["dashboard.manage"]'::jsonb)
    """)


def downgrade() -> None:
    # Remove dashboard.manage from roles that don't have it by default
    op.execute("""
        UPDATE tenant_user_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text != '"dashboard.manage"'
        ),
        updated_at = NOW()
        WHERE code IN ('office_staff', 'technician', 'accountant')
    """)
