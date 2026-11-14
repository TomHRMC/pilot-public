"""
DLC-1 / C-B8 / C-B9 Pydantic schemas for 10DLC profile + provisioning endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class Tenant10DlcProfileRequest(BaseModel):
    legal_business_name: str
    dba_name: str | None = None
    ein: str | None = None
    hq_address_line1: str | None = None
    hq_address_line2: str | None = None
    hq_city: str | None = None
    hq_state: str | None = None
    hq_postal_code: str | None = None
    hq_country: str = "US"
    support_email: str | None = None
    support_phone: str | None = None
    # C-B9: Brand registration fields for Telnyx API submission
    website: str | None = None
    stock_symbol: str | None = None
    vertical: str | None = None

    @field_validator("legal_business_name")
    @classmethod
    def legal_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("legal_business_name cannot be blank")
        return v.strip()


class Tenant10DlcProfileResponse(BaseModel):
    tenant_id: uuid.UUID
    legal_business_name: str
    dba_name: str | None
    ein_masked: str | None  # "**-***XXXX" or None
    hq_address_line1: str | None
    hq_address_line2: str | None
    hq_city: str | None
    hq_state: str | None
    hq_postal_code: str | None
    hq_country: str
    support_email: str | None
    support_phone: str | None
    # C-B9: Brand registration fields
    website: str | None
    stock_symbol: str | None
    vertical: str | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# ─── C-B8 / C-B9: Carrier Quote Schemas (millicents) ─────────────────────────


class CarrierQuoteLineItem(BaseModel):
    """Single line item in a carrier cost quote. Amounts in millicents."""

    fee_code: str
    description: str
    amount_millicents: int


class CarrierQuoteResponse(BaseModel):
    """Itemized 10DLC carrier cost quote for a tenant's entity type.

    C-B9: All amounts are in millicents (1 millicent = $0.00001).
    """

    entity_type: str
    setup_total_millicents: int
    recurring_monthly_millicents: int
    setup_items: list[CarrierQuoteLineItem]
    recurring_items: list[CarrierQuoteLineItem]

    model_config = {"from_attributes": True}


# ─── C-B9: Provisioning Schemas ──────────────────────────────────────────────


class ProvisionRequest(BaseModel):
    """POST /messaging/provision — initiate 10DLC provisioning.

    Contains entity type selection + full brand registration data.
    The service layer upserts tenant_10dlc_profile and creates/updates
    tenant_messaging_registration with status='quoting'.
    """

    entity_type: str  # "standard" | "sole_proprietor"
    legal_business_name: str
    dba_name: str | None = None
    ein: str | None = None
    hq_address_line1: str | None = None
    hq_address_line2: str | None = None
    hq_city: str | None = None
    hq_state: str | None = None
    hq_postal_code: str | None = None
    hq_country: str = "US"
    support_email: str | None = None
    support_phone: str | None = None
    website: str | None = None
    stock_symbol: str | None = None
    vertical: str | None = None

    @field_validator("entity_type")
    @classmethod
    def entity_type_valid(cls, v: str) -> str:
        if v not in ("standard", "sole_proprietor"):
            raise ValueError("entity_type must be 'standard' or 'sole_proprietor'")
        return v

    @field_validator("legal_business_name")
    @classmethod
    def legal_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("legal_business_name cannot be blank")
        return v.strip()


class ProvisionResponse(BaseModel):
    """Response from POST /messaging/provision."""

    registration_id: uuid.UUID
    status: str
    entity_type: str
    quote: CarrierQuoteResponse

    model_config = {"from_attributes": True}


class CheckoutResponse(BaseModel):
    """Response from POST /messaging/checkout — Stripe Checkout URL."""

    checkout_url: str
    checkout_session_id: str


class OtpRequest(BaseModel):
    """POST /messaging/otp — submit sole-proprietor OTP code."""

    otp_code: str

    @field_validator("otp_code")
    @classmethod
    def otp_code_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("otp_code cannot be blank")
        return v.strip()


class OtpResponse(BaseModel):
    """Response from POST /messaging/otp."""

    status: str


class ProvisioningStatusResponse(BaseModel):
    """GET /messaging/status — current provisioning state."""

    registration_id: uuid.UUID
    status: str
    entity_type: str
    telnyx_brand_id: str | None
    telnyx_campaign_id: str | None
    telnyx_phone_number: str | None
    quoted_setup_cents: int | None
    quoted_monthly_cents: int | None
    otp_requested_at: datetime | None
    failure_reason: str | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class RetryResponse(BaseModel):
    """Response from POST /messaging/retry."""

    status: str
    quote: CarrierQuoteResponse


class VerticalsResponse(BaseModel):
    """GET /messaging/verticals — carrier business verticals enum."""

    verticals: list[str]


class AvailablePhoneNumber(BaseModel):
    """A single available phone number from the carrier."""

    phone_number: str
    locality: str | None
    region: str | None
    monthly_cost_millicents: int


class AvailableNumbersResponse(BaseModel):
    """GET /messaging/available-numbers — carrier available numbers."""

    numbers: list[AvailablePhoneNumber]


class AssignNumberRequest(BaseModel):
    """POST /messaging/assign-number — assign selected phone number."""

    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def phone_number_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("phone_number cannot be blank")
        return v.strip()


class AssignNumberResponse(BaseModel):
    """Response from POST /messaging/assign-number."""

    status: str
    telnyx_phone_number: str
