"""add_database_triggers_for_quote_totals_and_user_email

Revision ID: a4d2659a2921
Revises: 17aa292ece75
Create Date: 2026-03-17 14:51:50.014682+00:00

Implements Gaps #31, #32, #33 from phase-1-4-implementation-gap-analysis.md:
- Gap #31 (BLOCKER): Quote totals recalculation trigger
- Gap #32 (HIGH): Change order totals recalculation trigger
- Gap #33 (HIGH): User email sync trigger

These triggers maintain data integrity at the database layer, eliminating race
conditions and ensuring financial accuracy for quote totals and user email sync.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4d2659a2921"
down_revision: str | None = "17aa292ece75"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create PostgreSQL triggers for:
    1. Quote totals recalculation (recalc_quote_totals_fn)
    2. Change order totals recalculation (recalc_change_order_totals_fn)
    3. User email sync from primary endpoint (sync_user_email_from_endpoint_fn)
    """

    # ========================================================================
    # TRIGGER #1: Quote Totals Recalculation
    # ========================================================================
    # Creates a trigger that automatically updates quote.subtotal_cents,
    # quote.tax_cents, and quote.total_cents whenever quote_line records
    # are inserted, updated, or deleted.
    #
    # This ensures financial accuracy and prevents race conditions from
    # concurrent updates. Critical for "Mike the Solo Contractor" to have
    # accurate quote totals for profitability tracking.
    # ========================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION recalc_quote_totals_fn()
        RETURNS TRIGGER AS $$
        DECLARE
            v_quote_id UUID;
        BEGIN
            -- Determine which quote_id to update based on operation type
            IF (TG_OP = 'DELETE') THEN
                v_quote_id := OLD.quote_id;
            ELSE
                -- INSERT or UPDATE
                v_quote_id := NEW.quote_id;
            END IF;

            -- Recalculate quote totals from all active quote lines
            -- Uses COALESCE to handle empty quotes (returns 0 instead of NULL)
            -- Filters out soft-deleted lines (is_active = false)
            UPDATE quote
            SET
                subtotal_cents = COALESCE((
                    SELECT SUM(subtotal_cents)
                    FROM quote_line
                    WHERE quote_id = v_quote_id
                      AND is_active = true
                ), 0),
                tax_cents = COALESCE((
                    SELECT SUM(tax_amount_cents)
                    FROM quote_line
                    WHERE quote_id = v_quote_id
                      AND is_active = true
                ), 0),
                updated_at = NOW()
            WHERE id = v_quote_id;
            
            -- Calculate total_cents = subtotal + tax in separate UPDATE
            -- to ensure both fields are available for calculation
            UPDATE quote
            SET total_cents = subtotal_cents + tax_cents
            WHERE id = v_quote_id;

            -- Return appropriate record based on operation
            IF (TG_OP = 'DELETE') THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger on quote_line table
    op.execute("""
        CREATE TRIGGER recalc_quote_totals_trigger
        AFTER INSERT OR UPDATE OR DELETE ON quote_line
        FOR EACH ROW
        EXECUTE FUNCTION recalc_quote_totals_fn();
    """)

    # ========================================================================
    # TRIGGER #2: Change Order Totals Recalculation
    # ========================================================================
    # Identical logic to quote totals, but operates on change_order table.
    # Change orders feed into job profitability calculations that Mike relies on.
    # ========================================================================

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

    # Create trigger on change_order_line table
    op.execute("""
        CREATE TRIGGER recalc_change_order_totals_trigger
        AFTER INSERT OR UPDATE OR DELETE ON change_order_line
        FOR EACH ROW
        EXECUTE FUNCTION recalc_change_order_totals_fn();
    """)

    # ========================================================================
    # TRIGGER #3: User Email Sync from Primary Endpoint
    # ========================================================================
    # Automatically syncs user.email when a primary email endpoint is
    # inserted, updated, or deleted. This ensures notifications reach
    # the correct email address.
    #
    # Only syncs when:
    # - channel = 'email'
    # - is_primary = true
    # ========================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION sync_user_email_from_endpoint_fn()
        RETURNS TRIGGER AS $$
        DECLARE
            next_primary_email TEXT;
        BEGIN
            IF (TG_OP = 'INSERT') THEN
                -- If inserting a primary email endpoint, sync to user table
                IF NEW.channel = 'email' AND COALESCE(NEW.is_primary, false) THEN
                    UPDATE "user"
                    SET email = LOWER(NEW.value),
                        updated_at = NOW()
                    WHERE id = NEW.user_id;
                END IF;
                RETURN NEW;
                
            ELSIF (TG_OP = 'UPDATE') THEN
                -- If updating to primary email or changing primary email value
                IF NEW.channel = 'email' THEN
                    IF COALESCE(NEW.is_primary, false) AND 
                       (NOT COALESCE(OLD.is_primary, false) OR NEW.value IS DISTINCT FROM OLD.value) THEN
                        UPDATE "user"
                        SET email = LOWER(NEW.value),
                            updated_at = NOW()
                        WHERE id = NEW.user_id;
                    ELSIF NOT COALESCE(NEW.is_primary, false) AND COALESCE(OLD.is_primary, false) THEN
                        -- Primary was demoted, find next primary email
                        SELECT LOWER(value) INTO next_primary_email
                        FROM user_endpoint
                        WHERE user_id = OLD.user_id
                          AND channel = 'email'
                          AND is_primary = true
                        ORDER BY created_at DESC
                        LIMIT 1;
                        
                        UPDATE "user"
                        SET email = next_primary_email,
                            updated_at = NOW()
                        WHERE id = OLD.user_id;
                    END IF;
                END IF;
                RETURN NEW;
                
            ELSIF (TG_OP = 'DELETE') THEN
                -- If deleting primary email, find next available primary
                IF OLD.channel = 'email' AND COALESCE(OLD.is_primary, false) THEN
                    SELECT LOWER(value) INTO next_primary_email
                    FROM user_endpoint
                    WHERE user_id = OLD.user_id
                      AND channel = 'email'
                      AND is_primary = true
                      AND id != OLD.id  -- Exclude the one being deleted
                    ORDER BY created_at DESC
                    LIMIT 1;
                    
                    UPDATE "user"
                    SET email = next_primary_email,
                        updated_at = NOW()
                    WHERE id = OLD.user_id;
                END IF;
                RETURN OLD;
            END IF;
            
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger on user_endpoint table
    op.execute("""
        CREATE TRIGGER sync_user_email_from_endpoint_trigger
        AFTER INSERT OR UPDATE OR DELETE ON user_endpoint
        FOR EACH ROW
        EXECUTE FUNCTION sync_user_email_from_endpoint_fn();
    """)


def downgrade() -> None:
    """
    Drop all triggers and functions in reverse order.

    Always drop triggers before their functions to avoid dependency errors.
    """

    # Drop user email sync trigger and function
    op.execute(
        "DROP TRIGGER IF EXISTS sync_user_email_from_endpoint_trigger ON user_endpoint;"
    )
    op.execute("DROP FUNCTION IF EXISTS sync_user_email_from_endpoint_fn();")

    # Drop change order totals trigger and function
    op.execute(
        "DROP TRIGGER IF EXISTS recalc_change_order_totals_trigger ON change_order_line;"
    )
    op.execute("DROP FUNCTION IF EXISTS recalc_change_order_totals_fn();")

    # Drop quote totals trigger and function
    op.execute("DROP TRIGGER IF EXISTS recalc_quote_totals_trigger ON quote_line;")
    op.execute("DROP FUNCTION IF EXISTS recalc_quote_totals_fn();")
