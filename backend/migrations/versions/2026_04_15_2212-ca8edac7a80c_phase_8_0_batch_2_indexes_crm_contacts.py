"""phase_8_0_batch_2_indexes_crm_contacts

Revision ID: ca8edac7a80c
Revises:
Create Date: 2026-04-15 22:12:07.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ca8edac7a80c"
down_revision: str | None = "522c3ca3cc9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- customer ---
    op.create_index(
        "ix_customer_lifecycle_status_id", "customer", ["lifecycle_status_id"]
    )

    # --- site ---
    op.create_index("ix_site_customer_id", "site", ["customer_id"])
    op.create_index("ix_site_lifecycle_status_id", "site", ["lifecycle_status_id"])

    # --- contact_type ---
    op.create_index("ix_contact_type_tenant_id", "contact_type", ["tenant_id"])

    # --- entity_contact ---
    op.create_index(
        "ix_entity_contact_contact_type_code", "entity_contact", ["contact_type_code"]
    )

    # --- address_type ---
    op.create_index("ix_address_type_tenant_id", "address_type", ["tenant_id"])

    # --- entity_address ---
    op.create_index(
        "ix_entity_address_address_type_code", "entity_address", ["address_type_code"]
    )

    # --- quote_public_link_contact_action ---
    op.create_index(
        "ix_quote_public_link_contact_action_qpl_contact_action_type_id",
        "quote_public_link_contact_action",
        ["qpl_contact_action_type_id"],
    )

    # --- quote_acceptance ---
    op.create_index(
        "ix_quote_acceptance_contact_id", "quote_acceptance", ["contact_id"]
    )
    op.create_index(
        "ix_quote_acceptance_accepted_by_user_id",
        "quote_acceptance",
        ["accepted_by_user_id"],
    )
    op.create_index(
        "ix_quote_acceptance_quote_public_link_id",
        "quote_acceptance",
        ["quote_public_link_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_customer_lifecycle_status_id", table_name="customer")
    op.drop_index("ix_site_customer_id", table_name="site")
    op.drop_index("ix_site_lifecycle_status_id", table_name="site")
    op.drop_index("ix_contact_type_tenant_id", table_name="contact_type")
    op.drop_index("ix_entity_contact_contact_type_code", table_name="entity_contact")
    op.drop_index("ix_address_type_tenant_id", table_name="address_type")
    op.drop_index("ix_entity_address_address_type_code", table_name="entity_address")
    op.drop_index(
        "ix_quote_public_link_contact_action_qpl_contact_action_type_id",
        table_name="quote_public_link_contact_action",
    )
    op.drop_index("ix_quote_acceptance_contact_id", table_name="quote_acceptance")
    op.drop_index(
        "ix_quote_acceptance_accepted_by_user_id", table_name="quote_acceptance"
    )
    op.drop_index(
        "ix_quote_acceptance_quote_public_link_id", table_name="quote_acceptance"
    )
