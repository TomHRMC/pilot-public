"""
Backfill internal_version_token for existing sync mappings.
Run after migration: python -m migrations.scripts.backfill_internal_version_tokens
"""

from sqlmodel import Session, select

from app.models.crm import Customer
from app.models.system import IntegrationSyncMapping
from core.db import engine


def backfill_internal_version_tokens():
    """Backfill internal_version_token for all existing mappings."""
    with Session(engine) as session:
        # Get all customer mappings without internal_version_token
        stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.entity_type_code == "customer",
            IntegrationSyncMapping.internal_version_token == None,
        )
        mappings = session.exec(stmt).all()

        print(f"Found {len(mappings)} customer mappings to backfill")

        for mapping in mappings:
            try:
                customer = session.get(Customer, mapping.entity_id)
                if customer:
                    mapping.internal_version_token = customer.updated_at.isoformat()
                    session.add(mapping)
                    print(f"✓ Backfilled mapping {mapping.id}")
                else:
                    print(
                        f"⚠ Customer {mapping.entity_id} not found, skipping mapping {mapping.id}"
                    )
            except Exception as e:
                print(f"✗ Error backfilling mapping {mapping.id}: {e}")
                continue

        session.commit()
        print(f"✅ Backfill complete! Updated {len(mappings)} mappings")


if __name__ == "__main__":
    backfill_internal_version_tokens()
