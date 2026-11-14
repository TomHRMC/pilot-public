"""phase_9_0_batch_2_soft_delete_sync_triggers

Revision ID: 39ca85621aad
Revises: 7c973ed46561
Create Date: 2026-04-16 14:08:19.000000

Phase 9.0 Batch 2: Soft-Delete Synchronization — Deletion Pathways

Adds DB-level AFTER UPDATE triggers that cascade is_active = false from parent
records to their direct children when a parent is soft-deleted.

Also adds missing is_active columns to quote_line_tax_component and job_expense.

ACTUAL FK HIERARCHY (verified from live DB — differs from prompt spec):
  Hierarchy A (CRM):
    customer → site    (site.customer_id)
    customer → contact (contact.customer_id)
    NOTE: address has NO contact_id FK; site→contact FK doesn't exist in DB.

  Hierarchy B (Sales):
    quote      → quote_line                (quote_line.quote_id)
    quote_line → quote_line_tax_component  (quote_line_tax_component.quote_line_id)

  Hierarchy C (Billing):
    invoice      → invoice_line               (invoice_line.invoice_id)
    invoice_line → invoice_line_tax_component (invoice_line_tax_component.invoice_line_id)

  Hierarchy D (Fulfillment):
    job          → change_order      (change_order.job_id)
    change_order → change_order_line (change_order_line.change_order_id)
    job          → job_expense       (job_expense.job_id)
    NOTE: change_order_line→job_expense FK doesn't exist in DB.

Total: 9 trigger function + trigger pairs.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "39ca85621aad"
down_revision = "7c973ed46561"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================
    # STEP 0: Add missing is_active columns to tables that lack them
    # =========================================================

    # quote_line_tax_component — append-only table, add is_active
    op.add_column(
        "quote_line_tax_component",
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )

    # job_expense — add is_active
    op.add_column(
        "job_expense",
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )

    # =========================================================
    # HIERARCHY A: Core CRM
    # customer → site
    # customer → contact
    # =========================================================

    # --- Level 1a: customer → site ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_site()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE site SET is_active = false
                WHERE customer_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_customer_to_site
        AFTER UPDATE OF is_active ON customer
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_site();
    """)

    # --- Level 1b: customer → contact ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_contact()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE contact SET is_active = false
                WHERE customer_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_customer_to_contact
        AFTER UPDATE OF is_active ON customer
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_contact();
    """)

    # =========================================================
    # HIERARCHY B: Sales
    # quote → quote_line → quote_line_tax_component
    # =========================================================

    # --- Level 1: quote → quote_line ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_quote_line()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE quote_line SET is_active = false
                WHERE quote_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_quote_to_quote_line
        AFTER UPDATE OF is_active ON quote
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_quote_line();
    """)

    # --- Level 2: quote_line → quote_line_tax_component ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_quote_line_tax_component()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE quote_line_tax_component SET is_active = false
                WHERE quote_line_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_quote_line_to_tax_component
        AFTER UPDATE OF is_active ON quote_line
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_quote_line_tax_component();
    """)

    # =========================================================
    # HIERARCHY C: Billing
    # invoice → invoice_line → invoice_line_tax_component
    # =========================================================

    # --- Level 1: invoice → invoice_line ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_invoice_line()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE invoice_line SET is_active = false
                WHERE invoice_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_invoice_to_invoice_line
        AFTER UPDATE OF is_active ON invoice
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_invoice_line();
    """)

    # --- Level 2: invoice_line → invoice_line_tax_component ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_invoice_line_tax_component()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE invoice_line_tax_component SET is_active = false
                WHERE invoice_line_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_invoice_line_to_tax_component
        AFTER UPDATE OF is_active ON invoice_line
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_invoice_line_tax_component();
    """)

    # =========================================================
    # HIERARCHY D: Fulfillment
    # job → change_order → change_order_line
    # job → job_expense (direct FK, not via change_order_line)
    # =========================================================

    # --- Level 1a: job → change_order ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_change_order()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE change_order SET is_active = false
                WHERE job_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_job_to_change_order
        AFTER UPDATE OF is_active ON job
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_change_order();
    """)

    # --- Level 2: change_order → change_order_line ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_change_order_line()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE change_order_line SET is_active = false
                WHERE change_order_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_change_order_to_change_order_line
        AFTER UPDATE OF is_active ON change_order
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_change_order_line();
    """)

    # --- Level 1b: job → job_expense (direct FK: job_expense.job_id) ---
    op.execute("""
        CREATE OR REPLACE FUNCTION cascade_soft_delete_to_job_expense()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.is_active = false AND OLD.is_active = true THEN
                UPDATE job_expense SET is_active = false
                WHERE job_id = NEW.id AND is_active = true;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_soft_delete_job_to_job_expense
        AFTER UPDATE OF is_active ON job
        FOR EACH ROW
        WHEN (OLD.is_active IS DISTINCT FROM NEW.is_active AND NEW.is_active = false)
        EXECUTE FUNCTION cascade_soft_delete_to_job_expense();
    """)


def downgrade() -> None:
    # Drop triggers first (in reverse dependency order), then functions.

    # Hierarchy D — Fulfillment
    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_job_to_job_expense ON job;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_job_expense();")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_soft_delete_change_order_to_change_order_line ON change_order;"
    )
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_change_order_line();")

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_job_to_change_order ON job;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_change_order();")

    # Hierarchy C — Billing
    op.execute(
        "DROP TRIGGER IF EXISTS trg_soft_delete_invoice_line_to_tax_component ON invoice_line;"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cascade_soft_delete_to_invoice_line_tax_component();"
    )

    op.execute(
        "DROP TRIGGER IF EXISTS trg_soft_delete_invoice_to_invoice_line ON invoice;"
    )
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_invoice_line();")

    # Hierarchy B — Sales
    op.execute(
        "DROP TRIGGER IF EXISTS trg_soft_delete_quote_line_to_tax_component ON quote_line;"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cascade_soft_delete_to_quote_line_tax_component();"
    )

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_quote_to_quote_line ON quote;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_quote_line();")

    # Hierarchy A — Core CRM
    op.execute(
        "DROP TRIGGER IF EXISTS trg_soft_delete_customer_to_contact ON customer;"
    )
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_contact();")

    op.execute("DROP TRIGGER IF EXISTS trg_soft_delete_customer_to_site ON customer;")
    op.execute("DROP FUNCTION IF EXISTS cascade_soft_delete_to_site();")

    # Remove added is_active columns
    op.drop_column("job_expense", "is_active")
    op.drop_column("quote_line_tax_component", "is_active")
