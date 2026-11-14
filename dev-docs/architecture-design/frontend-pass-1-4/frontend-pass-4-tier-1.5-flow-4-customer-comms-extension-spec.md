# Pilot for Trades Design System — Pass 4, Tier 1.5: Flow 4 Customer Communications Extension

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Inbound SMS handling for customer-tech conversations. Threading, free-form tech replies, voice-to-text reply composition, owner visibility from web, subscription quota management, carrier-agnostic adapter layer. Resolves Flow 4 Cross-Domain B (reply handling) and the original Flow 4 deferred items "Inbound reply handling" and "Free-form messaging."
**Resolves**: `frontend-pass-3-flow-4-customer-comms-spec.md` Cross-Domain B; deferred item "Inbound reply handling"; deferred item "Free-form messaging" (now in scope for replies only)
**Depends On**: Pass 3 Flow 4 (customer comms outbound) · Pass 4 Tier 1 #3 (push token registry — A51) · Settings IA framework · Tier 2 #4 mockups · `mvp-arch.md` §3.7 (Notifications & Comms)
**Backend additions**: A59–A66 (eight new additions; see backend additions section below)
**Deliverable shape**: Shape A (Full flow spec) per Pass 4 framework doc

---

## Purpose

Flow 4 today is outbound-only. A tech sends a templated message ("On my way, ETA 20 min"). The customer might reply ("I'm not home, can we reschedule?"). That reply has nowhere to go in current Pilot — Twilio receives it, the webhook isn't wired up, and the tech shows up to an empty house. This is a trust-shattering moment that kills early adoption.

Tier 1.5 closes the gap. The strategic frame: **all customer communication stays inside Pilot**. The tech never uses their own phone's SMS to text a customer. The customer texts a Pilot-owned phone number; Pilot routes the message to the right tech and to the owner's visibility surface; the tech replies through Pilot using free-form composition (with voice-to-text dictation); the conversation threads coherently from both sides.

This extension also locks the **carrier choice** (Telnyx) and a **carrier-agnostic adapter layer** so future provider swaps are a one-class change. It locks the **subscription tier model** for SMS (100 segments/month included; overage billing with tenant-controlled hard cap option). And it formalizes the **A2P 10DLC compliance dependency** as pre-launch hygiene (Tom-owned operational work that must complete 4–6 weeks before launch).

The original Flow 4 spec stays intact and is the source of truth for outbound templated messaging, voice intent grammar, customer channel preference, and the always-preview-before-send pattern. This extension adds the inbound and reply scope without modifying any locked Flow 4 outbound decision.

## Strategic direction

### All customer comms stay in Pilot — non-negotiable

The product principle that drives every decision in this extension. If the tech can use their personal phone for SMS, three things break: (1) the owner has no visibility into what was said, (2) the customer might end up texting both the Twilio number and the tech's personal cell creating fragmented threading, (3) the audit trail breaks for any compliance or dispute review. The architecture enforces this principle by routing all customer SMS through Pilot's Telnyx number; the tech literally never sees the customer's phone number on their own device's messaging app.

### Templates for initiation; free-form for replies

Original Flow 4's templates-only stance was correct for outbound initiation — templated messages give clean audit trails, no moderation risk, fast field operation. This extension preserves that posture for tech-initiated outreach.

Once the customer replies, the tech is in a conversation. Forcing them to pick a template to respond is contextually wrong. Free-form composition (with voice-to-text input and segment counter) is the right tool for replies. This is a defensible scope cut: free-form is allowed only when responding to an inbound message, not when initiating contact.

Phase 2 may relax this further (AI-suggested replies, intent classification, automated responses) but MVP keeps the line clean: tech-initiated = template; tech-responding = free-form.

### Voice-to-text is the intended primary input for replies

Pilot is voice-first. A tech with gloved hands at a job site can dictate "running 30 minutes late, sorry, see you soon" much faster than thumb-typing it. The Whisper infrastructure exists. The voice intent grammar from Flow 1 extends naturally to message composition.

The free-form reply UI defaults to voice input mode with a touch-to-type fallback. Touch typing is supported but not the primary path.

### One Telnyx number per tenant for MVP; per-tech is Phase 2

Each tenant gets one Telnyx number that all customer-facing SMS routes through. Solo Mike has one number; multi-person shops share one number with internal routing by `customer_id × tech_id × thread_id`. The customer sees a single stable number for the tenant's communications.

Per-tech numbers (each tech gets their own dedicated Telnyx number) is a Phase 2 nice-to-have. Cleaner customer experience but ~$1 more per month per tech and more provisioning logic. Out of MVP scope.

Tenants can add additional numbers at a per-number monthly fee (Decision 11 below) for use cases like separate marketing numbers, multi-location operations, or branding preferences.

### Carrier-agnostic adapter layer is non-speculative

Telecom carriers have a long history of pricing changes, deliverability issues, acquisitions, and policy shifts. A thin adapter (`SmsCarrier` interface with a `TelnyxSmsCarrier` implementation) costs roughly half a day of architecture work and makes future provider swaps a one-class change rather than a rewrite. This is cheap insurance, not over-engineering.

The adapter also enables a `MockSmsCarrier` implementation for integration testing without making real carrier API calls — essential for testing the end-to-end SMS flows reliably.

### Subscription quota with soft cap, optional hard cap, owner-controlled

100 SMS segments per month included in the $149 base subscription. Beyond 100, tenants choose at the policy level: (a) **soft cap** — tenant gets billed for overages at $0.05/segment, (b) **hard cap** — tech literally can't send more SMS until next billing cycle. Default is soft cap. Hard cap is for tenants with strict cost-control requirements.

In-month visibility is non-negotiable: both tech and owner can see current segment usage, remaining quota, and projected month-end usage. Cost surprises kill subscription products.

## Locked design decisions

### 1. Twilio number provisioning per tenant — Telnyx as MVP carrier

**Decision**: Each tenant gets one Telnyx phone number, provisioned at tenant signup (or first SMS use, see Decision 12 below for sequencing). Number rental: ~$1.00/month, paid by Pilot, included in the $149 subscription.

**Carrier**: Telnyx for MVP. The carrier-agnostic adapter layer (Decision 13) makes future swaps cheap, but the operational work for MVP is Telnyx-specific.

**Number selection**: tenant chooses an area code at provisioning time (default: tenant's primary office area code from their address). If the area code is unavailable, the system suggests three nearby alternatives.

**Tenant-visible affordance**: at `Settings > Integrations > SMS messaging`, the tenant sees their assigned number, can copy it to clipboard, and (in Phase 2) can request a new number. MVP: number assignment is sticky once provisioned.

**Rationale**: One-per-tenant is the right cost-complexity trade-off for MVP. Solo operators ship with one number, multi-person shops scale within the same number via threading. Per-tech numbers is genuinely cleaner from a customer-experience standpoint but costs ~$1/tech/month and adds provisioning logic that doesn't materially improve the MVP value.

### 2. A2P 10DLC compliance is the hard prerequisite — owned by Tom, blocks launch

**Decision**: A2P 10DLC brand registration and campaign approval must complete before MVP launch. This is operational work owned by Tom; it does not block the design or backend implementation but it does block the ability for any customer SMS to actually deliver reliably.

**Realistic timeline**:
- Brand registration: 1–2 weeks for approval
- Campaign approval per use case: 1–2 weeks after brand approval
- Total: 4–6 weeks from start to delivery-ready

**Use case to register**: "Customer service / appointment notifications for trades businesses" (or similar; Telnyx can advise on the specific The Campaign Registry classification).

**Risk if not approved**: messages will be filtered by US carriers (T-Mobile, AT&T, Verizon) and either not delivered or delivered with terrible deliverability. This is not optional or nice-to-have.

**Captured as a pre-launch hygiene item** in the framework doc; framework doc gets a row added for this.

**Rationale**: 10DLC isn't a Pilot or Telnyx requirement; it's a US carrier requirement flowing through whichever provider you pick. Switching to Twilio, Plivo, or SignalWire wouldn't avoid it. Treating it as the hard prerequisite it is — not a nice-to-have — is the correct framing.

### 3. Inbound webhook: Telnyx → Pilot → routing

**Decision**: Inbound flow:

```
Customer SMS → Telnyx → Pilot webhook (signature verified) →
  Pilot's customer_communication_thread engine →
  Push notification to originating tech +
  Push notification to owner (if their preferences allow) +
  Update web communication history surface +
  Update mobile job detail surface +
  Update tech's mobile inbox tab
```

**Webhook endpoint**: `POST /api/v1/webhooks/sms/telnyx-inbound` receives Telnyx's webhook payload, verifies signature, threads the inbound to the right conversation, and dispatches notifications.

**Threading logic** (Decision 4 below) determines which tech and which job context the inbound belongs to.

**Failure handling**: if signature verification fails, return 401 (Telnyx will retry per its policy). If threading fails (no matching outbound found), the inbound is parked in an "unrouted" queue with an alert to the owner ("a customer texted but we couldn't tell who they were responding to — review on web"). This is a rare edge case but real (e.g., customer texts the Pilot number cold without an outbound preceding).

**Rationale**: Standard webhook → routing → notification pipeline. The unrouted-message handling is the design nuance — silently dropping messages would violate the "all customer comms in Pilot" principle, but auto-creating a conversation without context could create false-positive customer relationships.

### 4. Threading model — `customer × tech × tenant_phone_number` as the conversation key

**Decision**: A conversation thread is keyed by `(tenant_id, customer_id, tech_id, tenant_phone_number_id)`. Inbound messages are matched to a thread by:

1. **Sender phone number** → look up `customer.phone` matching this number for this tenant
2. **Recipient phone number** → matches the tenant's Telnyx number
3. **Most recent outbound thread** → if the customer has multiple recent outbound conversations from different techs, the inbound matches the most recent one (within a 7-day window)

If no thread is found within the 7-day window, a new thread is created with the most recently active tech for that customer (per `customer.last_assigned_tech_id`). If still no match, the inbound goes to the unrouted queue per Decision 3.

**Schema** (captured in A60 below):

```
customer_communication_thread
  thread_id              UUID PK
  tenant_id              UUID
  customer_id            UUID
  tech_id                UUID
  tenant_phone_number_id UUID  -- links to the Telnyx number
  status                 TEXT  -- 'active' | 'archived'
  first_message_at       TIMESTAMPTZ
  last_message_at        TIMESTAMPTZ
  message_count          INT
  created_at             TIMESTAMPTZ
  updated_at             TIMESTAMPTZ

customer_communication_message
  message_id             UUID PK
  thread_id              UUID FK
  direction              TEXT  -- 'outbound' | 'inbound'
  channel                TEXT  -- 'sms' (MMS Phase 2)
  body                   TEXT
  segment_count          INT   -- for billing/quota
  status                 TEXT  -- 'pending_send' | 'sent' | 'delivered' | 'failed' | 'received'
  carrier_message_id     TEXT  -- Telnyx's message ID
  sent_at, delivered_at, received_at TIMESTAMPTZ
  composition_method     TEXT  -- 'template' | 'free_form_text' | 'free_form_voice'
  template_id            UUID NULL  -- for templated outbound
  voice_audio_id         UUID NULL  -- for voice-dictated replies, links to voice_command_log
  audit_user_id          UUID  -- the tech who sent (for outbound) or the tech the inbound was routed to
```

**Rationale**: Threading by `customer × tech` rather than just `customer` lets multi-person shops route correctly when two techs have worked with the same customer. The 7-day window for matching inbound to recent outbound is a reasonable default — most customer replies come within hours, occasionally within days, almost never beyond a week. The unrouted queue handles the edge cases without dropping anything silently.

### 5. Push notification to originating tech — forced minimum

**Decision**: When an inbound SMS routes to a tech, push notification fires to the tech's mobile device(s) immediately. This is a **forced-minimum push** in the Tier 2 #5 notification preference matrix sense — the tech cannot mute push for customer replies. Email and in-app channels are user-configurable.

**Push payload**:
- Title: "New message from [Customer name]"
- Body: First 80 characters of the message body (truncated with ellipsis if longer)
- Tap action: opens the conversation thread on the job detail screen

**Rationale**: The whole point of inbound SMS is the tech sees it in time to act. Allowing push to be muted for this category recreates the operational hole. Forced minimum is appropriate. This is the fourth forced-minimum category in MVP (alongside Field issues, Job activity assignment-only, and System announcements critical-only — all from Tier 2 #5 Decision 4).

**Tier 2 #5 spec update needed**: when Tier 2 #5 is drafted, the "Customer activity" category gains forced-minimum push for inbound customer replies (sub-trigger), parallel to how Job activity has forced-minimum push for assignment-only.

### 6. Owner visibility — web communication history extends; mobile owner gets notification

**Decision**: The web `Customers > [customer] > Comm history` surface from Flow 4 §10 extends to include inbound messages. Both directions render in the same chronological list with clear visual distinction (outbound: brand-indigo left-aligned bubble; inbound: neutral right-aligned bubble; like every messaging app).

**New web surface — top-level dashboard widget**: a "Recent customer messages" widget shows the last 10 customer-tech messages across the tenant, color-coded by direction, sorted by recency. Owner gets ambient awareness of comm activity without drilling into individual customers. This widget is added to the dashboard's customizable widget grid (per Pass 2 §5 pin-to-dashboard pattern).

**Mobile owner**: gets push notification for inbound customer messages per Tier 2 #5 default policy (the "Customer activity" category defaults to push ON for owners). Owner can mute this category if desired (it's not forced-minimum for owners — only for the tech who's actively in the conversation). Tapping the push opens the comm history in the mobile owner tab.

**Rationale**: Owner visibility was the second-half of your stated product principle ("the owner can see them and knows what is going on, from the web interface obviously though"). The web Comm history surface already exists from Flow 4; extending it for inbound is a natural fit. The dashboard widget is an additional ambient-awareness affordance for owners who don't want to drill into individual customer pages but want a feel for what's happening across the team's customer interactions.

### 7. Tech mobile reply UI — free-form composition with voice-to-text default

**Decision**: When the tech taps a customer message in the inbox tab, the job detail screen, or the push notification, they land on the **conversation thread screen**. This screen shows:

- **Thread header**: customer name, customer phone (display only), originating job context if available
- **Message list**: chronological conversation, scrollable, newest at the bottom
- **Message composition zone** at the bottom of the screen:
  - Voice button (mic icon) — primary, prominent (Pilot's voice-first posture)
  - Text input field — secondary, single-line that expands as needed
  - Send button — disabled until message has content
  - Segment counter — small annotation: "1 segment" or "3 segments · 47 segments remaining this month"

**Voice-to-text composition flow**:
1. Tech taps the voice button
2. Whisper captures audio (per existing Flow 1 voice infrastructure)
3. Transcribed text appears in the input field
4. Tech can edit the transcription (touch typing) before sending
5. Tech taps Send → message dispatches via Telnyx adapter
6. Message appears in the thread immediately with optimistic-UI pending badge until carrier confirms delivery

**Touch typing fallback**:
- Tech taps the input field directly (instead of voice button)
- Standard mobile keyboard input
- Same Send behavior

**Segment counter live-updates** as the tech types or after voice transcription completes. If the message will exceed the tenant's remaining quota, the counter turns amber with helper text: "*This message will exceed your monthly quota. Will incur overage charges* / *Will be blocked by your hard cap* (depending on tenant policy per Decision 8)."

**Rationale**: Voice-first because Pilot is voice-first. Touch fallback because not everywhere is good for voice (tech in a quiet customer's home, tech at night not wanting to disturb others). Segment counter is critical for cost predictability — without it, techs burn quota dictating long replies and discover overages at billing time. Optimistic UI matches the platform pattern (arch doc §16.8).

### 8. Subscription quota tier model

**Decision**: SMS quota tier:

| Aspect | Value |
| :--- | :--- |
| Included in $149/month | 100 SMS segments per month per tenant (rolling monthly cycle aligned to subscription billing) |
| Add-on numbers | $5/month per additional number; each adds 100 segments to quota |
| Cap policy | Tenant chooses: soft cap (default) or hard cap |
| Soft cap behavior | Notification at 80%, 100% usage; overages billed at $0.05/segment month-end |
| Hard cap behavior | At 100% usage, all outbound SMS blocked until next billing cycle; tech sees "monthly SMS quota reached — contact your owner" when attempting to send |
| Overage billing | $0.05/segment over included amount (10x markup over Telnyx cost) |
| MMS | Not included in MVP |
| Inbound SMS | Not counted against quota (Telnyx inbound is ~$0.002, effectively free; rolled into base subscription) |

**Tenant-controlled cap policy**: a tenant setting `sms_quota_cap_policy` with values `soft | hard`. Default `soft`. Owner-only edit. Lives at `Settings > Subscription & Billing > SMS quota` (a new sub-page).

**In-month visibility surfaces**:
- **Tech mobile**: the segment counter on the composition zone shows "X segments remaining this month" when below 80% usage; turns amber at 80% with "X segments left"; turns red at 100% with policy-specific messaging
- **Owner web**: a "SMS usage this month" widget shows current segment count, projected month-end based on current pace, and quota status. Available as a dashboard widget per Pass 2 §5 pattern.
- **Owner mobile**: the existing mobile owner status row pattern (per arch doc §16.9) gets a new row for SMS usage when usage exceeds 70% (otherwise hidden to avoid clutter)

**Notifications**:
- 80% usage: push + email to owner (uses the new "Billing" category from Tier 2 #5)
- 100% usage: push + email to owner; if soft cap, includes "you're now in overage territory at $0.05/segment"; if hard cap, includes "techs cannot send more SMS until [billing date]"
- Overage at month-end: billing line item added to next invoice; owner sees in `Settings > Subscription & Billing > Invoices`

**Rationale**: Soft cap by default because surprise hard caps in the field are a worse failure mode than a small bill. Owner-controlled hard cap option exists for tenants with strict cost-control requirements (some smaller shops genuinely cannot tolerate any unexpected billing). 10x markup on overages ($0.05 vs Telnyx's $0.003 cost) is reasonable for an overage tier — it's not the primary revenue model, just a safety valve. Visibility everywhere is non-negotiable; cost surprises destroy subscription trust.

### 9. Voice intent extension for SMS replies

**Decision**: A new voice intent `reply_to_customer_sms` extends the existing Flow 1 voice intent registry:

- **Trigger pattern**: "Reply to [customer name] saying [message body]"
- **Identifier resolution**: by customer name (most recent active thread); by tech context (when the tech is on a job detail screen for a known customer, the customer is implicit)
- **Always-preview-before-send applies** (per arch doc §16.7): AI reads the rendered message back, confirms via confirm-as-turn pattern (§16.3) before sending
- **Voice can dictate from any screen** (per Flow 4's "Voice override anywhere" pattern from Flow 4 Decision 7), but resolves to the customer's most recent active thread

**Examples**:
- *"Reply to John saying running 30 minutes late, sorry"* → composes free-form text, reads back, sends on confirm
- *"Tell Sarah I'll be there in 20"* → ambiguous between template and free-form; AI asks "is this a template or free-form? Sounds like 'on my way' template — should I use that?"
- *"Reply to that last message saying yes I can do tomorrow"* → uses the most recent inbound thread for the tech

**Voice readback example**:
> *"I'll send to John from the Johnson panel upgrade: 'running 30 minutes late, sorry.' That's 1 segment, you have 47 left this month. Confirm?"*

**Rationale**: Voice extension is the natural Pilot pattern. Confirm-as-turn safeguard prevents misrecognition disasters ("tell John I hate him" misheard as "tell John I'm late"). Segment count + quota-remaining readback gives cost awareness even on voice channel.

### 10. Mobile inbox tab — surface for unread customer messages

**Decision**: The existing Mobile > Today tab gains a new sub-section: "Customer messages" alongside the existing "Today's schedule" and "Inbox" sections (per Pass 2 mobile sitemap). This sub-section shows:

- **Unread count badge** on the Today tab when there are unread customer messages
- **Recent threads list** showing the last 5 customer conversations with unread indicator, last message preview, customer name, time
- **Tap thread → conversation thread screen** (per Decision 7)
- **"View all" link** → full inbox of customer threads

The existing Inbox section handles other notification types (push payload archive); the Customer messages section is specifically for the SMS conversation threads.

**Rationale**: Techs need a single place to see "what customer messages am I behind on?" — the Today tab is the right home because techs land there at clock-in and during the day. Putting customer messages alongside today's schedule makes the operational rhythm clear: see schedule, see messages, work the day.

### 11. Add-on number purchasing — Phase 2 consideration noted

**Decision**: For MVP, add-on numbers are mentioned in subscription pricing (Decision 8) and supported architecturally in the schema (`tenant_phone_number` table supports multiple rows per tenant), but the **purchasing UI is deferred to Phase 2**.

In MVP, tenants who want a second number contact Pilot support; Tom provisions manually. This is acceptable for a small early-MVP customer base.

**Phase 2 work**: a `Settings > Integrations > SMS messaging > Add a number` self-service flow with area code selection, monthly fee disclosure, billing system update, and Telnyx provisioning automation.

**Rationale**: One-per-tenant covers the vast majority of small electrical contractors (1–5 person shops). The minority who want multiple numbers can be served via support channel for the first 6–12 months. Self-service is real work (UI, billing updates, Telnyx automation) that doesn't gate MVP launch.

### 12. Number provisioning trigger — at first SMS use, not at signup

**Decision**: A tenant's Telnyx number is provisioned **at first SMS use**, not at tenant signup.

**Sequence**:
1. Tenant signs up → no Telnyx number provisioned yet
2. Tenant attempts first SMS (a tech tries to send a templated message via Flow 4) → Pilot triggers number provisioning
3. Provisioning takes ~5 seconds via Telnyx API → number assigned, tenant_phone_number row created
4. Original SMS attempt completes once number is provisioned

**Provisioning UI**: a brief loading state ("Setting up your SMS number — one moment...") with an explanation if it takes >10 seconds. On rare provisioning failure (Telnyx API issue, area code unavailable), the SMS is queued and the owner gets a notification to retry.

**Rationale**: Provisioning at signup wastes Telnyx number rental for tenants who never use SMS (genuinely some tenants — small shops who only quote and invoice without SMS communication). Lazy provisioning at first use ties the cost to actual usage. The 5-second one-time delay is acceptable UX for a first-ever-SMS moment.

**Tenant-visible affordance**: at any time before first SMS use, the tenant can pre-provision via `Settings > Integrations > SMS messaging > Set up SMS messaging` if they want to know their number in advance. Otherwise it happens automatically.

### 13. Carrier-agnostic adapter layer

**Decision**: The carrier integration lives behind a `SmsCarrier` interface in `services/sms_carrier.py`:

```python
class SmsCarrier(ABC):
    @abstractmethod
    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber: ...

    @abstractmethod
    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult: ...

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool: ...

    @abstractmethod
    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage: ...

    @abstractmethod
    def get_delivery_status(self, carrier_message_id: str) -> DeliveryStatus: ...

    @abstractmethod
    def release_number(self, phone_number: str) -> None: ...
```

**MVP implementation**: `TelnyxSmsCarrier(SmsCarrier)` with Telnyx-specific logic.

**Test implementation**: `MockSmsCarrier(SmsCarrier)` for integration tests that captures calls without making real API requests.

**Configuration**: which carrier implementation is used is determined by environment variable (`SMS_CARRIER=telnyx|mock`), not by tenant. All tenants on a given Pilot deployment use the same carrier. (Per-tenant carrier choice is Phase 2 if needed.)

**Future swap**: changing from Telnyx to Plivo or SignalWire later means writing `PlivoSmsCarrier` and changing the env variable. No call-site changes.

**Rationale**: Cheap insurance against carrier-side issues. The interface is small and stable across providers because the underlying primitives (provision number, send message, verify webhook, get delivery status) are the same. Half a day of upfront architecture; saves potentially weeks of rewrite work down the road.

### 14. Audit log captures all SMS activity

**Decision**: Every SMS event is audited per the existing `audit_log` infrastructure. Audited events:

- Outbound message sent (template name if applicable, body length, segment count, send_user_id, delivery status when carrier confirms)
- Inbound message received (sender phone, threaded to which tech, body length)
- Free-form reply composed (composition_method: free_form_text vs free_form_voice; voice_audio_id if applicable)
- Number provisioned (tenant_id, area_code, provisioned_phone_number)
- Quota threshold notification (80%, 100% triggers)
- Hard cap blocked send attempt (which tech, which customer, attempted body)

**Audit log query**: at `Settings > Audit Log`, owners can filter by `category: 'sms_communication'` to see all SMS activity. Useful for compliance review, cost attribution, and dispute resolution.

**Rationale**: SMS activity has compliance, billing, and dispute-resolution implications. Audit log is non-optional. Existing audit_log infrastructure covers this without new tables.

### 15. Scope cuts explicitly excluded from MVP

To prevent scope creep during implementation, these are documented as explicitly out of MVP scope:

- **MMS** (image/photo attachments) — Phase 2; pricing still acceptable but adds 4× per-message cost and storage infrastructure
- **AI classification of customer intent** ("customer wants to reschedule") — Phase 2; complex with significant test surface
- **Automated rescheduling suggestions** — depends on AI classification; Phase 2
- **Customer self-service reschedule links** — Phase 2; requires customer-facing portal infrastructure
- **Multi-message threading across channels** (e.g., conversation continued via email) — Phase 2
- **Per-tech Twilio numbers** — Phase 2; one-per-tenant for MVP
- **AI-suggested replies for techs** ("looks like the customer wants to reschedule, here's a suggested response") — Phase 2
- **Out-of-band notification to customer when their message can't be delivered** ("we couldn't reach the tech") — Phase 2
- **SMS conversation export / archive** — Phase 2; existing audit log covers compliance but not user-friendly export
- **Scheduled message sending** ("send 'on my way' at 8 AM tomorrow") — Phase 2
- **Cross-tenant message routing** (e.g., tenant has multiple businesses sharing a Telnyx number) — Phase 2
- **Tenant-side carrier choice** (different tenants on different carriers) — Phase 2 if ever
- **Shortcode messaging** — Phase 2; 10DLC long codes for MVP

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| Carrier-agnostic adapter layer pattern | **NEW** | — |
| Subscription quota with soft/hard cap option | **NEW** | — |
| Lazy provisioning of external resource at first use | **NEW** | — |
| Two-direction message threading UI (chat-style bubbles) | **NEW** | — |
| Forced-minimum push for time-critical category | Reused | Tier 2 #5 Decision 4 |
| Mobile owner status row for usage indicator | Reused | Arch doc §16.9 |
| Voice composition with confirm-as-turn safeguard | Reused | Flow 1, arch doc §16.3 |
| Always-preview-before-send | Reused | Flow 4, arch doc §16.7 |
| Optimistic UI with pending badges | Reused | Arch doc §16.8 |
| Audit log capture for compliance-relevant activity | Reused | Settings IA framework Cross-Domain G |
| Free-form composition with segment-count visibility | **NEW** | — |
| Add-on monthly subscription with included quota expansion | **NEW** | — |

Five new patterns introduced; seven inherited. The carrier-agnostic adapter layer pattern is generalizable to other external service integrations (payment processors, mapping providers, email services) — Phase 2 surfaces inherit this approach by default.

## Cross-domain considerations

### A. Tier 2 #5 (notification preferences) integration

Tier 2 #5's "Customer activity" category covers inbound customer SMS replies. Add to Tier 2 #5's Decision 4 (forced-minimum categories): **Customer activity has a forced-minimum push for the originating tech only**. Owners can mute the category at their discretion; the tech who is actively in the conversation cannot.

Tier 2 #5's Decision 2 category descriptions need a sub-bullet for Customer activity covering inbound SMS replies specifically.

### B. Settings IA framework — new sub-surface for SMS

Add to Settings IA framework Decision 1 web tree: `Settings > Integrations > SMS messaging` (replaces the placeholder "Notifications channels" entry from the IA framework with a more specific sub-surface). Contents:

- Telnyx number assignment (read-only display)
- Quota status (current usage, remaining, projected month-end)
- `sms_quota_cap_policy` setting (soft / hard)
- (Phase 2: Add-a-number self-service)

This needs to be added to the Settings inventory in Tier 2 #4 spec at Pass 4 close.

### C. Subscription tier setting integration

The `sms_quota_cap_policy` tenant setting follows the standard Tier 2 #4 patterns: system-default-with-tenant-override per arch doc §16.5; lives in `Settings > Subscription & Billing > SMS quota`; save-on-blur per IA framework Decision 5; owner-only RBAC per IA framework Decision 8.

### D. Onboarding flow integration (Tier 3 #10)

When a new tenant goes through onboarding, SMS messaging is mentioned (not provisioned) as one of the available features. Tenant signup does **not** auto-provision the number (per Decision 12). Onboarding includes a brief educational moment: "Customer SMS messaging is available — your number will be assigned when you send your first message."

Tier 3 #10 should include this educational step. The 10DLC compliance status (whether registration is complete) is also surfaced — if Tom hasn't completed 10DLC by tenant onboarding time, the tenant is informed that SMS may be delayed for compliance approval.

### E. Help / about / feedback (Tier 4 #14)

The help system needs articles covering:
- "How customer SMS messaging works"
- "What's a segment? Why does it matter?"
- "What happens when I hit my SMS quota?"
- "How do I see my month's SMS usage?"
- "What if a customer texts and I don't see a notification?"

These are content tasks for Tier 4 #14, not design work for this spec.

### F. Voice persona tone and SMS

Voice persona tone (Tier 2 #6) is for AI voice interactions. It does NOT affect SMS reply tone — replies are tech-composed, not AI-generated, in MVP. (Phase 2 may introduce AI-suggested replies which would inherit voice persona.)

### G. Web push for customer messages (in-app banner)

If Tier 2 #5 ships with in-app banner channel, the in-app banner should fire for inbound customer SMS the same way it fires for any Customer activity notification. Web user (typically owner) gets ambient awareness via banner without leaving their current page.

If Tier 2 #5 defers in-app banner to Phase 2, web users only see customer message activity by visiting the dashboard widget (Decision 6) or the customer comm history surface.

### H. Quota reset timing

Quota resets on the first day of each subscription billing cycle (not the calendar month). For a tenant who signed up on the 15th, the quota resets on the 15th of each month. This matches subscription invoice cycles and avoids the edge case where a tenant signs up late in a calendar month and gets a partial first quota.

### I. Refund / credit handling for failed sends

If an outbound message fails to deliver (carrier returns failure status), the segment count is **not** decremented from the tenant's quota. Failed sends don't cost the tenant. This is implementation detail but affects the quota tracker logic.

### J. Customer phone number changes

If a customer's phone number changes in Pilot (the tenant updates the customer's contact info), in-flight conversation threads remain bound to the old phone number until the customer re-establishes contact from the new number. New outbound messages route to the new number. This is the simplest approach; more sophisticated thread-merging is Phase 2.

## Deferred items (Phase 2 / for future iteration)

See [Decision 15 — Scope cuts explicitly excluded from MVP](#15-scope-cuts-explicitly-excluded-from-mvp) for the full list. Beyond those:

- **Per-tenant carrier choice** — different tenants on different carriers via the adapter layer
- **Self-service number purchasing** — Phase 2 UI for add-on numbers
- **Customer-facing self-service portal** — link in outbound messages to a Pilot-hosted page where the customer can confirm/reschedule
- **WhatsApp / iMessage business integration** — Phase 2 alternative channels via the same adapter pattern
- **Voice calls inbound and outbound** through Telnyx — Phase 2 if customers want to call the Pilot number; for MVP, calls to the Pilot number get a recorded message redirecting to the tech's actual phone

## Validation checklist

Before implementation begins:

- [ ] Telnyx account created and API credentials in place
- [ ] 10DLC brand registration started (4–6 week timeline before MVP launch)
- [ ] 10DLC campaign approval submitted for "customer service / appointment notifications" use case
- [ ] Carrier-agnostic adapter layer (`SmsCarrier`) interface specified
- [ ] `TelnyxSmsCarrier` and `MockSmsCarrier` implementations stubbed
- [ ] Threading model (`customer × tech × tenant_phone_number`) validated against multi-person shop edge cases
- [ ] Subscription quota model implemented with soft/hard cap policy
- [ ] In-month visibility surfaces (mobile composition zone, web widget, owner mobile status row) implemented
- [ ] Push notification infrastructure verified — A51 push token registry covers SMS notifications
- [ ] Voice intent `reply_to_customer_sms` added to voice intent registry per arch doc §6
- [ ] Tier 2 #5 spec updated when drafted: Customer activity gains forced-minimum push for originating tech
- [ ] Settings IA framework Decision 1 web tree updated to add `Settings > Integrations > SMS messaging`
- [ ] Tier 2 #4 settings inventory updated to include `sms_quota_cap_policy` at Pass 4 close
- [ ] PRD §3.7 updated for inbound SMS feature scope
- [ ] Arch doc updated for SMS infrastructure chapter
- [ ] Pre-launch hygiene track in framework doc updated with 10DLC registration item
- [ ] Mobile inbox tab "Customer messages" sub-section added to mobile sitemap
- [ ] Web dashboard widget "Recent customer messages" added to dashboard widget catalog (per Pass 2 §5)

## Backend additions (new for Tier 1.5)

### A59. Telnyx Webhook Handler + Carrier-Agnostic Adapter Layer

**Triggered by**: Decisions 3, 13 — inbound SMS receive infrastructure with carrier abstraction.

**Scope**:
- New module `services/sms_carrier.py` with abstract `SmsCarrier` interface (per Decision 13)
- `TelnyxSmsCarrier(SmsCarrier)` implementation:
  - Webhook signature verification using Telnyx's public-key signature scheme
  - `parse_inbound_webhook()` extracting sender, recipient, body, timestamp, carrier_message_id
  - `send_message()` calling Telnyx send API
  - `provision_number()` calling Telnyx number search + acquire APIs
  - `release_number()` calling Telnyx number release API
  - `get_delivery_status()` calling Telnyx message status API
- `MockSmsCarrier(SmsCarrier)` for integration testing
- New API endpoint: `POST /api/v1/webhooks/sms/telnyx-inbound` — receives Telnyx webhook
- Configuration: `SMS_CARRIER` env var (`telnyx | mock`)
- Failure handling: signature verification failure returns 401; routing failure parks inbound in unrouted queue

**Effort estimate**: Small-Medium — 3 days (interface + Telnyx implementation + Mock implementation + webhook endpoint + signature verification).

### A60. Customer Communication Threading Schema and Routing

**Triggered by**: Decision 4 — threading model.

**Scope**:
- New tables: `customer_communication_thread` and `customer_communication_message` per the schema in Decision 4
- New module `services/customer_communication_threading.py` containing the routing logic:
  - `route_inbound_message(inbound: InboundMessage) -> ThreadingResult`
  - Match by sender phone + recent outbound thread + 7-day window
  - Fallback: customer's `last_assigned_tech_id` if no recent outbound; otherwise unrouted queue
  - Returns the `thread_id` and `tech_id` for notification dispatch
- Schema migrations to add the two tables
- Migration of existing `customer_communication` table from Flow 4 outbound to the new threading model (or coexist if the flat table is sufficient for outbound — implementation detail; the threading model wraps the flat table)
- New table: `customer_communication_unrouted` for the edge case from Decision 3
- API: `GET /api/v1/communications/unrouted` — owner-only surface to review and manually route unrouted messages

**Effort estimate**: Medium — 4 days (schema + migration + routing logic + unrouted handling + tests).

### A61. Telnyx Number Provisioning at First Use

**Triggered by**: Decision 12 — lazy provisioning.

**Scope**:
- New table: `tenant_phone_number`
  - `phone_number_id` UUID PK
  - `tenant_id` UUID FK
  - `phone_number` TEXT (E.164 format)
  - `area_code` TEXT
  - `carrier` TEXT (`telnyx`)
  - `carrier_provisioning_id` TEXT (Telnyx's reference)
  - `monthly_fee_cents` INT (for billing tracking)
  - `provisioned_at`, `released_at` TIMESTAMPTZ
  - `status` TEXT (`active | released | provisioning_failed`)
- Provisioning trigger: first SMS attempt for a tenant without an assigned number invokes `services/sms_provisioning.py::provision_for_tenant()`
- Pre-provisioning UI affordance: `Settings > Integrations > SMS messaging > Set up SMS` button calls the same service
- Area code selection: tenant's primary office area code (default); fallback suggests three nearby alternatives if unavailable
- Failure handling: if Telnyx provisioning fails (rare), SMS attempt is queued, owner gets notification to retry
- Subscription billing integration: `monthly_fee_cents` is added to the tenant's recurring billing line items
- API: `POST /api/v1/tenants/{tenant_id}/phone-numbers/provision` — request a number
- API: `GET /api/v1/tenants/{tenant_id}/phone-numbers` — list assigned numbers

**Effort estimate**: Medium — 3 days (schema + provisioning service + Telnyx integration + billing integration + failure handling).

### A62. Free-Form Reply Composition Endpoints

**Triggered by**: Decision 7 — free-form tech reply UI.

**Scope**:
- API: `POST /api/v1/communications/threads/{thread_id}/reply` — send a free-form reply
  - Request body: `{body: str, composition_method: 'free_form_text' | 'free_form_voice', voice_audio_id: UUID?}`
  - Validates: body within segment limits; tenant within quota (per A65); thread is active
  - Dispatches via `SmsCarrier.send_message()` (per A59)
  - Updates `customer_communication_message` and `customer_communication_thread.last_message_at`
  - Decrements tenant quota (per A65)
  - Audit log entry per Decision 14
  - Pre-commit staleness check per arch doc §16.4 (concurrent thread modifications)
- Optimistic UI support: 200 response includes the new message in the thread payload
- Validation: body cannot be empty; body length checked; segment count computed

**Effort estimate**: Small — 2 days.

### A63. Voice-to-Text Reply Integration

**Triggered by**: Decisions 7, 9 — voice-to-text composition flow and `reply_to_customer_sms` voice intent.

**Scope**:
- Voice intent `reply_to_customer_sms` added to voice intent registry (`api/voice/intents.py`)
- Intent handler:
  - Extract customer identifier from utterance (most recent active thread by default)
  - Extract message body
  - Call `customer_communication_preview_service.render(...)` with composition_method `free_form_voice`
  - Render preview: "I'll send to [customer]: '[body].' That's [segment_count] segments, you have [remaining] left this month. Confirm?"
  - On confirmation, invoke A62 `POST /threads/{thread_id}/reply` with `voice_audio_id` populated
- The voice composition path on mobile UI (per Decision 7) calls the same intent flow as voice-anywhere, so this is shared infrastructure
- Voice audio link: `voice_audio_id` references `voice_command_log.id` to maintain the audit trail of what audio was captured
- Confirm-as-turn safeguard per arch doc §16.3

**Effort estimate**: Small-Medium — 2–3 days (intent handler + preview rendering + integration with A62).

### A64. Owner Visibility Surfaces — Web Comm History Extension and Dashboard Widget

**Triggered by**: Decision 6 — owner visibility.

**Scope**:
- Web `Customers > [customer] > Comm history` surface extended:
  - Two-direction message rendering (outbound: brand-indigo; inbound: neutral; chat-style)
  - Threaded by `thread_id`; multiple threads per customer when multiple techs have communicated
  - API: `GET /api/v1/customers/{customer_id}/communication-history` — returns threaded message list
- Dashboard widget: "Recent customer messages"
  - API: `GET /api/v1/dashboard/widgets/recent-customer-messages?limit=10` — returns last 10 messages across the tenant
  - Widget config (per Pass 2 §5 pin-to-dashboard pattern): owner can pin to dashboard, configurable `limit`
  - Real-time updates via SSE per arch doc §13.11
- Mobile owner: per Tier 2 #5 default policy for Customer activity category (push ON for owners by default; can be muted)

**Effort estimate**: Small-Medium — 2–3 days.

### A65. SMS Quota Tracking and Cap Enforcement

**Triggered by**: Decision 8 — subscription quota model.

**Scope**:
- New table: `sms_quota_period`
  - `period_id` UUID PK
  - `tenant_id` UUID FK
  - `period_start`, `period_end` TIMESTAMPTZ (aligned to subscription billing cycle)
  - `included_segments` INT (computed: 100 base + 100 per add-on number)
  - `used_segments` INT (incremented per outbound send)
  - `overage_segments` INT (segments beyond included; for billing)
  - `cap_policy` TEXT (`soft | hard`; copied from tenant setting at period start to lock in policy mid-period)
- Tenant setting: `sms_quota_cap_policy` (`soft | hard`; default `soft`)
- New module `services/sms_quota.py`:
  - `check_quota(tenant_id, requested_segments) -> QuotaCheckResult` — returns whether the send is allowed under current policy
  - `consume_quota(tenant_id, segments)` — atomic increment of used_segments
  - Hard cap: `check_quota` returns `blocked: True` when used + requested > included
  - Soft cap: `check_quota` always returns `allowed: True` but flags `overage: True` for billing
  - Periodic notification dispatch at 80% and 100% (Celery task)
- Period rollover: scheduled Celery task at subscription cycle boundaries creates new `sms_quota_period` row
- Billing integration: at month-end, `overage_segments × $0.05` added to tenant invoice
- API: `GET /api/v1/sms/quota` — returns current period status (used, remaining, projected, policy)
- Failed send refund: if `SmsCarrier.send_message()` returns failure, `consume_quota` is rolled back

**Effort estimate**: Medium — 4 days (schema + quota service + billing integration + period rollover + notifications + Celery task).

### A66. Mobile Inbox "Customer Messages" Sub-Section + Conversation Thread Screen

**Triggered by**: Decisions 7, 10 — mobile UI surfaces.

**Scope**:
- Mobile API: `GET /api/v1/mobile/inbox/customer-threads` — returns recent threads for the requesting tech (last 5 by default, paginated)
- Response: `{thread_id, customer_name, last_message_preview, last_message_at, unread_count, originating_job_context (if available)}`
- API: `GET /api/v1/communications/threads/{thread_id}/messages?paginate` — returns full message history for a thread
- API: `POST /api/v1/communications/threads/{thread_id}/mark-read` — marks all unread messages in thread as read
- Mobile UI components: conversation thread screen (per Decision 7); inbox sub-section (per Decision 10); composition zone with voice button + text input + segment counter
- Real-time updates via SSE per arch doc §13.11 — when a new inbound arrives in an open thread, it appears immediately
- Push notification deep-link target: tapping a customer-message push opens the conversation thread screen for that thread

**Effort estimate**: Medium — 3–4 days (multiple endpoints + mobile UI components + SSE integration + push deep-link).

### Total Tier 1.5 backend additions

A59 (3) + A60 (4) + A61 (3) + A62 (2) + A63 (2–3) + A64 (2–3) + A65 (4) + A66 (3–4) = **23–26 days**.

---

## What this surface does NOT cover

Per Decision 15:

- MMS / image attachments — Phase 2
- AI classification of customer intent — Phase 2
- Automated rescheduling suggestions — Phase 2
- Customer self-service reschedule links — Phase 2
- Multi-channel threading (SMS + email) — Phase 2
- Per-tech Telnyx numbers — Phase 2
- AI-suggested replies — Phase 2
- Self-service number purchasing UI — Phase 2
- Voice calls inbound/outbound — Phase 2
- WhatsApp / iMessage business — Phase 2
- Per-tenant carrier choice — Phase 2
- Scheduled message sending — Phase 2

Plus all original Flow 4 deferred items (settings UI for template management → Tier 2 #4; SMS consent capture → still Pass 4 work; bulk customer messaging → Phase 2; multi-language template variants → Phase 2; voice persona affecting comm tone → Post-MVP).

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A59–A66 added (8 additions). Cumulative through Tier 1.5: A1–A66.

**Backend day estimate update**:
- Pre-Tier-1.5 cumulative remaining MVP: 148–203.5 days
- Tier 1.5 additions: 23–26 days
- New cumulative remaining MVP: **171–229.5 days**

**Pre-launch hygiene track**: 10DLC registration added as new operational item, owned by Tom, target completion 4–6 weeks before MVP launch. Failure to complete blocks MVP launch readiness for SMS deliverability.

**Framework doc**: Tier 1.5 inserted between Tier 1 close and Tier 2 #5 in the Pass 4 progress detail. PRD update track and architecture doc track both gain pending v3.1 / v4.2 entries for SMS infrastructure.

**Tier 2 #5 update**: when drafted, must include "Customer activity" category with forced-minimum push for the originating tech (per Cross-Domain A above).

## Next: Tier 2 #5 — Notification Preference Center

Tier 2 #5 picks up where this extension paused. The Customer activity category in the Tier 2 #5 matrix gains the forced-minimum push designation for inbound customer SMS replies. Estimated 200–250 lines per the framework's Shape C deliverable definition. Inherits Mockups A and C from Tier 2 #4 wholesale.

After Tier 2 #5, Tier 2 continues with #6 (voice persona tone) and #7 (account settings).
