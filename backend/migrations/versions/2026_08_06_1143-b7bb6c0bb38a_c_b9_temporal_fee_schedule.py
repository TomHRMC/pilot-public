"""c_b9_temporal_fee_schedule

Revision ID: b7bb6c0bb38a
Revises: 545a54f97cf7
Create Date: 2026-08-06 11:43:09.000000+00:00

C-B9 Task 2: Migrate carrier_fee_schedule to a temporal lookup table with
millicents precision (1 millicent = $0.00001).

Per design doc §B.6:
  1. Add effective_from (TIMESTAMPTZ NOT NULL DEFAULT now()), effective_to (TIMESTAMPTZ),
     amount_millicents (BIGINT)
  2. Migrate existing rows: amount_millicents = amount_cents * 1000,
     effective_from = created_at, effective_to = NULL
  3. Drop amount_cents and is_active columns
  4. Set amount_millicents NOT NULL
  5. CREATE EXTENSION IF NOT EXISTS btree_gist (already exists — verified via MCP)
  6. Add GiST exclusion constraint on (fee_code, entity_type, tstzrange(effective_from, effective_to))
  7. Drop old UNIQUE constraint uq_carrier_fee_schedule_code_entity
  8. Seed 12 new fee codes (brand_vetting, campaign_registration_tmobile,
     phone_number_assignment, surcharge_att/tmobile/verizon — each x2 entity types)

Millicents convention: 1 millicent = 1/1000 of a cent = $0.00001.
  - $4.00 = 400,000 millicents
  - $0.003/segment = 300 millicents
  - $0.0031/segment = 310 millicents
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7bb6c0bb38a"
down_revision: str | None = "545a54f97cf7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Add temporal + millicents columns
    op.add_column(
        "carrier_fee_schedule",
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "carrier_fee_schedule",
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "carrier_fee_schedule",
        sa.Column("amount_millicents", sa.BigInteger(), nullable=True),
    )

    # 2. Migrate existing data: amount_millicents = amount_cents * 1000,
    #    effective_from = created_at, effective_to = NULL
    op.execute(
        sa.text(
            """
            UPDATE public.carrier_fee_schedule SET
                amount_millicents = amount_cents * 1000,
                effective_from = created_at,
                effective_to = NULL
            """
        )
    )

    # 3. Drop old columns
    op.drop_column("carrier_fee_schedule", "amount_cents")
    op.drop_column("carrier_fee_schedule", "is_active")

    # 4. Make amount_millicents NOT NULL
    op.alter_column(
        "carrier_fee_schedule",
        "amount_millicents",
        existing_type=sa.BigInteger(),
        nullable=False,
    )

    # 5. Ensure btree_gist extension exists (MCP confirmed it already does)
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    # 6. Drop old UNIQUE constraint (replaced by GiST exclusion)
    op.drop_constraint(
        "uq_carrier_fee_schedule_code_entity",
        "carrier_fee_schedule",
        type_="unique",
    )

    # 7. Add GiST exclusion constraint
    op.execute(
        sa.text(
            """
            ALTER TABLE public.carrier_fee_schedule
                ADD CONSTRAINT uq_carrier_fee_schedule_temporal
                EXCLUDE USING gist (
                    fee_code WITH =,
                    entity_type WITH =,
                    tstzrange(effective_from, effective_to) WITH &&
                )
            """
        )
    )

    # 8. Seed 12 new fee codes (idempotent — ON CONFLICT DO NOTHING)
    op.execute(
        sa.text(
            """
            INSERT INTO public.carrier_fee_schedule
                (fee_code, entity_type, amount_millicents, description,
                 effective_from, effective_to, created_at, updated_at)
            VALUES
                ('brand_vetting',                   'standard',         4000000, 'External brand vetting (optional)',          now(), NULL, now(), now()),
                ('brand_vetting',                   'sole_proprietor',  4000000, 'External brand vetting (optional)',          now(), NULL, now(), now()),
                ('campaign_registration_tmobile',   'standard',         5000000, 'T-Mobile campaign registration (currently waived)', now(), NULL, now(), now()),
                ('campaign_registration_tmobile',   'sole_proprietor',  5000000, 'T-Mobile campaign registration (currently waived)', now(), NULL, now(), now()),
                ('phone_number_assignment',         'standard',         30,      'Phone number to campaign assignment',        now(), NULL, now(), now()),
                ('phone_number_assignment',         'sole_proprietor',  30,      'Phone number to campaign assignment',        now(), NULL, now(), now()),
                ('surcharge_att',                   'standard',         300,     'Per-segment surcharge (AT&T)',               now(), NULL, now(), now()),
                ('surcharge_att',                   'sole_proprietor',  300,     'Per-segment surcharge (AT&T)',               now(), NULL, now(), now()),
                ('surcharge_tmobile',               'standard',         300,     'Per-segment surcharge (T-Mobile)',           now(), NULL, now(), now()),
                ('surcharge_tmobile',               'sole_proprietor',  300,     'Per-segment surcharge (T-Mobile)',           now(), NULL, now(), now()),
                ('surcharge_verizon',               'standard',         310,     'Per-segment surcharge (Verizon)',            now(), NULL, now(), now()),
                ('surcharge_verizon',               'sole_proprietor',  310,     'Per-segment surcharge (Verizon)',            now(), NULL, now(), now())
            ON CONFLICT DO NOTHING
            """
        )
    )

    op.execute("SET LOCAL session_replication_role = 'origin';")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Remove the 12 new fee codes (scoped — only the ones this migration added)
    op.execute(
        sa.text(
            """
            DELETE FROM public.carrier_fee_schedule
            WHERE fee_code IN (
                'brand_vetting',
                'campaign_registration_tmobile',
                'phone_number_assignment',
                'surcharge_att',
                'surcharge_tmobile',
                'surcharge_verizon'
            )
            """
        )
    )

    # Drop GiST exclusion constraint
    op.execute(
        sa.text(
            "ALTER TABLE public.carrier_fee_schedule "
            "DROP CONSTRAINT IF EXISTS uq_carrier_fee_schedule_temporal;"
        )
    )

    # Restore old UNIQUE constraint
    op.create_unique_constraint(
        "uq_carrier_fee_schedule_code_entity",
        "carrier_fee_schedule",
        ["fee_code", "entity_type"],
    )

    # Restore old columns
    op.add_column(
        "carrier_fee_schedule",
        sa.Column("amount_cents", sa.Integer(), nullable=True),
    )
    op.add_column(
        "carrier_fee_schedule",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=True,
        ),
    )

    # Migrate data back: amount_cents = amount_millicents // 1000, is_active = true
    op.execute(
        sa.text(
            """
            UPDATE public.carrier_fee_schedule SET
                amount_cents = amount_millicents / 1000,
                is_active = true
            """
        )
    )

    # Make restored columns NOT NULL
    op.alter_column(
        "carrier_fee_schedule",
        "amount_cents",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "carrier_fee_schedule",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
    )

    # Drop temporal + millicents columns
    op.drop_column("carrier_fee_schedule", "effective_to")
    op.drop_column("carrier_fee_schedule", "effective_from")
    op.drop_column("carrier_fee_schedule", "amount_millicents")

    op.execute("SET LOCAL session_replication_role = 'origin';")
