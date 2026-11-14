"""phase_fe_1_batch_b18_audit_triggers_rate_version_pricing_cache

FIND-131 (S2 High) — Add audit.log_changes() triggers to labor_rate_version
and pricing_cache tables.

labor_rate_version: Rate changes feed directly into labor cost calculations on
quotes, time entries, and job profitability. Without audit, rate changes produce
unexplained billing differences with no forensic trail.

pricing_cache: Supplier price changes that feed quote estimates are untracked.

MCP-verified 2026-05-10: no audit triggers exist on either table.

Revision ID: 00b2f1d3e1ce
Revises: 109af03f0a5f
Create Date: 2026-05-12 20:46:12.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00b2f1d3e1ce"
down_revision: str | None = "109af03f0a5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TRIGGER audit_labor_rate_version_changes
          AFTER INSERT OR UPDATE OR DELETE ON public.labor_rate_version
          FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_pricing_cache_changes
          AFTER INSERT OR UPDATE OR DELETE ON public.pricing_cache
          FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_pricing_cache_changes ON public.pricing_cache"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_labor_rate_version_changes ON public.labor_rate_version"
    )
