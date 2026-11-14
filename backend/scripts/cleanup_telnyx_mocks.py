#!/usr/bin/env python3
"""
Telnyx Mock Brand/Campaign Cleanup Script — TELNYX-INT-1
=========================================================
Lists and optionally deletes all mock 10DLC brands and campaigns from your
Telnyx account. Mock brands/campaigns are free ($0) but accumulate over time
from integration test runs.

Usage:
    cd backend && source .venv/bin/activate

    # List all mock brands and campaigns (dry run — no deletion):
    python scripts/cleanup_telnyx_mocks.py

    # Delete all mock brands and deactivate all mock campaigns:
    python scripts/cleanup_telnyx_mocks.py --delete

    # Delete only brands (campaigns are deactivated, not deletable):
    python scripts/cleanup_telnyx_mocks.py --delete --brands-only

Requires:
    TELNYX_API_KEY set in .env or environment.

Safety:
    - Only touches brands/campaigns where mock=True.
    - Real (non-mock) brands/campaigns are NEVER deleted.
    - Default mode is dry-run (list only). Must pass --delete to actually delete.
"""

import argparse
import sys

import telnyx

from core.config import settings


def _get_client():
    """Get a Telnyx client instance."""
    if not settings.TELNYX_API_KEY:
        print("ERROR: TELNYX_API_KEY is not set. Configure it in backend/.env")
        sys.exit(1)
    return telnyx.Telnyx(api_key=settings.TELNYX_API_KEY)


def list_mock_brands(client):
    """List all mock brands in the account."""
    brands = client.messaging_10dlc.brand.list()
    mock_brands = []
    for brand in brands.records:
        if getattr(brand, "mock", False):
            mock_brands.append(brand)
    return mock_brands


def list_mock_campaigns(client):
    """List all mock campaigns across all mock brands."""
    mock_campaigns = []
    mock_brands = list_mock_brands(client)
    for brand in mock_brands:
        try:
            campaigns = client.messaging_10dlc.campaign.list(brand_id=brand.brand_id)
            for campaign in campaigns.records:
                if getattr(campaign, "mock", False):
                    mock_campaigns.append(campaign)
        except Exception:
            pass  # Skip brands that error on campaign listing
    return mock_campaigns


def delete_brand(client, brand_id):
    """Delete a single brand."""
    client.messaging_10dlc.brand.delete(brand_id)


def deactivate_campaign(client, campaign_id):
    """Deactivate a single campaign (campaigns cannot be deleted, only deactivated)."""
    client.messaging_10dlc.campaign.deactivate(campaign_id)


def main():
    parser = argparse.ArgumentParser(
        description="Clean up Telnyx mock 10DLC brands and campaigns."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete/deactivate (default: dry run / list only)",
    )
    parser.add_argument(
        "--brands-only",
        action="store_true",
        help="Only process brands (skip campaign deactivation)",
    )
    args = parser.parse_args()

    client = _get_client()

    # ── Campaigns ──
    if not args.brands_only:
        print("\n── Mock Campaigns ──")
        mock_campaigns = list_mock_campaigns(client)
        if not mock_campaigns:
            print("  No mock campaigns found.")
        else:
            for c in mock_campaigns:
                cid = getattr(c, "campaign_id", "unknown")
                status = getattr(c, "status", "unknown")
                desc = getattr(c, "description", "")[:60]
                print(f"  {cid}  status={status}  desc={desc}")
                if args.delete:
                    try:
                        deactivate_campaign(client, cid)
                        print("    → DEACTIVATED")
                    except Exception as e:
                        print(f"    → FAILED: {e}")
            if not args.delete:
                print(
                    f"\n  {len(mock_campaigns)} mock campaign(s) found. "
                    "Use --delete to deactivate them."
                )

    # ── Brands ──
    print("\n── Mock Brands ──")
    mock_brands = list_mock_brands(client)
    if not mock_brands:
        print("  No mock brands found.")
    else:
        for b in mock_brands:
            bid = getattr(b, "brand_id", "unknown")
            status = getattr(b, "status", "unknown")
            name = getattr(b, "display_name", "")[:60]
            print(f"  {bid}  status={status}  name={name}")
            if args.delete:
                try:
                    delete_brand(client, bid)
                    print("    → DELETED")
                except Exception as e:
                    print(f"    → FAILED: {e}")
        if not args.delete:
            print(
                f"\n  {len(mock_brands)} mock brand(s) found. "
                "Use --delete to delete them."
            )

    if not args.delete:
        print("\nDry run complete. Use --delete to actually clean up.")
    else:
        print("\nCleanup complete.")


if __name__ == "__main__":
    main()
