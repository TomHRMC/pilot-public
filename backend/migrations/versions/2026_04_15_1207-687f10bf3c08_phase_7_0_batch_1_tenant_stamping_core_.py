"""phase_7_0_batch_1_tenant_stamping_core_crm

Revision ID: 687f10bf3c08
Revises: 942e0e011328
Create Date: 2026-04-15 12:07:28.972409+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "687f10bf3c08"
down_revision: str | None = "942e0e011328"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables to update
TABLES = [
    "entity_address",
    "entity_contact",
    "address",
    "contact",
    "contact_endpoint",
    "contact_notification_pref",
    "contact_portal_invite",
]


def upgrade() -> None:
    # 1. Add tenant_id as nullable=True to all tables
    for table_name in TABLES:
        op.add_column(table_name, sa.Column("tenant_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            f"fk_{table_name}_tenant_id", table_name, "tenant", ["tenant_id"], ["id"]
        )
        op.create_index(f"ix_{table_name}_tenant_id", table_name, ["tenant_id"])

    # 2. Backfill Data

    # entity_address
    op.execute("""
        UPDATE entity_address
        SET tenant_id = c.tenant_id
        FROM customer c
        WHERE entity_address.entity_type_code = 'customer' AND entity_address.entity_id = c.id
    """)
    op.execute("""
        UPDATE entity_address
        SET tenant_id = s.tenant_id
        FROM site s
        WHERE entity_address.entity_type_code = 'site' AND entity_address.entity_id = s.id
    """)

    # entity_contact
    op.execute("""
        UPDATE entity_contact
        SET tenant_id = c.tenant_id
        FROM customer c
        WHERE entity_contact.entity_type_code = 'customer' AND entity_contact.entity_id = c.id
    """)
    op.execute("""
        UPDATE entity_contact
        SET tenant_id = s.tenant_id
        FROM site s
        WHERE entity_contact.entity_type_code = 'site' AND entity_contact.entity_id = s.id
    """)

    # address
    op.execute("""
        UPDATE address
        SET tenant_id = ea.tenant_id
        FROM entity_address ea
        WHERE address.id = ea.address_id AND ea.tenant_id IS NOT NULL
    """)

    # contact (via customer_id or entity_contact)
    op.execute("""
        UPDATE contact
        SET tenant_id = c.tenant_id
        FROM customer c
        WHERE contact.customer_id = c.id
    """)
    op.execute("""
        UPDATE contact
        SET tenant_id = ec.tenant_id
        FROM entity_contact ec
        WHERE contact.id = ec.contact_id AND contact.tenant_id IS NULL AND ec.tenant_id IS NOT NULL
    """)

    # contact_endpoint
    op.execute("""
        UPDATE contact_endpoint
        SET tenant_id = c.tenant_id
        FROM contact c
        WHERE contact_endpoint.contact_id = c.id AND c.tenant_id IS NOT NULL
    """)

    # contact_notification_pref
    op.execute("""
        UPDATE contact_notification_pref
        SET tenant_id = c.tenant_id
        FROM contact c
        WHERE contact_notification_pref.contact_id = c.id AND c.tenant_id IS NOT NULL
    """)

    # contact_portal_invite
    op.execute("""
        UPDATE contact_portal_invite
        SET tenant_id = c.tenant_id
        FROM contact c
        WHERE contact_portal_invite.contact_id = c.id AND c.tenant_id IS NOT NULL
    """)

    # Purge any orphaned records to enforce NOT NULL
    for table_name in reversed(TABLES):
        op.execute(f"DELETE FROM {table_name} WHERE tenant_id IS NULL")

    # 3. Set nullable=False
    for table_name in TABLES:
        op.alter_column(table_name, "tenant_id", nullable=False)


def downgrade() -> None:
    for table_name in reversed(TABLES):
        op.drop_index(f"ix_{table_name}_tenant_id", table_name=table_name)
        op.drop_constraint(f"fk_{table_name}_tenant_id", table_name, type_="foreignkey")
        op.drop_column(table_name, "tenant_id")
