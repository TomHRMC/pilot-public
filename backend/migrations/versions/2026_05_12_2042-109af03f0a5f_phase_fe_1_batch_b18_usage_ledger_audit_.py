"""phase_fe_1_batch_b18_usage_ledger_audit_trigger

FIND-130 (S2 High) — Add audit.log_changes() trigger to usage_ledger table.

usage_ledger is the revenue backbone (voice AI minutes, QB sync calls, SMS
segments). Without an audit trigger, billing disputes have no forensic trail.
PRD-§3.1-F1 requires audit.log_changes() on all core tables.

MCP-verified 2026-05-10: no audit trigger exists on usage_ledger.

Revision ID: 109af03f0a5f
Revises: 316581e91652
Create Date: 2026-05-12 20:42:35.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "109af03f0a5f"
down_revision: str | None = "316581e91652"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TRIGGER audit_usage_ledger_changes
          AFTER INSERT OR UPDATE OR DELETE ON public.usage_ledger
          FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_usage_ledger_changes ON public.usage_ledger"
    )
