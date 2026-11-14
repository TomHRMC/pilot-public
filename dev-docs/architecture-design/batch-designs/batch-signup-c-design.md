# Batch SIGNUP-C — Signup Step 3 Redesign + Pathway C Platform Notifications

**Batch code**: SIGNUP-C (mixed: Python Engineer + React Engineer)
**Design doc owner**: Pilot Architect
**Created**: 2026-07-31
**Status**: 🟡 Draft — awaiting Tom approval before engineer prompts are authored
**Plan link**: `pilot-launch-plan.md`
**Related ADR**: ADR candidate — "Three-pathway SMS model; repurpose CXXXXXX as Pilot-sender platform-notifications campaign" (see §G)

---

## Problem Statement

The signup wizard's step 3 (`/signup/phone`) presents a "verify your phone" screen whose backend OTP endpoints (`/phone/send-otp`, `/phone/confirm-otp`) **do not exist** — `advance_signup_step3` only records `phone_verified`/`phone_skipped` booleans. It was originally intended to seed a phone number for **tenant→customer** job-alert SMS.

That original intent is **structurally impossible** under 10DLC: per `10dlc-registration-automation-requirements.md`, tenant→customer SMS (**Pathway B**) requires a **per-tenant brand + campaign** that clears TCR over a multi-day window — a number cannot exist for a tenant on signup day. The shared customer-comms campaign `CXXXXXX` was **rejected by Telnyx** (2026-07-27) for exactly this reason: *"each business will need a brand and campaign created specifically for them."*

**Decision (Tom, 2026-07-31):** Repurpose this screen and the `CXXXXXX` campaign for a new **Pathway C — Pilot → tenant-owner platform notifications** (system alerts, maintenance, billing/security). Pilot is the genuine sender, making it the compliance-clean single-brand case Telnyx wants. Pathway B (tenant→customer) defers entirely to a future per-tenant SMS-2 add-on; **there is no shared customer-comms campaign**.

**Consent-UX decision (Tom, 2026-07-31):** phone is **required**, but the SMS-alerts consent checkbox is **UNCHECKED by default** — the cleanest, lowest-risk 10DLC posture (no pre-checked-box scrutiny). The reply-YES double-opt-in remains the authoritative consent. The disclosure block must carry the **full required 10DLC CTA language** per the Telnyx-doc learnings (program name, message types, "Msg freq varies", "Msg & data rates may apply", STOP/HELP, Privacy Policy link, no-sharing statement).

---

## A. Input Read Summary

| Input | Section(s) read | What it established |
|---|---|---|
| `telnyx-10dlc-customer-comms-campaign.md` | §4, §6, §8, §16 | `CXXXXXX` rejected as B2B2C; double-opt-in "Reply YES" is the load-bearing consent; STOP/START/HELP strings |
| `10dlc-registration-automation-requirements.md` | §1 | Per-tenant brand+campaign is locked for Pathway B; SMS not live day-one |
| `pilot-operations.md` | §13.1, §13.12 | Two-pathway model (A=Cognito/SNS, B=Telnyx). This batch adds Pathway C |
| `tenant_signup.py` | `VALID_STATE_TRANSITIONS`, `_process_step_data` | step3 records booleans only; no OTP wired |
| `sms_compliance.py` | `_send_double_optin_sms_impl` | Existing double-opt-in resolves FROM from **tenant** `TenantPhoneNumber` (Pathway B). Pathway C needs a **platform** FROM number |
| `webhooks_sms.py` | STOP/START/HELP/YES routing | Reusable inbound handler; must learn to resolve `user_endpoint` (not just `customer`) |
| MCP `user_endpoint` | full column list | Already has `channel, value, verification_status, verified_at, consent_status, consent_updated_at` — **all Pathway C consent primitives exist** |
| MCP `notification_channel` | rows | `sms` channel exists and `is_active=true` |
| MCP `notification_category` | rows | `system_announcements` + `billing` categories already exist — Pathway C routes through these |
| MCP `notification_preference` | columns | Per-user, per-category, per-channel `enabled` flag already exists |
| MCP `alembic_version` | — | Current head: `990231f963b0` |

---

## Key Architectural Decision: Reuse the Notification Subsystem, Add No `user` Consent Columns

The live DB already contains a complete notification/consent substrate. Pathway C composes it rather than adding columns to `user`:

| Need | Existing mechanism | New work |
|---|---|---|
| Store owner mobile + consent | `user_endpoint` (channel=`sms`, value=phone, `consent_status`, `verification_status`) | Populate `sms` channel rows (currently only email/in_app/push exist; the `user_endpoint_channel_chk` **already allows** `sms` — MCP-verified) |
| Per-category opt-in | ⚠️ **NOT used at MVP** — `notification_preference.chk_notif_pref_channel` allows only `push/email/in_app` (MCP-verified), so `sms` prefs cannot be stored there without a CHECK migration | **None** — send-time gates on `user_endpoint.consent_status='opted_in'`; a per-category sms pref layer is a future add (would require extending the CHECK) |
| Verify number + seal consent | double-opt-in "Reply YES" | New **platform-sender** variant (Pilot FROM number) |
| STOP/START/HELP | `webhooks_sms.py` | Extend to resolve `user_endpoint` targets |
| Consent audit trail | `customer_sms_consent_audit` (customer-scoped) | New `user_sms_consent_audit` OR reuse pattern (see §B open item) |

**The single genuinely new infrastructure concept** is a **platform SMS sender**: Pathway C's FROM number is Pilot's ONE shared number (repurposed `CXXXXXX`), stored in Secrets Manager `pilot/prod/telnyx`, **not** a per-tenant `TenantPhoneNumber` row. The existing `sms_compliance.py` hard-resolves FROM from the tenant — Pathway C needs a distinct `send_platform_double_optin_sms` task that reads the platform number from config.

---

## B. Migration Plan

**Pre-migration state (MCP-verified, head `990231f963b0`):**
- `user_endpoint` exists with all needed consent columns; `channel` currently only holds `email|in_app|push`.
- `notification_channel.sms` active. `notification_category` has `system_announcements`, `billing`.
- `user.phone_number` exists (nullable varchar) — retained as the display copy; `user_endpoint.value` is the authoritative consent-bearing record.

**Migration 1 — `user_sms_consent_audit` table** (mirrors `customer_sms_consent_audit` for the owner surface; TCPA requires an immutable consent trail):

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | uuid | NO | PK |
| `tenant_id` | uuid | NO | tenant-scoped |
| `user_id` | uuid | NO | FK → `user.id` |
| `user_endpoint_id` | uuid | YES | FK → `user_endpoint.id` |
| `action` | text | NO | CHECK — **mirror `customer_sms_consent_audit` vocabulary**: `attested` \| `double_opt_in_sent` \| `double_opt_in_confirmed` \| `opted_out` (MCP-verified list). `attested`=checkbox at signup; `double_opt_in_sent`=platform text sent; `double_opt_in_confirmed`=owner replied YES; `opted_out`=STOP |
| `consent_text_hash` | text | NO | SHA-256 of disclosure text shown at signup |
| `ip_address` | text | YES | request IP at attestation (matches source table where it's NOT NULL — but owner opt-out via webhook has no IP, so nullable here) |
| `attested_at` | timestamptz | NO | |
| `created_at` | timestamptz | NO | from `AppendOnlyMixin` (do NOT hand-declare) |
| `created_by` | uuid | YES | from `AppendOnlyMixin`; FK → `user(id)` ON DELETE RESTRICT |

- **Mixin:** `AppendOnlyMixin` (mirrors `customer_sms_consent_audit`). Add `tenant_id` explicitly (mixin does not provide it). **No `updated_at`.**
- **Triggers: NONE.** MCP-verified that `customer_sms_consent_audit` carries **no** database triggers — append-only immutability is enforced at the ORM layer via `AppendOnlyMixin`, not a DB `immutable_guard` trigger. Do **not** add `audit_log`/`immutable_guard`/`updated_at_sync` triggers (that would diverge from the established consent-audit pattern).
- **FKs (mirror source):** `tenant_id`→`tenant(id)`, `user_id`→`user(id)`, `user_endpoint_id`→`user_endpoint(id)`, `created_by`→`user(id)` — all `ON DELETE RESTRICT`.
- No `NOT NULL`-on-existing-table changes → no 3-part pattern required.

**Migration 2 — DROPPED (2026-07-31, post-MCP).** The original plan seeded `notification_preference` sms rows, but MCP-verified `chk_notif_pref_channel` allows only `push/email/in_app` — an sms pref row would violate the CHECK. **No `notification_preference` change at MVP.** Send-time eligibility gates purely on `user_endpoint.consent_status='opted_in'` (which the `user_endpoint_channel_chk` and `consent_status_chk` both support). A per-category sms-preference layer is a deliberate future add (needs a CHECK-extension migration first).

> **MCP-verified for Migration 1 (2026-07-31):** `customer_sms_consent_audit` (the mirror source) has **NO database triggers** — it uses the ORM `AppendOnlyMixin` (`created_at`, `created_by` only; no `updated_at`). Its FKs are all `ON DELETE RESTRICT` to `user(id)`, `tenant(id)`, `customer(id)`. Its action CHECK values are `attested / double_opt_in_sent / double_opt_in_confirmed / opted_out`. `user_sms_consent_audit` must mirror this exactly: `AppendOnlyMixin`, no hand-rolled timestamps, no triggers, FKs `ON DELETE RESTRICT`, and reuse the **same action vocabulary** (see §F revised action list). `user_sms_consent_audit` confirmed **not to exist** yet.

---

## C. Execution Order

| # | Step | Owner | Status |
|---|---|---|---|
| 1 | Migration 1 (`user_sms_consent_audit`) + Migration 2 (sms default prefs) | Python | ✅ (Migration 2 dropped per §B) |
| 2 | `send_platform_double_optin_sms` Celery task (platform FROM number from config) | Python | ✅ |
| 3 | Extend `webhooks_sms.py` to resolve `user_endpoint` targets for STOP/START/HELP/YES | Python | ✅ |
| 4 | New endpoints §D (send-otp / confirm reframed as consent + double-opt-in) | Python | ✅ |
| 5 | `advance_wizard_step` step3: require phone; write `user_endpoint` + audit; enforce consent | Python | ✅ |
| 6 | OpenAPI regenerate → `python export_openapi_json.py`; handoff `pnpm sync-api-types` | Python → React | ✅ |
| 7 | Redesign `/signup/phone` → "Stay Informed" (required phone, unchecked-by-default consent, disclosure) | React | ✅ |
| 8 | Reframe `PhoneOtpSubscreen` from fake OTP to real double-opt-in confirmation state | React | ✅ |

---

## D. New / Changed API Endpoints

All under the existing `/api/v1/signup` router (JWT-gated post-verify, per current wizard).

| Path | Method | Auth | RBAC | Request | Response | Errors |
|---|---|---|---|---|---|---|
| `/{tenant_id}/phone/consent` | POST | JWT | `tenant.signup.complete` | `{ phone_number, sms_consent: bool, disclosure_hash }` | `{ user_endpoint_id, verification_status: "pending" }` | 422 invalid phone; 409 endpoint exists |
| `/{tenant_id}/phone/send-optin` | POST | JWT | `tenant.signup.complete` | `{ user_endpoint_id }` | `{ status: "sent" }` | 422 no phone; 429 resend cooldown |
| `/{tenant_id}/step3` | PUT | JWT | `tenant.signup.complete` | `{ phone_number (required), sms_consent (bool) }` | `SignupStepResponse` | **422 phone required** (skip removed) |

**Behavioral changes vs today:**
- **Phone is required** — `phone_skipped` path is removed from step3 (Tom decision). `_process_step_data` step3 branch rewritten.
- The consent checkbox is **unchecked by default** and drives `sms_consent`; the **reply-YES double-opt-in is the authoritative consent** (checkbox alone never sends beyond the confirmation text). If the box is left unchecked, phone is still stored on `user.phone_number` (for MFA reuse) but the `sms` `user_endpoint` is created with `consent_status='unknown'` and **no** double-opt-in SMS is sent. Send-time eligibility = `user_endpoint.consent_status='opted_in' AND verification_status='verified'`.
- `confirm-otp` is replaced by the inbound webhook: the owner replies **YES** to the platform number → `webhooks_sms.py` flips `user_endpoint.consent_status='opted_in'`, `verification_status='verified'`, writes `opted_in` audit row.

---

## E. Pattern Reuse Decisions (`mvp-arch.md` §16)

- **Always-Preview-Before-Send** — N/A (transactional).
- **Two-Tier Configuration (system-default / tenant-override)** — sms notification prefs use the existing default-policy → user-preference cascade; no new pattern.
- **Idempotency** — `send-optin` and `step3` POST/PUT must accept `Idempotency-Key` (mobile-offline resolvable), per infra rules.
- **Optimistic UI** — the "Stay Informed" confirmation state shows "Text sent — reply YES" optimistically; webhook confirmation updates status via existing polling on `/state`.

---

## F. Shared Module Interfaces & Celery Tasks

```
tasks/sms_compliance_platform.py
  def _send_platform_double_optin_sms_impl(user_id: str, tenant_id: str) -> dict
      # FROM = platform number (config: PILOT_PLATFORM_SMS_NUMBER / Secrets pilot/prod/telnyx)
      # TO   = user_endpoint.value (channel='sms')
      # Body = _PLATFORM_DOUBLE_OPTIN_TEMPLATE (Pilot-sender, Account Notifications)
      # Writes user_sms_consent_audit(action='double_opt_in_sent')
  @celery_app.task ... wrapper

services/notification_endpoints.py (extend)
  def upsert_owner_sms_endpoint(db, user_id, tenant_id, phone, consent, ip, disclosure_hash)
      # user_endpoint has NO unique constraint on (user_id,channel,value) — MCP-verified.
      # Idempotency = value-scoped DELETE+INSERT (delete WHERE user_id AND channel='sms' AND value=phone),
      #   per seed-safety §11.1 analog. Sets consent_status='opted_in' if consent else 'unknown',
      #   verification_status='pending'. Writes user_sms_consent_audit(action='attested').
      # webhooks_sms.py YES handler → consent_status='opted_in', verification_status='verified',
      #   audit action='double_opt_in_confirmed'. STOP handler → 'opted_out' + audit action='opted_out'.
```

**Canonical SMS strings (MUST match the Telnyx submission — `telnyx-10dlc-p4t-tenant-comms-campaign.md` §6/§8).** The §6↔§8 code-match rule means the backend must emit these verbatim or the first live message fails MNO review (error 806):

| Template | String |
|---|---|
| `_PLATFORM_DOUBLE_OPTIN_TEMPLATE` (first message) | `Pilot for Trades: Reply YES to get important account, billing & security alerts by text. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.` |
| STOP reply | `You have been unsubscribed from Pilot for Trades account alerts. No further messages will be sent. Reply START to re-subscribe.` |
| START/UNSTOP/YES reply | `Pilot for Trades: You're opted in to account, billing & security alerts. Msg freq varies. Msg & data rates may apply. Reply HELP for help, STOP to cancel.` |
| HELP/INFO reply | `Pilot for Trades account alerts. For help, visit pilotfortrades.com or email info@pilotfortrades.com. Msg & data rates may apply. Reply STOP to unsubscribe.` |
| Billing sample (`notification_template` sms row) | `Pilot for Trades: Your payment didn't go through. Please login to app.pilotfortrades.com and update your credit card to keep your account active. Reply STOP to opt out.` |
| Security sample | `Pilot for Trades: New sign-in to your account from a new device. If this wasn't you, secure your account now. Reply STOP to opt out.` |
| Maintenance sample | `Pilot for Trades: Scheduled maintenance {window}. The app may be briefly unavailable. Reply STOP to opt out.` |

> **Keyword note (Telnyx UI constraint):** portal keyword lists are **comma-delimited with no spaces** (`STOP,STOPALL,UNSUBSCRIBE,QUIT,CANCEL,END,ARRET` / `START,UNSTOP,YES` / `HELP,INFO`). The `webhooks_sms.py` inbound matcher is unaffected (case-insensitive per-keyword parse), but portal/doc copy must use the no-space comma form.

---

## G. Open Questions Resolved

1. **New `user` columns vs reuse `user_endpoint`?** → **Reuse `user_endpoint`.** It already carries `consent_status`/`verification_status`. No `user` schema change. *(MCP-verified.)*
2. **Marketing/promos in this campaign?** → **No.** Transactional-only (Account Notifications) for fastest TCR approval. Promotions become an **email** channel later (post-Founders), needing zero 10DLC. *(Tom, 2026-07-31.)*
3. **Repurpose `CXXXXXX` or file new?** → **Repurpose `CXXXXXX`** as the single Pilot-sender platform-notifications campaign. *(Tom.)*
4. **Shared customer-comms campaign?** → **None.** Pathway B defers to per-tenant SMS-2 add-on. *(Tom.)*
5. **Phone required or optional?** → **Required.** Consent checkbox **unchecked by default**, user-toggleable; reply-YES seals consent. *(Tom, 2026-07-31.)*
6. **Compliance posture of the checkbox?** → **Unchecked by default** — the lowest-risk 10DLC posture, eliminating pre-checked-box scrutiny entirely. Disclosure carries full required CTA language. Reply-YES double-opt-in is authoritative. *(Tom, 2026-07-31.)*
7. **ADR needed?** → **Yes** — clears the §7.1 bar: architecturally significant (new SMS pathway + compliance model), multiple viable options (per-tenant ISV vs single-sender), crosses boundaries (signup, notifications, Telnyx integration, ops doc). Author ADR on approval.

---

## H. Surface Mockup Reference (Frontend) — ✅ Implemented

- **Surface:** `/signup/phone` — web-only (signup wizard is web `apps/web`). Reframed from "Verify phone" → **"Stay Informed."**
- **Designer owner:** `pilot-web-ui-designer` → spec at `dev-docs/architecture-design/batch-designs/batch-signup-c-ui-design-spec.md` (to author after this design is approved; Tom-approved before React prompt).
- **Content requirements for the designer:**
  - Required mobile phone field (validated E.164).
  - Consent checkbox **unchecked by default**, toggleable, with an **enticing benefit-forward label** that motivates opting in (e.g., *"Yes — text me if there's a problem with my account, a billing issue, or a security alert so I never miss something urgent."*).
  - Compliance disclosure block with all text spelled out for easy reading (program name "Pilot for Trades", message types "account, billing & security alerts", "Msg freq varies", "Msg & data rates may apply", STOP/HELP, Privacy Policy link) — this renders the **TCR consent screenshot** for `CXXXXXX` resubmission.
  - Post-submit "reply YES" confirmation sub-state (replaces the fake 6-digit OTP grid).
  - WCAG 2.2 AA: color-independent status, ≥24×24px targets, `focus-visible`, `prefers-reduced-motion`.

## I. Component Manifest (Frontend)

| Component | Path | New/Change | Status |
|---|---|---|---|
| `StayInformedStep` (reframed phone page body) | `apps/web/src/app/signup/phone/page.tsx` | Change | ✅ |
| `SmsConsentDisclosure` | `apps/web/src/features/signup/components/SmsConsentDisclosure.tsx` | New — designer-confirmed not in `packages/ui` (`SmsOptOutBadge` is unrelated) | ✅ |
| `DoubleOptinConfirmSubscreen` | `apps/web/src/features/signup/components/DoubleOptinConfirmSubscreen.tsx` | New (replaces the deleted `PhoneOtpSubscreen`) | ✅ |
| `PhoneOtpSubscreen` | `apps/web/src/features/signup/components/PhoneOtpSubscreen.tsx` | **Delete** (fake OTP grid removed) | ✅ Deleted |
| `WizardProgressBar` | `apps/web/src/features/signup/components/WizardProgressBar.tsx` | No change (reused) | ✅ Reused |

> Manifest reconciled with the Tom-gated UI spec (`batch-signup-c-ui-design-spec.md`) — no orphan components.

---

## Cost Impact (infra guardrail check)

Pathway C is a **fixed** cost shared across all tenants: one campaign (~$1.50–2/mo) + one number (~$1/mo) ≈ **$3/mo total**, already effectively budgeted (the old customer-comms plan assumed one shared number). Per-tenant Pathway B cost **moves out** of Pilot COGS into the tenant-paid SMS-2 add-on. **Net effect on the $888 baseline: neutral-to-favorable.** No new AWS service. ✅ Within guardrails.
