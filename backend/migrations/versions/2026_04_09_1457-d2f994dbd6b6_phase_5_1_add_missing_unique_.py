"""phase_5_1_add_missing_unique_constraints_and_foreign_keys

Revision ID: d2f994dbd6b6
Revises: 9395bb5a44fc
Create Date: 2026-04-09 14:57:35.402835+00:00

Description:
Adds 8 missing multi-column unique constraints and 2 missing foreign keys
to align physical database with Golden Master JSON schema.

Reference:
- Analysis: dev-docs/analysis/phase-5.1-db-schema-sync-7-analysis.md
- Plan: dev-docs/analysis/phase-5.1-db-schema-sync-7-plan.md
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2f994dbd6b6"
down_revision: str | None = "9395bb5a44fc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # =====================================================
    # UNIQUE CONSTRAINTS (8 Total)
    # =====================================================

    # 1. tenant_domain
    op.create_unique_constraint(
        "uq_tenant_domain_tenant_id_domain", "tenant_domain", ["tenant_id", "domain"]
    )

    # 2. tenant_user_invite
    op.create_unique_constraint(
        "uq_tenant_user_invite_tenant_id_email",
        "tenant_user_invite",
        ["tenant_id", "email"],
    )

    # 3. quote_version
    op.create_unique_constraint(
        "uq_quote_version_quote_id_version_no",
        "quote_version",
        ["quote_id", "version_no"],
    )

    # 4. subscription_usage
    op.create_unique_constraint(
        "uq_subscription_usage_subscription_feature_period",
        "subscription_usage",
        ["subscription_id", "product_feature_code", "period_start", "period_end"],
    )

    # 5. supplier_item
    op.create_unique_constraint(
        "uq_supplier_item_tenant_supplier_sku",
        "supplier_item",
        ["tenant_id", "supplier_id", "sku"],
    )

    # 6a. integration_sync_mapping (internal)
    op.create_unique_constraint(
        "uq_integration_sync_mapping_internal",
        "integration_sync_mapping",
        ["app_service_id", "entity_type_code", "entity_id"],
    )

    # 6b. integration_sync_mapping (external)
    op.create_unique_constraint(
        "uq_integration_sync_mapping_external",
        "integration_sync_mapping",
        ["app_service_id", "entity_type_code", "external_id"],
    )

    # 7. entity_address
    op.create_unique_constraint(
        "uq_entity_address_entity_address",
        "entity_address",
        ["entity_type_code", "entity_id", "address_id"],
    )

    # 8. entity_contact
    op.create_unique_constraint(
        "uq_entity_contact_entity_contact",
        "entity_contact",
        ["entity_type_code", "entity_id", "contact_id"],
    )

    # =====================================================
    # FOREIGN KEYS (2 Total)
    # =====================================================

    # 1. tenant.created_by → user.id
    op.create_foreign_key(
        "fk_tenant_created_by",
        "tenant",
        "user",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # 2. tenant.updated_by → user.id
    op.create_foreign_key(
        "fk_tenant_updated_by",
        "tenant",
        "user",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop foreign keys first (dependencies)
    op.drop_constraint("fk_tenant_updated_by", "tenant", type_="foreignkey")
    op.drop_constraint("fk_tenant_created_by", "tenant", type_="foreignkey")

    # Drop unique constraints
    op.drop_constraint(
        "uq_entity_contact_entity_contact", "entity_contact", type_="unique"
    )
    op.drop_constraint(
        "uq_entity_address_entity_address", "entity_address", type_="unique"
    )
    op.drop_constraint(
        "uq_integration_sync_mapping_external",
        "integration_sync_mapping",
        type_="unique",
    )
    op.drop_constraint(
        "uq_integration_sync_mapping_internal",
        "integration_sync_mapping",
        type_="unique",
    )
    op.drop_constraint(
        "uq_supplier_item_tenant_supplier_sku", "supplier_item", type_="unique"
    )
    op.drop_constraint(
        "uq_subscription_usage_subscription_feature_period",
        "subscription_usage",
        type_="unique",
    )
    op.drop_constraint(
        "uq_quote_version_quote_id_version_no", "quote_version", type_="unique"
    )
    op.drop_constraint(
        "uq_tenant_user_invite_tenant_id_email", "tenant_user_invite", type_="unique"
    )
    op.drop_constraint(
        "uq_tenant_domain_tenant_id_domain", "tenant_domain", type_="unique"
    )
