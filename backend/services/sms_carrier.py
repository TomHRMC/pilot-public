"""
Carrier-Agnostic SMS Adapter — B11/A59
======================================
Abstract interface for SMS carrier integrations.
All carrier interactions MUST go through this module.
Never import Telnyx (or any carrier SDK) directly in routes or service code.

Factory: call get_sms_carrier() everywhere; configuration is via SMS_CARRIER env var.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

# Basic regex for E.164 phone number validation (e.g., +15551234567)
_PHONE_REGEX = re.compile(r"^\+?[1-9]\d{1,14}$")


def validate_phone_number(phone: str | None) -> bool:
    """
    Validate a phone number format (E.164).
    Moved here from the defunct sms_service.py (DLC-B2 Twilio removal).

    Args:
        phone: Phone number string to validate

    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    return bool(_PHONE_REGEX.match(phone))


@dataclass
class InboundMessage:
    """Normalized representation of an incoming SMS from any carrier."""

    from_number: str  # E.164  e.g. +15125551234
    to_number: str  # E.164 — the tenant_phone_number that received it
    body: str
    carrier_message_id: str
    received_at: str  # ISO timestamp string from carrier


@dataclass
class SendResult:
    """Result of an outbound SMS send attempt."""

    status: str  # "sent" | "failed"
    carrier_message_id: str | None
    error_message: str | None
    http_status: int
    retryable: bool  # True → safe to enqueue retry


@dataclass
class ProvisionedNumber:
    """Details of a newly provisioned phone number."""

    phone_number: str  # E.164
    carrier_provisioning_id: str  # Carrier's internal reference
    monthly_fee_cents: int


@dataclass
class BrandResult:
    """Result of a 10DLC brand registration or status poll (C-B9)."""

    brand_id: str
    status: str  # "pending" | "verified" | "rejected"
    rejection_reason: str | None = None


@dataclass
class CampaignResult:
    """Result of a 10DLC campaign registration or status poll (C-B9)."""

    campaign_id: str
    status: str  # "pending" | "approved" | "rejected"
    rejection_reason: str | None = None


class SmsCarrier(ABC):
    """
    Abstract interface for SMS carrier integrations.

    Configuration: set SMS_CARRIER env var to select implementation.
    Currently supported values: 'telnyx' | 'mock' (default: 'mock')

    All carrier interactions must go through this interface — never import
    the Telnyx SDK (or any other carrier SDK) directly in routes or services.
    Future provider swaps are a one-class change.
    """

    @abstractmethod
    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber:
        """Acquire a new phone number from the carrier for this tenant."""
        ...

    @abstractmethod
    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult:
        """Send an outbound SMS. Returns SendResult with status and carrier_message_id."""
        ...

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        """Return True if the webhook payload's signature is valid. False → reject (401).

        headers: the full HTTP headers dict from the incoming request.
        The Telnyx v4 SDK (standardwebhooks) requires telnyx-signature-ed25519,
        telnyx-timestamp, and telnyx-nonce to all be present.
        """
        ...

    @abstractmethod
    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage:
        """Parse carrier webhook payload into normalized InboundMessage dataclass."""
        ...

    @abstractmethod
    def get_delivery_status(self, carrier_message_id: str) -> str:
        """Return delivery status: 'delivered' | 'failed' | 'sent' | 'unknown'."""
        ...

    @abstractmethod
    def release_number(self, phone_number: str) -> None:
        """Release a provisioned number back to the carrier pool."""
        ...

    # ── C-B9: 10DLC Brand/Campaign/Verticals/Numbers methods ───────────────

    @abstractmethod
    def create_brand(self, brand_data: dict) -> BrandResult:
        """Submit brand registration to the carrier's 10DLC API."""
        ...

    @abstractmethod
    def get_brand(self, brand_id: str) -> BrandResult:
        """Poll brand registration status."""
        ...

    @abstractmethod
    def create_campaign(self, brand_id: str, campaign_data: dict) -> CampaignResult:
        """Submit campaign registration to the carrier's 10DLC API."""
        ...

    @abstractmethod
    def get_campaign(self, campaign_id: str) -> CampaignResult:
        """Poll campaign registration status."""
        ...

    @abstractmethod
    def get_verticals(self) -> list[str]:
        """Return valid business verticals from the carrier's 10DLC API."""
        ...

    @abstractmethod
    def list_available_numbers(self, area_code: str, limit: int = 10) -> list[dict]:
        """Return available phone numbers for an area code.

        Each dict: {phone_number, locality, region, monthly_cost_millicents}.
        """
        ...

    @abstractmethod
    def assign_number_to_campaign(self, phone_number: str, campaign_id: str) -> str:
        """Provision + assign a phone number to a campaign. Returns the assigned phone_number."""
        ...


class MockSmsCarrier(SmsCarrier):
    """
    In-memory mock implementation for testing and development.
    Captures all calls without making real API requests.

    SMS_CARRIER=mock (default) uses this implementation.

    Usage in tests:
        from unittest.mock import patch
        with patch("services.sms_carrier.get_sms_carrier", return_value=MockSmsCarrier()):
            ...
    """

    def __init__(self):
        self.sent_messages: list[dict] = []
        self.provisioned_numbers: list[str] = []

    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber:
        number = f"+1{area_code}5550001"
        self.provisioned_numbers.append(number)
        return ProvisionedNumber(
            phone_number=number,
            carrier_provisioning_id=f"mock-{number}",
            monthly_fee_cents=100,
        )

    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult:
        self.sent_messages.append({"from": from_number, "to": to_number, "body": body})
        return SendResult(
            status="sent",
            carrier_message_id=f"mock-msg-{len(self.sent_messages)}",
            error_message=None,
            http_status=200,
            retryable=False,
        )

    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        return True  # Always valid in mock/test mode

    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage:
        import json

        data = json.loads(payload)
        return InboundMessage(
            from_number=data["from"],
            to_number=data["to"],
            body=data["body"],
            carrier_message_id=data.get("id", "mock-id"),
            received_at=data.get("received_at", "2026-01-01T00:00:00Z"),
        )

    def get_delivery_status(self, carrier_message_id: str) -> str:
        return "delivered"

    def release_number(self, phone_number: str) -> None:
        if phone_number in self.provisioned_numbers:
            self.provisioned_numbers.remove(phone_number)

    # ── C-B9: 10DLC Brand/Campaign/Verticals/Numbers mock implementations ──

    def create_brand(self, brand_data: dict) -> BrandResult:
        """Deterministic mock: returns a pending brand with a fixed ID."""
        return BrandResult(
            brand_id="mock-brand-001",
            status="pending",
            rejection_reason=None,
        )

    def get_brand(self, brand_id: str) -> BrandResult:
        """Deterministic mock: brand is always verified."""
        return BrandResult(
            brand_id=brand_id,
            status="verified",
            rejection_reason=None,
        )

    def create_campaign(self, brand_id: str, campaign_data: dict) -> CampaignResult:
        """Deterministic mock: returns a pending campaign with a fixed ID."""
        return CampaignResult(
            campaign_id="mock-campaign-001",
            status="pending",
            rejection_reason=None,
        )

    def get_campaign(self, campaign_id: str) -> CampaignResult:
        """Deterministic mock: campaign is always approved."""
        return CampaignResult(
            campaign_id=campaign_id,
            status="approved",
            rejection_reason=None,
        )

    def get_verticals(self) -> list[str]:
        """Deterministic mock: returns a fixed list of verticals."""
        return [
            "ENERGY",
            "TECHNOLOGY",
            "FINANCE",
            "HEALTHCARE",
            "RETAIL",
            "CONSTRUCTION",
            "REAL_ESTATE",
            "EDUCATION",
            "HOSPITALITY",
            "TRANSPORTATION",
        ]

    def list_available_numbers(self, area_code: str, limit: int = 10) -> list[dict]:
        """Deterministic mock: returns fixed phone numbers for the area code."""
        numbers = []
        for i in range(min(limit, 5)):
            numbers.append(
                {
                    "phone_number": f"+1{area_code}555{i:04d}",
                    "locality": "Mock City",
                    "region": "MO",
                    "monthly_cost_millicents": 100000,
                }
            )
        return numbers

    def assign_number_to_campaign(self, phone_number: str, campaign_id: str) -> str:
        """Deterministic mock: returns the phone_number as assigned."""
        return phone_number


def get_sms_carrier() -> SmsCarrier:
    """
    Factory function — returns the configured SmsCarrier implementation.
    Call this everywhere; never instantiate a carrier class directly.

    Configuration via SMS_CARRIER env var:
        'telnyx' → TelnyxSmsCarrier (requires TELNYX_API_KEY + TELNYX_PUBLIC_KEY)
        'mock'   → MockSmsCarrier (default — no external API calls)
    """
    from core.config import settings

    carrier_name = getattr(settings, "SMS_CARRIER", "mock")
    if carrier_name == "telnyx":
        from services.telnyx_sms_carrier import TelnyxSmsCarrier  # lazy import

        return TelnyxSmsCarrier()
    return MockSmsCarrier()
