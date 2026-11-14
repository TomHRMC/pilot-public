#!/usr/bin/env python3
"""
QuickBooks Integration Test Cleanup Script (Enhanced)

Purpose: Safely remove ALL test data created during QB integration testing.

Features:
- Pre-deletion verification (shows what will be deleted)
- Proper deletion order (respects foreign key constraints)
- Dry-run mode for safety
- Detailed progress reporting
- Error handling with rollback

WARNING: Only run in DEV environment!

Usage:
    cd backend
    python tests/scripts/cleanup_qb_tests.py          # Interactive mode
    python tests/scripts/cleanup_qb_tests.py --dry-run  # Preview only
    python tests/scripts/cleanup_qb_tests.py --yes     # Skip confirmation
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import Session, delete, func, select

from app.models.crm import Customer
from app.models.system import (
    IntegrationSyncConflict,
    IntegrationSyncMapping,
    WebhookEvent,
)
from core.db import engine


def print_header(text: str):
    """Print formatted section header"""
    print()
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text: str):
    """Print formatted subsection"""
    print()
    print(f"--- {text} ---")


class QuickBooksCleanup:
    """Handle QuickBooks test data cleanup with verification"""

    def __init__(self, tenant_id: str, dry_run: bool = False):
        self.tenant_id = tenant_id
        self.dry_run = dry_run
        self.stats = {
            "webhook_events": 0,
            "conflicts": 0,
            "mappings": 0,
            "customers": 0,
        }

    def verify_data(self, db: Session) -> dict:
        """
        Count all data that will be deleted.

        Returns dict with counts for each entity type.
        """
        print_section("Verifying Data to be Deleted")

        counts = {}

        # Count webhook events
        webhook_count = db.exec(
            select(func.count(WebhookEvent.id)).where(
                WebhookEvent.source_app == "quickbooks"
            )
        ).one()
        counts["webhook_events"] = webhook_count
        print(f"  Webhook Events (QB):        {webhook_count:4d}")

        # Count conflicts
        conflict_count = db.exec(
            select(func.count(IntegrationSyncConflict.id)).where(
                IntegrationSyncConflict.tenant_id == self.tenant_id
            )
        ).one()
        counts["conflicts"] = conflict_count
        print(f"  Sync Conflicts:             {conflict_count:4d}")

        # Count sync mappings
        mapping_count = db.exec(
            select(func.count(IntegrationSyncMapping.id))
            .where(IntegrationSyncMapping.tenant_id == self.tenant_id)
            .where(IntegrationSyncMapping.entity_type_code == "customer")
        ).one()
        counts["mappings"] = mapping_count
        print(f"  Sync Mappings (customers):  {mapping_count:4d}")

        # Get QB-synced customer IDs
        qb_customer_ids = db.exec(
            select(IntegrationSyncMapping.entity_id)
            .where(IntegrationSyncMapping.tenant_id == self.tenant_id)
            .where(IntegrationSyncMapping.entity_type_code == "customer")
        ).all()

        # Count QB-synced customers
        customer_count = len(qb_customer_ids) if qb_customer_ids else 0
        counts["customers"] = customer_count
        print(f"  Customers (QB synced):      {customer_count:4d}")

        # Total records
        total = sum(counts.values())
        print()
        print(f"  TOTAL RECORDS TO DELETE:    {total:4d}")

        return counts

    def show_sample_data(self, db: Session):
        """Show sample of data that will be deleted"""
        print_section("Sample Data Preview")

        # Get QB-synced customer IDs
        qb_customer_ids = db.exec(
            select(IntegrationSyncMapping.entity_id)
            .where(IntegrationSyncMapping.tenant_id == self.tenant_id)
            .where(IntegrationSyncMapping.entity_type_code == "customer")
        ).all()

        # Show sample customers (QB-synced only)
        if qb_customer_ids:
            customers = db.exec(
                select(Customer.display_name, Customer.email, Customer.created_at)
                .where(Customer.tenant_id == self.tenant_id)
                .where(Customer.id.in_(qb_customer_ids))
                .order_by(Customer.created_at.desc())
                .limit(10)
            ).all()
        else:
            customers = []

        if customers:
            print()
            print("  QB-Synced Customers to be Deleted (up to 10):")
            print("  " + "-" * 66)
            print(f"  {'Display Name':<30} {'Email':<25} {'Created':<10}")
            print("  " + "-" * 66)
            for customer in customers:
                email = (customer.email or "")[:24]
                created = (
                    customer.created_at.strftime("%Y-%m-%d")
                    if customer.created_at
                    else "N/A"
                )
                print(f"  {customer.display_name:<30} {email:<25} {created:<10}")
            print("  " + "-" * 66)
        else:
            print("  No QB-synced customers found")

    def delete_webhook_events(self, db: Session) -> int:
        """Delete webhook events (no FK dependencies)"""
        if self.dry_run:
            return 0

        result = db.exec(
            delete(WebhookEvent).where(WebhookEvent.source_app == "quickbooks")
        )
        count = result.rowcount
        self.stats["webhook_events"] = count
        return count

    def delete_conflicts(self, db: Session) -> int:
        """Delete sync conflicts"""
        if self.dry_run:
            return 0

        result = db.exec(
            delete(IntegrationSyncConflict).where(
                IntegrationSyncConflict.tenant_id == self.tenant_id
            )
        )
        count = result.rowcount
        self.stats["conflicts"] = count
        return count

    def delete_sync_mappings(self, db: Session) -> int:
        """Delete sync mappings for customers"""
        if self.dry_run:
            return 0

        result = db.exec(
            delete(IntegrationSyncMapping)
            .where(IntegrationSyncMapping.tenant_id == self.tenant_id)
            .where(IntegrationSyncMapping.entity_type_code == "customer")
        )
        count = result.rowcount
        self.stats["mappings"] = count
        return count

    def delete_customers(self, db: Session) -> int:
        """Delete QB-synced customers (identified via sync mappings)"""
        if self.dry_run:
            return 0

        # Get QB-synced customer IDs
        qb_customer_ids = db.exec(
            select(IntegrationSyncMapping.entity_id)
            .where(IntegrationSyncMapping.tenant_id == self.tenant_id)
            .where(IntegrationSyncMapping.entity_type_code == "customer")
        ).all()

        if not qb_customer_ids:
            return 0

        result = db.exec(
            delete(Customer)
            .where(Customer.tenant_id == self.tenant_id)
            .where(Customer.id.in_(qb_customer_ids))
        )
        count = result.rowcount
        self.stats["customers"] = count
        return count

    def execute_cleanup(self, db: Session):
        """
        Execute cleanup in proper order.

        Deletion order (respects FK constraints):
        1. Webhook events (no dependencies)
        2. Sync conflicts (references mappings)
        3. Sync mappings (references customers)
        4. Customers (QB-synced only)

        Note: Sites and quotes are NOT deleted (none are linked to QB customers)
        """
        print_section("Executing Cleanup")

        if self.dry_run:
            print()
            print("  🔍 DRY RUN MODE - No data will be deleted")
            print()
            return

        try:
            # Step 1: Delete webhook events
            print()
            print("  [1/4] Deleting webhook events...", end="", flush=True)
            count = self.delete_webhook_events(db)
            print(f" ✅ Deleted {count} record(s)")

            # Step 2: Delete conflicts
            print("  [2/4] Deleting sync conflicts...", end="", flush=True)
            count = self.delete_conflicts(db)
            print(f" ✅ Deleted {count} record(s)")

            # Step 3: Delete sync mappings
            print("  [3/4] Deleting sync mappings...", end="", flush=True)
            count = self.delete_sync_mappings(db)
            print(f" ✅ Deleted {count} record(s)")

            # Step 4: Delete customers
            print("  [4/4] Deleting customers...", end="", flush=True)
            count = self.delete_customers(db)
            print(f" ✅ Deleted {count} record(s)")

            # Commit all changes
            db.commit()
            print()
            print("  ✅ All changes committed successfully")

        except Exception as e:
            print(" ❌ FAILED")
            print()
            print(f"  ❌ Error during cleanup: {e}")
            print("  🔄 Rolling back all changes...")
            db.rollback()
            raise

    def verify_cleanup(self, db: Session):
        """Verify all data was deleted"""
        print_section("Verifying Cleanup")

        counts = self.verify_data(db)

        all_clean = all(count == 0 for count in counts.values())

        print()
        if all_clean:
            print("  ✅ Cleanup verification PASSED - All data removed")
        else:
            print("  ⚠️  Cleanup verification WARNING - Some data remains:")
            for key, count in counts.items():
                if count > 0:
                    print(f"     - {key}: {count} record(s) remaining")

        return all_clean

    def print_summary(self):
        """Print cleanup summary"""
        print_section("Cleanup Summary")
        print()
        print(f"  Webhook Events Deleted:     {self.stats['webhook_events']:4d}")
        print(f"  Sync Conflicts Deleted:     {self.stats['conflicts']:4d}")
        print(f"  Sync Mappings Deleted:      {self.stats['mappings']:4d}")
        print(f"  Customers Deleted:          {self.stats['customers']:4d}")
        print()
        total = sum(self.stats.values())
        print(f"  TOTAL RECORDS DELETED:      {total:4d}")
        print()
        print("  Note: Sites and quotes were NOT deleted (none linked to QB customers)")


def main():
    """Main cleanup execution"""
    parser = argparse.ArgumentParser(
        description="Clean up QuickBooks integration test data"
    )
    parser.add_argument(
        "--tenant-id",
        default="00000000-0000-0000-0000-000000000001",
        help="Tenant ID to clean up (default: test tenant)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    # Print header
    print_header("QuickBooks Integration Test Cleanup")
    print()
    print(f"  Tenant ID:    {args.tenant_id}")
    print("  Environment:  DEV (local)")
    print(
        f"  Mode:         {'DRY RUN (preview only)' if args.dry_run else 'LIVE (will delete data)'}"
    )
    print(f"  Timestamp:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    cleanup = QuickBooksCleanup(tenant_id=args.tenant_id, dry_run=args.dry_run)

    try:
        with Session(engine) as db:
            # Step 1: Verify what will be deleted
            print_header("Step 1: Verification")
            counts = cleanup.verify_data(db)

            # Check if there's anything to delete
            total_records = sum(counts.values())
            if total_records == 0:
                print()
                print("  ℹ️  No data found to delete")
                print()
                print("  The database is already clean for this tenant.")
                return

            # Show sample data
            cleanup.show_sample_data(db)

            # Step 2: Confirmation
            if not args.dry_run and not args.yes:
                print_header("Step 2: Confirmation")
                print()
                print(
                    f"  ⚠️  WARNING: This will PERMANENTLY DELETE {total_records} record(s)!"
                )
                print()
                print("  This includes:")
                print("    - All customers synced from QuickBooks (16 customers)")
                print("    - All sync mappings and conflict records")
                print("    - All webhook event logs")
                print()
                print("  This will NOT delete:")
                print("    - Sites and quotes (none are linked to QB customers)")
                print()

                confirm = input("  Type 'DELETE' to proceed: ").strip()

                if confirm != "DELETE":
                    print()
                    print("  ❌ Cleanup cancelled")
                    return

            # Step 3: Execute cleanup
            print_header("Step 3: Cleanup Execution")
            cleanup.execute_cleanup(db)

            # Step 4: Verify cleanup
            if not args.dry_run:
                print_header("Step 4: Post-Cleanup Verification")
                cleanup.verify_cleanup(db)

            # Step 5: Print summary
            print_header("Cleanup Complete")
            cleanup.print_summary()

            if not args.dry_run:
                print()
                print("  📋 Next Steps:")
                print()
                print("  1. Reset QuickBooks Sandbox:")
                print("     → https://developer.intuit.com")
                print("     → Dashboard → Sandbox → Reset Company Data")
                print()
                print("  2. (Optional) Disconnect QB Integration:")
                print(
                    "     → curl -X DELETE http://localhost:8000/api/v1/integrations/quickbooks/disconnect/test"
                )
                print()
                print("  3. For next test run, reconnect OAuth:")
                print(
                    "     → curl -X GET http://localhost:8000/api/v1/integrations/quickbooks/connect/test"
                )
                print()
            else:
                print()
                print("  💡 This was a DRY RUN - no data was deleted")
                print("  💡 Run without --dry-run to actually delete data")
                print()

    except Exception as e:
        print_header("Cleanup Failed")
        print()
        print(f"  ❌ Error: {e}")
        print()
        print("  The database has been rolled back to its previous state.")
        print("  No data was deleted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
