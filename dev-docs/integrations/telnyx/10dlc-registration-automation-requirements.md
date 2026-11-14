# A2P 10DLC for Pilot: Process Overview & Registration Automation

## 1. Overview of the 10DLC Process for an ISV

**What 10DLC is.** 10DLC is the mandatory US compliance framework for application-to-person (A2P) SMS/MMS sent from standard 10-digit local numbers. Registration is a two-object hierarchy — a **Brand** (the legal business identity) and one or more **Campaigns** (use case + opt-in details) under that brand — with **phone numbers** assigned to an approved campaign before they can send reliable traffic. You don't register with The Campaign Registry (TCR) directly; registration is initiated through a Campaign Service Provider (Telnyx, in our case) that has an established relationship with the registry and is accountable to TCR for submission accuracy.

**The three roles that determine whose info gets registered.** In a SaaS/ISV setup there are three parties: the **Provider** (Pilot — the app supplying SMS capability), the **Customer** (the trades business — electrician, plumber, HVAC), and the **End User** (the homeowner receiving the text). The end user believes they're hearing from "Mike's Electric," not from Pilot. So **the brand and campaign are registered under the trades business's identity, not Pilot's** — messages appear to come from the contractor, and the Pilot name never appears in message content. This isn't a preference; it's what keeps the registration compliant and attributable to the right sender.

**We are an ISV, which makes this a per-tenant obligation.** Telnyx classifies a SaaS product that sells messaging services to other business entities as an Independent Service Vendor (ISV). Registration happens **per tenant**, not once for the platform. For every end-user we resell to, we create a separate brand, then a campaign to assign a campaign ID to that tenant's number — and phone numbers must never be shared across brands, or we violate 10DLC terms and risk fines and blocking. Our "one number per tenant, lazy-provisioned at first use" design is exactly what keeps traffic cleanly separated per brand.

**Structural decision — per-tenant brand + campaign (locked).** Each contractor is registered as their own brand + campaign with a dedicated number, so customers see the contractor's identity and one tenant's spam complaints can't poison another's deliverability. The shared/partner campaign alternative would put every tenant under Pilot's single identity and reputation — wrong for field service. **Decision: per-tenant brand + campaign.**

**The only entity branch that matters is EIN vs. no-EIN.** This affects the registration path and form fields, **not** the fees a tenant actually pays:

- **Standard brand (has an EIN):** a valid EIN is mandatory — SSNs are not accepted.
- **Sole Proprietor (no EIN):** the path for the many 1–5-person shops operating under their own name. Designed for a single individual without an EIN needing low-volume messaging, typically up to 1,000 messages/day, limited to 1 campaign and 1 number — which maps perfectly to our per-tenant model.

**Vetting is optional and irrelevant at our volumes.** External brand vetting (~$40) only raises the throughput ceiling; it is never a gate to sending. An unvetted brand and campaign still get approved and send at default throughput (roughly 75 message parts/min to AT&T and ~2,000 messages/day to T-Mobile). Our tenants send ~100–500 segments/month — a rounding error against even the unvetted default. **No Pilot tenant needs vetting**, standard or sole proprietor alike. The separate carrier rate-increase request that vetting enables is therefore not on our critical path.

**Opt-in / consent is the real vetting bar.** Each tenant must have a compliant opt-in flow where their client explicitly consents to SMS. Opt-ins must be explicit, direct, and specific to text messaging — not implied or buried in terms. A compliant disclosure must identify the trades business by name, describe message types, disclose frequency, include "Message and data rates may apply," and provide STOP opt-out instructions. Natural capture point: when a customer's number is entered on a quote or booking, with a consent checkbox.

**Campaign registration form — fields to collect/generate per tenant:** campaign description and purpose; vertical (electrical / plumbing / HVAC); publicly accessible Terms & Conditions URL; publicly accessible Privacy Policy URL; opt-in workflow description; opt-in screenshot/mockup; HELP response (≥20 chars); STOP response (≥20 chars); at least one sample message reflecting real traffic (must include brand name + "Reply STOP").

**Timelines.** Brand approval is typically fast — around 1–3 business days; Sole Proprietor campaigns are usually approved in 3–7 business days. Some providers quote conservative worst-case windows (campaign "up to 4 weeks," number assignment "up to 10 days"). Safe planning assumption: **SMS is not live on a tenant's day one; onboarding must gate around a multi-day approval window.**

### Fees

All of these are **TCR/carrier pass-through fees** — identical regardless of provider (AWS End User Messaging or Telnyx). Telnyx passes them through at cost with no markup.

- **Brand registration** — *~$4 one-time per tenant.* TCR fee to register the contractor's business identity. Same for standard and Sole Proprietor brands. Non-recurring, per brand; a re-verify is charged again if the initial info is insufficient.
- **Campaign registration** — *~$15 one-time per campaign.* TCR campaign vetting fee per new campaign — and it's re-charged on every rejected/resubmitted campaign, so clean intake data directly saves money.
- **Campaign monthly** — *$1.50–$10/mo per campaign, by campaign type.* Billed monthly on a 3-month minimum term. At our volumes the low-volume types are the right fit: **~$2/mo (Sole Proprietor)** or **~$1.50/mo (Low Volume Mixed)**. The $10/mo standard tier only applies if a tenant ever needs high throughput — not expected.
- **Phone number monthly** — *~$1/number/mo.* Lease on the tenant's dedicated number.
- **Per-message carrier surcharge** — *~$0.003/segment.* Roughly $0.003 on AT&T and T-Mobile and $0.0031 on Verizon per registered segment — and unregistered T-Mobile traffic jumps to $0.012, 4x the registered rate, which is why registration pays for itself immediately.
- **External brand vetting (OPTIONAL — excluded from our path)** — *~$40 one-time.* Charged only if requested; raises throughput ceiling only. Not needed at Pilot volumes.
- **T-Mobile campaign fee (currently waived)** — *$50 one-time.* Historically a T-Mobile registration charge; currently waived. Budget as a contingency in case it returns.

| Billing item | Price | Description / notes |
|---|---|---|
| Brand registration | ~$4, one-time | Per tenant brand. Same for standard (EIN) and Sole Proprietor. Re-verify re-charges if info insufficient. |
| Campaign registration | ~$15, one-time | Per campaign. **Re-charged on every rejection/resubmission** — validate intake data hard. |
| Campaign monthly fee | $1.50–$10 / mo | By campaign type; 3-month minimum term. Pilot fit: ~$2 (Sole Prop) or ~$1.50 (Low Volume Mixed). $10 = high-throughput standard tier (not expected). |
| Phone number | ~$1 / number / mo | Dedicated number lease, one per tenant brand. |
| Per-message carrier surcharge | ~$0.003 / segment | AT&T/T-Mobile ~$0.003, Verizon ~$0.0031. Unregistered T-Mobile = $0.012 (4×). |
| External vetting *(optional)* | ~$40, one-time | Throughput ceiling only. **Not on Pilot's path** at our volumes. |
| T-Mobile campaign fee | $50, one-time *(waived)* | Currently waived; hold as contingency. |

**Per-tenant cost summary (typical Pilot tenant, any entity type):** **~$19 one-time** ($4 brand + $15 campaign) + **~$3/mo** (~$2 campaign + ~$1 number) + ~$0.003/segment. Trivially absorbable against a $49/mo plan, but it's a **per-tenant** cost that belongs in COGS. T-Mobile raised pass-through fees in January 2026 and carriers refresh rules mid-year — revisit quarterly.

---

## 2. Approach & Requirements for Automating Registration

**Carrier decision (flag).** The AWS support answer describes **AWS End User Messaging SMS**; our shipped path is **Telnyx** behind the `SmsCarrier` adapter. Everything below is carrier-agnostic and sits behind that adapter, so it applies either way. Underneath is a real decision: stay on Telnyx (shipped, no-markup pass-through, strong ISV docs) or consolidate onto AWS End User Messaging to match the all-AWS stack (Cognito, RDS, Lambda, EventBridge, S3) for single-vendor billing and native EventBridge delivery events. **Recommendation: keep Telnyx for MVP; treat AWS as a genuine consolidation candidate to evaluate before Stage 3 scale; keep the automation carrier-agnostic so the swap stays a one-class change.**

### The five architectural models (and our recommendation)

They split across two axes — **who owns registration** (Models 1–4) and **how message content is controlled** (Model 5) — so the answer is a *combination*, not a single pick:

- **Model 1 — Customer-Connected Account:** each tenant connects their own carrier account and self-registers. **Reject** — our ICP runs the business from the truck.
- **Model 2 — Provider-Managed Manual:** Pilot owns the account and manually captures each tenant's registration info. **Use for beta only** — you're already doing a personal Teams onboarding call with each of the planned 20–30 Founding Testers; capture the 10DLC info there. Doesn't scale past Stage 2.
- **Model 3 — Provider-Built Registration Workflow:** a guided in-app form collects tenant info and submits it programmatically. **The build target** (state machine below).
- **Model 4 — Fully Automated Provider Registration:** Model 3 plus Pilot-hosted, compliant Terms & Privacy pages so tenants need nothing of their own. **The scale end-state.**
- **Model 5 — Pre-Approved Template Model:** Pilot manages compliance centrally with a library of pre-approved templates; tenants personalize only specific fields. **Already our design** — the PRD's always-preview-before-send rule and template-only tech-initiated outreach *is* Model 5.

**Recommendation: adopt Model 4 for registration + Model 5 for content, phased in through Model 2 during beta.** Run manual (Model 2) capture on the onboarding calls for the first 20–30 testers → build the guided workflow (Model 3) approaching Stage 2 (~10 paying customers) → finish hosted-compliance-page automation (Model 4) before Stage 3 (100 customers). Keep the Model 5 template/preview layer throughout — it's what makes campaign approval predictable and blocks non-compliant free-form blasts.

### Onboarding state machine

1. **Identity capture** — collect tenant identity (fields below).
2. **Branch on EIN** — EIN → standard brand; no EIN → Sole Proprietor path.
3. **Create brand** via API.
4. **Create campaign** via API (low-volume use case) with message-flow/opt-in text and sample messages.
5. **Listen on 10DLC event webhooks** for brand-vetted and campaign-approved status; persist state on the tenant record.
6. **Provision + assign number** to the approved campaign on first SMS use (existing lazy-provisioning), one number per brand.
7. **Enforce consent + STOP** on all traffic.

*(No throughput/rate-increase step — default throughput exceeds our needs, so vetting and rate requests stay out of the standard flow.)*

### UI requirements

- **Identity intake form** — legal business name, business address, EIN (optional; absence routes to Sole Proprietor), website URL (or election to use a Pilot-hosted page), vertical, and a plain-language opt-in description. For Sole Proprietor, the legal name must match government ID exactly — accuracy is critical for approval, so validate hard here (bad data re-incurs the $15 campaign fee on resubmission).
- **Activation-status gate** — a persistent "SMS activation pending / approved / rejected" state on the tenant dashboard driven by webhook status, so a new contractor understands texts aren't live during the approval window, with next-step guidance on rejection.
- **Opt-in consent capture** in the customer-add / quote flow — an SMS consent checkbox at number capture, feeding the per-record opt-in tracking the PRD specifies and generating the opt-in screenshot/mockup the campaign form requires.
- **HELP/STOP response config** — sensible per-tenant defaults (≥20 chars each) so we never submit a non-compliant campaign.

### Website / opt-in hosting options

The campaign needs public T&C and Privacy Policy URLs. Most of our ICP won't have compliant pages, so:

- **Recommended (Model 4): Pilot-hosted per-tenant compliance pages** — Pilot-generated pages carrying the tenant's business name plus platform-standard SMS Terms and Privacy Policy, describing the opt-in flow. Removes tenant friction and guarantees a consistent, compliant URL for every submission.
- **Fallback: tenant's own website** — accepted when it already includes compliant privacy/terms language.

**Decision to lock:** default to Pilot-hosted compliance pages; tenant's own site as override.

### API integration

- **Brand + campaign creation** against the carrier's 10DLC API, branched by entity type.
- **Webhook consumer** for brand/campaign lifecycle events to drive the status state machine (no polling).
- **Number assignment** to the approved campaign on first use.
- **Inbound STOP webhook handler** — already in the PRD; sets the opt-out flag/timestamp on the customer record. Hard TCPA/carrier requirement, audited, non-optional.
- **Quota monitoring** — if many tenants live under one account, watch account-level limits (registrations, brands, numbers per campaign) and plan increases ahead of the customer curve.

**Implementation note:** exact endpoint names, required fields, and Sole Proprietor OTP-verification quirks change over time and differ between Telnyx and AWS End User Messaging — pull the live schema from the chosen provider's developer docs at build time rather than coding against a snapshot.

---

## 3. Telnyx 10DLC API Reference

**Source**: Telnyx's OpenAPI 3.0 spec for the 10DLC Passthrough API (a local copy was used during the build; it is not redistributed in this snapshot — see the developer docs below).
**Developer docs**: https://developers.telnyx.com/docs/messaging/10dlc/quickstart
**Support page (fees)**: https://support.telnyx.com/en/articles/5634625-10dlc-fees-and-charges

### 3.1 API Basics

- **Base URL**: `https://api.telnyx.com/10dlc`
- **Auth**: `Authorization: Bearer YOUR_API_KEY` header (API key from Telnyx Portal → API Keys tab)
- **Content-Type**: `application/json`

```sh
# Example: list all brands
curl --location --request GET 'https://api.telnyx.com/10dlc/brand' \
  --header 'Authorization: Bearer YOUR_API_KEY_GOES_HERE' \
  --data-raw ''
```

### 3.2 The 10DLC Workflow (4 Steps)

1. **Create a brand** — `POST /brand` (entails $4 one-time charge)
2. **Apply for brand vetting** (optional — not needed at Pilot volumes)
3. **Create a campaign** — `POST /campaign` (associated with the brand; first 3 months charged upfront)
4. **Assign a phone number** — `POST /phone_number_campaign` ($0.03 one-time per assignment)

### 3.3 Brand Schema (`POST /brand`)

**Required fields**:

| Field | Type | Description | Example |
|---|---|---|---|
| `entityType` | enum | `PRIVATE_PROFIT` (standard/EIN), `INDIVIDUAL` (sole prop), `PUBLIC_PROFIT`, `NON_PROFIT` | `"PRIVATE_PROFIT"` |
| `displayName` | string (max 100) | Display or marketing name of the brand | `"Acme Electric"` |
| `country` | string (max 2) | ISO2 country code | `"US"` |
| `email` | string (max 100) | Valid email of brand support contact | `"owner@acme.example.com"` |
| `brandRelationship` | enum | `BASIC_ACCOUNT`, `SMALL_ACCOUNT`, `MEDIUM_ACCOUNT`, `LARGE_ACCOUNT`, `KEY_ACCOUNT` | `"SMALL_ACCOUNT"` |
| `vertical` | string (max 50) | Business/industry segment — use `/enum/vertical` to get valid values | `"ENERGY"` |

**Optional fields**:

| Field | Type | Description |
|---|---|---|
| `companyName` | string (max 100) | Legal company name (required for non-profit/private/public) |
| `ein` | string (max 20) | Government assigned corporate tax ID (9 digits in U.S.) |
| `phone` | string (max 20) | Valid phone number in E.164 format |
| `street` | string (max 100) | Street number and name |
| `city` | string (max 100) | City name |
| `state` | string (max 20) | 2-letter US state code |
| `postalCode` | string (max 10) | 5-digit ZIP for US |
| `stockSymbol` | string (max 10) | Stock symbol (required for public company) |
| `stockExchange` | enum | Stock exchange (required for public company) — use `/enum/stockExchange` |
| `website` | string (max 100) | Brand website URL |
| `altBusinessId` | string (max 50) | Alternate business identifier (DUNS, LEI, GIIN) |
| `altBusinessIdType` | enum | Type of alt business ID — use `/enum/altBusinessIdType` |
| `ipAddress` | string (max 50) | IP address of browser requesting brand creation |
| `universalEin` | string | Universal EIN (read-only, returned by registry) |

**EntityType mapping** (Pilot → Telnyx):

| Pilot `entity_type` | Telnyx `entityType` | Description |
|---|---|---|
| `standard` | `PRIVATE_PROFIT` | Has an EIN — standard brand registration path |
| `sole_proprietor` | `INDIVIDUAL` | No EIN — sole proprietor path with OTP verification |

### 3.4 Campaign Schema (`POST /campaign`)

**Required fields**:

| Field | Type | Description |
|---|---|---|
| `brandId` | string (max 8) | Alphanumeric brand ID from brand creation response |
| `vertical` | string (max 20) | Business/industry segment — use `/enum/vertical` |
| `usecase` | string (max 20) | Campaign use case — use `/enum/usecase` for valid values |
| `description` | string (max 4096) | Summary description of the campaign |

**Optional fields**:

| Field | Type | Description | Default |
|---|---|---|---|
| `sample1`–`sample5` | string (max 255) | Message samples (some tiers require 1+) | — |
| `messageFlow` | string (max 2048) | Message flow description (how users opt in) | — |
| `helpMessage` | string (max 255) | Help message response | — |
| `subscriberOptin` | boolean | Does campaign require opt-in before sending? | `false` |
| `subscriberOptout` | boolean | Does campaign support opt-out keywords? | `false` |
| `subscriberHelp` | boolean | Does campaign respond to help keywords? | `false` |
| `embeddedLink` | boolean | Does message include URL links? | `false` |
| `embeddedPhone` | boolean | Does message include phone numbers? | `false` |
| `affiliateMarketing` | boolean | Is content controlled by affiliate marketing? | — |
| `numberPool` | boolean | Does campaign use a pool of phone numbers? | `false` |
| `ageGated` | boolean | Age-gated content? | — |
| `directLending` | boolean | Direct lending content? | — |
| `autoRenewal` | boolean | Campaign subscription auto-renewal? | — |
| `subUsecases` | array[string] | Sub-use-case codes — use `/enum/usecase?validSubUsecase=true` | — |

### 3.5 Enum Endpoints (with curl commands)

All enum endpoints are `GET` requests under `/enum/`. These return the valid values for dropdowns and form validation. **Call these at build time to populate form options — do not hardcode enum values.**

```sh
# ── Entity types (PRIVATE_PROFIT, INDIVIDUAL, PUBLIC_PROFIT, NON_PROFIT) ──
PILOT_TELNYX_API_KEY="KEY_REDACTED_SET_IN_ENV"
curl -X GET 'https://api.telnyx.com/10dlc/enum/entityType' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Business verticals (industry segments — for brand + campaign vertical field) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/vertical' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Campaign use cases (MARKETING, CUSTOMER_CARE, 2FA, ACCOUNT_NOTIFICATIONS, etc.) ──
#    Pass validSubUsecase=true to also get valid sub-use-cases
curl -X GET 'https://api.telnyx.com/10dlc/enum/usecase?validSubUsecase=true' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Brand relationship to CSP (BASIC_ACCOUNT, SMALL_ACCOUNT, MEDIUM_ACCOUNT, etc.) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/brandRelationship' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Alternative business ID types (DUNS, GIIN, LEI) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/altBusinessIdType' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Stock exchanges (for public company brands) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/stockExchange' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── TCR approved public companies (searchable by displayName, symbol, exchange, country) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/approvedPublicCompany?displayName=Acme&country=US' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Campaign status types ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/campaignStatus' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Mobile Network Operators (AT&T, T-Mobile, Verizon, etc.) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/mno' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── MNO operation status (for polling brand/campaign approval per carrier) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/operationStatus' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── External vetting providers (optional vetting path) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/extVettingProvider' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Vetting classes ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/vettingClass' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Connectivity partners ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/cnp' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── DCAs (Direct Connection Agreements) ──
curl -X GET 'https://api.telnyx.com/10dlc/enum/dca' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"
```

### 3.6 Brand + Campaign CRUD Endpoints

```sh
# ── Create a brand ($4 one-time charge) ──
PILOT_TELNYX_API_KEY="KEY_REDACTED_SET_IN_ENV"
curl -X POST 'https://api.telnyx.com/10dlc/brand' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY" \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "entityType": "PRIVATE_PROFIT",
    "displayName": "Acme Electric LLC",
    "companyName": "Acme Electric LLC",
    "ein": "123456789",
    "phone": "+13025551234",
    "street": "123 Main St",
    "city": "Wilmington",
    "state": "DE",
    "postalCode": "19801",
    "country": "US",
    "email": "owner@acme.example.com",
    "website": "https://acme.example.com",
    "brandRelationship": "SMALL_ACCOUNT",
    "vertical": "ENERGY"
  }'

# ── List all brands (filter by displayName, entityType, state) ──
curl -X GET 'https://api.telnyx.com/10dlc/brand?entityType=PRIVATE_PROFIT' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Get a specific brand by brandId ──
curl -X GET 'https://api.telnyx.com/10dlc/brand/BXXXXXX' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Create a campaign (first 3 months charged upfront) ──
curl -X POST 'https://api.telnyx.com/10dlc/campaign' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY" \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "brandId": "BXXXXXX",
    "vertical": "ENERGY",
    "usecase": "CUSTOMER_CARE",
    "description": "Customer care and appointment notifications for Acme Electric LLC.",
    "sample1": "Hi, this is Acme Electric confirming your appointment tomorrow between 8-10 AM. Reply STOP to opt out.",
    "messageFlow": "Customer opts in by providing their phone number for appointment notifications and billing communications.",
    "subscriberOptin": true,
    "subscriberOptout": true,
    "subscriberHelp": true,
    "helpMessage": "Acme Electric: Reply STOP to opt out. Msg rates may apply. Call 302-555-1234 for help.",
    "embeddedLink": true,
    "embeddedPhone": false
  }'

# ── Get a specific campaign by campaignId ──
curl -X GET 'https://api.telnyx.com/10dlc/campaign/CXXXXXX' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY"

# ── Assign a phone number to a campaign ($0.03 one-time) ──
curl -X POST 'https://api.telnyx.com/10dlc/phone_number_campaign' \
  --header "Authorization: Bearer $PILOT_TELNYX_API_KEY" \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "campaignId": "CXXXXXX",
    "phoneNumber": "+13025559999"
  }'
```

### 3.7 Sole Proprietor OTP Procedure

**Q#2 Resolution (2026-08-02)**: OTP is delivered via **SMS** to the mobile phone number associated with the brand — **not via email**. The spec §5.3 description of "email to Telnyx desk" for OTP delivery is incorrect.

**Current understanding** (must verify against Telnyx live help center before building C-B9):

1. On entering `awaiting_otp` state, the brand registration is submitted with `entityType: INDIVIDUAL`.
2. Telnyx/TCR sends an OTP PIN via SMS to the brand's mobile phone number (`phone` field on the brand).
3. The tenant sees an in-app PIN entry panel: *"The carrier is texting a PIN to {phone}. Enter it here."*
4. The tenant enters the PIN in the app → backend relays it to Telnyx → on confirmation, transition to `brand_verified`.
5. **24-hour window**: if the PIN is not verified within 24 hours, the brand registration must be restarted.
6. **Alert Tom at T+18h** if still `awaiting_otp` — manual intervention path.
7. On expiry (T+24h), transition back to `quoting` **without re-charging** — the $4 brand fee is consumed but re-registration under the same Stripe payment is the correct customer treatment.

**⚠️ Verification required**: The exact API endpoint for submitting the OTP and the full request/relay procedure must be confirmed against the Telnyx live help center (https://support.telnyx.com) or developer docs (https://developers.telnyx.com/docs/messaging/10dlc/quickstart) before building C-B9. The Telnyx 10DLC API spec (local copy, not redistributed) does not contain an explicit OTP submission endpoint — the OTP flow may be handled outside the 10DLC API (via Telnyx support desk or a separate API).

### 3.8 10DLC Costs (from API JSON description + support page)

| Cost item | Amount | Type | Notes |
|---|---|---|---|
| Brand registration | $4.00 | One-time | Per tenant brand. Same for standard and sole prop. Non-refundable. |
| Brand vetting (optional) | $40.00 | One-time | Raises throughput ceiling only. **Not on Pilot's path** at our volumes. |
| Campaign registration (T-Mobile) | $50.00 | One-time | Currently waived. Hold as contingency. |
| Campaign creation — Charity | $15.00 | Upfront (3 months) | Then $5/month after. Not our use case. |
| Campaign creation — Low Mixed Volume | $6.00 | Upfront (3 months) | Then $2/month after. **Pilot fit for sole prop.** |
| Campaign creation — Any Other | $30.00 | Upfront (3 months) | Then $10/month after. **Pilot fit for standard.** |
| Phone number assignment | $0.03 | One-time | Per number-to-campaign assignment. |
| Phone number monthly | ~$1.00 | Monthly | Per number lease. |
| Per-message surcharge (AT&T) | ~$0.003 | Per segment | Registered traffic. |
| Per-message surcharge (T-Mobile) | ~$0.003 | Per segment | Registered traffic. Unregistered = $0.012 (4×). |
| Per-message surcharge (Verizon) | ~$0.0031 | Per segment | Registered traffic. |

**Per-tenant cost summary (typical Pilot tenant)**:
- **Standard (EIN)**: ~$34 one-time ($4 brand + $30 campaign) + ~$11/mo ($10 campaign + $1 number)
- **Sole Proprietor**: ~$10 one-time ($4 brand + $6 campaign) + ~$3/mo ($2 campaign + $1 number)
- **Per-message**: ~$0.003/segment (absorbed into $0.05/segment overage rate)

---

## 4. TCR Fee Lookup Table Design Proposal

### 4.1 Problem

The C-B8 `carrier_fee_schedule` table stores fees as static rows with `is_active` flags. When TCR/carrier fees change (they do — T-Mobile raised fees in January 2026, carriers refresh mid-year), the old prices are overwritten. There is no way to look up "what was the brand registration fee on the date this tenant was charged?"

### 4.2 Proposed Design: Temporal Fee Schedule

Replace `carrier_fee_schedule` with a **temporal lookup table** that preserves historical prices:

```sql
CREATE TABLE carrier_fee_schedule (
    id              UUID        NOT NULL DEFAULT gen_random_uuid(),
    fee_code        TEXT        NOT NULL,      -- TCR fee code (see §4.3)
    entity_type     TEXT        NOT NULL,      -- 'standard' | 'sole_proprietor'
    amount_cents    INTEGER     NOT NULL,      -- fee amount in cents
    description     TEXT        NOT NULL,      -- human-readable description
    effective_from  TIMESTAMPTZ NOT NULL,      -- when this price takes effect
    effective_to    TIMESTAMPTZ,               -- NULL = currently in effect
    -- StandardAuditMixin
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      UUID,
    updated_by      UUID,
    CONSTRAINT pk_carrier_fee_schedule PRIMARY KEY (id),
    -- Only one active price per (fee_code, entity_type) at any given time
    CONSTRAINT uq_carrier_fee_schedule_temporal
        EXCLUDE USING gist (
            fee_code WITH =,
            entity_type WITH =,
            tstzrange(effective_from, effective_to) WITH &&
        )
    );
```

**Key design properties**:
- **GiST exclusion constraint** ensures no two price rows for the same `(fee_code, entity_type)` overlap in time — same pattern used by `tax_rate_version` and other temporal tables in the project.
- `effective_to IS NULL` means the price is currently in effect.
- To look up the price at a specific point in time: `WHERE effective_from <= :charge_date AND (effective_to IS NULL OR effective_to > :charge_date)`.
- To introduce a new price: set the current row's `effective_to = now()`, insert a new row with `effective_from = now(), effective_to = NULL`.

### 4.3 TCR Fee Codes

| `fee_code` | Description | Entity types | Current amount |
|---|---|---|---|
| `brand_registration` | TCR brand registration (one-time) | standard, sole_proprietor | $4.00 (400¢) |
| `brand_vetting` | External brand vetting (optional, one-time) | standard, sole_proprietor | $40.00 (4000¢) |
| `campaign_registration_tmobile` | T-Mobile campaign registration (one-time, currently waived) | standard, sole_proprietor | $50.00 (5000¢) |
| `campaign_creation_3mo` | Campaign creation — first 3 months upfront | standard | $30.00 (3000¢) |
| `campaign_creation_3mo` | Campaign creation — first 3 months upfront | sole_proprietor | $6.00 (600¢) |
| `campaign_monthly` | Campaign monthly recurring (after first 3 months) | standard | $10.00 (1000¢) |
| `campaign_monthly` | Campaign monthly recurring (after first 3 months) | sole_proprietor | $2.00 (200¢) |
| `phone_number_assignment` | Phone number to campaign assignment (one-time) | standard, sole_proprietor | $0.03 (3¢) |
| `phone_number_monthly` | Phone number monthly lease | standard, sole_proprietor | $1.00 (100¢) |
| `surcharge_att` | Per-segment surcharge (AT&T) | standard, sole_proprietor | $0.003 (≈0¢ — tracked at sub-cent) |
| `surcharge_tmobile` | Per-segment surcharge (T-Mobile) | standard, sole_proprietor | $0.003 (≈0¢ — tracked at sub-cent) |
| `surcharge_verizon` | Per-segment surcharge (Verizon) | standard, sole_proprietor | $0.0031 (≈0¢ — tracked at sub-cent) |

**✅ Tom decision 2026-08-05**: Store sub-cent surcharges in the fee schedule with **millicents** precision. This allows the DB to be used to compare carrier surcharge rates against Pilot's $0.05/segment overage rate and calculate margins when carriers increase fees. The table uses `amount_millicents BIGINT` (1 millicent = 1/1000 of a cent = $0.00001) for all amounts, replacing the C-B8 `amount_cents INTEGER` column. Existing rows are migrated by multiplying by 1000.

### 4.4 Migration Path from C-B8 — Adopted as Part of C-B9

**✅ Tom decision 2026-08-05**: Adopt the temporal design as part of C-B9 (not a separate C-B8a batch).

C-B8 created `carrier_fee_schedule` with 8 seed rows and `is_active` flags. The C-B9 migration will:

1. **Add `effective_from` / `effective_to` columns** (both TIMESTAMPTZ)
2. **Add `amount_millicents BIGINT` column** — replaces `amount_cents` for all amounts (1 millicent = $0.00001)
3. **Migrate existing rows**: `amount_millicents = amount_cents * 1000`, `effective_from = created_at`, `effective_to = NULL`
4. **Drop the `is_active` column** — replaced by `effective_to IS NULL` check
5. **Drop the `amount_cents` column** — replaced by `amount_millicents`
6. **Add the GiST exclusion constraint** on `(fee_code, entity_type, tstzrange(effective_from, effective_to))` — requires `CREATE EXTENSION IF NOT EXISTS btree_gist` (may already exist for `tax_rate_version`)
7. **Add new fee codes** not in the original 8: `brand_vetting`, `campaign_registration_tmobile`, `phone_number_assignment`, `surcharge_att`, `surcharge_tmobile`, `surcharge_verizon`
8. **Seed the new surcharge rows** with millicents: `surcharge_att` = 300 millicents ($0.003), `surcharge_tmobile` = 300 millicents ($0.003), `surcharge_verizon` = 310 millicents ($0.0031)
9. **Update the quoting adapter** (`get_carrier_quote()`) to query `WHERE effective_to IS NULL` instead of `WHERE is_active = true`, and return `amount_millicents` instead of `amount_cents`
10. **Update `CarrierQuoteLineItem` schema** — change `amount_cents: int` to `amount_millicents: int` (or add both for backward compatibility during transition)
11. **Update `CarrierFeeSchedule` SQLModel** — replace `amount_cents` with `amount_millicents`, add `effective_from`/`effective_to` fields
12. **Update `seed_platform.py`** — carrier_fee_schedule seed block uses `amount_millicents` + `effective_from`/`effective_to`

### 4.5 Relationship to C-B9 and C-B10

- **C-B9** (this batch): The quoting adapter reads from `carrier_fee_schedule` to display costs to the tenant before Stripe Checkout. If the temporal design is adopted, C-B9's `get_carrier_quote()` queries `WHERE effective_to IS NULL` for current prices.
- **C-B10** (recurring pass-through): When creating the recurring subscription item at month 4, the system looks up the campaign monthly fee **at the date of the charge** — the temporal design ensures the correct historical price is used even if TCR changed fees between provisioning and month 4.

---

## Appendix A - AWS support guidance

The author also asked AWS's support assistant how a SaaS platform registers brands and campaigns through AWS End User Messaging (SNS). Its guidance was folded into the sections above; the transcript is not reproduced here.
