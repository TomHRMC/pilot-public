"""qt_fix_1_quote_template_line_tenant_nullable

Revision ID: 990231f963b0
Revises: 44b3427a0e57
Create Date: 2026-07-30 17:50:48.045074+00:00

QT-FIX-1: Make quote_template_line.tenant_id nullable so system templates
(tenant_id IS NULL) can own their lines at the platform level, matching the
already-nullable parent quote_template.tenant_id.

upgrade(): DROP NOT NULL on quote_template_line.tenant_id, then convert the
9 existing system-template lines (parent quote_template.tenant_id IS NULL)
from the test-tenant workaround (0000…0001) to tenant-agnostic NULL.

downgrade() caveat: restores the test-tenant workaround and re-applies NOT
NULL. This assumes the canonical test tenant 00000000-0000-0000-0000-000000000001
exists. On a database without that tenant, delete the NULL-tenant
system-template lines (or re-seed the test tenant) before downgrading.
Downgrade is dev/local only.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "990231f963b0"
down_revision = "44b3427a0e57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Drop NOT NULL — the tenant FK (ON DELETE RESTRICT) stays valid for
    #    NULL values (a NULL FK does not reference any row, so RESTRICT never
    #    fires).
    op.execute(
        "ALTER TABLE public.quote_template_line ALTER COLUMN tenant_id DROP NOT NULL;"
    )

    # 2. Convert existing system-template lines from the test-tenant
    #    workaround to tenant-agnostic NULL. Scoped to lines whose parent
    #    template is a system template (quote_template.tenant_id IS NULL) —
    #    never touches real tenant lines.
    op.execute(
        """
        UPDATE public.quote_template_line qtl
        SET tenant_id = NULL
        FROM public.quote_template qt
        WHERE qtl.quote_template_id = qt.id
          AND qt.tenant_id IS NULL
          AND qtl.tenant_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    """Restore the test-tenant workaround + NOT NULL.

    CAVEAT: requires the canonical test tenant
    00000000-0000-0000-0000-000000000001 to exist. On a DB without it, delete
    the NULL-tenant system-template lines (or re-seed the test tenant) before
    downgrading. Downgrade is dev/local only.
    """
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Re-attach system-template lines to the canonical test tenant so
    #    NOT NULL can be restored.
    op.execute(
        """
        UPDATE public.quote_template_line qtl
        SET tenant_id = '00000000-0000-0000-0000-000000000001'
        FROM public.quote_template qt
        WHERE qtl.quote_template_id = qt.id
          AND qt.tenant_id IS NULL
          AND qtl.tenant_id IS NULL;
        """
    )

    # 2. Restore NOT NULL.
    op.execute(
        "ALTER TABLE public.quote_template_line ALTER COLUMN tenant_id SET NOT NULL;"
    )
