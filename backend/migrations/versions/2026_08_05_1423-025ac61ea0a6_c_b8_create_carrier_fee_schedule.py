"""c_b8_create_carrier_fee_schedule

Revision ID: 025ac61ea0a6
Revises: a1a52ec11da8
Create Date: 2026-08-05 14:23:00.000000+00:00

C-B8: Creates the carrier_fee_schedule operator-maintained config table.
Telnyx has no public API for pre-transaction pricing (Q#1 resolution), so
carrier fees are stored here and read by the quoting adapter at quote time.
Operator can update fees via SQL without a deploy.

Table: carrier_fee_schedule
  - StandardAuditMixin (created_at, updated_at, created_by, updated_by)
  - UNIQUE (fee_code, entity_type)
  - 3-trigger set: audit, guard_created_immutable, set_updated_at
  - 8 seed rows (4 fee_codes x 2 entity_types)

All inserts are idempotent (ON CONFLICT DO NOTHING) and wrapped in
SET LOCAL session_replication_role = 'replica' to bypass triggers.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "025ac61ea0a6"
down_revision: str | None = "a1a52ec11da8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Create carrier_fee_schedule table
    op.execute(
        sa.text(
            """
            CREATE TABLE carrier_fee_schedule (
                id              UUID        NOT NULL DEFAULT gen_random_uuid(),
                fee_code        TEXT        NOT NULL,
                entity_type     TEXT        NOT NULL,
                amount_cents    INTEGER     NOT NULL,
                description     TEXT        NOT NULL,
                is_active       BOOLEAN     NOT NULL DEFAULT true,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_by      UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
                updated_by      UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
                CONSTRAINT pk_carrier_fee_schedule PRIMARY KEY (id),
                CONSTRAINT uq_carrier_fee_schedule_code_entity UNIQUE (fee_code, entity_type),
                CONSTRAINT carrier_fee_schedule_entity_type_chk
                    CHECK (entity_type IN ('standard', 'sole_proprietor'))
            )
            """
        )
    )

    # 2. Audit trigger — fires audit.log_changes() on every change
    op.execute(
        sa.text(
            """
            CREATE TRIGGER audit_carrier_fee_schedule_changes
                AFTER INSERT OR DELETE OR UPDATE ON public.carrier_fee_schedule
                FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
            """
        )
    )

    # 3. Guard created_at/created_by immutability
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_carrier_fee_schedule_guard_created_immutable
                BEFORE UPDATE ON public.carrier_fee_schedule
                FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
            """
        )
    )

    # 4. Auto-bump updated_at on UPDATE
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_carrier_fee_schedule_set_updated_at
                BEFORE UPDATE ON public.carrier_fee_schedule
                FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
            """
        )
    )

    # 5. Seed initial fee rows (8 rows - 4 fee_codes x 2 entity_types)
    #    Idempotent: ON CONFLICT DO NOTHING
    op.execute(
        sa.text(
            """
            INSERT INTO public.carrier_fee_schedule
                (fee_code, entity_type, amount_cents, description, is_active, created_at, updated_at)
            VALUES
                ('brand_registration',        'standard',         400, 'Brand registration',                          true, NOW(), NOW()),
                ('brand_registration',        'sole_proprietor',  400, 'Brand registration',                          true, NOW(), NOW()),
                ('campaign_registration_3mo', 'standard',         1500, 'Campaign registration (3 months prepaid)',    true, NOW(), NOW()),
                ('campaign_registration_3mo', 'sole_proprietor',  1000, 'Campaign registration (3 months prepaid)',    true, NOW(), NOW()),
                ('phone_number',              'standard',         100, 'Phone number assignment',                      true, NOW(), NOW()),
                ('phone_number',              'sole_proprietor',  100, 'Phone number assignment',                      true, NOW(), NOW()),
                ('campaign_quarterly',        'standard',         1500, 'Campaign quarterly recurring',                 true, NOW(), NOW()),
                ('campaign_quarterly',        'sole_proprietor',  1000, 'Campaign quarterly recurring',                 true, NOW(), NOW())
            ON CONFLICT (fee_code, entity_type) DO NOTHING
            """
        )
    )

    op.execute("SET LOCAL session_replication_role = 'origin';")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_carrier_fee_schedule_set_updated_at "
        "ON public.carrier_fee_schedule;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_carrier_fee_schedule_guard_created_immutable "
        "ON public.carrier_fee_schedule;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_carrier_fee_schedule_changes "
        "ON public.carrier_fee_schedule;"
    )
    op.execute("DROP TABLE IF EXISTS public.carrier_fee_schedule CASCADE;")
    op.execute("SET LOCAL session_replication_role = 'origin';")
