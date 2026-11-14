# Telnyx 10DLC Campaign — Pilot for Trades Platform Notifications (Pathway C)

**Document type**: Integration record / compliance submission playbook
**Created**: 2026-07-25 (original B2B2C draft) — **Repurposed 2026-07-31 for Pathway C**
**Owner**: Tom Lang (Founder)
**Status**: 🟡 Draft — repurposing the existing `CXXXXXX` brand/campaign from B2B2C customer-comms to **Pilot → tenant-owner platform notifications**. Blocked on batch **SIGNUP-C** shipping the "Stay Informed" consent screen + platform double-opt-in strings before portal resubmission.
**Design doc**: `batch-signup-c-design.md`
**Sibling template**: `telnyx-10dlc-tenant-customer-comms-campaign.md` — the future **per-tenant** (Pathway B) brand+campaign template each contractor submits under their own identity.

---

## 0. What Changed and Why (READ FIRST)

This doc **used to describe a shared B2B2C "customer communications" campaign** (Pathway B — contractor → their own customers, sent under one shared Pilot number). That model was **rejected by Telnyx** on 2026-07-27 (`CXXXXXX`, Telnyx ID `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1`) with the reviewer stating:

> *"Who is the perceived sender of the messages? If it's a business using your platform, then each business will need a brand and campaign created specifically for them."*

**That rejection is correct and structural, not a copy fix.** Per `10dlc-registration-automation-requirements.md`, Pilot is an **ISV**: tenant→customer SMS (Pathway B) requires a **per-tenant brand + campaign** under each contractor's own legal identity. There is **no** shared customer-comms campaign.

**Decision (Tom, 2026-07-31):** Repurpose the `CXXXXXX` brand/campaign for a fundamentally different, compliance-clean purpose:

| | Old (rejected) | New (this doc) |
|---|---|---|
| **Pathway** | B — tenant → their customers | **C — Pilot → tenant owner** |
| **Perceived sender** | The contractor (B2B2C — the rejection cause) | **Pilot for Trades itself** (single-brand, clean) |
| **Recipients** | Homeowners/clients | **Tenant owners** (Pilot's own customers) |
| **Content** | Job updates, invoice links | Account/billing/security/maintenance alerts **+ support-ticket resolution replies** |
| **Use case** | Mixed (Account Notifications + Customer Care) | **Mixed** (Account Notifications + Customer Care) — reuses the two sub-use cases already on file for `CXXXXXX` |
| **Consent capture** | Customer add form + attestation | **Signup "Stay Informed" screen** (owner opt-in) |

Pathway C is exactly the single-sender case Telnyx *wants*: Pilot is the legal sender, the tenant owner is the subscriber, no intermediary. The rejection reason evaporates.

**Why Customer Care is safe to add here (2026-07-31).** Tenant owners submit support tickets **to Pilot** (billing questions, a feature not working, etc.) and Pilot replies with the resolution — a genuine two-way support conversation in which **Pilot is still the sole sender**. Adding the **Customer Care** sub-use case therefore introduces **no** sender ambiguity (it does not resurrect the B2B2C rejection cause), and it restores the campaign to the **Mixed** shape `CXXXXXX` was originally registered under — so the two sub-use cases are reused rather than newly filed.

> **The three SMS pathways** (see `pilot-operations.md §13.1`):
> **A** — MFA OTP → AWS Cognito→SNS (no 10DLC). **B** — tenant→customer → Telnyx, **per-tenant** brand+campaign (future SMS-2 add-on; see sibling template). **C** — **Pilot→owner → Telnyx, this campaign.**

---

## 1. Campaign Identity

| Field | Value |
|---|---|
| **Brand** | Pilot for Trades (verified) |
| **TCR Brand ID** | `CXXXXXX` (reused) |
| **Telnyx Campaign ID** | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1` (repurpose) — or new campaign under same brand if Telnyx requires a fresh use-case |
| **Use case** | **Mixed — Account Notifications + Customer Care** (single-sender; reuses the two sub-use cases already registered for `CXXXXXX`) |
| **Vertical** | Software / SaaS (Pilot is the sender, not a trade vertical) |
| **Date registered** | Approved 2026-08-07 |
| **Current status** | ✅ **Campaign approved; carrier loop proven 2026-08-10 with real texts to the author's own phone** (outbound double opt-in, inbound YES → `verification_status=verified`, HELP/STOP/START auto-replies all confirmed end-to-end) |

> **Open portal question:** confirm whether Telnyx lets you change the use case on the existing failed campaign or requires a new campaign object under the same `CXXXXXX` brand. Either way the **brand is reused** (no new $4 brand fee); a new campaign object would re-incur the ~$15 campaign fee. Because `CXXXXXX` was originally registered as **Mixed (Account Notifications + Customer Care)**, restoring both sub-use cases here should map to the existing use-case profile rather than a narrowing/changing edit — confirm the portal treats it as the same Mixed use case.

---

## 2. Campaign Description (paste into portal)

Pilot for Trades is a SaaS field-service management platform. This campaign sends transactional account notifications from Pilot for Trades directly to our own registered users (trade-business owners and staff) who have signed up for the platform: system/service alerts, scheduled-maintenance notices, billing issues (failed payment, card expiring), security alerts (new sign-in, password change), and replies resolving support tickets the user submitted to Pilot (e.g., a billing question or a feature not working). Some of these are two-way support conversations in which the user may reply and our support team responds in-thread. Recipients opt in during account signup and confirm via a double opt-in text before any further messages are sent. No marketing content. Message frequency varies by account activity. Reply STOP to opt out, HELP for help.

---

## 3. Sub-Use Cases

A **Mixed** campaign requires **2–5 sub-use cases**. Use exactly these two — the same pair `CXXXXXX` was originally registered under:

| Sub-use case | Why it applies | Example sample (§6) |
|---|---|---|
| **Account Notifications** | Transactional platform messages Pilot sends to its own account holders about their account, billing, security, and platform status | Samples 1–4 |
| **Customer Care** | Two-way support conversation — the owner submitted a support ticket **to Pilot** (billing question, feature not working); Pilot replies with the resolution and the owner may reply back in-thread | Sample 5 (two-way support thread) |

**Perceived-sender note:** both sub-use cases are **single-sender** — Pilot for Trades is the sole sender in every message, including the Customer Care thread. This is the distinction from the rejected B2B2C model (§0) and is what keeps the Mixed use case compliance-clean.

**Do NOT select:**
- **2FA** — Pathway A via Cognito/SNS; no 10DLC campaign required.
- **Marketing** — Pilot sends no promotional SMS on this campaign; deferred to an email channel post-Founders. Selecting it triggers stricter opt-in scrutiny.
- **Delivery Notifications** — implies package/shipping tracking; not applicable.

---

## 4. Message Flow / Opt-In Narrative (paste into portal — load-bearing field)

Paste this into the "Message Flow" / "How do end users consent?" field:

Pilot for Trades sends account notifications only to its own registered users. Consent is captured in two stages:

**(1) Signup opt-in (explicit consent).** During account signup, on the "Stay Informed" step, the user enters their mobile number (required for the account) and may check an **unchecked-by-default** box: "Yes — text me about urgent account, billing, security, and support updates so I'm never caught off guard." The box is not pre-checked. Directly beneath it a disclosure states the program name (Pilot for Trades), the message types (account, billing, security & support messages, including replies to support requests the user submits), "Message frequency varies," "Msg & data rates may apply," STOP/HELP instructions, and a link to the privacy policy. Screenshots: https://pilotfortrades.com/compliance/signup-stayinformed-checked.png (consent given) and https://pilotfortrades.com/compliance/signup-stayinformed-unchecked.png (default state, box unchecked).

**(2) Double opt-in confirmation.** Immediately after signup, if the box was checked, Pilot sends a confirmation text: "Pilot for Trades: Reply YES to get important account, billing & security alerts by text. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel." The number is only marked verified and eligible for further messages after the user replies YES. If they reply STOP, no further messages are ever sent.

All messages are transactional account notifications from Pilot for Trades (system/service alerts, scheduled-maintenance notices, billing issues, security alerts) plus support-ticket resolution replies. Some messages are part of a **two-way support conversation**: when the user has submitted a support request to Pilot, they may reply to Pilot's message and our support team responds in-thread (this is the Customer Care sub-use case). Pilot for Trades remains the sole sender throughout. No marketing. Message frequency varies with account activity. Reply STOP to opt out, HELP for help. Privacy policy: https://www.pilotfortrades.com/legal/privacy

**Mobile information will not be shared with third parties or used for marketing purposes.**

> **⚠️ Disclosure copy must enumerate Customer Care — code change required before screenshots (2026-08-01).** The consent disclosure is the load-bearing evidence (§5) proving the disclosed message types match the campaign's sub-use cases. Because this campaign is submitted as **Mixed (Account Notifications + Customer Care)**, the live disclosure must list **support** as a message type — otherwise a reviewer sees a Customer Care sub-use case with no matching disclosed type (mismatch flag). The current live strings list only "account, billing & security alerts" and must be updated before the §5 screenshots are captured:
>
> | String | File | Target wording |
> |---|---|---|
> | Checkbox label | `page.tsx` | `Yes — text me about urgent account, billing, security, and support updates so I'm never caught off guard.` |
> | Disclosure constant `SMS_CONSENT_DISCLOSURE_TEXT` | `SmsConsentDisclosure.tsx` | `Account & support alerts from Pilot for Trades. You'll receive account, billing, security, and support messages — including replies to support requests you submit to us — at the mobile number provided. Message frequency varies. Msg & data rates may apply. Reply HELP for help, STOP to opt out. See our Privacy Policy. Mobile information will not be shared with third parties or used for marketing purposes.` |
> | Message-types assertion | `SmsConsentDisclosure.test.tsx` | update the asserted string to include `support` |
>
> **Sequencing note (Tom's call):** adding "support" to the disclosure at submission time is the recommended, lowest-mismatch-risk posture — disclosing a message type before the ticket-system feature fully ships is TCR-safe (the rule reviewers enforce is *don't send types you didn't disclose*, not *don't disclose types you don't yet send*). If you'd rather keep the initial screenshot to account/billing/security only and add support when the ticket system (§6 follow-on) lands, that is defensible but risks a disclosure↔Customer-Care mismatch on this submission. The double-opt-in first message (Sample 1 / §8) may optionally add "support" for consistency, but that is a `notification_template` string change subject to the §6↔§8 code-match rule.

---

## 5. Consent & Opt-In Evidence (screenshots)

| # | Surface | Screenshot URL | Role |
|---|---|---|---|
| 1 | **Signup "Stay Informed" — checked** (web signup wizard step 3, mobile entered, alerts box checked) | `https://pilotfortrades.com/compliance/signup-stayinformed-checked.png` | **PRIMARY** — disclosure paragraph + consent checked |
| 2 | **Signup "Stay Informed" — unchecked** (default state) | `https://pilotfortrades.com/compliance/signup-stayinformed-unchecked.png` | **PRIMARY (pair)** — proves the box is **not** pre-checked (clean consent) |

> **Screenshots are gated on the React Engineer's SIGNUP-C work.** The "Stay Informed" screen (unchecked-default consent box + full disclosure paragraph) must be built and deployed to production before Tom can capture these two screenshots. **Submission sequence:** (1) Python Engineer ships SIGNUP-C backend + templates → (2) React Engineer ships the "Stay Informed" screen → (3) deploy to prod → (4) Tom captures `signup-stayinformed-checked.png` + `-unchecked.png` → (5) upload to `/compliance/` → (6) submit campaign. The unchecked default is the key compliance signal — it removes any pre-checked-box objection.

---

## 6. Sample Messages (paste into portal — must match live templates)

Every sample leads with **`Pilot for Trades:`** so the platform brand is the perceived sender.

**Sample 1 — Double opt-in confirmation (first message)**
> Pilot for Trades: Reply YES to get important account, billing & security alerts by text. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.

**Sample 2 — Billing / failed payment (Account Notifications)**
> Pilot for Trades: Your payment didn't go through. Please login to app.pilotfortrades.com and update your credit card to keep your account active. Reply STOP to opt out.

**Sample 3 — Security alert (Account Notifications)**
> Pilot for Trades: New sign-in to your account from a new device. If this wasn't you, secure your account now. Reply STOP to opt out.

**Sample 4 — Scheduled maintenance (Account Notifications)**
> Pilot for Trades: Scheduled maintenance Sun 08-02-2026 from 2:00–3:00 AM ET. The app may be briefly unavailable. Reply STOP to opt out.

**Sample 5 — Support-ticket resolution, two-way (Customer Care)**
> Pilot for Trades: Good news — the billing issue you reported (ticket #1042) is resolved. Reply here if you're still seeing a problem and our team will follow up. Reply STOP to opt out.

> **✅ Samples 3 & 4 are now live in code (PLATFORM-SMS-B2, 2026-08-16).** Type codes `platform_security_new_device` (Sample 3) and `platform_maintenance_broadcast` (Sample 4) are seeded as system `notification_template` sms rows (Alembic migration `58c3ad26129f` + `seed_platform.py` parity). Sample 3 is stored fully static; Sample 4 is stored parameterized (`{{ maint_date }}` / `{{ maint_window }}` Jinja2 placeholders) and the verbatim-guardrail test renders it with the registered values (`Sun 08-02-2026`, `2:00–3:00 AM ET` — en-dash U+2013 preserved) asserting byte-equality with the registered Sample 4 string above — §6↔§8 code-match satisfied. Sample 3 is triggered by the Cognito Post-Authentication Lambda (device tracking = Always remember, `newDeviceUsed` gate); Sample 4 is triggered by the operator-run CLI `scripts/broadcast_maintenance_sms.py`. **Sample 5 remains with SUPPORT-B1** (Customer Care two-way — not yet implemented; see note below).

> **⚠️ §6↔§8 code-match rule.** These strings must match the live templates the backend emits (batch SIGNUP-C: `tasks/sms_compliance_platform.py` double-opt-in + `notification_template` rows for the sms channel). If a sample doesn't match the deployed template, the first live message fails MNO review (error 806). **Do not resubmit until SIGNUP-C has shipped to production.**

> **⚠️ Customer Care template + categories do NOT exist yet — planned follow-on (MCP-verified 2026-07-31).** `postgres-local` confirms `notification_template` has **zero `sms`-channel rows**, and `notification_category` has **no `support` or `customer_care` code** (only `billing`, `system_announcements`, `customer_activity`, etc.). Sample 5 is therefore a **target string** a backend batch must implement before this can go live. **Decision (Tom, 2026-07-31):** add **two new `notification_category` rows — `support` and `customer_care`** — fed by a new **online ticket-collection system** where a tenant submits a ticket describing their issue (billing, feature not working, etc.). The inbound ticket is the anchor for the two-way Customer Care thread: the ticket ID (e.g., `#1042` in Sample 5) ties the outbound resolution SMS and any inbound owner reply back to the originating ticket. The follow-on backend batch must deliver: (1) the ticket-collection intake surface + storage; (2) the `support` and `customer_care` `notification_category` rows; (3) an `sms` `notification_template` row emitting Sample 5 verbatim (§6↔§8 code-match); and (4) inbound-reply threading in `webhooks_sms.py` so a free-text owner reply attaches to the open ticket rather than being parsed as a keyword. This is **out of SIGNUP-C's scope** (SIGNUP-C ships only the double-opt-in + consent surface). Until the follow-on ships, the campaign can submit as **Mixed** but must **not** send Customer Care messages.

> **Embedded link note:** Sample 2 references the bare app domain `app.pilotfortrades.com` (already owned/warmed) as a **login destination** — no deep path (`/billing` is not a valid public route; the user logs in and self-navigates). A bare domain still counts as an embedded link → **Embedded link = Yes**. No sample contains a phone number → **Embedded phone number = No**.

---

## 7. Keywords (paste into portal — must match code exactly)

Verified against `webhooks_sms.py`. SIGNUP-C extends this handler to resolve `user_endpoint` targets (owner numbers), in addition to the existing `customer` targets.

### Opt-out Keywords
`STOP`,`STOPALL`,`UNSUBSCRIBE`,`QUIT`,`CANCEL`,`END`,`ARRET`

### Opt-in Keywords
`START`,`UNSTOP`,`YES`

### Help Keywords
`HELP`,`INFO`

---

## 8. Auto-Response Messages (paste into portal — MUST match SIGNUP-C code exactly)

> These are the target strings for the **platform** double-opt-in flow (Pilot-sender). SIGNUP-C sets the code to emit exactly these; submit the same strings to Telnyx.

### Opt-out (STOP) reply
> You have been unsubscribed from Pilot for Trades account alerts. No further messages will be sent. Reply START to re-subscribe.

### Opt-in (START/UNSTOP/YES) reply
> Pilot for Trades: You're opted in to account, billing & security alerts. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.

### Help (HELP/INFO) reply
> Pilot for Trades account alerts. For help, visit pilotfortrades.com or email info@pilotfortrades.com. Msg & data rates may apply. Reply STOP to unsubscribe.

### Double opt-in confirmation request (first message the user receives)
> Pilot for Trades: Reply YES to get important account, billing & security alerts by text. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.
> _Code: `tasks/sms_compliance_platform.py` (SIGNUP-C) — platform FROM number, not tenant number._

---

## 9. Campaign Attributes

| Attribute | Value | Notes |
|---|---|---|
| Subscriber opt-in | **Yes** | Double opt-in (signup checkbox + reply YES) |
| Subscriber opt-out | **Yes** | STOP keyword set |
| Subscriber help | **Yes** | HELP keyword set |
| Number pooling | No | Single shared Pilot platform number |
| Direct lending / loan arrangement | No | |
| Embedded link | **Yes** | bare `app.pilotfortrades.com` login link (Sample 2) — no deep path |
| Embedded phone number | **No** | HELP reply uses website/email, no phone |
| Age-gated content | No | |
| Affiliate marketing | No | |

---

## 10. Webhook Configuration

| Field | Value |
|---|---|
| **Inbound webhook URL** | `https://api.pilotfortrades.com/api/v1/webhooks/sms/telnyx-inbound` |

Handled by `webhooks_sms.py` — signature-verified; SIGNUP-C extends it to route STOP/START/HELP/YES against `user_endpoint` (owner) targets in addition to `customer` targets.

### 10.1 — Messaging Profiles: DEV vs PROD Split (READ BEFORE TOUCHING MISSION CONTROL)

**Canonical route path**: `/api/v1/webhooks/sms/telnyx-inbound` (app prefix `/api/v1/webhooks` + route `/sms/telnyx-inbound`, `webhooks_sms.py`). Any other path 404s.

| | **DEV profile** | **PROD profile** |
|---|---|---|
| Purpose | Local dev + TELNYX-INT-1 real-API tests | Production traffic (the `CXXXXXX` number lives here) |
| Inbound webhook URL | `https://<your-ngrok>.ngrok-free.dev/api/v1/webhooks/sms/telnyx-inbound` | `https://api.pilotfortrades.com/api/v1/webhooks/sms/telnyx-inbound` |
| API key | Dev key (tagged, expirable) | Prod key → Secrets Manager `pilot/prod/telnyx` (`api_key`, `messaging_profile_id`, `public_key`, `platform_sms_number`) |
| `TELNYX_MESSAGING_PROFILE_ID` | DEV profile ID in local `.env` | **PROD profile ID in the prod secret — must be THIS profile's ID** |

**Two incidents from the 2026-08-10 Step 3 live test — both console-config errors, both silent:**

1. **Number on the wrong profile**: the campaign number was assigned to the DEV profile, so inbound YES webhooks went to the ngrok URL (dev server) instead of prod. Outbound SMS was unaffected (sending only needs number + campaign) — the failure was invisible except for `user_endpoint.verification_status` never flipping to `verified`. **After moving a number between profiles, verify: (a) `TELNYX_MESSAGING_PROFILE_ID` in the target env matches the profile the number now sits on, (b) the number is still assigned to campaign `CXXXXXX`.**
2. **Wrong webhook path programmed in the profile**: the profile carried `/api/v1/webhooks/telnyx/inbound` → every delivery 404'd at the ALB (visible in `/ecs/pilot-api` logs). Telnyx retries failed webhooks; the handler is idempotent, so replays after a fix are safe.

**Diagnostic shortcut**: if outbound works but inbound never lands, check Mission Control → Messages → Inbound → webhook delivery status first, then `/ecs/pilot-api` for the POST — a 404 means the path is wrong, no log line means the wrong profile/URL, a 401 means `TELNYX_PUBLIC_KEY` mismatch.

---

## 11. Number Provisioning & End-to-End Test

- [x] Confirm the repurposed campaign is approved (or new campaign object under `CXXXXXX`). — **APPROVED 2026-08-07**
- [x] Keep/buy **1** Pilot platform number under the approved campaign.
- [x] Store the **platform** number in Secrets Manager `pilot/prod/telnyx` as the Pathway-C FROM number (distinct from any per-tenant number). SIGNUP-C's `sms_compliance_platform.py` reads it.
- [x] **Outbound test**: complete signup with the alerts box checked using your own mobile → receive the double opt-in → reply YES → confirm `user_endpoint.consent_status='opted_in'`, `verification_status='verified'`. — **✅ 2026-08-10** (verified=14:55:36 UTC; required fixes: celery task registration, `.env`-in-image removal §19.7 runbook, number moved DEV→PROD messaging profile + webhook path correction §10.1)
- [x] **Auto-reply test**: reply HELP → HELP text; STOP → opt-out text; START → opt-in text. Each matches §8 exactly. — **✅ 2026-08-10** (all three passed live; real webhook payload + ed25519 headers captured → `backend/tests/integration/fixtures/telnyx/real_webhook_capture.json`, closing TELNYX-INT-1 gap G4)
- [ ] **Two-way Customer Care test** *(only after the support-ticket SMS template + category follow-on ships — see §6 warning)*: send a support-ticket-resolution SMS (Sample 5) to your own opted-in number → reply with a free-text follow-up → confirm the inbound reply is captured/threaded (not misinterpreted as a keyword) so support can respond in-thread.
- [x] Update §1 status → ✅ Active. — **2026-08-10**

---

## 12. Compliance Links

| Document | URL |
|---|---|
| **Privacy policy** | https://www.pilotfortrades.com/legal/privacy |
| **Terms and conditions** | https://www.pilotfortrades.com/legal/terms |

---

## 13. Cross-References

| Doc | Role |
|---|---|
| `batch-signup-c-design.md` | The implementation design for the signup consent screen + platform double-opt-in |
| `telnyx-10dlc-tenant-customer-comms-campaign.md` | **Per-tenant** Pathway-B template (future SMS-2 add-on — each contractor's own brand+campaign) |
| `telnyx-10dlc-mfa-campaign.md` | History of the deleted `CYYYYYY` "2FA" campaign + why MFA needs no 10DLC |
| `10dlc-registration-automation-requirements.md` | The per-tenant ISV model for Pathway B |
| `pilot-operations.md §13.1` | The three-SMS-pathway architecture |
| `pilot-adr-log.md` | ADR: three-pathway SMS model + repurpose `CXXXXXX` |

---

## 14. Testing Modes (mock vs live)

**Added by TELNYX-INT-1 (2026-08-09).** The SMS carrier stack supports three
testing modes, all selected by environment variables at the
`get_sms_carrier()` factory seam.
See also `telnyx-spike-1-findings.md` §4b for the
distinction between *in-memory mock* and *Telnyx-side mock brand/campaign*.

### 14.1 Three-mode matrix

| Mode | Env vars | Carrier behavior | Use |
|---|---|---|---|
| **Mock** (default) | `SMS_CARRIER=mock` | `MockSmsCarrier` — deterministic, no network calls | Unit tests, E2E suite, local dev default |
| **Telnyx-mock** | `SMS_CARRIER=telnyx` + `TELNYX_10DLC_MOCK=true` + dev API key | Real Telnyx API; brands/campaigns created as **mock** objects ($0, no TCR fees, no SMS traffic) | Real-API provisioning-flow + webhook integration tests (`tests/integration/test_telnyx_real_api.py`) |
| **Telnyx-live** | `SMS_CARRIER=telnyx` + prod keys (`TELNYX_10DLC_MOCK` unset/false) | Real everything — real brands, real SMS, real fees | Prod; Step 3 E2E SMS test; final pre-launch verification |

### 14.2 Key points

- **`TELNYX_10DLC_MOCK=true` only has effect when `SMS_CARRIER=telnyx`.** With
  `SMS_CARRIER=mock`, the in-memory `MockSmsCarrier` is used regardless — the
  flag is never read.
- **Mock brands/campaigns cannot carry SMS traffic** (Telnyx constraint). They
  exist for provisioning-flow and webhook integration testing only. Real SMS
  requires a live campaign (e.g., `CXXXXXX`).
- **Campaigns under a mock brand are mock by inheritance** — no explicit
  `mock` flag on campaign creation is needed. Verified against Telnyx Help
  Center: *"During creation of the brand set the 'mock' field to true. Once
  you've created your mock brand, create a 10DLC campaign as normal."*
  ([source](https://support.telnyx.com/en/articles/12812898-10dlc-mock-brands-and-campaigns))
- **Init WARNING**: when `TELNYX_10DLC_MOCK=true`, `TelnyxSmsCarrier.__init__`
  logs a loud WARNING so nobody accidentally runs prod in mock mode.
- **Prod ECS task definition** must set `SMS_CARRIER=telnyx` with the
  `pilot/prod/telnyx` secret and `TELNYX_10DLC_MOCK` unset/false.

### 14.3 Real-API integration test suite

File: `backend/tests/integration/test_telnyx_real_api.py`

- **Skip condition**: entire module skips unless `TELNYX_API_KEY` is set.
- **Fee guard**: brand/campaign creation tests hard-refuse to run unless
  `TELNYX_10DLC_MOCK=true` (fixture-level assertion — prevents accidental
  fee-bearing registrations).
- **Scenarios**: mock brand create→poll, mock campaign create→poll, verticals
  list, number search (read-only), 4xx error mapping, Ed25519 webhook
  signature verification against a captured real payload.
- **Excluded**: `send_message` (live SMS), `provision_number` (paid number
  order), `assign_number_to_campaign` on the live campaign — these belong to
  Tom's Step 3 E2E run.

### 14.4 Webhook payload capture (for Ed25519 verification — G4)

The Ed25519 signature verification path
(`verify_webhook_signature()`)
has unit coverage only. To prove it against a real Telnyx event:

1. During Tom's Step 3 live E2E SMS test, capture a real webhook delivery
   (the raw HTTP body + `telnyx-signature-ed25519` + `telnyx-timestamp`
   headers) from the ALB endpoint or a temporary capture endpoint.
2. Save the captured payload to:
   `backend/tests/integration/fixtures/telnyx/real_webhook_capture.json`
   with this shape:
   ```json
   {
     "payload": "<raw JSON body as a string>",
     "headers": {
       "telnyx-signature-ed25519": "<base64 signature>",
       "telnyx-timestamp": "<unix timestamp string>"
     }
   }
   ```
3. The test `test_ed25519_webhook_capture_verification` in
   `test_telnyx_real_api.py` will automatically pick it up and verify
   `verify_webhook_signature()` returns `True`. Until the fixture exists,
   the test skips with a message pointing here.

---

## 15. History — Rejected B2B2C Rev (archived context)

The original B2B2C rev-1 submission (2026-07-25) failed MNO review 2026-07-27 with the "each business needs its own brand and campaign" reason (§0). Rev-2 attempted two copy fixes (no-sharing disclosure + brand-prefix on samples). **That path is abandoned** in favor of the correct structural answer: Pathway C (this doc) for Pilot-sender platform notices, and the **per-tenant** template (sibling doc) for genuine tenant→customer messaging. The full rejection record and the DLC-B4 brand-prefix backend work are preserved in git history and the sibling template.

---

*Maintained by: Tom + Pilot Architect. This is the portal-submission playbook for the **Pathway C** platform-notifications campaign (Pilot → tenant owners) — a **Mixed** campaign covering **Account Notifications + Customer Care** (support-ticket resolutions), reusing the two sub-use cases already on file for `CXXXXXX`. Update §1 with assigned IDs on resubmit, §5 screenshots after SIGNUP-C deploys, and §11 statuses as the end-to-end test completes. Note (§6): the Customer Care `sms` template + routing category are a follow-on backend dependency before Customer Care traffic can send.*
