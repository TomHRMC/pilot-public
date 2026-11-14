"""c_b2_charter_entitlement_schema

Revision ID: 28af5f068549
Revises: a9089b7ad378
Create Date: 2026-08-04 11:57:59.653230+00:00

C-B2: Charter entitlement schema — adds Charter program lifecycle fields
and the tenant_messaging_registration table (10DLC provisioning state).

DDL changes (all column names verified via postgres-local MCP 2026-08-04):
  - subscription_tier: +4 cols (free_period_days, requires_payment_method,
    signup_cap, price_locked)
  - tenant: +3 cols (free_period_ends_at, charter_member_number,
    charter_eligible) + 2 partial indexes
  - tenant_tier_override: +1 col (override_free_period_ends_at)
  - tenant_messaging_registration: NEW table (14 cols + 4 audit = 18 total)

Data UPDATE (tier pricing + new field values for all 4 tiers):
  - Charter: $49/mo, $588 annual, 90 days free, no card, cap 12, price locked
  - Trial: 14 days, $0, no card, no cap, not locked
  - Starter: no free period, card required, no cap, not locked
  - Teams: no free period, card required, no cap, not locked

The new table inherits StandardAuditMixin (created_at, updated_at,
created_by, updated_by) — the raw DDL includes all four audit columns
per Rule 15 / Architect audit mixin rule.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "28af5f068549"
down_revision: Union[str, None] = "a9089b7ad378"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════════
    # Part 1: New columns on subscription_tier (4 cols)
    # ═══════════════════════════════════════════════════════════════
    op.execute(
        sa.text(
            """
            ALTER TABLE public.subscription_tier
              ADD COLUMN free_period_days INTEGER,
              ADD COLUMN requires_payment_method BOOLEAN NOT NULL DEFAULT TRUE,
              ADD COLUMN signup_cap INTEGER,
              ADD COLUMN price_locked BOOLEAN NOT NULL DEFAULT FALSE
            """
        )
    )

    # ═══════════════════════════════════════════════════════════════
    # Part 2: New columns on tenant (3 cols) + 2 partial indexes
    # ═══════════════════════════════════════════════════════════════
    op.execute(
        sa.text(
            """
            ALTER TABLE public.tenant
              ADD COLUMN free_period_ends_at TIMESTAMPTZ,
              ADD COLUMN charter_member_number INTEGER,
              ADD COLUMN charter_eligible BOOLEAN NOT NULL DEFAULT TRUE
            """
        )
    )

    # Partial index — only indexes non-NULL free_period_ends_at rows
    # (non-Charter tenants have NULL, so they're excluded from the index)
    op.execute(
        sa.text(
            """
            CREATE INDEX ix_tenant_free_period_ends_at
              ON public.tenant (free_period_ends_at)
              WHERE free_period_ends_at IS NOT NULL
            """
        )
    )

    # Partial unique index — enforces uniqueness on assigned charter numbers
    # while allowing multiple NULLs (non-Charter tenants)
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX ix_tenant_charter_member_number
              ON public.tenant (charter_member_number)
              WHERE charter_member_number IS NOT NULL
            """
        )
    )

    # ═══════════════════════════════════════════════════════════════
    # Part 3: New column on tenant_tier_override (1 col)
    # ═══════════════════════════════════════════════════════════════
    op.execute(
        sa.text(
            """
            ALTER TABLE public.tenant_tier_override
              ADD COLUMN override_free_period_ends_at TIMESTAMPTZ
            """
        )
    )

    # ═══════════════════════════════════════════════════════════════
    # Part 4: New table — tenant_messaging_registration
    # 10DLC provisioning state machine. One row per tenant (UNIQUE on tenant_id).
    # Inherits StandardAuditMixin pattern: all 4 audit columns included in DDL.
    # ═══════════════════════════════════════════════════════════════
    op.execute(
        sa.text(
            """
            CREATE TABLE public.tenant_messaging_registration (
              id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
              tenant_id               UUID NOT NULL REFERENCES public.tenant(id),
              entity_type             TEXT NOT NULL,
              status                  TEXT NOT NULL,
              telnyx_brand_id         TEXT,
              telnyx_campaign_id      TEXT,
              telnyx_phone_number     TEXT,
              quoted_setup_cents      INTEGER,
              quoted_monthly_cents    INTEGER,
              stripe_checkout_id      TEXT,
              stripe_payment_intent   TEXT,
              otp_requested_at        TIMESTAMPTZ,
              otp_verified_at         TIMESTAMPTZ,
              failure_reason          TEXT,
              created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
              updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
              created_by              UUID,
              updated_by              UUID,
              CONSTRAINT uq_tenant_messaging_registration_tenant UNIQUE (tenant_id)
            )
            """
        )
    )

    # ═══════════════════════════════════════════════════════════════
    # Part 5: Update tier seed data (Charter pricing + new fields)
    # Uses SET LOCAL session_replication_role = replica for the data UPDATEs
    # (consistent with C-B1 pattern; subscription_tier has no FK dependencies
    # on these new columns, but the replica role keeps the pattern uniform).
    # ═══════════════════════════════════════════════════════════════
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Charter: $49/mo flat (annual rate billed monthly), 90 days free,
    # no card, cap 12, price locked
    op.execute(
        sa.text(
            """
            UPDATE public.subscription_tier SET
              monthly_price_cents = 4900,
              annual_price_cents = 58800,
              free_period_days = 90,
              requires_payment_method = FALSE,
              signup_cap = 12,
              price_locked = TRUE,
              updated_at = NOW()
            WHERE tier_name = 'charter'
            """
        )
    )

    # Trial: 14 days, $0, no card, no cap, not locked
    op.execute(
        sa.text(
            """
            UPDATE public.subscription_tier SET
              free_period_days = 14,
              requires_payment_method = FALSE,
              signup_cap = NULL,
              price_locked = FALSE,
              updated_at = NOW()
            WHERE tier_name = 'trial'
            """
        )
    )

    # Starter: no free period, card required, no cap, not locked
    op.execute(
        sa.text(
            """
            UPDATE public.subscription_tier SET
              free_period_days = NULL,
              requires_payment_method = TRUE,
              signup_cap = NULL,
              price_locked = FALSE,
              updated_at = NOW()
            WHERE tier_name = 'starter'
            """
        )
    )

    # Teams: no free period, card required, no cap, not locked
    op.execute(
        sa.text(
            """
            UPDATE public.subscription_tier SET
              free_period_days = NULL,
              requires_payment_method = TRUE,
              signup_cap = NULL,
              price_locked = FALSE,
              updated_at = NOW()
            WHERE tier_name = 'teams'
            """
        )
    )

    op.execute("SET LOCAL session_replication_role = 'origin';")


def downgrade() -> None:
    # Reverse all changes — drop table, drop columns, restore old tier pricing.
    # Order: data UPDATEs first (restore old values), then DDL drops.

    # ═══════════════════════════════════════════════════════════════
    # Reverse Part 5: Restore old tier pricing + null out new fields
    # ═══════════════════════════════════════════════════════════════
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Charter back to $0/$0 (C-B1 state)
    op.execute(
        sa.text(
            """
            UPDATE public.subscription_tier SET
              monthly_price_cents = 0,
              annual_price_cents = 0,
              updated_at = NOW()
            WHERE tier_name = 'charter'
            """
        )
    )

    op.execute("SET LOCAL session_replication_role = 'origin';")

    # ═══════════════════════════════════════════════════════════════
    # Reverse Part 4: Drop tenant_messaging_registration table
    # ═══════════════════════════════════════════════════════════════
    op.execute(sa.text("DROP TABLE IF EXISTS public.tenant_messaging_registration;"))

    # ═══════════════════════════════════════════════════════════════
    # Reverse Part 3: Drop override_free_period_ends_at from tenant_tier_override
    # ═══════════════════════════════════════════════════════════════
    op.execute(
        sa.text(
            "ALTER TABLE public.tenant_tier_override "
            "DROP COLUMN IF EXISTS override_free_period_ends_at;"
        )
    )

    # ═══════════════════════════════════════════════════════════════
    # Reverse Part 2: Drop indexes + columns from tenant
    # ═══════════════════════════════════════════════════════════════
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_tenant_charter_member_number;"))
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_tenant_free_period_ends_at;"))
    op.execute(
        sa.text(
            "ALTER TABLE public.tenant "
            "DROP COLUMN IF EXISTS charter_eligible, "
            "DROP COLUMN IF EXISTS charter_member_number, "
            "DROP COLUMN IF EXISTS free_period_ends_at;"
        )
    )

    # ═══════════════════════════════════════════════════════════════
    # Reverse Part 1: Drop columns from subscription_tier
    # ═══════════════════════════════════════════════════════════════
    op.execute(
        sa.text(
            "ALTER TABLE public.subscription_tier "
            "DROP COLUMN IF EXISTS price_locked, "
            "DROP COLUMN IF EXISTS signup_cap, "
            "DROP COLUMN IF EXISTS requires_payment_method, "
            "DROP COLUMN IF EXISTS free_period_days;"
        )
    )
