"""fix_recalc_invoice_totals_fn_status_col

Revision ID: c3d4e5f6a7b8
Revises: b8f2a1c9d4e5
Create Date: 2026-04-15 17:05:00.000000+00:00

Fix a bug in recalc_invoice_totals_fn() where the balance_due_cents calculation
referenced `payment.status = 'completed'` but the actual column is `payment.status_id`
(a UUID FK to payment_status). The fix uses a subquery to look up the 'completed'
payment_status record.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b8f2a1c9d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.recalc_invoice_totals_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
          _iid uuid;
        BEGIN
          -- Determine parent invoice id from NEW/OLD
          IF TG_OP IN ('INSERT','UPDATE') THEN
            IF TG_TABLE_NAME = 'invoice_line' THEN
              _iid := NEW.invoice_id;
            ELSIF TG_TABLE_NAME = 'invoice_line_tax_component' THEN
              SELECT il.invoice_id INTO _iid FROM invoice_line il WHERE il.id = NEW.invoice_line_id;
            END IF;
          ELSE
            -- DELETE
            IF TG_TABLE_NAME = 'invoice_line' THEN
              _iid := OLD.invoice_id;
            ELSIF TG_TABLE_NAME = 'invoice_line_tax_component' THEN
              SELECT il.invoice_id INTO _iid FROM invoice_line il WHERE il.id = OLD.invoice_line_id;
            END IF;
          END IF;

          IF _iid IS NOT NULL THEN
            UPDATE invoice i SET
              subtotal_cents = COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0),
              tax_cents      = COALESCE((
                                  SELECT SUM(t.amount_cents)
                                    FROM invoice_line_tax_component t
                                    JOIN invoice_line l ON l.id = t.invoice_line_id
                                   WHERE l.invoice_id = _iid AND l.is_active = true
                                ), 0),
              total_cents    = COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0)
                                + COALESCE((
                                    SELECT SUM(t.amount_cents)
                                      FROM invoice_line_tax_component t
                                      JOIN invoice_line l ON l.id = t.invoice_line_id
                                     WHERE l.invoice_id = _iid AND l.is_active = true
                                  ), 0),
              balance_due_cents = (
                                    COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0)
                                    + COALESCE((
                                        SELECT SUM(t.amount_cents)
                                          FROM invoice_line_tax_component t
                                          JOIN invoice_line l ON l.id = t.invoice_line_id
                                         WHERE l.invoice_id = _iid AND l.is_active = true
                                      ), 0)
                                  )
                                  - COALESCE((
                                      SELECT SUM(p.amount_cents)
                                        FROM payment p
                                        JOIN payment_status ps ON ps.id = p.status_id
                                       WHERE p.invoice_id = _iid
                                         AND ps.code = 'completed'
                                    ), 0),
              updated_at     = now()
            WHERE i.id = _iid;
          END IF;

          RETURN COALESCE(NEW, OLD);
        END;$$;
    """)


def downgrade() -> None:
    # Restore the original (buggy) version for rollback
    op.execute("""
        CREATE OR REPLACE FUNCTION public.recalc_invoice_totals_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
          _iid uuid;
        BEGIN
          -- Determine parent invoice id from NEW/OLD
          IF TG_OP IN ('INSERT','UPDATE') THEN
            IF TG_TABLE_NAME = 'invoice_line' THEN
              _iid := NEW.invoice_id;
            ELSIF TG_TABLE_NAME = 'invoice_line_tax_component' THEN
              SELECT il.invoice_id INTO _iid FROM invoice_line il WHERE il.id = NEW.invoice_line_id;
            END IF;
          ELSE
            -- DELETE
            IF TG_TABLE_NAME = 'invoice_line' THEN
              _iid := OLD.invoice_id;
            ELSIF TG_TABLE_NAME = 'invoice_line_tax_component' THEN
              SELECT il.invoice_id INTO _iid FROM invoice_line il WHERE il.id = OLD.invoice_line_id;
            END IF;
          END IF;

          IF _iid IS NOT NULL THEN
            UPDATE invoice i SET
              subtotal_cents = COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0),
              tax_cents      = COALESCE((
                                  SELECT SUM(t.amount_cents)
                                    FROM invoice_line_tax_component t
                                    JOIN invoice_line l ON l.id = t.invoice_line_id
                                   WHERE l.invoice_id = _iid AND l.is_active = true
                                ), 0),
              total_cents    = COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0)
                                + COALESCE((
                                    SELECT SUM(t.amount_cents)
                                      FROM invoice_line_tax_component t
                                      JOIN invoice_line l ON l.id = t.invoice_line_id
                                     WHERE l.invoice_id = _iid AND l.is_active = true
                                  ), 0),
              balance_due_cents = (
                                    COALESCE((SELECT SUM(subtotal_cents) FROM invoice_line WHERE invoice_id = _iid AND is_active = true), 0)
                                    + COALESCE((
                                        SELECT SUM(t.amount_cents)
                                          FROM invoice_line_tax_component t
                                          JOIN invoice_line l ON l.id = t.invoice_line_id
                                         WHERE l.invoice_id = _iid AND l.is_active = true
                                      ), 0)
                                  )
                                  - COALESCE((SELECT SUM(amount_cents) FROM payment WHERE invoice_id = _iid AND status = 'completed'), 0),
              updated_at     = now()
            WHERE i.id = _iid;
          END IF;

          RETURN COALESCE(NEW, OLD);
        END;$$;
    """)
