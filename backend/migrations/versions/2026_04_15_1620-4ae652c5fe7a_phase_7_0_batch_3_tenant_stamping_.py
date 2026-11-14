"""phase_7_0_batch_3_tenant_stamping_operations_jobs

Revision ID: 4ae652c5fe7a
Revises: 7d0f9c2be964
Create Date: 2026-04-15 16:20:03.221208+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4ae652c5fe7a"
down_revision: str | None = "7d0f9c2be964"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==============================================================
    # TABLE: job_notes  (parent: job via job_id)
    # ==============================================================
    op.add_column("job_notes", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_job_notes_tenant_id", "job_notes", "tenant", ["tenant_id"], ["id"]
    )
    op.create_index("ix_job_notes_tenant_id", "job_notes", ["tenant_id"])
    op.execute("""
        UPDATE job_notes
        SET tenant_id = job.tenant_id
        FROM job
        WHERE job_notes.job_id = job.id
    """)
    op.alter_column("job_notes", "tenant_id", nullable=False)

    # ==============================================================
    # TABLE: job_time_entry  (parent: job via job_id)
    # ==============================================================
    op.add_column("job_time_entry", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_job_time_entry_tenant_id", "job_time_entry", "tenant", ["tenant_id"], ["id"]
    )
    op.create_index("ix_job_time_entry_tenant_id", "job_time_entry", ["tenant_id"])
    op.execute("""
        UPDATE job_time_entry
        SET tenant_id = job.tenant_id
        FROM job
        WHERE job_time_entry.job_id = job.id
    """)
    op.alter_column("job_time_entry", "tenant_id", nullable=False)

    # ==============================================================
    # TABLE: change_order  (parent: job via job_id)
    # ==============================================================
    op.add_column("change_order", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_change_order_tenant_id", "change_order", "tenant", ["tenant_id"], ["id"]
    )
    op.create_index("ix_change_order_tenant_id", "change_order", ["tenant_id"])
    op.execute("""
        UPDATE change_order
        SET tenant_id = job.tenant_id
        FROM job
        WHERE change_order.job_id = job.id
    """)
    op.alter_column("change_order", "tenant_id", nullable=False)

    # ==============================================================
    # TABLE: change_order_attachment  (parent: change_order via change_order_id)
    # ==============================================================
    op.add_column(
        "change_order_attachment", sa.Column("tenant_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_change_order_attachment_tenant_id",
        "change_order_attachment",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        "ix_change_order_attachment_tenant_id", "change_order_attachment", ["tenant_id"]
    )
    op.execute("""
        UPDATE change_order_attachment
        SET tenant_id = change_order.tenant_id
        FROM change_order
        WHERE change_order_attachment.change_order_id = change_order.id
    """)
    op.alter_column("change_order_attachment", "tenant_id", nullable=False)

    # ==============================================================
    # TABLE: change_order_line  (parent: change_order via change_order_id)
    # ==============================================================
    op.add_column("change_order_line", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_change_order_line_tenant_id",
        "change_order_line",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        "ix_change_order_line_tenant_id", "change_order_line", ["tenant_id"]
    )
    op.execute("""
        UPDATE change_order_line
        SET tenant_id = change_order.tenant_id
        FROM change_order
        WHERE change_order_line.change_order_id = change_order.id
    """)
    op.alter_column("change_order_line", "tenant_id", nullable=False)

    # ==============================================================
    # TABLE: change_order_line_tax_component  (2-HOP: via change_order_line -> change_order)
    # NOTE: change_order must already have tenant_id at this point (set above).
    # ==============================================================
    op.add_column(
        "change_order_line_tax_component",
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_change_order_line_tax_component_tenant_id",
        "change_order_line_tax_component",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        "ix_change_order_line_tax_component_tenant_id",
        "change_order_line_tax_component",
        ["tenant_id"],
    )
    op.execute("""
        UPDATE change_order_line_tax_component
        SET tenant_id = change_order.tenant_id
        FROM change_order_line
        JOIN change_order ON change_order_line.change_order_id = change_order.id
        WHERE change_order_line_tax_component.change_order_line_id = change_order_line.id
    """)
    op.alter_column("change_order_line_tax_component", "tenant_id", nullable=False)


def downgrade() -> None:
    op.drop_index(
        "ix_change_order_line_tax_component_tenant_id",
        table_name="change_order_line_tax_component",
    )
    op.drop_constraint(
        "fk_change_order_line_tax_component_tenant_id",
        "change_order_line_tax_component",
        type_="foreignkey",
    )
    op.drop_column("change_order_line_tax_component", "tenant_id")

    op.drop_index("ix_change_order_line_tenant_id", table_name="change_order_line")
    op.drop_constraint(
        "fk_change_order_line_tenant_id", "change_order_line", type_="foreignkey"
    )
    op.drop_column("change_order_line", "tenant_id")

    op.drop_index(
        "ix_change_order_attachment_tenant_id", table_name="change_order_attachment"
    )
    op.drop_constraint(
        "fk_change_order_attachment_tenant_id",
        "change_order_attachment",
        type_="foreignkey",
    )
    op.drop_column("change_order_attachment", "tenant_id")

    op.drop_index("ix_change_order_tenant_id", table_name="change_order")
    op.drop_constraint("fk_change_order_tenant_id", "change_order", type_="foreignkey")
    op.drop_column("change_order", "tenant_id")

    op.drop_index("ix_job_time_entry_tenant_id", table_name="job_time_entry")
    op.drop_constraint(
        "fk_job_time_entry_tenant_id", "job_time_entry", type_="foreignkey"
    )
    op.drop_column("job_time_entry", "tenant_id")

    op.drop_index("ix_job_notes_tenant_id", table_name="job_notes")
    op.drop_constraint("fk_job_notes_tenant_id", "job_notes", type_="foreignkey")
    op.drop_column("job_notes", "tenant_id")
