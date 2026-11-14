"""remove_audit_triggers_from_composite_pk_tables

Revision ID: 3f70e1ae4474
Revises: 6a5d362b524d
Create Date: 2026-03-31 20:36:08.123456+00:00

Remove audit triggers from tables with composite or non-standard primary keys.

Context:
- The audit.log_changes() and audit.log_changes_code_pk() functions assume single-column PKs
- 4 tables have non-standard PKs that cause trigger errors:
  * tenant_user: PRIMARY KEY (tenant_id, user_id) - composite
  * pricing_cache: PRIMARY KEY (supplier_id, sku) - composite
  * tenant_product_feature_override: PRIMARY KEY (tenant_id, product_feature_code) - composite
  * idempotency_key: PRIMARY KEY (key) - single but non-standard name

These tables are either:
- Reference/junction tables (tenant_user, tenant_product_feature_override)
- Cache tables (pricing_cache)
- Technical tables (idempotency_key)

None are critical for compliance audit trails, so removing their triggers is acceptable.

Reference: Phase 4.5, Task 6 - Audit Trigger Coverage
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f70e1ae4474"
down_revision: str | None = "6a5d362b524d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Remove audit triggers from tables with composite/non-standard primary keys.

    These tables cannot use the current audit functions which assume single-column
    primary keys named 'id' or 'code'.
    """

    # Remove triggers from composite PK tables
    op.execute("DROP TRIGGER IF EXISTS audit_tenant_user_changes ON tenant_user;")
    op.execute("DROP TRIGGER IF EXISTS audit_pricing_cache_changes ON pricing_cache;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_product_feature_override_changes ON tenant_product_feature_override;"
    )

    # Remove trigger from non-standard PK table
    op.execute(
        "DROP TRIGGER IF EXISTS audit_idempotency_key_changes ON idempotency_key;"
    )


def downgrade() -> None:
    """
    Re-add the (broken) triggers - mainly for migration reversibility.
    Note: These triggers will fail if data is inserted, but the downgrade maintains
    consistency with the previous migration state.
    """

    # Re-add triggers (will be broken until proper composite-PK function exists)
    op.execute("""
        CREATE TRIGGER audit_tenant_user_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_user
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_pricing_cache_changes
        AFTER INSERT OR UPDATE OR DELETE ON pricing_cache
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_product_feature_override_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_product_feature_override
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_idempotency_key_changes
        AFTER INSERT OR UPDATE OR DELETE ON idempotency_key
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
