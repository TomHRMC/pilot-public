# Pilot For Trades Design System — Pass 3, Flow 1: Voice Quote Creation

**Version**: 1.0
**Status**: Locked
**Date**: April 24, 2026
**Scope**: Chat-style voice interface for quote creation on mobile
**Depends On**: Pass 1 (tokens), Pass 2 (IA), PRD §3.10 (Sales & Quoting), PRD §3.13 (Voice AI), mvp-arch.md §6 (Voice AI Pipeline)
**Backend Reference**: conversation_session, conversation_message, voice_comand_log, context_window_json (existing schema)

---

## Purpose

Flow 1 is the hero interaction for Pilot For Trades's mobile app — the moment that makes the product's "voice-first" positioning concrete. A field technician finishes a site walk and creates a complete, accurate, margin-visible quote entirely through conversation. The flow establishes the voice UX grammar that every other voice-enabled feature (customer comms, scheduling, field notes) will inherit.

This spec documents the locked design for Pass 3 Flow 1 after iteration across v1 (big-bang utterance model) and v2 (chat-style conversational model). v2 is the target for implementation.

## Design Evolution (v1 → v2)

The v1 prototype used a "big-bang" model: Mike speaks one complete utterance, the AI processes it, a quote appears. This model was rejected after review because:

1. **It assumes Mike knows the entire quote before he starts talking.** Real estimators think iteratively — they remember things, correct themselves, add details as they recall them.
2. **It offers no natural path for correction.** If the AI mishears "Tom Johnson" as "Tim Johnson," the user has to restart rather than correct mid-stream.
3. **It doesn't leverage the existing conversation architecture.** The backend already has `conversation_session`, `conversation_message`, and `context_window_json` designed for multi-turn interaction; a single-utterance UI fails to use that power.

v2 adopts a chat-style model matching user mental models formed by ChatGPT, Claude, and other frontier LLM mobile apps. This is the locked design.

## Architectural Anchors

The UI is a direct expression of the existing backend model:

| UI concept | Backend anchor |
| :--- | :--- |
| A "session" (named conversation in the drawer) | `conversation_session` row |
| Each bubble (user or AI turn) | `conversation_message` row with `role = 'user' \| 'assistant' \| 'system'` |
| The session's title in the drawer | `conversation_session.context_summary` (Ollama-generated, user-editable) |
| The "→ Tom Johnson · panel upgrade" context chip | Real-time read of `conversation_session.context_window_json` |
| Audio playback on user turns | `conversation_message.audio_object_key` |
| Voice command that created an action | `voice_command_log` linking message to action |
| Quote card rendered inline | Assistant message with a structured content payload (not free text) |

**Consequence**: the UI never builds its own state model. It renders what the backend already captures.

## Locked Design Decisions

### 1. Chat-Style Conversation Metaphor

**Decision**: The Voice tab is a chat interface modeled on frontier LLM mobile apps (ChatGPT, Claude). Turn-by-turn conversation. User bubbles right-aligned in brand indigo; assistant bubbles left-aligned in neutral-800.

**Rationale**: Mike already knows how this works. Zero learning curve. The metaphor encodes the backend's multi-turn architecture naturally.

### 2. Session History as Hamburger Drawer

**Decision**: On mobile, session history lives in a drawer opened via the hamburger icon at top-left. Tap a session to load and close the drawer. "+ New session" button creates a fresh conversation. Pattern matches ChatGPT mobile and Claude mobile.

**Rationale**: No sidebar on a phone. The drawer pattern is universal and requires no explanation.

### 3. Generic Opening Prompt

**Decision**: AI opens every session with "What can I help you with?" — not a quote-specific greeting.

**Rationale**: The Voice tab is used for more than quoting (customer comms, notes, calcs, schedule). A quote-specific opener narrows the user's mental model of what's possible. Neutrality invites broader use.

### 4. Context Chip in Conversation Header

**Decision**: When `context_window_json` has an active entity, a small indigo pill shows it at the top of the conversation ("→ Tom Johnson · 42 Oak Street"). Appears only when context is established. Updates as context shifts mid-session.

**Rationale**: Deictic references ("add it to the quote," "log 4 hours on that job") work because the AI tracks context. The chip shows the user *what the AI thinks the current referent is*, preventing silent wrong-job errors. A future lock icon will allow users to pin context against drift.

### 5. Per-Day-Reset Session Numbers for Voice Addressing

**Decision**: Session numbers shown as `#1`, `#2`, `#3` in the drawer, scoped to the calendar day. Reset at midnight (tenant timezone). Enables voice commands like "rename chat 2 to Williams service call," "delete chat 4," "open chat 1."

**Rationale**: Voice addressability requires a stable, speakable reference. Considered and rejected: ordinal (ambiguous as list changes), all-time numbers (grow large), themed labels like Greek letters or animals (voice recognition accuracy collapses; cognitive load too high for a feature whose point is not-looking-at-the-screen). Per-day reset hits the sweet spot of small, speakable, unambiguous.

**Implementation**: session number is a derived property, not stored. Computed via `ROW_NUMBER() OVER (PARTITION BY DATE(created_at AT TIME ZONE tenant_tz), user_id ORDER BY created_at)`.

**Voice grammar**:
- "Rename chat 2 to [new name]" → renames today's #2
- "Rename yesterday's chat 3 to..." → day-scoped
- "Delete chat 4" → destructive; requires spoken confirmation
- "Open chat 2" → switches active session
- "What did I work on in chat 1?" → AI reads back session summary + recent messages

**Error handling**: if Mike references a number that doesn't exist ("rename chat 5" when only 2 exist today), AI asks rather than guesses: "You only have 2 chats today. Did you mean yesterday's chat 5, or one of today's?"

### 6. AI-Driven Turn Flow

**Decision**: The AI leads the conversation when information is missing. Short prompts, domain-appropriate. Mike volunteers what he knows; the AI asks for gaps.

Example turn flow for quote creation:

```
AI:   "What can I help you with?"
Mike: "Create a quote for Tom Johnson"
AI:   "Matched Tom Johnson at 42 Oak Street. Different one?"
Mike: "That's him"
AI:   "Got it. What's the job?"
Mike: "200 amp panel upgrade, Square D main, 42 circuit panel"
AI:   "Adding those. What else for materials?"
Mike: "4/0 SER service cable and the permit"
AI:   "Added. Labor hours?"
Mike: "Six and a half at my standard rate"
AI:   "Here's where it lands. Say 'add' followed by items to keep building, or
       'looks good' to move on."
[AI renders quote card inline]
Mike: "Add five 20 amp breakers"
AI:   "Added 5 × 20A breakers at $13.50 each. New total $2,335.18, margin
       holds at 23.3%."
[AI re-renders quote card with new line highlighted]
Mike: "Looks good — submit it"
AI:   [technician] "Submitting quote for $2,335.18 for owner approval.
       You'll get a notification when it's reviewed."
AI:   [owner] "Sending quote for $2,335.18 to Tom Johnson. Say 'yes' to
       confirm or tell me what to change."
```

**Pacing rationale**: terse in field conditions; wordier in the UI design review would be wrong. Mike is often glanceing at the screen between tasks.

### 7. Role-Aware Terminal Action

**Decision**: Quote card's primary action button reads "Submit for approval" for technicians and "Send" for owners. Assistant's final message mirrors the button. When tenant setting `require_approval_for_tech_quotes = false`, everyone sees "Send."

**Rationale**: Mirrors Pass 2 quote approval workflow. Techs can never unilaterally send a quote to a customer under the default configuration. Owners see a confirm-to-send loop because voice UIs need trust rails against misrecognition.

### 8. Inline Quote Card Rendering (Live vs Snapshot)

**Decision**: The quote (customer, line items, totals, margin, actions) renders as an assistant turn *inside the conversation*. Not a separate screen, not a bottom sheet, not a modal.

**Rationale**: Treating the quote as a structured assistant message keeps the conversation model pure. It mirrors how ChatGPT renders code blocks and Claude renders artifacts — output is part of the conversation, not a context switch.

**Live vs snapshot rendering rules**: Quote cards have two rendering modes depending on context. This distinction is critical for correctness of historical review and must be honored by the backend (see A12 in backend-mvp-additions.md).

| Context | Render mode | Data source |
| :--- | :--- | :--- |
| Latest assistant turn in a session whose quote has NOT been submitted | `live` | Current state of quote entity |
| Earlier assistant turn in a session whose quote has NOT been submitted (scrollback) | `snapshot` | Frozen state as of when that turn was generated |
| Any assistant turn in a session whose quote HAS been submitted | `snapshot` | Frozen state of the submitted quote version |
| Quote shown in historical contexts (customer detail, quote list, approval queue, audit) | `snapshot` | Frozen `quote_version` record |

**Freeze trigger — submission is the event**: The specific moment that transitions all remaining `live` quote_preview messages in a session to `snapshot` is when the user (tech or owner) successfully submits the quote — Submit for approval (tech) or Send (owner). The UI returns to the home screen after acknowledging the submission, and by that time the freeze has been applied. No session "completion" heuristic is involved — only the explicit user action. This means:

- A session where Mike starts a quote and walks away without submitting → quote_preview messages remain `live` indefinitely (or until the underlying draft quote is garbage-collected by a retention policy, at which point the UI shows "this quote was discarded")
- A session where Mike submits successfully → all quote_preview messages frozen to the submitted `quote_version`; session becomes historically accurate from that moment forward

**Scrollback during active authoring (pre-submission)**: when the user adds a new turn that modifies the quote (e.g., "add five breakers"), the existing quote_preview card from the prior turn freezes to `snapshot` at that moment, capturing what it showed. The newly emitted assistant turn renders `live`. This preserves the "each card shows what it showed at that moment" principle without waiting for submission.

**Rationale for the nuance**: Mike's mental model while actively authoring is "the AI is showing me the quote" — a singular, current object that updates as he refines. But once he's done and revisits the session later (or scrolls back during authoring after adding items), each card should preserve what it showed at that point. This matches the ChatGPT code block pattern: each rendered block is what was generated at that turn, not a live view of current code. It also aligns with the existing `quote_version` immutability in the PRD.

**Historical review context** (not in Flow 1 scope, but worth naming): quotes viewed from customer records, quote lists, approval queues, or audit surfaces are always snapshots. A quote sent to a customer at $2,263.63 six months ago displays at $2,263.63 regardless of current price book or margin calculations. This will be enforced consistently across all future design flows that surface historical quotes.

**MVP constraint**: max 5 line items visible in the inline card. Scroll behavior for longer quotes deferred to post-MVP.

### 9. Margin Visualization

**Decision**: Margin gets its own sub-card on the quote. Emerald background when ≥ tenant target (default 20%), amber with gentle advisory note when below. Warning does NOT block sending.

**Rationale**: Margin is the single most important number for the owner value prop. Visual prominence reinforces the positioning. The no-block philosophy respects Mike's authority — he may strategically accept low margin (new customer acquisition, friend rate, seasonal slowdown).

### 10. Entity Highlighting in Transcription

**Decision**: As detected, entities (customer names, line items) render in brand indigo within the user's own message bubble. Real-time during live transcription.

**Rationale**: Gives Mike immediate confidence feedback. He sees whether the AI heard the right customer name before the AI even responds. Errors surface early, not buried in the quote output.

### 11. Confirmation as Conversation Turn (Not Modal)

**Decision**: Destructive actions (sending a quote, deleting a session) trigger a confirmation turn from the assistant, not a system modal. User responds by speaking or tapping.

**Rationale**: Maintains the conversation metaphor. The dialogue IS the confirmation. Modals steal focus and break the chat flow — which is wrong for voice-first interaction where Mike isn't always looking.

### 12. Amber-200 Mic Button (Contrast-Corrected)

**Decision**: Idle mic background is amber-200 (#FDD997) with amber-900 icon. Listening state shifts to amber-400 (#F59E0B) with subtle pulse.

**Rationale**: v1 used amber-400 with amber-900 icon — technically accessible but muddy in dark mode. Amber-200 idle + amber-400 active gives clear state differentiation while maintaining readability.

### 13. Text Input as First-Class Escape Hatch

**Decision**: The composer shows a text input next to the mic, always. Either path (voice or text) creates the same `conversation_message` row.

**Rationale**: Loud shops, repeated misrecognition, privacy situations — text is a required fallback. First-class placement (not hidden behind a menu) keeps it equally accessible.

### 14. AI-Generated Session Titles via Ollama

**Decision**: After the first meaningful turn, Ollama generates a 3-5 word `context_summary` stored on the session. Example: "Johnson panel upgrade," "Williams service call notes," "Truck stock audit."

**Rationale**: The drawer needs scannable titles. User-editable (voice or touch). See Pass 3 deferred items for personality-tuning of these titles.

### 15. Intent-Derived Session Icons (Future, Not MVP)

**Deferred to post-MVP**: Small glyph next to each session title in the drawer, derived from first detected intent (quoting = ⚡, field ops = 🔧, customer comms = 📞, notes = 📋). Flagged here so it's on the radar and doesn't get forgotten.

## UX Patterns Established (Inherited by All Future Voice Flows)

Flow 1's design becomes the template for:

| Pattern | Reuse |
| :--- | :--- |
| Hamburger drawer → session history | Every voice surface uses this |
| Generic opener + AI-led information gathering | All voice entry points |
| Context chip from `context_window_json` | Any voice flow that references entities |
| Per-day-reset session numbers | Global voice addressing grammar |
| Inline structured artifacts (quote card) | Job cards, customer comm previews, scheduled events |
| Confirm-as-turn for destructive actions | Scheduling changes, deletions, sends |
| Role-aware terminal actions | Quote send, schedule publish, customer comms dispatch |
| Text input alongside mic | Every voice surface |
| Entity highlighting in user turn | All flows that extract entities |

Subsequent flows (customer comms, scheduling, field notes) will consume these patterns, not redefine them.

## Voice Command Grammar Reference

Canonical commands established for quote creation. Handler implementations live in `backend/services/voice_action_router.py`.

| Intent | Example utterances | Action |
| :--- | :--- | :--- |
| `create_quote` | "create a quote for Tom Johnson", "new quote, Johnson house" | Initializes quote, matches customer, sets context |
| `add_line_item` | "add five 20 amp breakers", "add the permit" | Appends line items to active quote; margin recomputed |
| `set_labor` | "six and a half hours at my standard rate", "8 hours overtime" | Sets labor line; rate lookup from user or tenant defaults |
| `remove_line_item` | "remove the breakers", "drop the last item" | Removes line from quote |
| `set_discount` | "apply 10% discount, good for 7 days" | Owner-only; enforces margin cap |
| `submit_quote` | "submit it", "looks good, submit", "send it" | For techs: submit for approval. For owners: confirm-to-send |
| `cancel_quote` | "cancel this quote", "never mind" | Closes session without submission; quote remains draft |
| `disambiguate` | "the first one", "Oak Street one", "no, the other Tom" | Resolves ambiguous customer matches |
| `rename_session` | "rename chat 2 to Johnson panel", "call this Williams job" | Updates `context_summary` |
| `open_session` | "open chat 3", "show me yesterday's chat 1" | Switches active session |
| `delete_session` | "delete chat 4" | Destructive; confirm-as-turn |

## Addendum: Quote Style Support (Added April 25, 2026)

**Context**: After Flow 1 was originally locked, Pass 3 Flow 5 design discussions surfaced that Pilot For Trades must support three quote presentation styles (component, deliverable, lump-sum) to match real-world contractor workflows. See `quote-line-item-architecture.md` for the full architectural specification. This section documents how Flow 1 (voice quote creation) interacts with the three styles.

### Style Selection at Quote Creation

The voice flow's quote creation is **template-driven for style selection**. When a tech says "Create a quote for Tom Johnson, 200 amp panel upgrade," the AI matches against the tenant's quote templates by category and uses the matched template's style.

- If a tenant template `panel_upgrade_install` exists with style `deliverable`, the resulting quote is deliverable-style
- If no template matches, the AI falls back to the tenant's default style (or `component` if no default is configured)
- The tech can verbally request a style: "make it lump sum" early in the conversation switches the active template to a lump-sum-style template if one is available

### Quote Card Rendering by Style

The inline quote card rendered in the conversation thread adjusts its presentation based on the active quote's style:

**Component-style** (existing design from this spec):
- Flat list of line items, each with description and price
- All items shown
- Standard quote card layout

**Deliverable-style**:
- Customer-visible parent lines shown prominently with their full descriptions (collapsible if long)
- Internal child cost-tracking lines NOT shown by default (they're "what we pay," not "what the customer sees")
- A small toggle chip — "Customer view / My view" — switches between these two modes
- Tech reviews customer view to verify what gets sent; switches to my-view when checking margin or making cost adjustments

**Lump-sum-style**:
- Single prominent line with the full prose description
- Total prominent at the top
- "My view" toggle reveals the internal cost decomposition for margin verification

### Voice Grammar Adjustments per Style

Voice commands are still natural-language ("add five 20 amp breakers"), but the AI's interpretation differs by style:

- **Component-style**: "add five 20 amp breakers" creates a new visible line item with quantity 5, standard breaker pricing
- **Deliverable-style**: "add five 20 amp breakers" prompts the AI to ask "add as a new deliverable, or add to the cost breakdown of [active deliverable]?" — because in deliverable-style, breakers are typically internal cost components rolled into a parent deliverable like "Panel Upgrade Install"
- **Lump-sum-style**: "add five 20 amp breakers" defaults to adding as an internal cost component (the customer sees only the total), but the AI confirms: "adding to internal costs — your total stays the same, your tracked margin updates"

This means deliverable and lump-sum styles benefit from the AI's contextual awareness more than component-style does. The AI is not just translating commands, it's interpreting them against the active style's conventions.

### Margin Visualization Across Styles

Margin display in the quote card is unaffected by style — the calculation is always `(customer-visible total) − (sum of all costs including hidden children)`. What changes is which lines contribute to which side of that equation, governed by the visibility flags from `quote-line-item-architecture.md` A24.

### Touch-Based Editing Reference

For deliverable and lump-sum styles, line item descriptions can run hundreds of characters with bullet formatting. Voice editing of long descriptions is impractical (per the architecture doc's voice-editing constraint). The "Edit" button on the quote card opens a multi-line description editor for these cases. See A28 in `backend-mvp-additions.md` for the editor support details.

For component-style quotes (typically short descriptions), voice editing remains the primary path.

## Deferred Items (Post-Pass-3, For Future Iteration)

The following are captured here so they don't get lost:

- **Intent-derived session icons** in the drawer
- **Voice persona tone slider** (config setting: "boring ↔ creative" scale; affects Ollama prompts for titles and assistant messages)
- **Ambiguous customer disambiguation UI** (two Tom Johnsons in DB)
- **Unrecognized item handling** ("couldn't match 'super breaker' — did you mean?")
- **Offline mode** (voice capture works without network; quote saved locally; syncs when online)
- **Voice timeout/retry logic** (what if Mike starts speaking but Whisper gets nothing usable)
- **Long-quote scroll behavior** (quotes with 6+ line items)
- **Touch-based rich description editor** (markdown preview, bullet auto-formatting)
- **Session archival and retention** (what happens to sessions after 30/90 days)
- **Cross-session context** (can session #3 reference an entity from session #1?)
- **Session sharing** (owner views a tech's session for audit)

Each of these is a legitimate MVP-adjacent feature. They're intentionally scoped out of Pass 3 Flow 1 to keep the locked design tractable. They will be addressed in Pass 3.2+ or rolled into later flows that naturally surface them.

## Validation Checklist

Before implementation begins:

- [ ] Dev team reviewed and aligned on `conversation_session`, `conversation_message`, `context_window_json` as the backend anchors
- [ ] Ollama prompt for `context_summary` generation defined and tested
- [ ] Voice command grammar reviewed against `voice_action_router.py` handler registry
- [ ] Session number computation (per-day, per-user window function) confirmed performant at scale
- [ ] Accessibility review: screen reader labels on mic button, drawer, context chip, quote card
- [ ] Role-based rendering of terminal button verified against RBAC
- [ ] Margin warning copy approved by Tom

## Next: Pass 3 Flow 2

The next flow to prototype is recommended: **real-time job profitability drill-down on web**. This moves from mobile-first to web-first, exercises the Reports + Dashboard pin patterns, and delivers the owner's core value proposition — seeing where money goes on every job.

Alternative candidates: tech-to-customer templated communications (extends voice patterns established here), or quote approval workflow (closes the loop on governance introduced in this flow).
