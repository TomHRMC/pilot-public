"""billing_b1_payment_schedule

Revision ID: 2dba31137096
Revises: 3131f106f1b9
Create Date: 2026-07-28 18:13:09.340030+00:00

BILLING-B1: Progress Billing — Payment Schedule Orchestration

Three logical groups (parent → child → invoice column; DDL ordering avoids the
circular FK deadlock):

  Group 1 — payment_schedule (parent)
      table + 3 indexes + 2 CHECKs + 3 triggers (mirror customer DDL;
      audit fn is schema-qualified audit.log_changes()).

  Group 2 — payment_schedule_line (child / draw)
      table + 2 plain indexes + 2 unique indexes + 4 CHECKs + 3 triggers.
      Conditional-NOT-NULL enforced by table-level CHECKs (psl_basis_amount_chk,
      psl_trigger_detail_chk). One invoice per draw via partial unique index
      uq_psl_invoice_id. Draw order unique via uq_psl_schedule_sequence.

  Group 3 — invoice.payment_schedule_line_id (nullable additive FK)
      ALTER TABLE ADD COLUMN + index. No 3-part NOT NULL pattern (nullable;
      existing rows correctly NULL). ON DELETE SET NULL on both sides of the
      circular FK (invoice ↔ payment_schedule_line) — no ordering deadlock.

FK ON DELETE semantics (§B):
  payment_schedule.tenant_id/customer_id/site_id → RESTRICT
  payment_schedule.quote_id/job_id                → SET NULL
  payment_schedule_line.tenant_id                 → RESTRICT
  payment_schedule_line.payment_schedule_id       → CASCADE
  payment_schedule_line.invoice_id                → SET NULL
  invoice.payment_schedule_line_id                → SET NULL
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2dba31137096"
down_revision: str | None = "3131f106f1b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # =========================================================================
    # Group 1 — payment_schedule (parent table)
    # =========================================================================
    op.execute(
        """
        CREATE TABLE payment_schedule (
            created_at           TIMESTAMPTZ NOT NULL,
            updated_at           TIMESTAMPTZ NOT NULL,
            created_by           UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by           UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            id                   UUID PRIMARY KEY,
            tenant_id            UUID NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            quote_id             UUID REFERENCES quote(id) ON DELETE SET NULL,
            job_id               UUID REFERENCES job(id) ON DELETE SET NULL,
            customer_id          UUID NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
            site_id              UUID NOT NULL REFERENCES site(id) ON DELETE RESTRICT,
            contract_total_cents INTEGER NOT NULL,
            status               TEXT NOT NULL DEFAULT 'draft',
            basis_default        TEXT NOT NULL DEFAULT 'percent',
            is_active            BOOLEAN NOT NULL DEFAULT true
        );
        """
    )

    # Indexes
    op.execute(
        "CREATE INDEX ix_payment_schedule_tenant_id ON payment_schedule (tenant_id);"
    )
    op.execute(
        "CREATE INDEX ix_payment_schedule_quote_id ON payment_schedule (quote_id);"
    )
    op.execute("CREATE INDEX ix_payment_schedule_job_id ON payment_schedule (job_id);")

    # CHECKs
    op.execute(
        "ALTER TABLE payment_schedule ADD CONSTRAINT chk_payment_schedule_status "
        "CHECK (status IN ('draft','active','completed','cancelled'));"
    )
    op.execute(
        "ALTER TABLE payment_schedule ADD CONSTRAINT chk_payment_schedule_basis_default "
        "CHECK (basis_default IN ('percent','fixed_amount'));"
    )

    # Triggers — mirror customer DDL exactly (audit fn is schema-qualified)
    op.execute(
        "CREATE TRIGGER trg_payment_schedule_set_updated_at "
        "BEFORE UPDATE ON payment_schedule "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )
    op.execute(
        "CREATE TRIGGER audit_payment_schedule_changes "
        "AFTER INSERT OR DELETE OR UPDATE ON payment_schedule "
        "FOR EACH ROW EXECUTE FUNCTION audit.log_changes();"
    )
    op.execute(
        "CREATE TRIGGER trg_payment_schedule_guard_created_immutable "
        "BEFORE UPDATE ON payment_schedule "
        "FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();"
    )

    # =========================================================================
    # Group 2 — payment_schedule_line (child / draw table)
    # =========================================================================
    op.execute(
        """
        CREATE TABLE payment_schedule_line (
            created_at           TIMESTAMPTZ NOT NULL,
            updated_at           TIMESTAMPTZ NOT NULL,
            created_by           UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by           UUID REFERENCES "user"(id) ON DELETE RESTRICT,
            id                   UUID PRIMARY KEY,
            tenant_id            UUID NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            payment_schedule_id  UUID NOT NULL REFERENCES payment_schedule(id) ON DELETE CASCADE,
            sequence             INTEGER NOT NULL,
            label                TEXT NOT NULL,
            basis                TEXT NOT NULL,
            percent              NUMERIC(5,2),
            amount_cents         INTEGER,
            trigger_type         TEXT NOT NULL DEFAULT 'manual',
            trigger_date         DATE,
            milestone_label      TEXT,
            invoice_id           UUID REFERENCES invoice(id) ON DELETE SET NULL,
            status               TEXT NOT NULL DEFAULT 'pending',
            is_active            BOOLEAN NOT NULL DEFAULT true
        );
        """
    )

    # Plain indexes
    op.execute("CREATE INDEX ix_psl_tenant_id ON payment_schedule_line (tenant_id);")
    op.execute(
        "CREATE INDEX ix_psl_schedule_id ON payment_schedule_line (payment_schedule_id);"
    )

    # Unique indexes
    op.execute(
        "CREATE UNIQUE INDEX uq_psl_schedule_sequence "
        "ON payment_schedule_line (payment_schedule_id, sequence);"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_psl_invoice_id "
        "ON payment_schedule_line (invoice_id) WHERE invoice_id IS NOT NULL;"
    )

    # CHECKs — conditional NOT NULL (basis drives amount column; trigger_type drives detail)
    op.execute(
        """
        ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_basis_amount_chk CHECK (
          (basis = 'percent'      AND percent IS NOT NULL AND amount_cents IS NULL)
          OR
          (basis = 'fixed_amount' AND amount_cents IS NOT NULL AND percent IS NULL)
        );
        """
    )
    op.execute(
        """
        ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_trigger_detail_chk CHECK (
          (trigger_type = 'date'      AND trigger_date IS NOT NULL)
          OR
          (trigger_type = 'milestone' AND milestone_label IS NOT NULL)
          OR
          (trigger_type = 'manual')
        );
        """
    )
    op.execute(
        "ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_basis_chk "
        "CHECK (basis IN ('percent','fixed_amount'));"
    )
    op.execute(
        "ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_trigger_type_chk "
        "CHECK (trigger_type IN ('manual','date','milestone'));"
    )
    op.execute(
        "ALTER TABLE payment_schedule_line ADD CONSTRAINT psl_status_chk "
        "CHECK (status IN ('pending','invoiced','paid','void'));"
    )

    # Triggers — same three as Group 1, renamed for payment_schedule_line
    op.execute(
        "CREATE TRIGGER trg_payment_schedule_line_set_updated_at "
        "BEFORE UPDATE ON payment_schedule_line "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )
    op.execute(
        "CREATE TRIGGER audit_payment_schedule_line_changes "
        "AFTER INSERT OR DELETE OR UPDATE ON payment_schedule_line "
        "FOR EACH ROW EXECUTE FUNCTION audit.log_changes();"
    )
    op.execute(
        "CREATE TRIGGER trg_payment_schedule_line_guard_created_immutable "
        "BEFORE UPDATE ON payment_schedule_line "
        "FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();"
    )

    # =========================================================================
    # Group 3 — invoice.payment_schedule_line_id (nullable additive FK)
    # =========================================================================
    op.execute(
        "ALTER TABLE invoice ADD COLUMN payment_schedule_line_id UUID "
        "REFERENCES payment_schedule_line(id) ON DELETE SET NULL;"
    )
    op.execute(
        "CREATE INDEX ix_invoice_payment_schedule_line_id "
        "ON invoice (payment_schedule_line_id);"
    )


def downgrade() -> None:
    # =========================================================================
    # Reverse Group 3 — invoice.payment_schedule_line_id
    # =========================================================================
    op.execute("DROP INDEX IF EXISTS ix_invoice_payment_schedule_line_id;")
    op.execute("ALTER TABLE invoice DROP COLUMN IF EXISTS payment_schedule_line_id;")

    # =========================================================================
    # Reverse Group 2 — payment_schedule_line (triggers → indexes → CHECKs → table)
    # =========================================================================
    op.execute(
        "DROP TRIGGER IF EXISTS trg_payment_schedule_line_guard_created_immutable "
        "ON payment_schedule_line;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_payment_schedule_line_changes ON payment_schedule_line;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_payment_schedule_line_set_updated_at ON payment_schedule_line;"
    )

    op.execute("DROP INDEX IF EXISTS uq_psl_invoice_id;")
    op.execute("DROP INDEX IF EXISTS uq_psl_schedule_sequence;")
    op.execute("DROP INDEX IF EXISTS ix_psl_schedule_id;")
    op.execute("DROP INDEX IF EXISTS ix_psl_tenant_id;")

    op.execute(
        "ALTER TABLE payment_schedule_line DROP CONSTRAINT IF EXISTS psl_status_chk;"
    )
    op.execute(
        "ALTER TABLE payment_schedule_line DROP CONSTRAINT IF EXISTS psl_trigger_type_chk;"
    )
    op.execute(
        "ALTER TABLE payment_schedule_line DROP CONSTRAINT IF EXISTS psl_basis_chk;"
    )
    op.execute(
        "ALTER TABLE payment_schedule_line DROP CONSTRAINT IF EXISTS psl_trigger_detail_chk;"
    )
    op.execute(
        "ALTER TABLE payment_schedule_line DROP CONSTRAINT IF EXISTS psl_basis_amount_chk;"
    )

    op.execute("DROP TABLE IF EXISTS payment_schedule_line;")

    # =========================================================================
    # Reverse Group 1 — payment_schedule (triggers → indexes → CHECKs → table)
    # =========================================================================
    op.execute(
        "DROP TRIGGER IF EXISTS trg_payment_schedule_guard_created_immutable ON payment_schedule;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_payment_schedule_changes ON payment_schedule;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_payment_schedule_set_updated_at ON payment_schedule;"
    )

    op.execute("DROP INDEX IF EXISTS ix_payment_schedule_job_id;")
    op.execute("DROP INDEX IF EXISTS ix_payment_schedule_quote_id;")
    op.execute("DROP INDEX IF EXISTS ix_payment_schedule_tenant_id;")

    op.execute(
        "ALTER TABLE payment_schedule DROP CONSTRAINT IF EXISTS chk_payment_schedule_basis_default;"
    )
    op.execute(
        "ALTER TABLE payment_schedule DROP CONSTRAINT IF EXISTS chk_payment_schedule_status;"
    )

    op.execute("DROP TABLE IF EXISTS payment_schedule;")
