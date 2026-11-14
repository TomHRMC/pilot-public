"""
C-B8 / C-B9 — Telnyx 10DLC cost quoting adapter.

Reads carrier fees from the operator-maintained carrier_fee_schedule table.
NEVER hardcode fee amounts — carrier fees change (D25).

Q#1 Resolution: Telnyx has no public API for pre-transaction pricing rates.
Only post-transaction cost endpoints exist (Detail Records API, Usage Reports API).
Therefore, carrier fees are stored in carrier_fee_schedule and read at quote time.

C-B9: The carrier_fee_schedule table is now a temporal lookup with millicents
precision (1 millicent = $0.00001). The quoting adapter queries
WHERE effective_to IS NULL to get the current fee for each (fee_code, entity_type).

---
C-B9 Research: Telnyx Brand/Campaign Registration API Fields
=============================================================

Based on Telnyx API v2 documentation (https://developers.telnyx.com/api):
The 10DLC brand and campaign registration uses these endpoints and fields.

POST /v2/10dlc/brands — Brand Registration
------------------------------------------
Required fields for brand registration:
  - entity_type: "STANDARD" | "SOLE_PROPRIETOR"
  - legal_business_name: str (legal entity name)
  - dba: str | None (doing-business-as alias)
  - ein: str (Employer Identification Number, digits only)
  - phone_number: str (contact phone, E.164)
  - street: str (business HQ address line 1)
  - city: str
  - state: str (2-letter US state code)
  - postal_code: str (ZIP)
  - country: str (ISO 3166-1 alpha-2, e.g. "US")
  - email: str (contact email for brand)
  - stock_symbol: str | None (publicly traded companies only)
  - website: str | None (business website URL)
  - vertical: str (business category/use case)

POST /v2/10dlc/campaigns — Campaign Registration
-------------------------------------------------
Required fields for campaign registration:
  - brand_id: str (Telnyx brand ID from brand registration response)
  - campaign_name: str (human-readable campaign name)
  - use_case: str (e.g. "MARKETING", "CUSTOMER_CARE", "2FA", "ACCOUNT_NOTIFICATIONS")
  - description: str (campaign description)
  - sample_message_1: str (sample message content)
  - sample_message_2: str | None (second sample message)
  - message_flow: str (description of how end users opt in)
  - opt_in_keywords: list[str] (e.g. ["START", "YES"])
  - opt_out_keywords: list[str] (e.g. ["STOP", "CANCEL"])
  - help_keywords: list[str] (e.g. ["HELP"])
  - opt_in_message: str (message sent on opt-in)
  - opt_out_message: str (message sent on opt-out)
  - help_message: str (message sent on help keyword)
  - sub_use_cases: list[str] | None (sub-use-case codes)

GET /v2/10dlc/brands — List Brands
GET /v2/10dlc/campaigns — List Campaigns

These fields inform C-B9's brand registration form design.
The tenant_10dlc_profile table (DLC-1) already stores: legal_business_name,
dba_name, ein, hq_address_*, support_email, support_phone.
C-B9 added: website, stock_symbol, vertical fields.
"""

from sqlmodel import Session, select

from app.models.billing import CarrierFeeSchedule


def get_carrier_quote(db: Session, entity_type: str) -> dict:
    """
    Returns itemized setup + recurring costs for 10DLC provisioning.

    Reads current fee rows (effective_to IS NULL) from carrier_fee_schedule
    for the given entity_type. Classifies fees as setup (one-time) vs
    recurring (quarterly/monthly). Quarterly fees are converted to monthly
    equivalent for display (amount_millicents // 3). The actual Stripe
    Checkout charges the full quarterly amount.

    C-B9: All amounts are in millicents (1 millicent = $0.00001).

    Args:
        db: SQLAlchemy/SQLModel Session.
        entity_type: "standard" | "sole_proprietor".

    Returns:
        Dict with keys:
            - entity_type: str
            - setup_total_millicents: int (sum of one-time fees)
            - recurring_monthly_millicents: int (sum of recurring fees, monthly equivalent)
            - setup_items: list[dict] with fee_code, description, amount_millicents
            - recurring_items: list[dict] with fee_code, description, amount_millicents
    """
    # Exclude fee codes that are not part of the provisioning quote:
    # - surcharge_* : per-segment usage costs (billed post-usage, not provisioning)
    # - brand_vetting : optional external vetting (not standard provisioning)
    # - campaign_registration_tmobile : currently waived
    # - phone_number_assignment : per-assignment cost (separate from phone_number)
    quote_excluded_prefixes = ("surcharge_",)
    quote_excluded_codes = frozenset(
        {"brand_vetting", "campaign_registration_tmobile", "phone_number_assignment"}
    )

    def _is_quote_eligible(fee_code: str) -> bool:
        if fee_code in quote_excluded_codes:
            return False
        return not fee_code.startswith(quote_excluded_prefixes)

    fees = db.exec(
        select(CarrierFeeSchedule)
        .where(CarrierFeeSchedule.entity_type == entity_type)
        .where(CarrierFeeSchedule.effective_to.is_(None))
    ).all()

    setup_items: list[dict] = []
    recurring_items: list[dict] = []

    for fee in fees:
        if not _is_quote_eligible(fee.fee_code):
            continue
        item = {
            "fee_code": fee.fee_code,
            "description": fee.description,
            "amount_millicents": fee.amount_millicents,
        }
        if "quarterly" in fee.fee_code or "monthly" in fee.fee_code:
            # Convert quarterly to monthly equivalent for display
            if "quarterly" in fee.fee_code:
                item["amount_millicents"] = fee.amount_millicents // 3
            recurring_items.append(item)
        else:
            setup_items.append(item)

    return {
        "entity_type": entity_type,
        "setup_total_millicents": sum(i["amount_millicents"] for i in setup_items),
        "recurring_monthly_millicents": sum(
            i["amount_millicents"] for i in recurring_items
        ),
        "setup_items": setup_items,
        "recurring_items": recurring_items,
    }
