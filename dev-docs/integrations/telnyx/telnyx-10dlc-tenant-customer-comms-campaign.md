# Telnyx 10DLC Campaign — Pilot for Trades Customer Communications (Mixed)

**Document type**: Integration record / compliance submission playbook
**Created**: 2026-07-25
**Owner**: Tom Lang (Founder)
**Status**: 🟢 Ready to submit — DLC-2 shipped the consumer disclosure; consent screenshots captured (§5). Remaining: create the Mixed campaign in the Telnyx portal.
**Supersedes**: The deleted `CYYYYYY` "2FA" campaign — see `telnyx-10dlc-mfa-campaign.md` for that history.

**Why a new campaign (not a re-submission):** The first campaign (`CYYYYYY`) was mis-filed as "2FA/Two-Factor Authentication." MFA OTP codes actually flow through **AWS Cognito → AWS SNS**, which handles carrier compliance natively — **no 10DLC campaign is required for MFA**. See `pilot-operations.md §13.12`. This campaign covers a completely different pathway: **B2B2C customer communications** (job updates, appointment reminders, invoice links) sent through the Telnyx messaging profile via `TelnyxSmsCarrier`. The `CYYYYYY` campaign was deleted; this is a fresh Mixed campaign.

---

## 0. Portal Submission Checklist (do these in order)

- [x] **Consumer disclosure shipped** — DLC-2 added the consent disclosure paragraph to the customer create/edit form (program name, message types, frequency, "Msg & data rates may apply", STOP/HELP, privacy link). Verified in the screenshots (§5).
- [ ] **DLC-B2 backend auto-reply fixes deployed to production** (`api.pilotfortrades.com`) — the STOP/START/HELP + double opt-in strings in code must match §8 before you submit. If the backend half has not shipped, submitting §8 text now risks a mismatch at first live message.
- [x] **Consent screenshots captured** — `customer-add-checked.png` (Save enabled) + `customer-add-unchecked.png` (Save disabled, consent enforced). See §11.
- [ ] Upload both screenshots to `https://pilotfortrades.com/compliance/` (same folder as the MFA images).
- [ ] In the Telnyx portal, create a new campaign under the verified Pilot for Trades brand.
- [ ] Select use case **Mixed** with sub-use cases **Account Notifications** + **Customer Care** (§3).
- [ ] Paste the campaign description (§2), message-flow / opt-in narrative (§4), sample messages (§6), keywords (§7), and auto-reply messages (§8) exactly as written here.
- [ ] Set campaign attributes (§9) — note **Embedded link = Yes** and **Embedded phone number = No** for this campaign (invoice links appear in messages; DLC-B2 removed the phone number from the HELP reply — see §9).
- [ ] Set the webhook URL (§10).
- [ ] Submit. Buy **1** Telnyx number after approval. Configure it in Secrets Manager `pilot/prod/telnyx` and run the end-to-end test (§13) — this closes **10DLC Step 3 of 3** in the launch plan §1.

### Post-Submit Fast-Follow — 🔴 ROOT CAUSE CORRECTED (2026-07-25): Backend route collision, not a frontend gap

> **Live test result:** `curl -i https://api.pilotfortrades.com/api/v1/public/invoices/A1b2C3` returns **`404 {"detail":"Invoice payment link not found"}`** — and browser rendering of `/i/A1b2C3` shows a **500**. Neither matches the frontend's expected 401/410 graceful branches. Investigation proved the cause is a **backend route collision**, not a missing frontend page.

- [x] **Root cause identified — DUPLICATE handlers for `GET /api/v1/public/invoices/{token}`.** Two routers are mounted at the same `/api/v1/public` prefix, both defining the same path:
  - **Legacy** `invoices.py` (`invoices.public_router`) — mounted **FIRST** at `main.py` → **WINS**. Its `_resolve_token` (`invoices.py`) treats the dotless `A1b2C3` as a legacy `token_hash` lookup → miss → **404 "Invoice payment link not found"** (exactly the curl result).
  - **Signed-token** `public_invoices.py` (`public_invoices.router`) — mounted at `main.py` → **SHADOWED, never reached**. This is the handler the frontend was written against (401/410 contract) and the one carrying the A81 `/payment-intent` + `/confirm-payment` routes.
- [x] **Frontend is NOT the primary bug.** `PublicInvoicePage.tsx` handles 401/410/ok but has **no 404 branch** — a 404 falls through to the generic "Error 404" state (functional but not the friendly invalid-link page). The browser **500** is a *separate* layer (Next.js SSR `generateMetadata` or the `/api/v1/*` rewrite proxy env var — `next.config.ts` `NEXT_PUBLIC_API_URL` vs `page.tsx` `NEXT_PUBLIC_API_BASE_URL` mismatch) — under isolation.
- [x] **✅ Payment-path risk RESOLVED (2026-07-25 — INV-ROUTE-FIX):** `invoices.public_router` removed from `main.py`. `public_invoices.py` is now the single canonical handler. Canonical-shape regression test passes (`test_public_invoice_canonical.py`). Full suite: 4128 passed, 0 failed.
- [x] **Fix split into two sequenced prompts (Python-first):**
  1. **INV-ROUTE-FIX (Python, P0) ✅ COMPLETE** — `batch-inv-route-fix-python-engr-prompt.md`. Removed legacy `invoices.public_router`, made `public_invoices.py` canonical, preserved FIND-071/072, upgraded 401/410 to RFC 7807, replaced hollow assertion with real route-uniqueness test, added canonical-shape regression test. OpenAPI regenerated.
  2. **[x] ✅ DLC-B3 (React) — COMPLETE (2026-07-25)** — `batch-dlc-b3-react-engr-prompt.md`. 404 branch added to both public pages; SSR env-var reconciled (`NEXT_PUBLIC_API_BASE_URL` → `NEXT_PUBLIC_API_URL`); 17 new regression tests (7 invoice unit + 7 quote unit + 3 integration) — fake-token `A1b2C3` → 401 → graceful page is now locked. DevOps: set `NEXT_PUBLIC_API_URL` on `pilot-web` ECS task for SSR metadata in production.
  10DLC review takes days–weeks, so this ships before any reviewer clicks — but the **payment-path risk above is independently launch-blocking** and INV-ROUTE-FIX resolves it.

---

## 1. Campaign Identity

| Field | Value |
|---|---|
| **Campaign ID** | _(assigned by Telnyx on submission)_ |
| **TCR Campaign ID** | _(assigned on TCR registration)_ |
| **Brand** | Pilot for Trades (verified) |
| **Use case** | **Mixed** |
| **Sub-use cases** | Account Notifications, Customer Care |
| **Date registered** | _(fill on submit)_ |
| **Current status** | Draft |

---

## 2. Campaign Description (paste into portal)

> Pilot for Trades is a field-service management platform used by trade contractors (electricians, plumbers, HVAC). Contractors send service-related SMS to their own customers: appointment confirmations and reminders, "on my way" / arrival / running-late updates, job-completion notices, invoice links, and payment receipts. End customers provide consent to their contractor and confirm via a double opt-in text before any further messages are sent. No marketing content. Message frequency varies by service activity. Reply STOP to opt out, HELP for help.

---

## 3. Sub-Use Case Selection & Rationale

A **Mixed** campaign requires **2–5 sub-use cases**. Use exactly these two:

| Sub-use case | Why it applies | Example sample (§6) |
|---|---|---|
| **Account Notifications** | Transactional service updates tied to a specific job/appointment/invoice the customer is expecting | Samples 1, 2, 3, 5 |
| **Customer Care** | Two-way service conversation — customer can reply to a thread; tech responds | Sample 4 (two-way thread) |

**Do NOT select:**
- **2FA** — wrong pathway (Cognito/SNS handles MFA, not Telnyx). This mis-selection killed `CYYYYYY`.
- **Marketing** — Pilot sends no promotional SMS; selecting it triggers stricter opt-in scrutiny and separate consent rules.
- **Delivery Notifications** — implies package/shipping tracking; not applicable.

---

## 4. Message Flow / Opt-In Narrative (paste into portal — this is the load-bearing field)

> **This is the field MNO reviewers scrutinize hardest for a B2B2C platform.** It must explain exactly where and how the *end consumer* consents, because the consumer never logs into Pilot. The double opt-in is the answer.

Paste this into the "Message Flow" / "How do end users consent?" field:

Pilot for Trades is used by trade contractors to communicate with their own customers. Consent is captured in two stages:

**(1) Contractor attestation (offline consent).** When a contractor adds a customer's mobile number in the Pilot web dashboard (Customers → Add/Edit Customer), the contractor must check a consent-confirmation box affirming they have received the customer's explicit permission to send service SMS. The number cannot be saved until the box is checked (the Save button is disabled). The form displays a consumer-facing disclosure with program name, message types, frequency, "Msg & data rates may apply," STOP/HELP instructions, and a privacy-policy link. Screenshots: https://pilotfortrades.com/compliance/customer-add-checked.png (consent given, Save enabled) and https://pilotfortrades.com/compliance/customer-add-unchecked.png (consent required, Save disabled).

**(2) Double opt-in confirmation (consumer confirmation).** Immediately after the number is saved, Pilot sends the customer a confirmation text: "Hi [Name], [Business] uses Pilot for Trades for service updates. Reply YES to confirm you want to receive texts. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel." The customer's number is only marked verified and eligible for further messages after they reply YES. If they reply STOP, no further messages are ever sent.

All messages are transactional and service-related (appointment confirmations/reminders, arrival/ETA updates, job-completion notices, invoice links, payment receipts). No marketing. Message frequency varies with the customer's service activity. Reply STOP to opt out, HELP for help. Privacy policy: https://www.pilotfortrades.com/legal/privacy

**Mobile information will not be shared with third parties or used for marketing purposes outside of Pilot for Trades service messages.**

> **⚠️ REJECTION FIX #1 (rev 2, 2026-07-27).** Campaign `CXXXXXX` (Telnyx ID `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1`) was set to `TELNYX_FAILED`. Per Telnyx compliance guidance, single-brand B2B2C **is** allowed; the two required fixes are: (1) the **no-sharing disclosure** bolded above (added to this Message Flow field), and (2) the **"Pilot for Trades:" sender prefix** on every sample message (§6). Both are applied in this revision. See §16 for the full rejection record.

---

## 5. Consent & Opt-In Evidence (screenshots)

| # | Surface | Screenshot URL | Role in submission |
|---|---|---|---|
| 1 | **Customer SMS consent — checked** (web: Customers → Add/Edit Customer, phone entered, consent box checked) | `https://pilotfortrades.com/compliance/customer-add-checked.png` | **PRIMARY** — shows the consumer disclosure paragraph + attestation checked + **Save enabled**. |
| 2 | **Customer SMS consent — unchecked** (same surface, box unchecked) | `https://pilotfortrades.com/compliance/customer-add-unchecked.png` | **PRIMARY (pair)** — proves consent is *enforced*: **Save disabled** + "You must confirm consent before saving a mobile phone number" warning. |
| 3 | Web MFA disclosure (Settings → Security → MFA) | `https://pilotfortrades.com/compliance/account-add-mfa.png` | Supporting — platform-wide SMS-compliance posture. Optional attach. |
| 4 | Mobile MFA disclosure | `https://pilotfortrades.com/compliance/account-add-mfa-mobile.png` | Supporting — optional attach. |

> Screenshots **1 + 2 are the load-bearing pair** for this customer-comms campaign — the checked/unchecked contrast demonstrates to the MNO reviewer that consent is not merely displayed but **enforced** (a number cannot be saved without attestation). The MFA screenshots (3, 4) belong to a different SMS surface (MFA/Cognito) and are optional supporting evidence. Both consent screenshots are captured; upload to the `/compliance/` folder before submitting.

---

## 6. Sample Messages (paste into portal — must match live templates)

These are derived from the live `communication_template` rows (channel = `sms`). Portal samples with variables rendered to realistic values.

> **⚠️ REJECTION FIX #2 (rev 2, 2026-07-27) — "Pilot for Trades:" sender prefix.** The reviewer flagged that samples identified the contractor, not Pilot for Trades, as the sender. Every sample below now leads with **`Pilot for Trades:`** so the platform brand is the perceived sender. **This is NOT just a portal edit** — per the §8 code↔portal match rule, the live SMS templates in `seed_core.py` and the `communication_template` rows must be updated to emit the same prefix, or the first live message fails MNO review (error 806). Tracked as backend batch **DLC-B4** (prepend brand prefix to all customer-facing SMS templates). **Do not resubmit until DLC-B4 has shipped to production** and these samples match the deployed templates.

**Sample 1 — Appointment reminder (Account Notifications)**
> Pilot for Trades: Reminder: Acme Electric appointment tomorrow at 2:00 PM. Reply STOP to opt out.
> _Source: `appointment_reminder_24h`_ — ⚠️ **DLC-B4 reconciliation (2026-07-27):** corrected to include "Reminder: " which the live template body_template emits. Prior rev-2 draft dropped the word — this fix ensures §6↔§8 code match.

**Sample 2 — On my way / ETA (Account Notifications)**
> Pilot for Trades: Hi John, this is Mike — I'm on my way, ETA 3:15 PM. Reply STOP to opt out.
> _Source: `on_my_way`_

**Sample 3 — Job complete (Account Notifications)**
> Pilot for Trades: Hi John, Mike here — work is complete. Invoice to follow. Reply STOP to opt out.
> _Source: `job_complete`_

**Sample 4 — Appointment confirmation, two-way (Customer Care)**
> Pilot for Trades: Hi John, please confirm your appointment for Thu Jul 30 at 2:00 PM at 789 Oak Blvd. Reply YES to confirm or call us. Reply STOP to opt out.
> _Source: `confirm_appointment`_

**Sample 5 — Invoice ready, embedded link (Account Notifications)**
> Pilot for Trades: Your invoice is ready. View and pay at https://app.pilotfortrades.com/i/A1b2C3. Reply STOP to opt out.
> _Source: `invoice_sent`_

> **⚠️ Link domain — MUST match production code.** The invoice-link domain is **`app.pilotfortrades.com`** — the domain the backend actually emits (`email_template_renderer.py`, `seed_scenario_customer_comms.py`). The earlier placeholder `p4t-link.com` was **never a real domain** (zero code references) — do NOT submit it; a reviewer clicking a dead link fails review. Do **not** register a new short domain for MVP: `app.pilotfortrades.com` is already owned, already warmed (URL reputation), and already in code. **Decision (2026-07-25):** single link host, no per-message-type split (`pay.`/`appt.`/`account.` rejected — fragments URL reputation 3 ways, 3× cert/ALB/DNS infra against the $888 cap, more embedded domains = more reviewer scrutiny). A dedicated neutral redirector (`link.pilotfortrades.com`) is a valid **post-MVP** option once SMS volume warrants decoupling link reputation from the app domain — but it must be **one** host, and it requires a `PUBLIC_BASE_URL` + invoice-link-renderer code change before use.

> **⚠️ Pre-§13 check — `{{invoice_link}}` render path.** The live SMS template (`seed_core.py`) uses the `{{invoice_link}}` variable, and a short-code generator exists (`short_link_resolver.py`), but the send-time wiring that populates `{{invoice_link}}` with a real URL is unconfirmed in code. Verify it renders a live `app.pilotfortrades.com/i/...` (or `/api/v1/short/...`) URL before the §13 end-to-end test — an empty/placeholder render breaks the invoice SMS.

> **Note on §9 attributes:** Sample 5 contains an embedded link → set **Embedded link = Yes**. No message contains a phone number (DLC-B2's HELP reply uses website/email, not a phone) → **Embedded phone number = No**.

---

## 7. Keywords (paste into portal — must match code exactly)

Verified against `webhooks_sms.py`. DLC-B2 documents `YES` and `ARRET` as declared so the portal matches the code.

### Opt-out Keywords
`STOP`, `STOPALL`, `UNSUBSCRIBE`, `QUIT`, `CANCEL`, `END`, `ARRET`

### Opt-in Keywords
`START`, `UNSTOP`, `YES`

### Help Keywords
`HELP`, `INFO`

---

## 8. Auto-Response Messages (paste into portal — MUST match DLC-B2 code exactly)

> **These are the DLC-B2 target strings.** The Python engineer sets the code to emit exactly these. Submit these same strings to Telnyx. If they don't match, MNO review fails (806).

### Opt-out (STOP) reply
> You have been unsubscribed from Pilot for Trades messages. No further messages will be sent. Reply START to re-subscribe.
> _Code: `customer_communication_threading.py`_

### Opt-in (START/UNSTOP/YES) reply
> Pilot for Trades: You're opted in to receive service updates. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.
> _Code: `customer_communication_threading.py`_

### Help (HELP/INFO) reply
> Pilot for Trades service messages. For help, visit pilotfortrades.com or email info@pilotfortrades.com. Msg & data rates may apply. Reply STOP to unsubscribe.
> _Code: `customer_communication_threading.py`_

### Double opt-in confirmation request (first message the consumer receives)
> Pilot for Trades: Hi {first_name}, {business_name} uses Pilot for Trades for service updates. Reply YES to confirm you want to receive texts. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.
> _Code: `sms_compliance.py`_ — **rev 2 (2026-07-27):** prefixed with `Pilot for Trades:` per rejection fix #2. This is the FIRST message the consumer receives, so it's the most important place to establish Pilot as the perceived sender. DLC-B4 must update this string in code to match.

---

## 9. Campaign Attributes

| Attribute | Value | Notes |
|---|---|---|
| Subscriber opt-in | **Yes** | Double opt-in (contractor attestation + consumer YES) |
| Subscriber opt-out | **Yes** | STOP keyword set |
| Subscriber help | **Yes** | HELP keyword set |
| Number pooling | No | Single shared number at beta (per-tenant numbers = SMS-2 add-on) |
| Direct lending / loan arrangement | No | |
| Embedded link | **Yes** | Invoice links (Sample 5) |
| Embedded phone number | **No** | DLC-B2 changed HELP reply from dynamic `{support_phone}` to fixed website/email — no phone number in any message |
| Age-gated content | No | |
| Affiliate marketing | No | |

---

## 10. Webhook Configuration

| Field | Value |
|---|---|
| **Inbound webhook URL** | `https://api.pilotfortrades.com/api/v1/webhooks/sms/telnyx-inbound` |

Handled by `webhooks_sms.py` — signature-verified, routes STOP/START/HELP + threads inbound replies.

---

## 11. Consent Screenshots — Customer SMS Consent (captured, ready to upload)

Shipped by DLC-2. Two screenshots on the customer create/edit surface, taken with a mobile phone entered so the consent block renders:

| File | State | What it proves |
|---|---|---|
| `customer-add-checked.png` | Consent box **checked** | Disclosure paragraph visible + **Save Changes enabled** |
| `customer-add-unchecked.png` | Consent box **unchecked** | **Save Changes disabled** + warning "You must confirm consent before saving a mobile phone number" — consent is enforced |

- **Upload target**: `https://pilotfortrades.com/compliance/customer-add-checked.png` and `.../customer-add-unchecked.png`
- **App route**: `/customers/{id}` Overview → Edit Customer (or `/customers/new`), mobile phone entered
- **Required visible elements** (confirmed present in both screenshots):
  - The attestation checkbox: "I confirm that I have received explicit, documented consent from this customer…"
  - Consumer disclosure paragraph (`data-testid="customer-sms-consent-disclosure"`) containing ALL of:
    - Program name — "Pilot for Trades" ✅
    - Message types — "appointment reminders, job updates, and invoice links" ✅
    - "Message frequency varies" ✅
    - "Msg & data rates may apply" ✅
    - "Reply STOP to opt out" ✅
    - "HELP for help" ✅
    - Clickable **Privacy Policy** link → `https://www.pilotfortrades.com/legal/privacy` ✅

---

## 12. Compliance Links

| Document | URL |
|---|---|
| **Privacy policy** | https://www.pilotfortrades.com/legal/privacy |
| **Terms and conditions** | https://www.pilotfortrades.com/legal/terms |

Website domain (`pilotfortrades.com`) matches the sender email domain and brand name — consistency check passes.

---

## 13. Post-Approval — Number Provisioning & End-to-End Test (closes 10DLC Step 3)

- [ ] Buy 1 Telnyx number under the approved campaign.
- [ ] Add number to Secrets Manager `pilot/prod/telnyx` (see `stripe-pricing-config.md` pattern for secret structure).
- [ ] Insert a `tenant_phone_number` row (status `active`) for the beta tenant — this is what `sms_compliance.py` and `webhooks_sms.py` resolve against.
- [ ] **Outbound test**: add a test customer with your own mobile + attestation → confirm you receive the double opt-in text → reply YES → confirm verified.
- [ ] **Auto-reply test**: reply HELP → confirm HELP text; reply STOP → confirm opt-out text; reply START → confirm opt-in text. Each must match §8 exactly.
- [ ] **Inbound thread test**: send a normal reply → confirm it appears in the Comms thread.
- [ ] Update §1 status → ✅ Active; update launch plan §1 "10DLC Step 3 of 3" → ✅.

---

## 14. Telnyx Reference Documentation

- [How to Create a 10DLC Campaign](https://support.telnyx.com/en/articles/6339152-how-to-create-a-10dlc-campaign)
- [10DLC Campaign Compliance Requirements](https://support.telnyx.com/en/articles/9940291-10dlc-campaign-compliance-requirements)

---

## 15. Cross-References

| Doc | Role |
|---|---|
| `telnyx-10dlc-mfa-campaign.md` | History of the deleted `CYYYYYY` campaign + why MFA needs no 10DLC |
| `mfa-integration-approach.md` | The 6-finding audit that drove DLC-B2 scope |
| `pilot-operations.md §13.12` | The two-SMS-pathway architecture (SNS vs Telnyx) |
| `batch-dlc-b2-python-engr-prompt.md` | Backend implementation of the strings above |
| `batch-dlc-b2-react-engr-prompt.md` | Frontend consent-disclosure implementation |
| `pilot-launch-plan.md §2.0 #9` | DLC-B2 batch card + gate item |

---

## 16. Rejection & Resubmission Record

### Rev 1 — Submitted 2026-07-25 → `TELNYX_FAILED` (2026-07-27)

| Field | Value |
|---|---|
| Brand | Pilot for Trades |
| TCR Brand ID | `CXXXXXX` |
| Telnyx Campaign ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx1` |
| Vertical | Construction, Materials, and Trade Services |
| Status | `TELNYX_FAILED` |

**Human reviewer reason (verbatim):** *"Who is the perceived sender of the messages? If it's a business using your platform, then each business will need a brand and campaign created specifically for them. Note: The current campaign describes contractors using Pilot for Trades to communicate with their own customers, and the sample messages identify the contractor/service context rather than Pilot for Trades as the sole sender."*

**Telnyx AI compliance assistant clarification (2026-07-27):** single-brand B2B2C **is** allowed for platforms (CRMs, field-service tools, appointment systems). The rejection is fixable with two edits, NOT a per-tenant ISV rebuild:
1. **Missing no-sharing disclosure** → added to §4 (bolded).
2. **Samples missing platform brand name** → §6 samples + §8 double opt-in now lead with `Pilot for Trades:`.

### Interpretation & decision (Architect, 2026-07-27)

Two conflicting signals from the same vendor: the human reviewer implied a per-tenant ISV model; the AI assistant says two copy fixes suffice. **The AI's path is not authoritative but is cheap, reviewer-aligned, and consistent with real 10DLC practice — so we try it FIRST.** Rev 2 applies both fixes. **Fallback if rev 2 also fails:** commit to the ISV per-tenant Brand+Campaign model, fold it into the SMS-2 add-on (contractor pays for their own brand/campaign/dedicated number via the Telnyx CSP API), and make SMS-2 the prerequisite for any customer SMS. Do NOT build the ISV flow until a second human rejection confirms it's required.

### Rev 2 — Prerequisite before resubmission

> **⚠️ Resubmission is BLOCKED on backend batch DLC-B4.** The `Pilot for Trades:` prefix in §6/§8 must match the live SMS templates (`seed_core.py` + `communication_template` rows + double opt-in in `sms_compliance.py`) or the first live message fails the §8 code↔portal match (error 806). DLC-B4 = prepend the brand prefix to all customer-facing SMS templates + update the double opt-in string. Deploy DLC-B4 → then resubmit with the rev-2 §4 disclosure + §6/§8 samples.

**Rev 2 resubmission checklist:**
- [x] DLC-B4 backend template-prefix batch shipped to production (2026-07-27) — all 11 SMS templates + double opt-in prefixed; idempotent migration `3131f106f1b9` applied; 8 new unit tests pass; full suite 4180 passed / 0 failed.
- [ ] §4 no-sharing disclosure pasted into Message Flow field
- [ ] §6 samples (all 5, brand-prefixed — incl. "Reminder:" in Sample 1 per DLC-B4 reconciliation) pasted
- [ ] §8 auto-replies + brand-prefixed double opt-in pasted (must match DLC-B4 code)
- [ ] Resubmit campaign; record new status here

---

*Maintained by: Tom + Pilot Architect. This is the single portal-submission playbook for the customer-communications 10DLC campaign. Update §1 with the assigned IDs on submit, §13 statuses as the end-to-end test completes, and §16 on each resubmission.*
