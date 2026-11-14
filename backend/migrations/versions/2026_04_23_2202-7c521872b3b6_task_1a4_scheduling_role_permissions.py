"""task_1a4_scheduling_role_permissions

Adds scheduling RBAC permission strings to tenant_user_role rows:

  office_staff  → schedule.manage, schedule.view_all
  technician    → schedule.view_own
  owner         → already covered by wildcard "*" (no change)
  accountant    → no scheduling access (no change)

Uses idempotent JSONB array append: permissions are only added when they
are not already present in the existing permissions array.

Revision ID: 7c521872b3b6
Revises: 992df63709de
Create Date: 2026-04-23 22:02:43
"""

from alembic import op

# revision identifiers
revision = "7c521872b3b6"
down_revision = "992df63709de"
branch_labels = None
depends_on = None

# New permissions keyed by role code
_ROLE_PERMISSIONS = {
    "office_staff": ["schedule.manage", "schedule.view_all"],
    "technician": ["schedule.view_own"],
}


def _add_permissions_sql(role_code: str, permissions: list[str]) -> str:
    """
    Build idempotent SQL: for each permission, append it to the JSONB array
    only when it is NOT already present.
    """
    # Build a chain of updates, one per permission
    parts = []
    for perm in permissions:
        # jsonb_array_elements_text returns the array unpacked; NOT EXISTS guard ensures idempotency
        parts.append(f"""
        UPDATE tenant_user_role
        SET permissions = permissions || '"{perm}"'::jsonb
        WHERE code = '{role_code}'
          AND is_active = true
          AND NOT (
              SELECT bool_or(elem.value = '"{perm}"')
              FROM jsonb_array_elements(permissions) AS elem(value)
          );
        """)
    return "\n".join(parts)


def _remove_permissions_sql(role_code: str, permissions: list[str]) -> str:
    """
    Build idempotent SQL: remove each permission from the JSONB array.
    Uses jsonb_agg to rebuild array without the target strings.
    """
    parts = []
    for perm in permissions:
        parts.append(f"""
        UPDATE tenant_user_role
        SET permissions = (
            SELECT COALESCE(jsonb_agg(elem ORDER BY elem), '[]'::jsonb)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text != '"{perm}"'
        )
        WHERE code = '{role_code}'
          AND is_active = true
          AND permissions @> '"{perm}"'::jsonb;
        """)
    return "\n".join(parts)


def upgrade() -> None:
    for role_code, permissions in _ROLE_PERMISSIONS.items():
        op.execute(_add_permissions_sql(role_code, permissions))


def downgrade() -> None:
    for role_code, permissions in _ROLE_PERMISSIONS.items():
        op.execute(_remove_permissions_sql(role_code, permissions))
