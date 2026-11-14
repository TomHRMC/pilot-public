"""
Signup Wizard Schemas — SIGNUP-C
================================
Pydantic v2 request/response schemas for the signup wizard endpoints.

Step 3 ("Stay Informed") was repurposed from a placeholder OTP screen into a
required-phone + unchecked-by-default SMS-consent flow (Pathway C — Pilot→owner
platform notifications). These schemas define the two new endpoints
(``/phone/consent``, ``/phone/send-optin``) and the changed step3 request shape.

Pydantic v2 only (Rule 22): ``model_config = ConfigDict(from_attributes=True)``,
``model_dump()``, ``model_validate()``.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PhoneConsentRequest(BaseModel):
    """Request body for ``POST /{tenant_id}/phone/consent``.

    Records the owner's mobile (required) + SMS-alerts consent (unchecked by
    default on the client) + the SHA-256 of the disclosure text shown.
    """

    phone_number: str = Field(
        ...,
        description="Owner mobile in E.164 format (e.g. +15125551234). Required.",
    )
    sms_consent: bool = Field(
        default=False,
        description=(
            "True if the owner checked the SMS-alerts checkbox. Unchecked by "
            "default — the reply-YES double-opt-in is the authoritative consent."
        ),
    )
    disclosure_hash: str = Field(
        ...,
        description="SHA-256 hex of the disclosure text shown at attestation.",
    )


class PhoneConsentResponse(BaseModel):
    """Response for ``POST /{tenant_id}/phone/consent``."""

    model_config = ConfigDict(from_attributes=True)

    user_endpoint_id: UUID
    verification_status: str = Field(
        default="pending",
        description="Always 'pending' — the reply-YES double-opt-in seals it.",
    )


class SendOptinRequest(BaseModel):
    """Request body for ``POST /{tenant_id}/phone/send-optin``."""

    user_endpoint_id: UUID


class SendOptinResponse(BaseModel):
    """Response for ``POST /{tenant_id}/phone/send-optin``."""

    status: str = Field(
        ...,
        description="'sent' on success, 'skipped' if preconditions not met.",
    )
