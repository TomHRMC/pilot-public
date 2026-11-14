"""phase_fe_1_batch_b7b_conflict_classification_matrix

Revision ID: 98dfa5001716
Revises: 9bcf354b282f
Create Date: 2026-05-01 21:06:50

B7b / A40 — Conflict Severity Classification Engine
Creates sync_conflict_classification_matrix table with 17 platform-default seed rows.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "98dfa5001716"
down_revision = "9bcf354b282f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Create table                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "sync_conflict_classification_matrix",
        sa.Column(
            "id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("trigger_condition", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("classification_reason", sa.Text(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_sync_conflict_classification_matrix"),
        sa.CheckConstraint(
            "severity IN ('auto_silent', 'auto_notice', 'tech_resolvable', 'owner_escalation')",
            name="chk_sync_conflict_matrix_severity",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_sync_conflict_matrix_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_sync_conflict_matrix_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_sync_conflict_matrix_updated_by",
            ondelete="RESTRICT",
        ),
    )

    # ------------------------------------------------------------------ #
    # 2. Partial unique index: one rule per (op_type, trigger, tenant)    #
    #    Platform rows (tenant_id IS NULL) enforced by partial index.     #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE UNIQUE INDEX uq_sync_conflict_matrix_platform_default
        ON public.sync_conflict_classification_matrix (operation_type, trigger_condition)
        WHERE tenant_id IS NULL;
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_sync_conflict_matrix_tenant_override
        ON public.sync_conflict_classification_matrix (operation_type, trigger_condition, tenant_id)
        WHERE tenant_id IS NOT NULL;
    """)

    # ------------------------------------------------------------------ #
    # 3. Regular indexes                                                   #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_sync_conflict_matrix_tenant_op",
        "sync_conflict_classification_matrix",
        ["tenant_id", "operation_type"],
    )

    op.execute("""
        CREATE INDEX ix_sync_conflict_matrix_active
        ON public.sync_conflict_classification_matrix (operation_type, trigger_condition)
        WHERE is_active = TRUE;
    """)

    # ------------------------------------------------------------------ #
    # 4. Triggers (mandatory per §13.4)                                   #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TRIGGER audit_sync_conflict_classification_matrix_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.sync_conflict_classification_matrix
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER trg_sync_conflict_classification_matrix_guard_created_immutable
        BEFORE UPDATE ON public.sync_conflict_classification_matrix
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)

    op.execute("""
        CREATE TRIGGER trg_sync_conflict_classification_matrix_set_updated_at
        BEFORE UPDATE ON public.sync_conflict_classification_matrix
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)

    # ------------------------------------------------------------------ #
    # 5. Seed 17 platform-default rows (tenant_id = NULL)                 #
    # ------------------------------------------------------------------ #
    op.execute("""
        INSERT INTO public.sync_conflict_classification_matrix
            (id, operation_type, trigger_condition, severity, classification_reason, is_active, tenant_id)
        VALUES
            (gen_random_uuid(), 'time_entry',    'job_still_assigned',          'auto_silent',      'Job still assigned to you',                       true, NULL),
            (gen_random_uuid(), 'time_entry',    'job_reassigned',              'tech_resolvable',  'Job reassigned to different tech',                 true, NULL),
            (gen_random_uuid(), 'time_entry',    'job_deleted',                 'owner_escalation', 'Job deleted while you worked it',                  true, NULL),
            (gen_random_uuid(), 'time_entry',    'time_overlap',                'tech_resolvable',  'Time overlaps an existing entry',                  true, NULL),
            (gen_random_uuid(), 'expense',       'category_exists_under_limit', 'auto_silent',      'Expense category exists and is under limit',       true, NULL),
            (gen_random_uuid(), 'expense',       'category_renamed',            'auto_notice',      'Expense category was renamed server-side',         true, NULL),
            (gen_random_uuid(), 'expense',       'exceeds_per_item_limit',      'tech_resolvable',  'Expense exceeds tenant per-item limit',            true, NULL),
            (gen_random_uuid(), 'expense',       'job_deleted',                 'owner_escalation', 'Job deleted while expense was captured',           true, NULL),
            (gen_random_uuid(), 'photo',         'job_exists',                  'auto_silent',      'Job exists and photo uploaded cleanly',            true, NULL),
            (gen_random_uuid(), 'photo',         'storage_limit_exceeded',      'tech_resolvable',  'Storage limit exceeded',                           true, NULL),
            (gen_random_uuid(), 'photo',         'job_deleted',                 'owner_escalation', 'Job deleted while photo was captured',             true, NULL),
            (gen_random_uuid(), 'status_change', 'normal_transition',           'auto_silent',      'Normal job status transition',                     true, NULL),
            (gen_random_uuid(), 'status_change', 'job_already_completed',       'owner_escalation', 'Job already completed by another tech',            true, NULL),
            (gen_random_uuid(), 'change_order',  'quote_version_active',        'auto_silent',      'Quote version is still active',                    true, NULL),
            (gen_random_uuid(), 'change_order',  'quote_version_superseded',    'tech_resolvable',  'Quote version superseded since capture',           true, NULL),
            (gen_random_uuid(), 'loto_check',    'job_in_progress',             'auto_silent',      'Job still in progress when LOTO synced',           true, NULL),
            (gen_random_uuid(), 'loto_check',    'job_completed_before_sync',   'auto_notice',      'Job completed before LOTO sync arrived',           true, NULL);
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_sync_conflict_classification_matrix_changes ON public.sync_conflict_classification_matrix;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_sync_conflict_classification_matrix_guard_created_immutable ON public.sync_conflict_classification_matrix;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_sync_conflict_classification_matrix_set_updated_at ON public.sync_conflict_classification_matrix;"
    )
    op.drop_index(
        "ix_sync_conflict_matrix_active",
        table_name="sync_conflict_classification_matrix",
    )
    op.drop_index(
        "ix_sync_conflict_matrix_tenant_op",
        table_name="sync_conflict_classification_matrix",
    )
    op.execute("DROP INDEX IF EXISTS public.uq_sync_conflict_matrix_tenant_override;")
    op.execute("DROP INDEX IF EXISTS public.uq_sync_conflict_matrix_platform_default;")
    op.drop_table("sync_conflict_classification_matrix")
