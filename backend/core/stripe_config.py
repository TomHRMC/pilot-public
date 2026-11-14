"""
Runtime loader for Stripe object IDs.

Reads stripe_ids.{mode}.json at startup; provides singleton accessor.
Mode determined by STRIPE_SECRET_KEY prefix: sk_test_ → test, sk_live_ → live.

C-B4 — created for the Charter subscription lifecycle.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_ids_cache: dict | None = None


def get_stripe_ids() -> dict:
    """
    Return the Stripe object ID mapping for the current mode.

    Structure matches stripe_ids.test.json::

        {
            "mode": "test",
            "products": {"prod_starter": "...", "prod_teams": "...", "prod_passthrough": "..."},
            "meters": {"meter_voice_minutes": "...", "meter_sms_segments": "..."},
            "prices": {"price_charter_monthly": "...", "price_voice_overage": "...", ...}
        }

    The result is cached for the lifetime of the process (singleton).
    Raises FileNotFoundError if the IDs file for the current mode is missing.
    """
    global _ids_cache
    if _ids_cache is not None:
        return _ids_cache

    from core.config import settings

    mode = "test" if settings.STRIPE_SECRET_KEY.startswith("sk_test_") else "live"
    ids_file = Path(__file__).parent.parent / "scripts" / f"stripe_ids.{mode}.json"

    if not ids_file.exists():
        raise FileNotFoundError(f"Stripe IDs file not found: {ids_file}")

    _ids_cache = json.loads(ids_file.read_text())
    logger.info(
        "Loaded Stripe IDs for %s mode: %d prices",
        mode,
        len(_ids_cache.get("prices", {})),
    )
    return _ids_cache


def reset_stripe_ids_cache() -> None:
    """Clear the singleton cache. Intended for tests only."""
    global _ids_cache
    _ids_cache = None
