"""
Telnyx Real-API Integration Tests — TELNYX-INT-1
=================================================
Hits the REAL Telnyx API using mock 10DLC objects ($0 — no TCR fees, no SMS
traffic). This is the suite that closes the gap between the C-B9 provisioning
state machine (built against API docs) and live carrier behavior.

Prerequisites (all env vars):
    TELNYX_API_KEY           — Telnyx dev API key (Mission Control → API Keys)
    TELNYX_10DLC_MOCK=true   — REQUIRED for brand/campaign tests (fee guard)
    TELNYX_PUBLIC_KEY        — Ed25519 public key (for webhook verify test)

Run:
    # Full real-API suite (mock objects only — $0):
    TELNYX_API_KEY=xxx TELNYX_10DLC_MOCK=true TELNYX_PUBLIC_KEY=xxx \
        pytest tests/integration/test_telnyx_real_api.py -v

    # Without a key → entire module skips cleanly (zero failures in CI):
    pytest tests/integration/test_telnyx_real_api.py -v

Excluded by design (Tom's Step 3 E2E run):
    - send_message (live SMS — costs per segment)
    - provision_number (paid number order)
    - assign_number_to_campaign on the live campaign

See: dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md §14
"""

import json
import os
import time
from pathlib import Path

import pytest

from core.config import settings

# Module-level skip: skip entire file if no Telnyx API key.
# This ensures zero failures in CI when env vars are absent.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_telnyx,
    pytest.mark.skipif(
        not os.getenv("TELNYX_API_KEY") and not getattr(settings, "TELNYX_API_KEY", ""),
        reason="TELNYX_API_KEY not set — skipping real-API Telnyx integration tests",
    ),
]

# Fixture directory for captured real webhook payloads (G4).
_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "telnyx"
_WEBHOOK_CAPTURE_FILE = _FIXTURE_DIR / "real_webhook_capture.json"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get_carrier():
    """Instantiate a TelnyxSmsCarrier for testing."""
    from services.telnyx_sms_carrier import TelnyxSmsCarrier

    return TelnyxSmsCarrier()


def _require_mock_mode():
    """Fee guard — refuse to run brand/campaign creation unless TELNYX_10DLC_MOCK=true.

    This is the anti-fee safety: without it, a developer with a live API key
    could accidentally submit real, fee-bearing brands to TCR.
    """
    mock_enabled = os.getenv("TELNYX_10DLC_MOCK", "").lower() in (
        "true",
        "1",
        "yes",
    ) or bool(getattr(settings, "TELNYX_10DLC_MOCK", False))
    if not mock_enabled:
        pytest.skip(
            "TELNYX_10DLC_MOCK is not true — refusing to create brands/campaigns "
            "against the live Telnyx API (fee guard). Set TELNYX_10DLC_MOCK=true "
            "to run provisioning-flow tests with mock objects ($0)."
        )


def _mock_brand_data() -> dict:
    """Return a minimal brand payload for mock brand creation."""
    return {
        "entity_type": "standard",
        "legal_business_name": "Pilot Test Mock Co",
        "dba_name": "Pilot Test Mock",
        "ein": "12-3456789",
        "support_phone": "+15125550001",
        "hq_address_line1": "123 Test St",
        "hq_city": "Austin",
        "hq_state": "TX",
        "hq_postal_code": "78701",
        "hq_country": "US",
        "support_email": "test-mock@pilotfortrades.com",
        "vertical": "ENERGY",
    }


def _mock_campaign_data() -> dict:
    """Return a minimal campaign payload for mock campaign creation."""
    return {
        "campaign_name": "Pilot Test Mock Campaign",
        "use_case": "MIXED",
        "description": "Mock campaign for integration testing — no SMS traffic.",
        "sample_message_1": "Your Pilot account verification code is 123456.",
        "sample_message_2": "Your appointment is confirmed for Tuesday 2pm.",
        "message_flow": "User opts in via web signup; Pilot sends account and appointment notifications.",
        "opt_in_keywords": ["START", "YES"],
        "opt_out_keywords": ["STOP", "CANCEL", "UNSUBSCRIBE"],
        "help_keywords": ["HELP"],
        "opt_in_message": "You are subscribed to Pilot notifications. Reply STOP to opt out.",
        "opt_out_message": "You have been unsubscribed from Pilot notifications. Reply START to resubscribe.",
        "help_message": "Pilot for Trades: reply STOP to unsubscribe, START to resubscribe.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1 — Mock brand create + retrieve
# ─────────────────────────────────────────────────────────────────────────────


def test_mock_brand_create_and_retrieve():
    """Create a mock brand via the real Telnyx API, then retrieve it.

    Verifies:
    - create_brand returns a BrandResult with a non-empty brand_id
    - get_brand retrieves the brand and returns a valid status
    - The carrier's _mock_10dlc flag is True (mock mode active)

    Note: Does NOT poll to terminal state — mock brands may take time to
    transition. Cleanup is handled by scripts/cleanup_telnyx_mocks.py.
    """
    _require_mock_mode()
    carrier = _get_carrier()

    assert carrier._mock_10dlc is True, (
        "Carrier should have _mock_10dlc=True when TELNYX_10DLC_MOCK=true"
    )

    brand_result = carrier.create_brand(_mock_brand_data())
    assert brand_result.brand_id, "create_brand must return a non-empty brand_id"
    assert brand_result.status in ("pending", "verified", "rejected"), (
        f"Unexpected brand status: {brand_result.status}"
    )

    # Retrieve the brand — verify get_brand works against the real API
    retrieved = carrier.get_brand(brand_result.brand_id)
    assert retrieved.brand_id == brand_result.brand_id
    assert retrieved.status in ("pending", "verified", "rejected"), (
        f"Unexpected retrieved brand status: {retrieved.status}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 2 — Mock campaign create + poll (under the mock brand)
# ─────────────────────────────────────────────────────────────────────────────


def test_mock_campaign_create_and_poll():
    """Create a mock campaign under a mock brand, then retrieve it.

    Campaigns under a mock brand are mock by inheritance (Telnyx docs).
    No explicit mock flag on campaign creation is needed.

    Note: Telnyx requires the brand to be in a non-pending state before
    campaign creation. Mock brands transition fast (~5-10s), so we poll
    briefly. Cleanup is handled by scripts/cleanup_telnyx_mocks.py.
    """
    _require_mock_mode()
    carrier = _get_carrier()

    # First create a mock brand to parent the campaign
    brand_result = carrier.create_brand(_mock_brand_data())
    assert brand_result.brand_id, "Prerequisite brand creation failed"

    # Wait for the brand to reach a non-pending state (mock brands are fast)
    brand_ready = False
    for _attempt in range(10):
        polled = carrier.get_brand(brand_result.brand_id)
        if polled.status != "pending":
            brand_ready = True
            break
        time.sleep(2)

    if not brand_ready:
        pytest.skip(
            f"Mock brand {brand_result.brand_id} did not transition from pending "
            "within 20s — campaign creation requires a verified brand. "
            "Run the test again or clean up with scripts/cleanup_telnyx_mocks.py."
        )

    campaign_result = carrier.create_campaign(
        brand_result.brand_id, _mock_campaign_data()
    )
    assert campaign_result.campaign_id, (
        "create_campaign must return a non-empty campaign_id"
    )
    assert campaign_result.status in ("pending", "approved", "rejected"), (
        f"Unexpected campaign status: {campaign_result.status}"
    )

    # Retrieve the campaign — verify get_campaign works against the real API
    retrieved = carrier.get_campaign(campaign_result.campaign_id)
    assert retrieved.campaign_id == campaign_result.campaign_id
    assert retrieved.status in ("pending", "approved", "rejected"), (
        f"Unexpected retrieved campaign status: {retrieved.status}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3 — Verticals list (real enum values)
# ─────────────────────────────────────────────────────────────────────────────


def test_get_verticals_returns_real_list():
    """get_verticals returns a non-empty list of real Telnyx vertical enum values.

    Compares shape with MockSmsCarrier's fixed list — the real list should
    contain ENERGY (our default) and differ in length/content from the mock.
    """
    carrier = _get_carrier()
    verticals = carrier.get_verticals()

    assert isinstance(verticals, list), "get_verticals must return a list"
    assert len(verticals) > 0, "get_verticals must return a non-empty list"
    assert "ENERGY" in verticals, (
        f"ENERGY vertical must be present in real Telnyx list; got: {verticals[:10]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 4 — Number search (read-only, no order placed)
# ─────────────────────────────────────────────────────────────────────────────


def test_list_available_numbers_readonly():
    """list_available_numbers for a real area code returns real numbers.

    This is read-only — no number order is placed. Verifies the adapter
    correctly maps Telnyx's available_phone_numbers response.
    """
    carrier = _get_carrier()
    # Use area code 512 (Austin, TX) — widely available on Telnyx
    numbers = carrier.list_available_numbers("512", limit=5)

    assert isinstance(numbers, list), "list_available_numbers must return a list"
    # Telnyx may have no numbers for a given area code at a given time,
    # but 512 is almost always available. If empty, it's a Telnyx-side issue.
    if len(numbers) == 0:
        pytest.skip(
            "Telnyx returned no available numbers for area code 512 — transient"
        )
    assert len(numbers) <= 5, "list_available_numbers must respect the limit param"

    first = numbers[0]
    assert "phone_number" in first, "Each number dict must have 'phone_number'"
    assert first["phone_number"].startswith("+1"), (
        f"Phone number must be E.164 US format; got: {first['phone_number']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 5 — Error path: 4xx mapping
# ─────────────────────────────────────────────────────────────────────────────


def test_brand_error_4xx_mapping():
    """Malformed brand payload → Telnyx 4xx error is raised (not silently swallowed).

    The adapter's create_brand re-raises exceptions (per existing code pattern).
    We verify that a deliberately invalid payload (missing required fields)
    produces an exception with a useful message — not a silent success.
    """
    _require_mock_mode()
    carrier = _get_carrier()

    # Deliberately invalid: missing entity_type, display_name, email — all required
    invalid_brand_data = {
        "legal_business_name": "",  # empty → should fail validation
    }

    with pytest.raises(Exception) as exc_info:
        carrier.create_brand(invalid_brand_data)

    # The exception should have a meaningful message (not empty)
    assert str(exc_info.value), "Error exception must have a non-empty message"


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 6 — Ed25519 webhook signature verification (G4)
# ─────────────────────────────────────────────────────────────────────────────


def test_ed25519_webhook_capture_verification():
    """Verify verify_webhook_signature() returns True for a captured real webhook payload.

    If the fixture file (real_webhook_capture.json) is absent, skip with a
    message pointing at the capture instructions in the 10DLC playbook §14.4.

    This closes spike gap G4: the Ed25519 verification path has unit coverage
    only (mock always returns True). This test proves it against a real
    Telnyx-signed payload captured during Tom's Step 3 E2E SMS test.
    """
    if not _WEBHOOK_CAPTURE_FILE.exists():
        pytest.skip(
            f"Webhook capture fixture not found at {_WEBHOOK_CAPTURE_FILE}. "
            "Capture a real Telnyx webhook payload during Step 3 (see 10DLC "
            "playbook §14.4 for capture instructions)."
        )

    capture = json.loads(_WEBHOOK_CAPTURE_FILE.read_text())
    payload = capture["payload"].encode("utf-8")
    headers = capture["headers"]

    carrier = _get_carrier()
    result = carrier.verify_webhook_signature(payload, headers)
    assert result is True, (
        "verify_webhook_signature() must return True for a real captured "
        "Telnyx webhook payload with a valid Ed25519 signature"
    )
