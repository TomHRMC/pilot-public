"""phase_fe_1_batch_b5_user_dashboard_widget_triggers

Revision ID: 87ee9cc8049d
Revises: ed3d99abe247
Create Date: 2026-05-01 18:16:00.000000

Adds the two standard triggers to user_dashboard_widget that are present on
all mutable tenant tables in the project:
  1. audit_user_dashboard_widget_changes  — fires audit.log_changes() on every change
  2. trg_user_dashboard_widget_set_updated_at — auto-updates updated_at on every UPDATE

These triggers are present in the Golden Master JSON (pilot-db-schema-v2.6h.json)
but were not included in the original table creation migration (d9b769a82720).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "87ee9cc8049d"
down_revision: str | None = "ed3d99abe247"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TRIGGER audit_user_dashboard_widget_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.user_dashboard_widget
        FOR EACH ROW
        EXECUTE FUNCTION audit.log_changes()
    """)

    op.execute("""
        CREATE TRIGGER trg_user_dashboard_widget_set_updated_at
        BEFORE UPDATE ON public.user_dashboard_widget
        FOR EACH ROW
        EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_user_dashboard_widget_set_updated_at "
        "ON public.user_dashboard_widget"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_user_dashboard_widget_changes "
        "ON public.user_dashboard_widget"
    )
