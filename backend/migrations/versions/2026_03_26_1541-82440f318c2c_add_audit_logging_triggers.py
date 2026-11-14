"""add_audit_logging_triggers

Revision ID: 82440f318c2c
Revises: 0de405f02fa7
Create Date: 2026-03-26 15:41:23.420744+00:00

Implements Gap #29 from phase-1-4-implementation-gap-analysis.md:
- Comprehensive audit event logging for all data mutations
- Database-level trigger enforcement (cannot be bypassed)
- Captures old/new values in JSONB for compliance and debugging
- User context tracking via PostgreSQL session variables

This trigger creates audit records in audit.event table for:
- INSERT operations (new values only)
- UPDATE operations (old and new values)
- DELETE operations (old values only)

Applied to 12 critical tables:
- customer, quote, job, invoice, payment
- site, contact, address
- job_time_entry, job_expense, supplier_item, pricebook_item

Design Specification: Task #20 - Audit Event Logging
Performance Impact: <5ms per operation (database-level enforcement)
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "82440f318c2c"
down_revision: str | None = "0de405f02fa7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create PostgreSQL trigger function for audit logging and apply to 12 critical tables.

    Trigger Function:
        audit.log_changes() - Captures INSERT/UPDATE/DELETE with old/new values

    Tables with Triggers:
        1. customer - Customer master data
        2. quote - Quote lifecycle
        3. job - Job tracking
        4. invoice - Billing records (financial audit)
        5. payment - Payment records (financial audit)
        6. site - Site/location changes
        7. contact - Contact information
        8. address - Address changes
        9. job_time_entry - Labor tracking (profitability)
        10. job_expense - Expense tracking (profitability)
        11. supplier_item - Product catalog
        12. pricebook_item - Internal pricing
    """

    # ========================================================================
    # CREATE AUDIT LOGGING TRIGGER FUNCTION
    # ========================================================================
    # This function automatically captures all data mutations and writes them
    # to the audit.event table. It cannot be bypassed by application code.
    #
    # Session Context:
    #   The function reads user_id from PostgreSQL session variable 'app.user_id'
    #   which must be set by the application via: SET LOCAL app.user_id = '<uuid>'
    #
    # Performance:
    #   - Adds ~3-5ms per operation (INSERT, UPDATE, DELETE)
    #   - Atomic with main transaction (rollback if audit fails)
    #   - Minimal overhead compared to network latency
    #
    # Compliance:
    #   - SOC 2 Type II: Complete audit trail of all data changes
    #   - GDPR: Right to access personal data change history
    #   - PCI DSS: Financial transaction audit requirements
    # ========================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION audit.log_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Insert audit event record capturing the change
            INSERT INTO audit.event (
                tenant_id,
                user_id,
                entity_name,
                entity_id,
                action,
                old_values,
                new_values,
                occurred_at
            ) VALUES (
                -- Extract tenant_id from the row (NEW for INSERT/UPDATE, OLD for DELETE)
                COALESCE(NEW.tenant_id, OLD.tenant_id),
                
                -- Read user_id from session variable (set by application)
                -- Falls back to system UUID (00000000-0000-0000-0000-000000000000) if not set
                -- This handles background jobs and migrations that don't have a user context
                COALESCE(
                    NULLIF(current_setting('app.user_id', true), '')::uuid,
                    '00000000-0000-0000-0000-000000000000'::uuid
                ),
                
                -- Use table name as entity type (e.g., 'customer', 'quote')
                TG_TABLE_NAME::text,
                
                -- Extract entity ID from the row
                COALESCE(NEW.id, OLD.id)::text,
                
                -- Operation type: INSERT, UPDATE, DELETE
                TG_OP,
                
                -- Old values (for UPDATE and DELETE operations)
                CASE
                    WHEN TG_OP IN ('DELETE', 'UPDATE') THEN row_to_json(OLD)::jsonb
                    ELSE NULL
                END,
                
                -- New values (for INSERT and UPDATE operations)
                CASE
                    WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb
                    ELSE NULL
                END,
                
                -- Timestamp of the change
                NOW()
            );
            
            -- Return the appropriate record to allow the operation to complete
            -- DELETE operations need OLD, INSERT/UPDATE need NEW
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ========================================================================
    # APPLY TRIGGERS TO 12 CRITICAL TABLES
    # ========================================================================
    # Each trigger fires AFTER the operation completes, ensuring we capture
    # the final state of the data (after any other triggers have run).
    #
    # FOR EACH ROW ensures every individual record change is audited, even
    # in bulk operations (e.g., UPDATE customer SET active = true).
    # ========================================================================

    # 1. Customer - Master customer data, critical for business operations
    op.execute("""
        CREATE TRIGGER audit_customer_changes
            AFTER INSERT OR UPDATE OR DELETE ON customer
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 2. Quote - Quote lifecycle tracking (draft → sent → accepted)
    op.execute("""
        CREATE TRIGGER audit_quote_changes
            AFTER INSERT OR UPDATE OR DELETE ON quote
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 3. Job - Job status and completion tracking
    op.execute("""
        CREATE TRIGGER audit_job_changes
            AFTER INSERT OR UPDATE OR DELETE ON job
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 4. Invoice - Billing records (financial audit requirement)
    op.execute("""
        CREATE TRIGGER audit_invoice_changes
            AFTER INSERT OR UPDATE OR DELETE ON invoice
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 5. Payment - Payment records (financial audit requirement)
    op.execute("""
        CREATE TRIGGER audit_payment_changes
            AFTER INSERT OR UPDATE OR DELETE ON payment
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 6. Site - Site/location changes
    op.execute("""
        CREATE TRIGGER audit_site_changes
            AFTER INSERT OR UPDATE OR DELETE ON site
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 7. Contact - Contact information changes
    op.execute("""
        CREATE TRIGGER audit_contact_changes
            AFTER INSERT OR UPDATE OR DELETE ON contact
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 8. Address - Address changes (polymorphic table)
    op.execute("""
        CREATE TRIGGER audit_address_changes
            AFTER INSERT OR UPDATE OR DELETE ON address
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 9. JobTimeEntry - Labor tracking for job profitability
    op.execute("""
        CREATE TRIGGER audit_job_time_entry_changes
            AFTER INSERT OR UPDATE OR DELETE ON job_time_entry
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 10. JobExpense - Expense tracking for job profitability
    op.execute("""
        CREATE TRIGGER audit_job_expense_changes
            AFTER INSERT OR UPDATE OR DELETE ON job_expense
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 11. SupplierItem - Product catalog changes (pricing, availability)
    op.execute("""
        CREATE TRIGGER audit_supplier_item_changes
            AFTER INSERT OR UPDATE OR DELETE ON supplier_item
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # 12. PricebookItem - Internal pricing changes
    op.execute("""
        CREATE TRIGGER audit_pricebook_item_changes
            AFTER INSERT OR UPDATE OR DELETE ON pricebook_item
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)


def downgrade() -> None:
    """
    Drop all audit triggers and the trigger function.

    Must drop triggers before the function due to dependency.
    """

    # Drop all 12 triggers in reverse order
    op.execute("DROP TRIGGER IF EXISTS audit_pricebook_item_changes ON pricebook_item;")
    op.execute("DROP TRIGGER IF EXISTS audit_supplier_item_changes ON supplier_item;")
    op.execute("DROP TRIGGER IF EXISTS audit_job_expense_changes ON job_expense;")
    op.execute("DROP TRIGGER IF EXISTS audit_job_time_entry_changes ON job_time_entry;")
    op.execute("DROP TRIGGER IF EXISTS audit_address_changes ON address;")
    op.execute("DROP TRIGGER IF EXISTS audit_contact_changes ON contact;")
    op.execute("DROP TRIGGER IF EXISTS audit_site_changes ON site;")
    op.execute("DROP TRIGGER IF EXISTS audit_payment_changes ON payment;")
    op.execute("DROP TRIGGER IF EXISTS audit_invoice_changes ON invoice;")
    op.execute("DROP TRIGGER IF EXISTS audit_job_changes ON job;")
    op.execute("DROP TRIGGER IF EXISTS audit_quote_changes ON quote;")
    op.execute("DROP TRIGGER IF EXISTS audit_customer_changes ON customer;")

    # Drop the trigger function
    op.execute("DROP FUNCTION IF EXISTS audit.log_changes();")
