# `mvp-prd.md` v3.1 Update Instructions (Pass 4 Tier 1.5 — Customer Comms Extension)

**Purpose**: Update `mvp-prd.md` from v3.0 to v3.1 (interim version; v3.1 final issued at Pass 4 close to capture all Pass 4 product-level decisions). This update adds the Pass 4 Tier 1.5 product scope: bidirectional customer SMS, threading, free-form replies, voice-to-text, owner visibility, subscription SMS quota tier.

**Affected file**: `mvp-prd.md`
**Total edits**: 4 (1 doc header version bump; 1 §3.7 feature additions; 1 §3.11 subscription tier additions; 1 changelog entry)
**Estimated edit time**: 10–15 minutes — mostly paste-ins.

---

## Edit 1 — Doc header version bump and changelog entry

**Find** the version table at the top of the doc (around the changelog).

**Add a new row** for v3.1 at the top of the changelog table (above the existing v3.0 row):

```markdown
| 3.1 | Apr 27, 2026 | Pass 4 interim update for Tier 1.5 — Flow 4 Customer Communications Extension. Adds: bidirectional customer SMS messaging (inbound replies + outbound), conversation threading, free-form tech replies with voice-to-text composition, owner visibility surfaces (web Comm history extension + dashboard widget), subscription SMS quota tier (100 segments/month included; soft cap with overage billing or tenant-controlled hard cap), Telnyx as the carrier choice with carrier-agnostic adapter pattern, A2P 10DLC compliance as pre-launch hygiene. Resolves the Flow 4 Cross-Domain B (reply handling) and the customer-text-into-the-void operational gap. Full v3.1 with all Pass 4 product decisions issues at Pass 4 close. |
```

If the doc has a `**Version**: 3.0` line in the header (above or below the changelog), update it:

**Find**: `**Version**: 3.0` (or similar)
**Replace with**: `**Version**: 3.1 (interim — Pass 4 Tier 1.5 captured; full v3.1 issues at Pass 4 close with all Pass 4 product decisions)`

---

## Edit 2 — §3.7 Notifications & Communications feature extension

**Locate** §3.7's MVP Features table (line 357 in your v3.0; the section beginning "**Domain Purpose**: Deliver reliable, multi-channel...").

**Update the Domain Purpose paragraph** to reflect the bidirectional scope:

**Find**:
```markdown
**Domain Purpose**: Deliver reliable, multi-channel (email, SMS, push) communications to customers and technicians with full delivery auditability, strict regulatory compliance, and templated workflows that minimize per-message overhead.
```

**Replace with**:
```markdown
**Domain Purpose**: Deliver reliable, multi-channel (email, SMS, push) communications to customers and technicians with full delivery auditability, strict regulatory compliance, and templated workflows that minimize per-message overhead. SMS supports bidirectional customer-tech conversations with threading, free-form tech replies (voice-to-text supported), and full owner visibility — all customer communications stay inside Pilot, with the tech never needing to use their personal phone's SMS to reach customers.
```

**Add new feature rows** to the §3.7 MVP Features table. Insert these rows below the existing "Voice Intent Grammar for Customer Comms" row:

```markdown
| **Bidirectional SMS Conversation Threading** | Customer SMS replies route through Pilot to the originating tech with conversation threading by `(tenant_id, customer_id, tech_id, tenant_phone_number_id)`. Inbound messages display alongside outbound in chat-style chronological view. Customer never reaches the tech's personal phone — all SMS routes through the tenant's Pilot-assigned Telnyx number. |
| **Free-Form Tech Reply Composition** | Once a customer replies, the tech can compose free-form text responses through Pilot mobile (templates remain the only option for tech-initiated outreach). Free-form composition supports voice-to-text dictation as the primary input method, with touch typing as fallback. Tier 2 #5's "Customer activity" notification category gains forced-minimum push for inbound customer replies (the originating tech cannot mute push for this category). |
| **Voice-to-Text SMS Reply (Voice Intent)** | The voice intent `reply_to_customer_sms` extends Pilot's voice intent registry. Tech says "Reply to John saying running 30 minutes late," AI captures, transcribes via Whisper, renders preview with segment count + remaining quota, confirms via confirm-as-turn pattern, then dispatches via Telnyx. Always-preview-before-send safeguard applies to voice-composed replies. |
| **Owner Visibility — Web Comm History + Dashboard Widget** | The web `Customers > [customer] > Comm history` surface extends to render inbound and outbound messages in chat-style threaded view. A dashboard widget "Recent customer messages" provides ambient awareness of comm activity across the tenant. Owner mobile receives push for inbound customer messages per Tier 2 #5's "Customer activity" category default. |
| **Telnyx as MVP Carrier; Carrier-Agnostic Adapter Layer** | SMS infrastructure uses Telnyx as the MVP carrier. All carrier interactions go through an `SmsCarrier` adapter interface, allowing future provider swaps as a one-class change. A `MockSmsCarrier` implementation supports integration testing without real carrier API calls. |
| **One Telnyx Number per Tenant; Lazy Provisioning at First Use** | Each tenant gets one Telnyx phone number, provisioned at first SMS use rather than at signup (avoids number rental cost for tenants who never send SMS). Add-on numbers available at +$5/month each (manual provisioning via support in MVP; self-service is Phase 2). |
| **Mobile Inbox "Customer Messages" Sub-Section** | The mobile Today tab gains a "Customer messages" sub-section showing recent threads with unread counts. Tapping a thread opens the conversation thread screen with composition zone (voice-first, touch-fallback). |
| **A2P 10DLC Compliance as Pre-Launch Hygiene** | A2P 10DLC brand and campaign registration with The Campaign Registry is a hard prerequisite for reliable US carrier deliverability. Registration owned operationally by Tom; targets completion 4–6 weeks before MVP launch. Without 10DLC approval, SMS still sends but deliverability is poor (carrier filtering). |
```

**Update the existing "A2P 10DLC Compliance (SMS Opt-In Tracking)" row** to reflect both the legal opt-in tracking AND the new deliverability dependency:

**Find**:
```markdown
| **A2P 10DLC Compliance (SMS Opt-In Tracking)** | Customer SMS opt-in consent, opt-in timestamp, and opt-in source are stored per-record, meeting 2026 US carrier audit requirements. |
```

**Replace with**:
```markdown
| **A2P 10DLC Compliance (SMS Opt-In Tracking)** | Customer SMS opt-in consent, opt-in timestamp, and opt-in source are stored per-record, meeting 2026 US carrier audit requirements. Pilot-level brand and campaign registration with The Campaign Registry is a separate pre-launch operational requirement (see "A2P 10DLC Compliance as Pre-Launch Hygiene" feature row). |
```

**Update the existing "SMS STOP / Opt-Out Webhook Handler" row** to reference Telnyx (not Twilio):

**Find**:
```markdown
| **SMS STOP / Opt-Out Webhook Handler** | An inbound Twilio webhook handler processes customer "STOP" SMS replies, immediately setting the opt-out flag and timestamp on the customer record. This is a hard legal requirement under TCPA law and A2P 10DLC carrier rules. |
```

**Replace with**:
```markdown
| **SMS STOP / Opt-Out Webhook Handler** | The inbound SMS webhook handler (Telnyx in MVP; carrier-agnostic via the `SmsCarrier` adapter) processes customer "STOP" SMS replies, immediately setting the opt-out flag and timestamp on the customer record. This is a hard legal requirement under TCPA law and A2P 10DLC carrier rules. Customer "STOP" replies are detected during inbound message routing and bypass normal threading; they update the customer record directly. |
```

---

## Edit 3 — §3.11 Subscriptions & Usage — SMS quota tier

**Locate** §3.11's MVP Features table.

**Add new feature rows** below the existing "Admin Tenant Feature Override API" row:

```markdown
| **SMS Subscription Quota (100 Segments/Month Included)** | The $149/month base subscription includes 100 SMS segments per tenant per month, aligned to the subscription billing cycle. Add-on Telnyx numbers each add 100 segments to the tenant's monthly quota at +$5/month per number. |
| **Tenant-Controlled SMS Cap Policy (Soft / Hard)** | Tenants choose at the policy level: (a) soft cap (default) — tenant gets billed for SMS overages at $0.05/segment month-end with no operational interruption, or (b) hard cap — at 100% used, all outbound SMS is blocked until next billing cycle. Setting `sms_quota_cap_policy` (default `soft`); owner-only edit. |
| **In-Month SMS Usage Visibility** | Both tech and owner see current SMS segment usage and remaining quota in real-time: mobile composition zone shows segment count + remaining; web dashboard widget shows current, projected month-end, policy; mobile owner status row appears when usage exceeds 70%. Notifications fire at 80% and 100% usage thresholds. |
| **SMS Overage Billing** | Soft-cap tenants accrue overage charges at $0.05/segment month-end, added to the next subscription invoice as a line item. Failed sends are not counted (atomic rollback on carrier failure). MMS not included in MVP. |
```

The existing "Tiered Subscription Plans" and "Included Allowances & Hard / Soft Plan Limits" rows already cover the general pattern; the new SMS-specific rows surface the SMS tier as a distinct feature.

---

## Edit 4 — §4 Cross-Cutting Platform Patterns (or wherever cross-cutting patterns are formalized in PRD)

**If your PRD has a §4 or similar section formalizing cross-cutting platform UX vocabulary** (per the framework doc's mention that v3.0 "formalizes the cross-cutting platform UX vocabulary as product requirements in §4"), add these new patterns from Pass 4 Tier 1.5:

**Find** the existing list of cross-cutting platform patterns.

**Add these new entries**:

```markdown
- **Carrier-Agnostic Adapter Layer Pattern** — external service integrations (SMS carriers, payment processors, mapping providers, email services) live behind a thin adapter interface that abstracts the provider-specific API. Configured per-deployment via environment variable; future provider swaps are a one-class change. First instance: SMS via Telnyx (Pass 4 Tier 1.5).
- **Subscription Quota with Soft/Hard Cap Pattern** — subscription tiers include a metered allowance with tenant-controlled cap behavior: soft cap continues operating with overage billing; hard cap blocks at limit. Used for SMS quota (100 segments/month included; Pass 4 Tier 1.5). Available for any future per-event metered feature.
- **Lazy Provisioning of External Resource at First Use Pattern** — external resources with per-instance cost (Telnyx phone numbers in MVP; Phase 2 candidates: dedicated voice processing slots, customer-facing portal subdomains) are provisioned at first use rather than at tenant signup, avoiding cost waste for tenants who never use the feature. Pre-provisioning UI affordance available for tenants who want explicit setup.
```

If your PRD doesn't have a dedicated cross-cutting patterns section, these can be skipped — they're documented in the arch doc §16 / §17 instead.

---

## Edit 5 — Naming clarification (if your PRD still references Twilio)

The PRD v3.0 references "Twilio" specifically in the SMS STOP webhook handler row (already addressed in Edit 2). Search the rest of the PRD for any other "Twilio" references and update them to be carrier-agnostic ("SMS provider" or "the configured SMS carrier") or specifically mention "Telnyx" where appropriate.

Common locations to check:
- Cost analysis or scaling sections
- Phase 2 / future scope sections
- Any technical infrastructure mentions

---

## Verification checklist after edits

- [ ] Doc header version bumped to v3.1 with "interim" annotation (Edit 1)
- [ ] Changelog has new row for v3.1 with Pass 4 Tier 1.5 description (Edit 1)
- [ ] §3.7 Domain Purpose paragraph updated to reflect bidirectional SMS scope (Edit 2)
- [ ] §3.7 has 8 new feature rows for Tier 1.5 features (Edit 2)
- [ ] §3.7 existing "A2P 10DLC Compliance (SMS Opt-In Tracking)" row updated (Edit 2)
- [ ] §3.7 existing "SMS STOP" row updated to be carrier-agnostic / Telnyx (Edit 2)
- [ ] §3.11 has 4 new feature rows for SMS subscription quota (Edit 3)
- [ ] §4 (or equivalent) has 3 new cross-cutting pattern entries if applicable (Edit 4)
- [ ] No remaining "Twilio" references except where specifically appropriate (Edit 5)

After these edits, §3.7 grows from 12 features to roughly 19 features. §3.11 grows from 8 features to 12 features. The PRD overall grows by approximately 30–40 lines.

**Note on v3.1 framing**: this is intentionally an interim v3.1, not the final v3.1. The framework doc commits to issuing the full v3.1 at Pass 4 close that captures all Pass 4 product decisions (Tier 2 settings, Tier 3 onboarding, etc.). The interim v3.1 ensures the backend AI agent has accurate product context for SMS work without waiting for Pass 4 close. At Pass 4 close, the doc gets a more comprehensive v3.1 update (or v3.2 if interim v3.1 is treated as a published checkpoint).
