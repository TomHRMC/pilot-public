# `mvp-arch.md` v4.2 Update Instructions (Pass 4 Tier 1.5 — Customer Comms Extension)

**Purpose**: Update `mvp-arch.md` from v4.1 to v4.2 to capture Pass 4 Tier 1.5 architectural additions: SMS infrastructure (carrier adapter, threading, quota), Cost Analysis updates for Telnyx, and §16.5 settings list extension.

**Affected file**: `mvp-arch.md`
**Total edits**: 5 (1 new chapter; 2 chapter cross-references; 1 cost analysis update; 1 doc header version bump)
**Estimated edit time**: 20–30 minutes (the new chapter is the bulk of the work)

---

## Edit 1 — Doc header version bump

Locate the version metadata at the top of `mvp-arch.md`. Bump from v4.1 to v4.2.

**Find**: `**Version**: 4.1 ...` line
**Replace with**: `**Version**: 4.2 (Pass 4 Tier 1.5 — Customer Comms SMS infrastructure added as §17; full v5 issued at Pass 4 close)`

Update the "Last Updated" line to today's date.

---

## Edit 2 — New Chapter §17: SMS Infrastructure

**Insertion point**: After §16 closes (line 2818 in your v4.1; the `---` separator after §16.9), and before the `## Cost Analysis` chapter (line 2822).

**Content to insert**:

```markdown
## 17. SMS Infrastructure

Tier 1.5 (Pass 4) introduced full bidirectional customer SMS communication. This chapter covers the SMS-specific infrastructure that supports Flow 4's outbound templated messaging plus the Tier 1.5 inbound and free-form reply additions. SMS is the most operationally complex external integration in MVP because it has multi-direction message flow, third-party provider integration, ongoing per-message billing, US carrier compliance requirements (A2P 10DLC), and tenant-facing subscription quota management.

### 17.1 Carrier Choice and Adapter Layer

**Carrier**: Telnyx is the MVP carrier. Selected over Twilio, Plivo, and SignalWire based on pricing (~$0.003 outbound segment vs. Twilio's $0.0079), simpler 10DLC onboarding flow, and competitive number rental (~$1/month).

**Adapter pattern**: All carrier interactions go through `services/sms_carrier.py` which defines the abstract `SmsCarrier` interface. The `TelnyxSmsCarrier` implementation handles MVP; a `MockSmsCarrier` supports integration testing without real API calls. Configuration is per-deployment via `SMS_CARRIER` environment variable; per-tenant carrier choice is Phase 2 if needed.

The interface:

```python
class SmsCarrier(ABC):
    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber: ...
    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult: ...
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool: ...
    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage: ...
    def get_delivery_status(self, carrier_message_id: str) -> DeliveryStatus: ...
    def release_number(self, phone_number: str) -> None: ...
```

**Why the adapter abstraction**: telecom carriers have a long history of pricing changes, deliverability issues, acquisitions, and policy shifts. The interface is stable across providers because the underlying primitives (provision number, send, verify webhook, get status) are uniform across the industry. Cost: ~half a day of upfront work; benefit: future provider swaps are a one-class change.

### 17.2 A2P 10DLC Compliance

US carriers (T-Mobile, AT&T, Verizon) require business SMS senders to register their use case via The Campaign Registry. Without registration, messages are filtered with poor deliverability — they arrive late, or not at all.

**Registration components**:
- **Brand**: Pilot for Trades, registered with The Campaign Registry
- **Campaign**: "Customer service / appointment notifications for trades businesses" use case
- **Approval timeline**: 1–2 weeks brand approval; 1–2 weeks campaign approval; 4–6 weeks total before reliable deliverability

**Operational status**: Tom-owned pre-launch hygiene work; tracked in framework doc's pre-launch hygiene track. Failure to complete blocks reliable SMS delivery; SMS messages will still send but deliverability will be poor.

**Phase 2 considerations**: as Pilot scales to multiple tenants with different SMS volumes, additional campaigns may be required for differentiated use cases (e.g., marketing notifications separate from operational notifications). Initial campaign supports MVP scope only.

### 17.3 Number Provisioning Strategy

**Provisioning model**: One Telnyx phone number per tenant for MVP. Lazy provisioning at first SMS use rather than at tenant signup — prevents Telnyx number rental cost for tenants who never use SMS.

**Schema**: `tenant_phone_number` table tracks tenant → number assignment with carrier reference, monthly fee, and provisioning status. See A61 in backend additions ledger v5.2.

**Area code selection**: tenant's primary office area code is the default; if unavailable, system suggests three nearby alternatives. Once provisioned, the number is sticky — tenants cannot self-service swap to a different number in MVP.

**Add-on numbers**: tenants can request additional numbers via support channel in MVP at +$5/month per number (each additional number adds 100 segments to the tenant's monthly quota per §17.6). Self-service add-on UI is Phase 2.

**Provisioning failures**: rare but real (Telnyx API issues, area code completely unavailable). On failure, the original SMS attempt is queued; owner gets a notification to retry. Manual support intervention may be required for stubborn cases.

### 17.4 Inbound Message Routing

**Webhook flow**:

```
Customer SMS → Telnyx →
  POST /api/v1/webhooks/sms/telnyx-inbound (signature verified) →
  services/customer_communication_threading.py::route_inbound_message() →
  Match to thread → Notify tech + owner → Update web/mobile surfaces
```

**Threading logic**:
1. Match by sender phone → look up `customer.phone` for this tenant
2. Match by recipient phone → must equal a `tenant_phone_number` for this tenant
3. Find most recent active thread within 7-day window
4. If no recent thread: fall back to `customer.last_assigned_tech_id`
5. If still no match: park in `customer_communication_unrouted` table with owner alert

**Threading key**: `(tenant_id, customer_id, tech_id, tenant_phone_number_id)`. This allows multiple concurrent threads when multiple techs have communicated with the same customer.

**Edge case — customer texts cold (no prior outbound)**: routes to `customer.last_assigned_tech_id` if available; otherwise unrouted queue. Owner reviews unrouted messages and manually assigns to a thread.

**Edge case — customer phone number changes mid-conversation**: in-flight threads remain bound to the old number. New outbound goes to new number. Sophisticated thread merging is Phase 2.

### 17.5 Threading Schema

Two tables form the threading model:

```sql
customer_communication_thread (
    thread_id              UUID PRIMARY KEY,
    tenant_id              UUID NOT NULL,
    customer_id            UUID NOT NULL,
    tech_id                UUID NOT NULL,
    tenant_phone_number_id UUID NOT NULL REFERENCES tenant_phone_number,
    status                 TEXT NOT NULL,  -- 'active' | 'archived'
    first_message_at       TIMESTAMPTZ NOT NULL,
    last_message_at        TIMESTAMPTZ NOT NULL,
    message_count          INT NOT NULL DEFAULT 0,
    created_at             TIMESTAMPTZ NOT NULL,
    updated_at             TIMESTAMPTZ NOT NULL
)

customer_communication_message (
    message_id             UUID PRIMARY KEY,
    thread_id              UUID NOT NULL REFERENCES customer_communication_thread,
    direction              TEXT NOT NULL,  -- 'outbound' | 'inbound'
    channel                TEXT NOT NULL,  -- 'sms' (MMS Phase 2)
    body                   TEXT NOT NULL,
    segment_count          INT NOT NULL,
    status                 TEXT NOT NULL,  -- 'pending_send'|'sent'|'delivered'|'failed'|'received'
    carrier_message_id     TEXT,
    sent_at, delivered_at, received_at TIMESTAMPTZ,
    composition_method     TEXT,           -- 'template'|'free_form_text'|'free_form_voice'
    template_id            UUID NULL REFERENCES communication_template,
    voice_audio_id         UUID NULL REFERENCES voice_command_log,
    audit_user_id          UUID NOT NULL
)
```

**Coexistence with existing `customer_communication` table** (from A4): the threading model wraps the existing flat message table. Existing outbound rows backfill into threads at the v5.2 deployment. The `customer_communication` table itself is preserved for backward compatibility but new code reads/writes through the threading model.

### 17.6 Subscription Quota and Cap Enforcement

**Quota model**:
- Base: 100 SMS segments per month per tenant, included in $149 subscription
- Add-on numbers: each adds 100 segments to the quota
- Inbound messages: not counted against quota (Telnyx inbound cost ~$0.002, rolled into base)
- MMS: not in MVP

**Cap policy** (`tenant_setting.sms_quota_cap_policy`):
- `soft` (default): tenant gets billed for overages at $0.05/segment; sends continue normally
- `hard`: at 100% used, all outbound SMS is blocked until next billing cycle

**Period model**: `sms_quota_period` table; one row per tenant per billing cycle. Period boundaries align with subscription billing (not calendar month). Created by Celery task `rollover_sms_quota_periods`.

**In-month visibility**:
- Mobile composition zone shows segment count + remaining quota for the current message
- Web dashboard widget "SMS usage this month" shows current, projected month-end, policy
- Mobile owner status row appears when usage >70% (otherwise hidden)
- Notifications fire at 80% (push + email to owner) and 100% (push + email)

**Atomicity**: `consume_quota` increments atomically; rolls back on send failure (failed sends don't cost the tenant).

**Billing integration**: month-end overage billing is handled by existing subscription billing infrastructure; `overage_segments × $0.05` added as a line item.

### 17.7 Voice Intent Integration

A new voice intent `reply_to_customer_sms` extends the voice intent registry (§6.2) for free-form SMS reply composition.

**Trigger pattern**: "Reply to [customer name] saying [message body]"

**Identifier resolution**: most recent active thread for the requesting tech by default; explicit by name/job context if specified

**Flow**:
1. Voice captures audio via existing Whisper infrastructure
2. Transcribed body extracted; customer identifier resolved
3. Confirm-as-turn safeguard (§6.6): preview rendered; AI reads back including segment count and remaining quota
4. On confirmation, dispatches via `POST /api/v1/communications/threads/{thread_id}/reply`

**Always-preview-before-send** (§16.7) applies — voice cannot bypass preview.

**Voice composition can be initiated from any screen** per Flow 4's "Voice override anywhere" pattern, but resolves to the customer's most recent active thread for the requesting tech.

### 17.8 Notification Integration

Inbound SMS messages dispatch push notifications to:
- **The originating tech**: forced-minimum push (per Tier 2 #5 notification preferences) — cannot be muted by user override
- **The owner**: per Tier 2 #5 default policy for "Customer activity" category (push ON by default for owners; can be muted)

Push payload includes `thread_id` for deep-link routing — tapping the push opens the conversation thread screen on mobile.

**Web in-app banner** (if Tier 2 #5 ships with the in-app channel): inbound messages also fire an in-app banner for active web sessions; owner sees ambient awareness without leaving current page.

### 17.9 Audit and Compliance

Every SMS event is captured in `audit_log` per the existing audit infrastructure:

- Outbound message sent (template if applicable, body length, segment count, send_user_id, delivery status)
- Inbound message received (sender phone, threaded to which tech, body length)
- Free-form reply composed (composition_method: free_form_text vs free_form_voice; voice_audio_id if applicable)
- Number provisioned (tenant_id, area_code, provisioned_phone_number)
- Quota threshold notifications (80%, 100% triggers)
- Hard cap blocked send attempt (which tech, which customer, attempted body)

Owners can filter audit log by `category: 'sms_communication'` for compliance review, cost attribution, or dispute resolution.

### 17.10 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── webhooks_sms.py            # POST /api/v1/webhooks/sms/telnyx-inbound
│   │   ├── communications_threads.py  # thread CRUD, reply endpoints
│   │   ├── sms_quota.py               # GET /api/v1/sms/quota
│   │   └── tenant_phone_numbers.py    # provisioning endpoints
│   └── voice/
│       └── intents.py                 # reply_to_customer_sms intent handler added
├── services/
│   ├── sms_carrier.py                 # Adapter interface + TelnyxSmsCarrier + MockSmsCarrier
│   ├── customer_communication_threading.py  # routing logic
│   ├── sms_provisioning.py            # number provisioning at first use
│   └── sms_quota.py                   # quota check, consume, rollover
└── tasks/
    ├── rollover_sms_quota_periods.py  # daily Celery task
    └── monitor_sms_quota_thresholds.py  # hourly Celery task for 80/100% notifications
```

### 17.11 Cost Implications

Per-tenant SMS costs vary by usage. For an active tenant at 200 segments/month (well above included 100):

| Cost component | Monthly per-tenant |
| :--- | :--- |
| Number rental (Telnyx) | ~$1.00 |
| Outbound segments (100 × $0.003) | $0.30 |
| Inbound segments (100 × $0.002) | $0.20 |
| **Total Telnyx cost at 200 segments** | **~$1.50** |
| Tenant overage billing (100 × $0.05) | +$5.00 to tenant (Pilot revenue, not cost) |

At Pilot scale (100 tenants average, mixed usage), aggregate Telnyx cost ~$150–250/month. See Cost Analysis chapter for the full update.

### 17.12 Phase 2 Roadmap

Out of MVP scope per Tier 1.5 Decision 15:

- MMS / image attachments
- AI classification of customer intent ("customer wants to reschedule")
- Automated rescheduling suggestions
- Customer self-service reschedule links
- Multi-channel threading (SMS + email continuity)
- Per-tech Telnyx numbers
- AI-suggested replies for techs
- Self-service number purchasing UI
- Voice calls inbound/outbound through Telnyx
- WhatsApp / iMessage business integration
- Per-tenant carrier choice
- Scheduled message sending
```

---

## Edit 3 — Update §3.7 (Notifications & Comms) cross-reference

If your arch doc has a chapter or section discussing customer communications / notifications (search for "customer communication" or "Flow 4" references), add a forward-reference to the new §17.

For example, if §3 (Background Processing) mentions notification dispatching, add a note like:

> **SMS infrastructure**: customer-facing SMS messaging — outbound (Flow 4) and inbound (Tier 1.5 extension) — is detailed in §17. The notification dispatching infrastructure here covers email and push only; SMS uses a separate dispatch path through the `SmsCarrier` adapter.

Search for places where SMS or `notification_outbox` is currently referenced and confirm the references still apply or now point to §17 for SMS-specific paths.

---

## Edit 4 — Update Cost Analysis chapter

In the "Total Infrastructure Cost (100 Customers — MVP)" table, add new line items for SMS infrastructure. The current table has no SMS line.

**Find** the existing cost table, and **insert** these rows in the appropriate sections:

After the `**Subtotal Database**` row, add a new section:

```markdown
| **SMS Infrastructure** | Telnyx number rentals (100 tenants × ~$1) | $100 |
| | Telnyx outbound SMS (~10K segments/mo aggregate × $0.003) | $30 |
| | Telnyx inbound SMS (~5K segments/mo × $0.002) | $10 |
| **Subtotal SMS** | | **$140** |
```

**Update the GRAND TOTAL line** to include the new $140:

Find:
```markdown
| **GRAND TOTAL** | | **~$741/month** |
```

Replace with:
```markdown
| **GRAND TOTAL** | | **~$881/month** |
```

**Update per-customer cost and gross margin**:

Find:
```markdown
**Per-customer cost:** $7.41/month
**Gross margin at $149/month:** 95.0%
```

Replace with:
```markdown
**Per-customer cost:** $8.81/month
**Gross margin at $149/month:** 94.1%
```

**Add a Pass 4 Tier 1.5 cost delta paragraph** after the "Pass 3 cost delta" paragraph:

```markdown
**Pass 4 Tier 1.5 cost delta from Pass 3 baseline ($741/month)**:

- SMS Infrastructure added as a new $140/month line item: Telnyx number rentals, outbound and inbound SMS at typical 100-tenant aggregate volume
- Number rental dominates at $100; per-message costs scale roughly with tenant SMS activity
- Tenant overage billing at $0.05/segment generates Pilot revenue when tenants exceed 100-segment included quota; not reflected in cost analysis (it's revenue, not cost)
- A2P 10DLC registration is a one-time setup cost (~$50 brand registration + per-campaign fees) and does not appear in monthly recurring
```

**Update Scaling Economics table** to reflect new costs:

| Scale | Monthly Cost | Per-Customer Cost | Gross Margin (at $149) |
| :--- | :--- | :--- | :--- |
| 100 customers | $881 | $8.81 | 94.1% |
| 500 customers | $1,665 | $3.33 | 97.8% |
| 1,000 customers | $2,950 | $2.95 | 98.0% |

(SMS costs scale roughly linearly with customer count, so at 500 customers SMS is ~$700; at 1,000 it's ~$1,400. Other costs scale sub-linearly per the existing analysis.)

---

## Edit 5 — Update §16.5 settings list extension (minor)

Locate §16.5 "System Default + Tenant Override Two-Tier Configuration" — specifically the "Settings using this pattern" subsection that you previously updated for Pass 4 Tier 1.

**Find** the existing "Settings using this pattern (Pass 4 Tier 1)" sub-list.

**Add a new sub-list immediately below it**:

```markdown
**Settings using this pattern** (Pass 4 Tier 1.5):

- `sms_quota_cap_policy` (`soft | hard`; default `soft`; tenant-only override; per Tier 1.5 Decision 8)

**SMS-related settings without §16.5 system default involvement** (just tenant settings):

- `sms_quota_cap_policy` is currently the only SMS-related tenant setting using §16.5; SMS quota itself (`sms_quota_period.included_segments`) is computed from subscription tier, not a tenant override
```

---

## Verification checklist after edits

- [ ] Doc header version bumped to v4.2 (Edit 1)
- [ ] §17 chapter inserted between §16 close and Cost Analysis (Edit 2)
- [ ] §17 has 12 subsections: 17.1 through 17.12
- [ ] §3 or wherever notifications are discussed has forward-reference to §17 (Edit 3)
- [ ] Cost Analysis table has new SMS Infrastructure section with $140/month subtotal (Edit 4)
- [ ] GRAND TOTAL updated to ~$881/month (Edit 4)
- [ ] Per-customer cost updated to $8.81; gross margin to 94.1% (Edit 4)
- [ ] Pass 4 Tier 1.5 cost delta paragraph added (Edit 4)
- [ ] Scaling Economics table updated (Edit 4)
- [ ] §16.5 settings list extended for Pass 4 Tier 1.5 (Edit 5)
- [ ] §17 anchor links work in TOC (you may need to add the §17 entry to the TOC at the top of the doc)

After these edits, Chapter 17 is approximately 200 lines and the doc grows from ~3,055 lines (v4.1) to ~3,260 lines (v4.2).
