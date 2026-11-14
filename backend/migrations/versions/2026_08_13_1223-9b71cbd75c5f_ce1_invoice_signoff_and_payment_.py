"""ce1_invoice_signoff_and_payment_variance_resolution

Revision ID: 9b71cbd75c5f
Revises: ba16d3b7fb6f
Create Date: 2026-08-13 12:23:17.123456+00:00

CE-1 Part A: Invoice sign-off capture + overpayment variance resolution.

Two changes:
  1. New table ``invoice_signoff`` — customer signature captured at invoice
     sign-off (mobile, offline-first). One active row per invoice (partial
     unique index); re-capture supersedes the prior row.
  2. Four nullable columns on ``payment`` for overpayment variance resolution
     tracking (record-keeping only — no Stripe refund execution).

Design doc: dev-docs/architecture-design/batch-designs/batch-ce-1-design.md §B.
No new triggers or functions (design §B.4 — audit columns are app-managed via
StandardAuditMixin, matching the C-B2 tenant_messaging_registration precedent).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b71cbd75c5f"
down_revision: str | None = "ba16d3b7fb6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. New table: invoice_signoff ──────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE TABLE public.invoice_signoff (
                id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id             UUID NOT NULL REFERENCES public.tenant (id),
                invoice_id            UUID NOT NULL REFERENCES public.invoice (id),
                signed_by_name        VARCHAR(200) NOT NULL,
                signature_object_key  VARCHAR(500) NOT NULL,
                terms_acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
                signed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
                client_capture_at     TIMESTAMPTZ NULL,
                captured_by_user_id   UUID NOT NULL REFERENCES public."user" (id),
                superseded_at         TIMESTAMPTZ NULL,
                idempotency_key       VARCHAR(100) NULL,
                created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_by            UUID NULL,
                updated_by            UUID NULL,
                CONSTRAINT ck_invoice_signoff_terms CHECK (terms_acknowledged = TRUE)
            )
            """
        )
    )

    # One active (non-superseded) sign-off per invoice — race-safe re-capture
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_invoice_signoff_one_active
                ON public.invoice_signoff (invoice_id)
                WHERE superseded_at IS NULL
            """
        )
    )

    # Tenant-scoped lookups
    op.execute(
        sa.text(
            """
            CREATE INDEX ix_invoice_signoff_tenant_invoice
                ON public.invoice_signoff (tenant_id, invoice_id)
            """
        )
    )

    # Offline replay dedup (natural-key fallback per §15.4)
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_invoice_signoff_tenant_idempotency
                ON public.invoice_signoff (tenant_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL
            """
        )
    )

    # ── 2. payment variance-resolution columns ─────────────────────────────
    op.execute(
        sa.text(
            "ALTER TABLE public.payment ADD COLUMN variance_resolution VARCHAR(20) NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE public.payment ADD COLUMN variance_resolution_note TEXT NULL"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE public.payment ADD COLUMN variance_resolved_at TIMESTAMPTZ NULL"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE public.payment
              ADD COLUMN variance_resolved_by_user_id UUID NULL
              REFERENCES public."user" (id)
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE public.payment ADD CONSTRAINT ck_payment_variance_resolution
                CHECK (variance_resolution IS NULL
                       OR variance_resolution IN ('credit', 'refund_offline', 'writeoff'))
            """
        )
    )


def downgrade() -> None:
    # ── Reverse 2: payment variance-resolution columns ─────────────────────
    op.execute(
        sa.text(
            "ALTER TABLE public.payment DROP CONSTRAINT IF EXISTS ck_payment_variance_resolution"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE public.payment DROP COLUMN IF EXISTS variance_resolved_by_user_id"
        )
    )
    op.execute(
        sa.text("ALTER TABLE public.payment DROP COLUMN IF EXISTS variance_resolved_at")
    )
    op.execute(
        sa.text(
            "ALTER TABLE public.payment DROP COLUMN IF EXISTS variance_resolution_note"
        )
    )
    op.execute(
        sa.text("ALTER TABLE public.payment DROP COLUMN IF EXISTS variance_resolution")
    )

    # ── Reverse 1: drop invoice_signoff table ──────────────────────────────
    op.execute(
        sa.text("DROP INDEX IF EXISTS public.uq_invoice_signoff_tenant_idempotency")
    )
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_invoice_signoff_tenant_invoice"))
    op.execute(sa.text("DROP INDEX IF EXISTS public.uq_invoice_signoff_one_active"))
    op.execute(sa.text("DROP TABLE IF EXISTS public.invoice_signoff"))
