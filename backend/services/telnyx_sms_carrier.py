"""
Telnyx SMS Carrier Implementation — B11/A59 (v2 SDK rewrite: B21/FIND-173)
==========================================================================
Concrete SmsCarrier implementation for Telnyx.

SDK: telnyx v4.x (v2 API — client-based, not global module-level state)

Requires env vars:
    TELNYX_API_KEY              — Telnyx API key
    TELNYX_PUBLIC_KEY           — Telnyx webhook public key (for signature verification)
    TELNYX_MESSAGING_PROFILE_ID — Messaging profile ID for outbound send (optional)

Never import this module directly in routes or services.
Always call services.sms_carrier.get_sms_carrier() as the factory.

v1 → v2 SDK migration summary (B21/FIND-173):
  - Old: telnyx.api_key = ...; telnyx.Message.create(...)
  - New: client = telnyx.Telnyx(api_key=...); client.messages.send(...)
  - Old webhook: telnyx.Webhook.construct_event(payload, sig, public_key)
  - New webhook: client.webhooks.unwrap(payload_str, headers={...}) raises APIWebhookValidationError
  - Old response: message.id, getattr(message, "to", [{}])[0].get("status")
  - New response: msg.data.id, msg.data.to[0].status (Pydantic objects)
  - Old provision: telnyx.AvailablePhoneNumber.list() / telnyx.NumberOrder.create()
  - New provision: client.available_phone_numbers.list() / client.number_orders.create()
"""

import json
import logging
from uuid import UUID

from services.sms_carrier import (
    BrandResult,
    CampaignResult,
    InboundMessage,
    ProvisionedNumber,
    SendResult,
    SmsCarrier,
)

logger = logging.getLogger(__name__)


def _extract_failure_reasons(obj: object) -> str | None:
    """Extract a human-readable failure reason from a Telnyx brand/campaign response.

    The Telnyx v4.x SDK uses a 'failure_reasons' field (a list of dicts or
    strings) rather than a single 'rejection_reason' string. This helper
    normalizes it to a single string for the BrandResult/CampaignResult
    rejection_reason field.
    """
    reasons = getattr(obj, "failure_reasons", None)
    if not reasons:
        return None
    if isinstance(reasons, str):
        return reasons
    if isinstance(reasons, list):
        parts = []
        for r in reasons:
            if isinstance(r, str):
                parts.append(r)
            elif isinstance(r, dict):
                desc = r.get("description") or r.get("reason") or str(r)
                parts.append(str(desc))
        return "; ".join(parts) if parts else None
    return str(reasons)


class TelnyxSmsCarrier(SmsCarrier):
    """
    Telnyx carrier adapter — Telnyx v2 SDK (telnyx>=4.x).

    All external Telnyx SDK calls are confined to this class.
    The SDK is imported lazily to avoid hard dependency when SMS_CARRIER != 'telnyx'.
    """

    def __init__(self):
        import telnyx  # lazy import — only installed in telnyx-enabled environments

        from core.config import settings

        self._telnyx = telnyx
        self._client = telnyx.Telnyx(api_key=settings.TELNYX_API_KEY)
        self._messaging_profile_id = (
            getattr(settings, "TELNYX_MESSAGING_PROFILE_ID", "") or None
        )
        self._public_key = getattr(settings, "TELNYX_PUBLIC_KEY", "")

        # TELNYX-INT-1: 10DLC mock-object mode. When True, brand/campaign
        # creation uses Telnyx mock objects ($0 — no TCR fees, no SMS traffic).
        # See 10DLC playbook §14 for the 3-mode testing matrix.
        self._mock_10dlc: bool = bool(getattr(settings, "TELNYX_10DLC_MOCK", False))
        if self._mock_10dlc:
            logger.warning(
                "TelnyxSmsCarrier running with TELNYX_10DLC_MOCK=true — "
                "10DLC brands/campaigns will be created as MOCK objects "
                "(no TCR fees, no SMS traffic)"
            )

    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber:
        """
        Acquire a new phone number from Telnyx for this tenant.
        Searches available numbers in the given area_code, acquires the first result.
        """
        try:
            available = self._client.available_phone_numbers.list(
                filter={
                    "national_destination_code": area_code,
                    "features": ["sms"],
                    "limit": 1,
                }
            )
            if not available.data:
                raise ValueError(
                    f"No Telnyx numbers available for area code {area_code}"
                )

            phone_number = available.data[0].phone_number

            order = self._client.number_orders.create(
                phone_numbers=[{"phone_number": phone_number}]
            )
            provisioning_id = order.id

            logger.info(
                "Provisioned Telnyx number %s for tenant %s", phone_number, tenant_id
            )

            return ProvisionedNumber(
                phone_number=phone_number,
                carrier_provisioning_id=str(provisioning_id),
                monthly_fee_cents=100,
            )
        except Exception as exc:
            logger.error(
                "Telnyx provision_number failed for area_code=%s: %s", area_code, exc
            )
            raise

    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult:
        """
        Send an outbound SMS via Telnyx v2 SDK.
        Returns SendResult with carrier_message_id on success.
        """
        try:
            msg = self._client.messages.send(
                from_=from_number,
                to=to_number,
                text=body,
                messaging_profile_id=self._messaging_profile_id,
            )
            # v2: msg.data.id (str), msg.data.to is a list of recipient objects
            return SendResult(
                status="sent",
                carrier_message_id=str(msg.data.id),
                error_message=None,
                http_status=200,
                retryable=False,
            )
        except self._telnyx.RateLimitError as exc:
            logger.warning("Telnyx rate limit on send to=%s: %s", to_number, exc)
            return SendResult(
                status="failed",
                carrier_message_id=None,
                error_message=str(exc),
                http_status=429,
                retryable=True,
            )
        except self._telnyx.APIStatusError as exc:
            status_code = exc.status_code
            retryable = status_code in (429, 500, 502, 503, 504)
            logger.error("Telnyx send_message failed to=%s: %s", to_number, exc)
            return SendResult(
                status="failed",
                carrier_message_id=None,
                error_message=str(exc),
                http_status=status_code,
                retryable=retryable,
            )
        except Exception as exc:
            logger.error(
                "Telnyx send_message unexpected error to=%s: %s", to_number, exc
            )
            return SendResult(
                status="failed",
                carrier_message_id=None,
                error_message=str(exc),
                http_status=500,
                retryable=False,
            )

    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        """
        Verify Telnyx Ed25519 webhook signature directly (FIND-DLC-B4-FIX, 2026-07-27).

        Telnyx sends:
          telnyx-timestamp: Unix timestamp string
          telnyx-signature-ed25519: base64-encoded Ed25519 signature

        Signed payload = timestamp + "|" + raw_body (UTF-8)
        Public key = TELNYX_PUBLIC_KEY (base64-encoded Ed25519 public key from portal)

        The Telnyx v4 SDK's webhooks.unwrap() delegates to standardwebhooks which
        expects "v1,<base64>" signature format and "webhook-id" header — neither of
        which Telnyx actually sends. We do raw Ed25519 verification instead.
        """
        import base64

        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        try:
            sig_b64 = headers.get("telnyx-signature-ed25519", "")
            timestamp = headers.get("telnyx-timestamp", "")

            if not sig_b64 or not timestamp or not self._public_key:
                logger.warning(
                    "Telnyx webhook verify: missing header or public key "
                    "(sig_present=%s, ts_present=%s, key_configured=%s)",
                    bool(sig_b64),
                    bool(timestamp),
                    bool(self._public_key),
                )
                return False

            # Telnyx signed payload: timestamp + "|" + body
            signed_payload = (timestamp + "|" + payload.decode("utf-8")).encode("utf-8")
            signature_bytes = base64.b64decode(sig_b64)
            public_key_bytes = base64.b64decode(self._public_key)

            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature_bytes, signed_payload)
            return True

        except InvalidSignature:
            logger.warning("Telnyx webhook Ed25519 signature mismatch")
            return False
        except Exception as exc:
            logger.warning("Telnyx webhook verify error: %s", exc)
            return False

    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage:
        """
        Parse a Telnyx inbound SMS webhook payload into a normalized InboundMessage.
        Telnyx sends application/json with event data nested under data.payload.
        """
        data = json.loads(payload)
        event_payload = data.get("data", {}).get("payload", {})

        return InboundMessage(
            from_number=event_payload.get("from", {}).get("phone_number", ""),
            to_number=event_payload.get("to", [{}])[0].get("phone_number", ""),
            body=event_payload.get("text", ""),
            carrier_message_id=event_payload.get("id", ""),
            received_at=event_payload.get("received_at", ""),
        )

    def get_delivery_status(self, carrier_message_id: str) -> str:
        """
        Query Telnyx for delivery status of a previously sent message.
        v2: client.messages.retrieve(id) → msg.data.to is a list; each item has .status attribute.
        Returns 'delivered' | 'failed' | 'sent' | 'unknown'.
        """
        try:
            msg = self._client.messages.retrieve(carrier_message_id)
            # v2: msg.data.to[0].status is a Pydantic field (attribute, not .get())
            recipients = msg.data.to if msg.data and msg.data.to else []
            raw_status = recipients[0].status if recipients else "unknown"
            mapping = {
                "delivered": "delivered",
                "sending": "sent",
                "sent": "sent",
                "delivery_failed": "failed",
                "failed": "failed",
            }
            return mapping.get(str(raw_status), "unknown")
        except Exception as exc:
            logger.warning(
                "Telnyx get_delivery_status failed for %s: %s", carrier_message_id, exc
            )
            return "unknown"

    def release_number(self, phone_number: str) -> None:
        """
        Release a provisioned Telnyx number back to the pool.
        """
        try:
            numbers = self._client.phone_numbers.list(
                filter={"phone_numbers": [phone_number]}
            )
            if numbers.data:
                self._client.phone_numbers.delete(numbers.data[0].id)
                logger.info("Released Telnyx number %s", phone_number)
        except Exception as exc:
            logger.error("Telnyx release_number failed for %s: %s", phone_number, exc)
            raise

    # ── C-B9: 10DLC Brand/Campaign/Verticals/Numbers implementations ─────────

    # EntityType mapping: Pilot → Telnyx
    _ENTITY_TYPE_MAP = {
        "standard": "PRIVATE_PROFIT",
        "sole_proprietor": "INDIVIDUAL",
    }

    # Brand status mapping: Telnyx → Pilot BrandResult.status
    # Telnyx brand statuses: REGISTRATION_PENDING, OK, and rejection variants.
    _BRAND_STATUS_MAP = {
        "registration_pending": "pending",
        "ok": "verified",
        "verified": "verified",
        "rejected": "rejected",
        "suspended": "rejected",
    }

    # Campaign status mapping: Telnyx → Pilot CampaignResult.status
    _CAMPAIGN_STATUS_MAP = {
        "registration_pending": "pending",
        "pending": "pending",
        "ok": "approved",
        "approved": "approved",
        "active": "approved",
        "rejected": "rejected",
        "suspended": "rejected",
        "deactivated": "rejected",
        "tcr_failed": "rejected",
    }

    def create_brand(self, brand_data: dict) -> BrandResult:
        """POST /v2/10dlc/brand — submit brand registration to Telnyx.

        Maps Pilot entity_type to Telnyx entityType before calling the API.
        Uses the v2 SDK messaging_10dlc.brand resource (TELNYX-INT-1 fix:
        previous code used self._client.brand which does not exist in the
        telnyx v4.x SDK — the correct path is messaging_10dlc.brand).
        """
        try:
            entity_type = brand_data.get("entity_type", "standard")
            telnyx_entity_type = self._ENTITY_TYPE_MAP.get(
                entity_type, "PRIVATE_PROFIT"
            )

            payload = {
                "entity_type": telnyx_entity_type,
                "display_name": brand_data.get("legal_business_name", ""),
                "company_name": brand_data.get("legal_business_name", ""),
                "ein": brand_data.get("ein"),
                "phone": brand_data.get("support_phone", ""),
                "street": brand_data.get("hq_address_line1", ""),
                "city": brand_data.get("hq_city", ""),
                "state": brand_data.get("hq_state", ""),
                "postal_code": brand_data.get("hq_postal_code", ""),
                "country": brand_data.get("hq_country", "US"),
                "email": brand_data.get("support_email", ""),
                "stock_symbol": brand_data.get("stock_symbol"),
                "website": brand_data.get("website"),
                "vertical": brand_data.get("vertical", "ENERGY"),
            }

            # TELNYX-INT-1: mock-object mode — brands created as mock ($0, no
            # TCR fees). Campaigns under a mock brand are mock by inheritance
            # (Telnyx Help Center: "create a 10DLC campaign as normal").
            if self._mock_10dlc:
                payload["mock"] = True

            # Remove None values — Telnyx rejects nulls for optional fields
            payload = {k: v for k, v in payload.items() if v is not None}

            brand = self._client.messaging_10dlc.brand.create(**payload)
            brand_id = str(brand.brand_id)
            raw_status = str(getattr(brand, "status", "pending")).lower()
            status = self._BRAND_STATUS_MAP.get(raw_status, "pending")

            return BrandResult(
                brand_id=brand_id,
                status=status,
                rejection_reason=_extract_failure_reasons(brand),
            )
        except Exception as exc:
            logger.error("Telnyx create_brand failed: %s", exc)
            raise

    def get_brand(self, brand_id: str) -> BrandResult:
        """GET /v2/10dlc/brand/{brand_id} — poll brand registration status."""
        try:
            brand = self._client.messaging_10dlc.brand.retrieve(brand_id)
            raw_status = str(getattr(brand, "status", "pending")).lower()
            status = self._BRAND_STATUS_MAP.get(raw_status, "pending")

            return BrandResult(
                brand_id=brand_id,
                status=status,
                rejection_reason=_extract_failure_reasons(brand),
            )
        except Exception as exc:
            logger.error("Telnyx get_brand failed for %s: %s", brand_id, exc)
            raise

    def create_campaign(self, brand_id: str, campaign_data: dict) -> CampaignResult:
        """POST /v2/10dlc/campaign_builder/submit — submit campaign to Telnyx.

        TELNYX-INT-1 fix: the v4.x SDK uses campaign_builder.submit (not
        campaign.create) for campaign creation. Field names differ from the
        old code: usecase (not use_case), sample1/sample2 (not
        sample_message_1/2), keywords as comma-joined strings (not lists).
        Campaigns under a mock brand are mock by inheritance — no explicit
        mock flag needed (verified against Telnyx Help Center docs).
        """
        try:
            # Keywords: SDK expects comma-joined strings, not lists
            opt_in_kw = campaign_data.get("opt_in_keywords", ["START", "YES"])
            opt_out_kw = campaign_data.get(
                "opt_out_keywords", ["STOP", "CANCEL", "UNSUBSCRIBE"]
            )
            help_kw = campaign_data.get("help_keywords", ["HELP"])

            payload = {
                "brand_id": brand_id,
                "usecase": campaign_data.get("use_case", "MIXED"),
                "description": campaign_data.get("description", ""),
                "sample1": campaign_data.get("sample_message_1", ""),
                "message_flow": campaign_data.get("message_flow", ""),
                "optin_keywords": ",".join(opt_in_kw)
                if isinstance(opt_in_kw, list)
                else opt_in_kw,
                "optout_keywords": ",".join(opt_out_kw)
                if isinstance(opt_out_kw, list)
                else opt_out_kw,
                "help_keywords": ",".join(help_kw)
                if isinstance(help_kw, list)
                else help_kw,
                "optin_message": campaign_data.get("opt_in_message", ""),
                "optout_message": campaign_data.get("opt_out_message", ""),
                "help_message": campaign_data.get("help_message", ""),
            }

            # Optional sample2
            sample2 = campaign_data.get("sample_message_2")
            if sample2:
                payload["sample2"] = sample2

            # Optional sub_usecases
            sub_usecases = campaign_data.get("sub_use_cases")
            if sub_usecases:
                payload["sub_usecases"] = sub_usecases

            campaign = self._client.messaging_10dlc.campaign_builder.submit(**payload)
            campaign_id = str(campaign.campaign_id)
            raw_status = str(getattr(campaign, "status", "pending")).lower()
            status = self._CAMPAIGN_STATUS_MAP.get(raw_status, "pending")

            return CampaignResult(
                campaign_id=campaign_id,
                status=status,
                rejection_reason=_extract_failure_reasons(campaign),
            )
        except Exception as exc:
            logger.error("Telnyx create_campaign failed: %s", exc)
            raise

    def get_campaign(self, campaign_id: str) -> CampaignResult:
        """GET /v2/10dlc/campaign/{campaign_id} — poll campaign registration status."""
        try:
            campaign = self._client.messaging_10dlc.campaign.retrieve(campaign_id)
            raw_status = str(getattr(campaign, "status", "pending")).lower()
            status = self._CAMPAIGN_STATUS_MAP.get(raw_status, "pending")

            return CampaignResult(
                campaign_id=campaign_id,
                status=status,
                rejection_reason=_extract_failure_reasons(campaign),
            )
        except Exception as exc:
            logger.error("Telnyx get_campaign failed for %s: %s", campaign_id, exc)
            raise

    def get_verticals(self) -> list[str]:
        """GET /10dlc/enum/vertical — returns valid business verticals.

        TELNYX-INT-1 fix: uses messaging_10dlc.get_enum('vertical') instead
        of the non-existent self._client.verticals.list(). The response is a
        Union[List[str], EnumPaginatedResponse, ...] — handle both shapes.
        """
        try:
            result = self._client.messaging_10dlc.get_enum("vertical")

            # The response can be a list of strings, an EnumPaginatedResponse,
            # a list of dicts, or a dict. Handle all shapes defensively.
            if isinstance(result, list):
                verticals = []
                for item in result:
                    if isinstance(item, str):
                        verticals.append(item)
                    elif isinstance(item, dict):
                        name = item.get("name") or item.get("value")
                        if name:
                            verticals.append(str(name))
                return verticals
            elif hasattr(result, "records"):
                # EnumPaginatedResponse
                verticals = []
                for item in result.records:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("value")
                        if name:
                            verticals.append(str(name))
                    elif isinstance(item, str):
                        verticals.append(item)
                return verticals
            elif isinstance(result, dict):
                # The vertical enum returns a dict keyed by vertical code
                # (e.g., {"ENERGY": {"industryId": ...}, "RETAIL": {...}}).
                # The keys ARE the vertical enum values.
                # First check for list-valued keys (other enum endpoints)
                for key in ("verticals", "records", "data"):
                    if key in result and isinstance(result[key], list):
                        return [
                            str(v) if isinstance(v, str) else str(v.get("name", v))
                            for v in result[key]
                        ]
                # Otherwise, the dict keys are the enum values
                return [str(k) for k in result]
            return []
        except Exception as exc:
            logger.error("Telnyx get_verticals failed: %s", exc)
            raise

    def list_available_numbers(self, area_code: str, limit: int = 10) -> list[dict]:
        """GET /v2/available_phone_numbers — returns available numbers for area_code.

        Maps Telnyx response to {phone_number, locality, region, monthly_cost_millicents}.
        """
        try:
            available = self._client.available_phone_numbers.list(
                filter={
                    "national_destination_code": area_code,
                    "features": ["sms"],
                    "limit": limit,
                }
            )
            numbers = []
            if available.data:
                for item in available.data:
                    # monthly_cost_millicents: Telnyx doesn't expose per-number monthly cost
                    # in the available_phone_numbers endpoint. Use the carrier_fee_schedule
                    # phone_number fee (100000 millicents = $1.00/month) as the default.
                    numbers.append(
                        {
                            "phone_number": str(item.phone_number),
                            "locality": getattr(item, "locality", None),
                            "region": getattr(item, "region", None),
                            "monthly_cost_millicents": 100000,
                        }
                    )
            return numbers
        except Exception as exc:
            logger.error(
                "Telnyx list_available_numbers failed for area_code=%s: %s",
                area_code,
                exc,
            )
            raise

    def assign_number_to_campaign(self, phone_number: str, campaign_id: str) -> str:
        """POST /10dlc/phone_number_campaigns — assigns number to campaign ($0.03).

        TELNYX-INT-1 fix: uses messaging_10dlc.phone_number_campaigns (not
        the non-existent self._client.phone_number_campaign).
        Returns the assigned phone_number.
        """
        try:
            self._client.messaging_10dlc.phone_number_campaigns.create(
                phone_number=phone_number,
                campaign_id=campaign_id,
            )
            logger.info(
                "Assigned Telnyx number %s to campaign %s", phone_number, campaign_id
            )
            return phone_number
        except Exception as exc:
            logger.error(
                "Telnyx assign_number_to_campaign failed for %s/%s: %s",
                phone_number,
                campaign_id,
                exc,
            )
            raise
