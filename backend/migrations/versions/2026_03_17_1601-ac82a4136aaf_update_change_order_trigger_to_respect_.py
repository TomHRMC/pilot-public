"""update_change_order_trigger_to_respect_is_active

Revision ID: ac82a4136aaf
Revises: c31f8a628d3d
Create Date: 2026-03-17 16:01:43.128712+00:00

Now that change_order_line has an is_active field, update the trigger to
filter out soft-deleted lines when calculating totals (matching quote behavior).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac82a4136aaf"
down_revision: str | None = "c31f8a628d3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Replace the change order totals trigger function to respect is_active field.
    Now filters out soft-deleted lines (is_active = false) when calculating totals.
    """

    op.execute("""
        CREATE OR REPLACE FUNCTION recalc_change_order_totals_fn()
        RETURNS TRIGGER AS $$
        DECLARE
            v_change_order_id UUID;
        BEGIN
            -- Determine which change_order_id to update
            IF (TG_OP = 'DELETE') THEN
                v_change_order_id := OLD.change_order_id;
            ELSE
                -- INSERT or UPDATE
                v_change_order_id := NEW.change_order_id;
            END IF;

            -- Recalculate change order totals from all active change order lines
            -- Uses COALESCE to handle empty change orders (returns 0 instead of NULL)
            -- Filters out soft-deleted lines (is_active = false)
            UPDATE change_order
            SET
                subtotal_cents = COALESCE((
                    SELECT SUM(subtotal_cents)
                    FROM change_order_line
                    WHERE change_order_id = v_change_order_id
                      AND is_active = true
                ), 0),
                tax_cents = COALESCE((
                    SELECT SUM(tax_amount_cents)
                    FROM change_order_line
                    WHERE change_order_id = v_change_order_id
                      AND is_active = true
                ), 0),
                updated_at = NOW()
            WHERE id = v_change_order_id;
            
            -- Calculate total_cents = subtotal + tax
            UPDATE change_order
            SET total_cents = subtotal_cents + tax_cents
            WHERE id = v_change_order_id;

            -- Return appropriate record
            IF (TG_OP = 'DELETE') THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """
    Revert to the original trigger function that doesn't check is_active.
    """

    op.execute("""
        CREATE OR REPLACE FUNCTION recalc_change_order_totals_fn()
        RETURNS TRIGGER AS $$
        DECLARE
            v_change_order_id UUID;
        BEGIN
            -- Determine which change_order_id to update
            IF (TG_OP = 'DELETE') THEN
                v_change_order_id := OLD.change_order_id;
            ELSE
                -- INSERT or UPDATE
                v_change_order_id := NEW.change_order_id;
            END IF;

            -- Recalculate change order totals from all lines
            -- Note: ChangeOrderLine doesn't have is_active field
            UPDATE change_order
            SET
                subtotal_cents = COALESCE((
                    SELECT SUM(subtotal_cents)
                    FROM change_order_line
                    WHERE change_order_id = v_change_order_id
                ), 0),
                tax_cents = COALESCE((
                    SELECT SUM(tax_amount_cents)
                    FROM change_order_line
                    WHERE change_order_id = v_change_order_id
                ), 0),
                updated_at = NOW()
            WHERE id = v_change_order_id;
            
            -- Calculate total_cents = subtotal + tax
            UPDATE change_order
            SET total_cents = subtotal_cents + tax_cents
            WHERE id = v_change_order_id;

            -- Return appropriate record
            IF (TG_OP = 'DELETE') THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)
