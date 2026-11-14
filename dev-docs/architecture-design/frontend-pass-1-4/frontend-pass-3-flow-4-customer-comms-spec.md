# Pilot for Trades Design System — Pass 3, Flow 4: Tech-to-Customer Templated Communications

**Version**: 1.0
**Status**: Locked
**Date**: April 25, 2026
**Scope**: Mobile flow for sending templated SMS/email to customers from job context, plus web view of communication history
**Depends On**: Pass 1 (tokens), Pass 2 (IA), Pass 3 Flow 1 (voice patterns), PRD §3.7 (Notifications & Communications)
**Backend Reference**: A4 (Templated Customer Communications), with potential additions noted in this spec

---

## Purpose

Flow 4 designs the everyday touchpoint between technicians and customers — the moment Mike taps a button or speaks a phrase and a customer instantly knows where their job stands. This flow is operationally critical for two reasons. First, customer comms is *the* most-used field-service feature in the incumbent products (ServiceTitan, Jobber), so getting it right is table stakes. Second, voice-triggered customer comms is a defining differentiator for Pilot — every other product makes you tap through 3+ screens to send "on my way."

The design's goal is to make the common case fast, the voice-triggered case faster, and the wrong-customer-or-wrong-message case impossible.

## Strategic Direction

### Voice describes intent, not template names

Mike doesn't pick templates by name; he describes what he wants to communicate. "I'm 20 out" maps to `on_my_way` with computed ETA. "Running 30 late" maps to `running_late`. The AI's job is to recognize the intent and route to the matching template, not to require the user to memorize template names. Template names exist for the touch UI list — when Mike taps to pick visually — but are not the canonical voice grammar.

This treats voice as a natural-language interface to the templates, not a verbal directory lookup. It's the same philosophy as Flow 1's "create a quote for Tom Johnson" — describe the goal, let the AI route to the action.

### Friction is the right safeguard for outbound communications

Every send shows a preview. Always. Even for clean voice commands like "tell Johnson I'm 20 out" with full intent detection and matched customer. The cost of a wrong message reaching a customer (apology, trust damage, schedule reconciliation) far exceeds the cost of one extra tap or one extra spoken "send."

This differs from internal-state changes (like adding a line to a quote) where errors are recoverable and friction-light is correct. Outbound communication is a one-way door.

### Customer preference drives default channel; tech can override per-message

Customer records carry a preferred contact method (SMS or email). The composer defaults to that channel without asking. Mike can override per-message via a small "Use email instead" / "Use SMS instead" link near the customer info. Override doesn't change the customer's stored preference — just routes this one message differently.

Rationale: in 80% of cases, the customer's preference is the right answer. Forcing Mike to pick channel every time adds friction without value. But the override is essential — there are real days when a customer says "actually, text me today, I'm not at my desk" and Mike needs to honor that.

## Locked Design Decisions

### 1. Six MVP Templates (Per Pass 2 A4)

**Decision**: Ship with six templates as the MVP set. Tenant-configurable list will be a Pass 4 Settings flow.

| Template code | User-facing name | Rendered example |
| :--- | :--- | :--- |
| `on_my_way` | On my way | "On my way, ETA 2:45 PM" |
| `running_late` | Running late | "Running 15 min late — apologies, light traffic from prior job." |
| `arrived` | Arrived | "Arrived, starting work." |
| `job_complete` | Job complete | "Job complete, invoice to follow." |
| `parts_delay` | Parts delay | "Parts delay — will update when resolved." |
| `confirm_appointment` | Confirm appt | "Please confirm appointment for [date/time] at [site]." |

**Rationale**: These cover the day-shape of a typical service tech: arriving, working, completing, and the two main exception cases (late, parts delay). Confirmation is the most common pre-job comm. Six is enough to be useful, few enough to fit a 2×3 card grid without scrolling, and short enough that the AI's voice intent matching can be tuned reliably.

### 2. Communicate Action on Job Detail (Touch Entry Point)

**Decision**: From the mobile Job Detail screen, "Communicate" appears as a primary action button alongside Clock In/Out, Log Expense, Change Order. Tapping opens the template picker.

**Rationale**: Most templated comms happen in-job context. Surfacing the action on the job screen makes the customer-context implicit — Mike doesn't have to specify "to Johnson" because the job *is* Johnson's job. This eliminates an entire class of routing errors.

### 3. Template Picker as 2×3 Card Grid

**Decision**: Six templates render as 2×3 cards (two columns, three rows). Each card shows:
- An intent-derived icon (different per template)
- The user-facing template name (e.g., "On my way")
- A one-line preview of what the rendered message looks like (e.g., `"On my way, ETA [auto-computed]"`)

**Rationale**: Cards are tactile and fast in the field. The icon-plus-name combo creates a recognizable shape — Mike doesn't have to read every word, he sees the shape and taps. The preview text answers "what will this actually send?" without requiring a tap-through.

**Above the grid**: a small amber-tinted "voice CTA" panel reminds the user of the voice option: *"Or use voice: 'Tell Tom I'm 20 out' — the AI picks the right template and fills in the ETA."* This is teaching grammar, not selling a feature.

### 4. Channel Display + Override Affordance on Picker

**Decision**: Above the card grid, the customer info shows their preferred channel as a pill ("SMS preferred") with a discreet override link ("Send via email instead →"). Tapping the override link sets the channel for *this message only*, not the customer's stored preference.

**Rationale**: Channel is metadata Mike usually doesn't need to think about. Showing it without forcing a decision keeps the channel transparent. The override link is visible enough to find when needed, quiet enough to ignore otherwise.

### 5. Preview Screen Before Every Send

**Decision**: After a template is selected (touch) or a voice intent is parsed (voice), the user lands on a preview screen showing exactly the message that will be sent, who it goes to, and via which channel. The user must tap "Send to [name]" or say "send" to commit.

This applies even when the voice command was unambiguous and complete. No auto-send, ever, for outbound customer communications.

**Rationale**: As discussed in design — Whisper misrecognitions, intent-matching errors, customer ambiguity, and ETA mistakes are all real failure modes. A wrong message to a customer is high-cost. Always-preview is the simple, defensible safeguard. (Tenant override to enable auto-send was considered and rejected — owners who'd want to flip this on don't yet know the failure modes that would teach them not to.)

### 6. Inline Editable Variables (Tap or Voice)

**Decision**: Variables in the message preview (ETA time, late minutes, appointment date, etc.) render as visually distinct chips — amber-tinted with a dashed border — to signal they're editable. Two ways to edit:

- **Tap** the chip to bring up a quick-pick scrollwheel or option list (e.g., for late minutes: 5 / 10 / 15 / 20 / 30 / 45 / Custom)
- **Voice** override at any time via the mic button — "make it 30 minutes" updates the value and re-renders the message

Below the message bubble, an explicit "ETA — auto-computed from your route" or "How late?" option block surfaces the same editable values as quick-pick buttons, for users who don't realize the chip is tappable.

**Rationale**: ETA from route data is going to be wrong sometimes — traffic, planned stops the system doesn't know about, lunch. The override path needs to be obvious and frictionless. Showing the editable variable in two ways (chip + button row) accommodates both "I see it's editable, I'll tap" users and "I don't know what's editable, but the buttons are obvious" users.

The amber-on-amber styling reuses the alert color ramp from Pass 1, semantically signaling "this is something you can act on."

### 7. Voice Override Anywhere on the Screen

**Decision**: Every screen in this flow has a microphone button visible. Tapping it opens a full-screen listening overlay that captures voice input contextual to the current screen state.

- On the **template picker**, voice can pick a template AND fill variables in one utterance: "tell him I'm 20 out" → routes to On My Way with 20-min ETA, lands on preview
- On the **preview screen**, voice can edit any variable ("make it 30 minutes"), change channel ("use email"), or commit ("send")

**Rationale**: Voice override universality is a stated principle of the Pilot design system. Reinforcing it here is critical because customer comms is the most likely place a tech needs hands-free in the field — they're driving to a stop, holding a tool, can't tap precisely.

### 8. Sent Confirmation Screen with Auto-Return

**Decision**: After send, a brief (~2.4 second) confirmation screen displays: success checkmark, "Sent to [name]", the rendered message that was sent, and the channel + recipient. Then the app auto-returns to the previous screen (job detail).

**Rationale**: Mike needs visual confirmation that the message went, but he doesn't need to dwell on it. Auto-return keeps him moving — he's likely about to clock in, log an expense, or complete the job. The confirmation lives 2-3 seconds because that's enough to register without becoming a hold-step.

The confirmation also notes "Logged to job · visible in customer history" — communicating that the message is auditable, which builds trust for both Mike (his sent messages are preserved as a record) and the owner (every comm is logged for review).

### 9. Customer Resolution from Voice Without Job Context

**Decision**: When voice is triggered from a non-job screen (Today tab, Voice tab, Customer page, dashboard), customer resolution follows this priority:

1. **Explicit context** — if voice is on a customer page or job page, that customer is implicit
2. **Named in utterance** — "tell *Tom Johnson* I'm 20 out" — search for matching customer
3. **Named with disambiguation needed** — "tell *Johnson* I'm 20 out" with two Johnsons in DB — AI asks "which Johnson — Tom on Oak Street or Sarah on Cedar?"
4. **No customer named** — "tell them I'm 20 out" without context — AI asks "which customer?"

**Rationale**: Mirrors the Flow 1 disambiguation pattern. Never silently picks; always asks when ambiguous. Voice that defaults to "the most recent customer" or "the active job" without asking is how messages go to the wrong people.

### 10. Web Communication History (Per Customer)

**Decision**: On the web, the Customer detail page has a Communications tab that shows a chronological table of all messages sent to this customer. Columns:

| Time | Channel | Message | Status |

Each row shows the rendered message text, a small template tag pill (`on_my_way`, `running_late`), the sender, any flags ("voice-triggered", "channel overridden from SMS to email"), and the delivery status (delivered / opened / replied / failed).

**Rationale**: Audit trail is essential. Owners need to be able to answer "what did we tell this customer last week?" without digging through SMS logs or email accounts. The table format supports scanning; the metadata supports investigation.

The rendered message text (not the template name) is what's shown, because *that's what the customer received*. Showing only "Sent: on_my_way template" would be useless — the rendered message including the actual ETA at that moment is what mattered.

### 11. Channel Indicators with Real Icons

**Decision**: SMS and email channels each have their own icon (chat bubble for SMS, envelope for email) used consistently across mobile picker, preview screen, sent confirmation, and web history.

**Rationale**: Visual consistency across channels reinforces that they're equivalent paths. Iconography is universal — readable at any zoom level, language-independent.

### 12. Customer Channel Override Persistence

**Decision**: When a tech overrides the channel for a single message, the override is logged in the comm history but does **not** change the customer's stored preference. The next message defaults back to the customer's preferred channel.

**Rationale**: Per-message overrides are tactical (today's situation). Permanent preference changes are strategic (the customer's communication preference). Conflating them would mean a single override silently changes the customer's stored preference — surprising and wrong. The customer's preference is a property of the customer record, edited in customer settings, not in a transactional comm screen.

## UX Patterns Established (Inherited by Future Flows)

Flow 4's design becomes the template for:

| Pattern | Reuse |
| :--- | :--- |
| Voice describes intent, not picks templates | All voice commands across the platform |
| Always-preview before customer-facing send | Future quote send, invoice send, payment request flows |
| Inline editable variables (chip + option row) | Any flow with templated content |
| Channel preference from entity, override per-action | Any multi-channel notification flow |
| Auto-return after success | All transactional confirmations |
| Customer disambiguation as conversation turn | Any voice-triggered customer-targeted action |

## Cross-Domain Considerations

### A. Communication template management UI

Tenants will eventually want to add custom templates beyond the MVP six. The Settings UI for managing templates (add, edit, disable, set per-channel rendering) is a Pass 4 deferred item. Schema and backend support this from MVP day one (per A4); only the UI is deferred.

### B. Reply handling

The web history shows "replied 'yes'" for one row in the prototype. Inbound replies (customer texts back) need a parallel design — where do they appear in Pilot, who gets notified, can voice respond to them? Out of scope for Flow 4 but flagged for a future Pass 3.X or Pass 4 design pass.

### C. Compliance and consent

SMS to customers requires opt-in consent in many jurisdictions. The design assumes consent is captured at customer creation. The actual consent flow (capture, storage, opt-out handling) is a backend + Settings UI concern flagged for Pass 4.

### D. Voice intent ambiguity at the boundaries

Some utterances are genuinely ambiguous — "tell Johnson the job's done" could be `arrived` (job site arrived) or `job_complete` (work finished). The intent matcher needs to be tuned to ask for clarification when confidence is below threshold, rather than picking. This is a tuning concern for the Llama prompt, not a design concern, but worth flagging that the design assumes the AI will gracefully ask when uncertain.

## Deferred Items (For Future Iteration)

- **Settings UI for template management** — Pass 4
- **Inbound reply handling** — Future flow
- **SMS consent capture and management** — Pass 4
- **Bulk customer messaging** (e.g., "notify all customers tomorrow's appointments") — Phase 2
- **Free-form messaging** (override the templated model with custom text) — Phase 2 per Pass 2 decision
- **Read receipts and customer-side actions** (link tracking, accept/decline buttons in messages) — Phase 2
- **Multi-language template variants** (Spanish, etc.) — Phase 2
- **Voice persona affecting comm tone** (formal vs friendly variants) — tied to A13 (post-MVP voice persona)

## Validation Checklist

Before implementation begins:

- [ ] Dev team aligned on the always-preview-before-send rule
- [ ] Voice intent grammar reviewed in `voice_action_router.py` registry
- [ ] Channel override persistence logic confirmed (per-message, not per-customer)
- [ ] Disambiguation flows match Flow 1 pattern (AI asks, doesn't guess)
- [ ] Customer preference field exists on customer record (or schema addition needed?)
- [ ] Comm history rendering on web verified against existing customer detail layout

## Next: Pass 3 Flow 5

Recommended next per the locked sequence: **Quote approval workflow**. Closes the governance loop introduced in Flow 1 (where techs submit quotes for owner approval). Touches both mobile (tech submits, owner approves on mobile) and web (owner approves with full editing). Should be a focused single session — the state machine is well-defined per Pass 2 A2.

Remaining flows after that:
- Flow 6: Calendar conflict resolution (web)
- Flow 7: Offline-to-online sync (mobile, hardest, saved for last)
