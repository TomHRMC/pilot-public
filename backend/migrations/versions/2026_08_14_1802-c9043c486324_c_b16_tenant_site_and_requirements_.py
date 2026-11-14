"""c_b16_tenant_site_and_requirements_emailed_at

Revision ID: c9043c486324
Revises: 9b71cbd75c5f
Create Date: 2026-08-14 18:02:02.700817+00:00

C-B16 Part A — Pilot-Hosted Tenant Sites (SMS Compliance Pages + Compliance Kit)

DDL-only migration (no data changes):
  1. New table ``public.tenant_site`` (25 columns incl. 4 StandardAuditMixin cols)
     + 3 unique indexes + ``set_updated_at_tenant_site`` trigger.
  2. Nullable ALTER on ``public.tenant_10dlc_profile`` — adds ``requirements_emailed_at``.

Design doc: dev-docs/architecture-design/batch-designs/batch-c-b16-design.md §B.1 + §B.2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9043c486324"
down_revision: str | None = "9b71cbd75c5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. New table: public.tenant_site ──────────────────────────────────────
    op.execute(
        """
        CREATE TABLE public.tenant_site (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id               UUID NOT NULL REFERENCES public.tenant (id),
            slug                    VARCHAR(63) NOT NULL,
            site_kind               VARCHAR(20) NOT NULL,
            status                  VARCHAR(20) NOT NULL DEFAULT 'draft',
            display_name            VARCHAR(200) NOT NULL,
            tagline                 VARCHAR(300) NULL,
            public_email            VARCHAR(320) NULL,
            public_phone            VARCHAR(32) NULL,
            public_city             VARCHAR(120) NULL,
            public_state            VARCHAR(2) NULL,
            public_address_line1    VARCHAR(200) NULL,
            public_postal_code      VARCHAR(10) NULL,
            show_full_address       BOOLEAN NOT NULL DEFAULT FALSE,
            template_version        VARCHAR(20) NOT NULL DEFAULT 'v1',
            published_snapshot      JSONB NULL,
            published_at            TIMESTAMPTZ NULL,
            unpublished_at          TIMESTAMPTZ NULL,
            kit_sent_at             TIMESTAMPTZ NULL,
            website_auto_populated  BOOLEAN NOT NULL DEFAULT FALSE,
            idempotency_key         VARCHAR(100) NULL,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by              UUID NULL,
            updated_by              UUID NULL,
            CONSTRAINT ck_tenant_site_kind CHECK (site_kind IN ('compliance_kit', 'hosted_compliance')),
            CONSTRAINT ck_tenant_site_status CHECK (status IN ('draft', 'published', 'unpublished')),
            CONSTRAINT ck_tenant_site_slug_format CHECK (slug ~ '^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$')
        );
        """
    )

    # 1:1 per tenant for MVP
    op.execute(
        "CREATE UNIQUE INDEX uq_tenant_site_tenant ON public.tenant_site (tenant_id);"
    )

    # Slug globally unique across the shared hosting domain
    op.execute("CREATE UNIQUE INDEX uq_tenant_site_slug ON public.tenant_site (slug);")

    # Offline/idempotent upsert fallback (natural-key convention §15.4)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_tenant_site_tenant_idempotency
            ON public.tenant_site (tenant_id, idempotency_key)
            WHERE idempotency_key IS NOT NULL;
        """
    )

    # House updated_at trigger (verified convention on tenant_10dlc_profile)
    op.execute(
        """
        CREATE TRIGGER set_updated_at_tenant_site BEFORE UPDATE ON public.tenant_site
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # ── 2. Nullable ALTER: tenant_10dlc_profile.requirements_emailed_at ────────
    op.add_column(
        "tenant_10dlc_profile",
        sa.Column(
            "requirements_emailed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Reverse order: drop column, drop trigger, drop table (indexes drop with it)
    op.drop_column("tenant_10dlc_profile", "requirements_emailed_at")

    op.execute(
        "DROP TRIGGER IF EXISTS set_updated_at_tenant_site ON public.tenant_site;"
    )
    op.execute("DROP TABLE IF EXISTS public.tenant_site;")
