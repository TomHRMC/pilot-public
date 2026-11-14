"""plp_fix_3_backfill_quote_version_v1

Revision ID: ec2df153a859
Revises: c8d06a6ffdd2
Create Date: 2026-09-02 14:17:53.845938+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec2df153a859"
down_revision: str | None = "c8d06a6ffdd2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill an active v1 quote_version for every versionless quote.

    Quotes created before PLP-FIX-3 (or via builder paths that skipped version
    creation) have no active quote_version row, so GET /quotes/{id}/detail
    404s. This INSERT ... SELECT heals them idempotently. The marker key
    ``snapshot->>'source' = 'plp_fix_3_backfill'`` makes the downgrade surgical.

    Scope = quotes with NO active version (covers both no-versions-at-all and
    only-inactive-versions). ``version_no = COALESCE(max,0)+1`` respects
    ``uq_quote_version_quote_id_version_no``.
    """
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute(
        """
        INSERT INTO public.quote_version
            (id, tenant_id, quote_id, version_no, snapshot, is_active,
             presentation_style, created_at, created_by)
        SELECT
            gen_random_uuid(),
            q.tenant_id,
            q.id,
            COALESCE(mx.max_vn, 0) + 1,
            jsonb_build_object(
                'quote', to_jsonb(q),
                'lines', COALESCE(ls.lines, '[]'::jsonb),
                'source', 'plp_fix_3_backfill'
            ),
            true,
            'clean',
            now(),
            NULL
        FROM public.quote q
        LEFT JOIN (
            SELECT quote_id, max(version_no) AS max_vn
            FROM public.quote_version GROUP BY quote_id
        ) mx ON mx.quote_id = q.id
        LEFT JOIN (
            SELECT quote_id,
                   jsonb_agg(to_jsonb(ql) || '{"taxes": []}'::jsonb) AS lines
            FROM public.quote_line ql GROUP BY quote_id
        ) ls ON ls.quote_id = q.id
        WHERE NOT EXISTS (
            SELECT 1 FROM public.quote_version av
            WHERE av.quote_id = q.id AND av.is_active
        )
        """
    )


def downgrade() -> None:
    """Remove only the rows this migration created (surgical marker-key DELETE)."""
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute(
        "DELETE FROM public.quote_version "
        "WHERE snapshot->>'source' = 'plp_fix_3_backfill';"
    )
