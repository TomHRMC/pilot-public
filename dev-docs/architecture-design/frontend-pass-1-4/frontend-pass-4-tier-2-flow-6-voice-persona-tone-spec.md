# Pilot for Trades Design System — Pass 4, Tier 2 #6: Voice Persona Tone Setting UI

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Tenant-level setting UI for `voice_persona_tone` — the AI personality tone that affects voice readback, session title generation, assistant turn responses, and empty-state welcome copy. Brings A13 from "Post-MVP captured for roadmap" into MVP scope. Smallest Tier 2 surface.
**Depends On**: Settings IA framework · Tier 2 #4 (Mockup A) · `mvp-arch.md` §6 Voice AI Pipeline · A13 (existing schema field reservation)
**Backend additions**: A67 (voice persona prompt switching + preview audio generation)
**Deliverable shape**: Shape C (Settings IA + per-setting spec) per Pass 4 framework doc

---

## Purpose

The `voice_persona_tone` setting was reserved in the schema during Pass 3 (A13) and marked Post-MVP. The Settings IA framework brought it into MVP scope by giving it an IA home (`Settings > Voice AI > Persona tone`). Tier 2 #6 surfaces the actual UI.

Two genuine design problems despite the surface's small scope:

1. **Data type lock-in**: A13 left the type ambiguous (numeric scale 0–100, OR enum `conservative | balanced | playful`). Tier 2 #6 picks one and commits. This decision affects backend prompt engineering, the UI affordance, and the future Phase 2 expansion path.
2. **Preview affordance**: voice persona tone is meaningless without hearing it. An owner won't commit to "playful" without hearing what playful sounds like. The preview is the central UX problem — without it, the setting is unconfigurable in practice.

Everything else inherits: Mockup A (system-default-with-tenant-override) for the visual treatment, save-on-blur category, owner-only RBAC, mobile read-only display per the three-question inclusion rule.

## Strategic direction

### Three-position enum is the right granularity for MVP

A continuous 0–100 slider implies finer-grained control than the underlying LLM prompt-switching can actually deliver. Moving a slider from 47 to 53 produces no perceptible difference in AI output because the underlying mechanism is prompt template selection, not continuous interpolation. Three named positions match the prompt engineering reality and give the owner a simpler mental model.

The three positions: `conservative` (formal, brief), `balanced` (default; helpful and clear without personality), `playful` (warmer, conversational, occasional light humor). Phase 2 may extend to an enum-plus-slider hybrid for tenants who want finer control, but MVP doesn't justify the complexity.

### Audio preview is non-negotiable

The setting can't be evaluated without hearing it. A text description of "playful" is meaningfully different from actually hearing the voice say a representative phrase in playful tone. The preview affordance is the design work in this spec — without it, the setting becomes a configuration item that owners click once and never revisit because they have no basis for decision.

The preview is server-rendered audio generated on-demand for each tone, served as a small audio file the owner plays in-page. Three preview clips total (one per tone), generated server-side, cached.

### Voice persona tone is per-user with tenant default; tenant-controlled disable available

Each user picks the tone they hear when interacting with the AI. A tenant default applies when the user hasn't overridden — most users won't, and the default is `balanced`. A meta-toggle on the tenant defaults sub-page lets owners disable per-user override entirely if their brand requires uniform AI tone across the team. Default is "per-user override allowed."

Per-user override is a deliberate MVP feature (not Phase 2) because voice persona tone is inherently personal — it's the AI talking *to me* during my work day. Letting each user pick their preferred tone is a differentiator: techs who like a friendly AI get one; techs who want maximum efficiency get conservative; the team isn't locked into one owner's taste. The same three-tier resolution chain pattern from Tier 2 #4 Mockup C applies here: user override → tenant default → system default → fallback (`balanced`).

### Mobile is editable per-user override

Per Settings IA framework Decision 6 three-question test:
1. Affects tech mobile UX? **Yes** — tech hears voice persona constantly during voice intents
2. Could surprise tech if not visible? **Yes** — tech wonders why the AI sounds different than they remember
3. User override allowed? **Yes** — per the per-user override decision above

→ **Mobile is editable for the user's own override.** Tech sees their current effective tone at `Mobile > Settings > Voice > Persona tone` with three-card selector and preview affordances (Decision 5). The tenant default is shown for context with a "Match team default" affordance. If the tenant has disabled per-user override (Decision 9), the mobile view falls back to read-only with provenance annotation.

## Locked design decisions

### 1. Data type — three-position enum with three-tier resolution

**Decision**: `voice_persona_tone` is an enum with three values: `conservative | balanced | playful`. System default: `balanced`. Three-tier resolution: user override → tenant override → system default → fallback.

**Schema** (this confirms the enum option from A13's "or" clause; the numeric scale option is rejected):

```sql
-- system_default row:
-- key = 'voice_persona_tone'
-- value = 'balanced'

-- tenant_setting row (optional override):
-- tenant_id = ...
-- key = 'voice_persona_tone'
-- value = 'conservative' | 'balanced' | 'playful'

-- user_setting_override row (optional override; per A53 from Tier 2 #4):
-- tenant_id = ...
-- user_id = ...
-- key = 'voice_persona_tone'
-- value = 'conservative' | 'balanced' | 'playful'

-- Meta-toggle on tenant for whether per-user override is allowed:
-- tenant_setting row:
-- key = 'voice_persona_tone_user_override_allowed'
-- value = 'true' (default) | 'false'
```

**Rationale**: numeric scale is rejected because it implies prompt-engineering granularity that doesn't exist. The actual mechanism is selecting one of three prompt templates; a slider on top of that is misleading UI. Three named positions match the engineering reality and give users a clearer choice space.

**Three-tier resolution at runtime** (per A53 from Tier 2 #4):
1. If user has override AND tenant allows per-user override → use user override
2. Else if tenant has override → use tenant override
3. Else use system default (`balanced`)
4. Fallback constant: `balanced`

**Forward-compatibility for Phase 2**: if observed demand justifies finer control, the schema can extend to support per-tone customization (e.g., `playful_intensity` as a sub-setting of the playful tone) without breaking the enum primary value. This avoids the "we shipped a slider, now we need to migrate" trap.

### 2. The three tones — what each one means

**Decision**: each tone has a defined personality with defined effects:

| Tone | Personality | Effect on AI output |
| :--- | :--- | :--- |
| **`conservative`** | Formal, brief, business-like | Voice readback uses minimal pleasantries; session titles are descriptive without flair; empty-state copy is functional ("Tap to speak"); assistant responses are direct |
| **`balanced` (default)** | Helpful and clear without strong personality | Standard professional tone; brief but warm; default for most operational contexts |
| **`playful`** | Warmer, conversational, occasional light humor | Voice readback uses friendly pleasantries; session titles can be evocative; empty-state copy is welcoming ("Hey! Tap to speak"); assistant responses use slightly more conversational phrasing |

**Where the tone applies** (locked in A67 below):
- Voice intent assistant turn responses (per arch doc §6 Voice AI Pipeline)
- Session title generation (per A11)
- Empty-state welcome text in the Voice tab
- Voice readback for confirmations (e.g., "Confirming you want to send this quote? Yes or no.")

**Where the tone explicitly does NOT apply**:
- Customer-facing SMS messages (templates are tenant-fixed; tech-composed free-form replies are unmodified)
- System-generated emails (transactional emails use a fixed Pilot voice, not tenant-tone)
- Push notification copy (driven by category templates, not LLM-generated)
- Any UI copy outside the Voice tab (button labels, settings descriptions, error messages — all use Pilot's standard product voice)

**Rationale**: limiting tone to AI-generated voice and Voice-tab surfaces keeps the personality consistent where it makes sense (the AI itself) without bleeding into surfaces that should sound like Pilot rather than the tenant's chosen tone. SMS templates use tenant-set wording but not tenant-set tone modifiers. System emails use Pilot's brand voice for legal/billing reliability.

### 3. Audio preview — three on-demand server-generated clips

**Decision**: The settings UI offers a "Hear preview" affordance per tone. Tapping plays a server-generated audio clip of the AI saying a representative phrase in that tone. The owner can play any of the three previews at any time, before or after committing to a tone.

**Preview behavior**:
- Three preview clips, one per tone — generated server-side via the existing voice synthesis pipeline (or a dedicated TTS service if voice synthesis isn't ready; see A67 below)
- Cached aggressively — preview clips don't change between deployments unless the prompt templates change
- Played in-page via standard HTML5 audio with play/pause control
- Each preview is ~5–8 seconds of representative AI output for that tone

**Preview content** (the actual phrase the AI says):
- *Conservative*: "Quote QU-1024 has been sent to John Smith. Total: $4,250. Customer acceptance is pending."
- *Balanced*: "I sent the quote for John Smith — $4,250 total. Waiting on his acceptance now."
- *Playful*: "Quote's on its way to John Smith for $4,250. Now we wait — fingers crossed!"

These three phrases are the same factual content rendered through each tone's personality. Owner can hear the difference directly.

**Rationale**: an audio preview is the only way for an owner to actually evaluate tone choice. Text descriptions are abstract; hearing a 6-second clip is concrete. Server-side caching keeps the preview cost negligible — three audio files served from a CDN. The representative phrase is intentionally a quote-completion confirmation because that's a high-frequency real-world AI utterance the owner will hear repeatedly.

### 4. UI layout — two web pages: personal preference and team defaults

**Decision**: Two web sub-pages mirror the Tier 2 #5 personal-vs-tenant split:

- **`Settings > Voice AI > Persona tone`** — the user's personal preference (all roles see this; everyone has a personal preference)
- **`Settings > Voice AI > Tenant defaults > Persona tone`** — the team default + meta-toggle for whether per-user override is allowed (owner-only)

#### Personal preference page (all roles)

Three tone cards in a horizontal row. Card states:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Voice persona tone                                                         │
│ ───────────────────                                                        │
│                                                                            │
│ How the AI sounds when speaking to you. Your team's default is Balanced.   │
│                                                                            │
│   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐    │
│   │ Conservative      │   │ Balanced          │   │ Playful           │    │
│   │                   │   │ (team default)    │   │                   │    │
│   │ Formal, brief,    │   │ Helpful, clear,   │   │ Warmer, more      │    │
│   │ business-like     │   │ professional      │   │ conversational    │    │
│   │                   │   │                   │   │                   │    │
│   │ [▶ Hear preview]  │   │ [▶ Hear preview]  │   │ [▶ Hear preview]  │    │
│   │                   │   │                   │   │                   │    │
│   │ [Use this tone]   │   │ ✓ Selected        │   │ [Use this tone]   │    │
│   │                   │   │   (current)       │   │                   │    │
│   └───────────────────┘   └───────────────────┘   └───────────────────┘    │
│                                                                            │
│ Currently using: your team's default · [Match team default]                │
└────────────────────────────────────────────────────────────────────────────┘
```

Card states with per-user override layer:
- **Unselected card**: brand-indigo "Use this tone" button
- **Selected card matching team default**: "✓ Selected (current)" annotation, plus subtitle "(team default)" indicating the user is inheriting
- **Selected card differing from team default**: "✓ Selected (your preference)" annotation, plus the team-default card has a "(team default)" annotation for context
- **Footer when no user override**: "Currently using: your team's default · [Match team default]" (link is disabled when already on team default)
- **Footer when user has overridden**: "Currently using: your preference · [Match team default]" (link reverts user override; falls back to team default)

#### Team defaults page (owner-only)

Same three-card layout; the cards now drive the tenant default rather than the user's personal override. Plus a meta-toggle at the top:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Tenant defaults > Voice persona tone                                       │
│ ──────────────────────────────────                                         │
│                                                                            │
│ The default tone for users who haven't picked their own. Users can pick    │
│ a different tone for themselves unless you disable that below.             │
│                                                                            │
│ Allow users to pick their own tone?  [ ● yes ]                             │
│   Default: yes                                                             │
│                                                                            │
│ ─────────────────                                                          │
│                                                                            │
│ Default tone (when users haven't picked their own):                        │
│                                                                            │
│   [Three tone cards here, same layout as personal preference page]         │
│                                                                            │
│ ─────────────────                                                          │
│                                                                            │
│ Currently using: system default · [Reset to system default]                │
└────────────────────────────────────────────────────────────────────────────┘
```

The meta-toggle (`voice_persona_tone_user_override_allowed`) defaults to `true`. Disabling it locks all team members to the tenant default; their personal preference page becomes read-only with a "Set by your tenant" annotation (see Decision 5 mobile rendering for the parallel mobile behavior).

**Save behavior on both pages**: Save-on-blur per Settings IA framework Decision 5. Tapping "Use this tone" or toggling the meta-toggle commits immediately with optimistic UI. Toast surfaces: "Voice tone updated to [tone name]" or "Per-user override allowed/disabled."

**Confirmation before changing — none in MVP**: I considered requiring confirmation before disabling per-user override ("Are you sure? All your team's personal preferences will be overridden until you re-enable this."). I rejected confirmation because (a) personal preferences aren't deleted, just suspended — re-enabling restores everyone's previous picks, (b) the change is auditable and reversible, (c) confirmation friction is wrong for a low-stakes setting. The footer text on the team defaults page makes the consequence explicit: "Users can pick a different tone for themselves unless you disable that."

**Rationale**: card layout is the right affordance because tones are mutually exclusive choices. Three cards horizontally on web shows all options at a glance with previews ready. Splitting into two pages mirrors the Tier 2 #5 personal-vs-tenant pattern and keeps each page focused on a single decision scope.

### 5. Mobile editable display — three-card vertical stack

**Decision**: At `Mobile > Settings > Voice > Persona tone`, the tech sees a three-card vertical stack with the same affordances as the web personal preference page (Decision 4):

```
┌─────────────────────────────────┐
│ Persona tone                    │
│ ─────────────                   │
│                                 │
│ How the AI sounds when speaking │
│ to you. Your team's default is  │
│ Balanced.                       │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Conservative                │ │
│ │ Formal, brief, business     │ │
│ │ [▶ Hear preview]            │ │
│ │ [Use this tone]             │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Balanced  ✓ Selected        │ │
│ │ (your team's default)       │ │
│ │ Helpful, clear, professional│ │
│ │ [▶ Hear preview]            │ │
│ │ (current)                   │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Playful                     │ │
│ │ Warmer, more conversational │ │
│ │ [▶ Hear preview]            │ │
│ │ [Use this tone]             │ │
│ └─────────────────────────────┘ │
│                                 │
│ [Match team default]            │
└─────────────────────────────────┘
```

Each card has the preview affordance plus the "Use this tone" commit button. The currently-selected card shows "✓ Selected" with subtitle indicating whether the user is on the team default or has overridden. "Match team default" link at the bottom (parallel to web, but worded for tenant-default-not-system-default since that's what makes sense for a tech).

**Save behavior**: same as web (Decision 4) — save-on-blur, optimistic UI, toast confirmation.

**Fallback to read-only when tenant disables per-user override**: if the tenant has set `voice_persona_tone_user_override_allowed = false` (per Decision 9), the mobile UI falls back to read-only display:

```
┌─────────────────────────────────┐
│ Persona tone                    │
│ ─────────────                   │
│                                 │
│ AI is set to: Balanced          │
│                                 │
│ Set by your tenant              │
│                                 │
│ Helpful, clear, professional    │
│                                 │
│ [▶ Hear current tone]           │
└─────────────────────────────────┘
```

In this fallback state, the tech can play the preview for the currently-set tone but cannot change it (tenant has disabled per-user override). Provenance annotation ("Set by your tenant") follows the Settings IA framework Decision 2 pattern.

**Rationale**: vertical-stack three-card mobile UI is the right size for a phone screen — each card has clear affordances, the previews are easy to tap, and the choice space is comprehensible. Total page length is bounded (three cards plus header plus link). The fallback-to-read-only when tenant disables per-user override handles the meta-toggle correctly without requiring a separate UI state machine.

### 6. Voice intent extension — tone applies to assistant turn output, evaluated per-user

**Decision**: The voice intent grammar from Flow 1 doesn't change for owner-facing or tech-facing intents. But the assistant's *output* — the AI's spoken response back to the user — renders through the **requesting user's** effective `voice_persona_tone`, not the tenant's. Two different users speaking voice intents to the same AI in the same conversation can hear different tones.

**Implementation** (captured in A67):
- Existing voice intent handlers in `api/voice/intents.py` produce structured response payloads
- A new layer `services/voice_persona_renderer.py` takes the structured payload + the **requesting user's effective `voice_persona_tone`** (resolved via three-tier chain per Decision 1) and produces the final TTS-ready text via tone-specific Ollama prompt template
- Three prompt templates: `prompts/voice_response_conservative.md`, `prompts/voice_response_balanced.md`, `prompts/voice_response_playful.md`
- The renderer is called from every intent handler that produces voice output
- Same renderer is used by A11 session title generation (Decision 7) and Voice tab empty-state copy generation (Decision 8) — both also evaluated per-user

**Why per-user evaluation matters**:
- Mike (tech, prefers playful) speaks a voice intent → AI responds in playful tone
- Sarah (owner, prefers conservative) speaks a voice intent later → AI responds in conservative tone
- The same physical AI infrastructure produces different-sounding output per user

**When tenant disables per-user override** (Decision 9): the renderer's three-tier resolution returns the tenant default (or system default) for all users; per-user effective tone collapses to the tenant value.

**Rationale**: per-user evaluation is the natural extension of the three-tier resolution chain. The architecture from A53 (Tier 2 #4) handles per-user resolution generically; A67 just calls into it. The result: each user has their own AI personality experience while operational consistency for shared artifacts (session titles visible across the team) follows the same per-user evaluation rule — see Decision 7 for that nuance.

### 7. Session title generation — uses the session creator's tone

**Decision**: Per A11, session titles are auto-generated by Ollama from session content. With Tier 2 #6 in effect, title generation uses the **session creator's** effective tone (the user who initiated the voice session), not the viewer's tone. The title is generated once at session creation; subsequent viewers see the title as the creator's AI rendered it.

| Tone | Example session title for the same conversation |
| :--- | :--- |
| Conservative | "Quote QU-1024 review and customer acceptance follow-up" |
| Balanced | "Quote QU-1024 — review and follow-up with customer" |
| Playful | "QU-1024: review and chase the customer" |

**Per-user implication**: if Mike (playful) creates a voice session, the title is generated playful. Sarah (conservative) viewing Mike's session later sees Mike's playful title. This is intentional — the title reflects how Mike experienced the AI at creation time, not how Sarah would have heard it.

**Rationale**: session titles are creation-time artifacts; regenerating them per-viewer would be expensive and confusing ("why does this session have a different title than yesterday?"). Locking to creator's tone matches user intuition — the title is part of the session's history. Exception consideration: if a tenant disables per-user override mid-session-history, future titles will be tenant-default; existing titles remain as they were generated. This is consistent with normal setting-change semantics.

### 8. Empty-state welcome copy in the Voice tab — per-user

**Decision**: The Voice tab's empty state (no recent voice commands) renders welcome copy that varies by the **current viewing user's** tone:

| Tone | Empty state copy |
| :--- | :--- |
| Conservative | "Tap the microphone to begin voice input." |
| Balanced | "Tap the microphone to start. Try 'create quote' or 'show me today.'" |
| Playful | "Hey! Tap the mic to get started. I can do quotes, schedules, the works." |

**Per-user implication**: Mike (playful) opens the Voice tab and sees the playful welcome; Sarah (conservative) opens her Voice tab and sees the conservative welcome.

**Rationale**: empty states are a real surface where the user's chosen personality should show through. Conservative users don't want the AI saying "Hey!"; playful users want warmth. Same engineering pattern as voice readback — three template variants resolved per-user at render time.

### 9. Tenant disable of per-user override — meta-toggle on team defaults page

**Decision**: A tenant-level meta-toggle `voice_persona_tone_user_override_allowed` controls whether users can pick their own tone. Default: `true`. Owner-only edit at `Settings > Voice AI > Tenant defaults > Persona tone` (per Decision 4 team defaults page layout).

**Behavior when toggle is `true` (default)**:
- Each user can pick their own tone via personal preference page (web) or three-card vertical stack (mobile)
- AI renders responses using each user's effective tone
- Standard three-tier resolution: user override → tenant default → system default

**Behavior when toggle is `false` (tenant disables per-user override)**:
- User personal preference page falls back to read-only display showing the tenant default
- Mobile UI falls back to read-only with provenance annotation per Decision 5 fallback state
- AI renders all responses using the tenant default for all users (per-user overrides are suspended, not deleted)
- If tenant re-enables the toggle later, all previously-set user overrides come back into effect (no data loss)
- Audit log captures the tenant-level toggle change per Settings IA framework Cross-Domain G

**UI treatment of the meta-toggle** on the team defaults page:

```
Allow users to pick their own tone?  [ ● yes ]
  Default: yes
```

When toggled to "no":

```
Allow users to pick their own tone?  [ ◯ no ]
  Default: yes  ·  Re-enabling will restore each user's previous selection
```

The "re-enabling will restore" annotation surfaces only when the tenant has disabled and there are existing user overrides in the database — otherwise the annotation is hidden.

**Rationale**: most tenants leave the meta-toggle alone (default `yes`). Tenants with strict brand/voice policies can disable per-user override to enforce uniform tone. Suspending vs. deleting user overrides is the safer model — re-enabling restores everyone's prior preferences without requiring users to re-pick. This is forward-compatible with Phase 2's potential "tenant policy library" feature where multiple meta-toggles might collectively define a "voice policy" preset.

**Tenant-level setting key**: `voice_persona_tone_user_override_allowed` (boolean; default true; tenant-only; no system default override since this is a tenant-policy decision, not a Pilot-platform decision).

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| Card-based mutually-exclusive selection with audio preview | **NEW** | — |
| Server-cached audio preview clips for setting evaluation | **NEW** | — |
| Tone-specific prompt template selection (data-driven AI personality) | **NEW** | Arch doc §6 voice intent infrastructure |
| Three-position enum data type for AI personality controls | **NEW** | — |
| Tenant meta-toggle for "per-user override allowed" | **NEW** | — |
| Suspend-not-delete user overrides when tenant disables per-user override | **NEW** | — |
| Per-user evaluation of three-tier resolution chain at runtime | Reused | Tier 2 #4 Mockup C, A53 |
| Personal preference vs. team defaults two-page split | Reused | Tier 2 #5 (notification preferences) |
| System-default-with-tenant-override visual treatment | Reused | Tier 2 #4 Mockup A |
| Save-on-blur category | Reused | Settings IA framework Decision 5 |
| Mobile editable per-user override (with fallback to read-only when tenant disables) | Reused / extended | Settings IA framework Decision 6 |

Four new patterns, three reused. The card-based selection with preview pattern is reusable for any future "pick one of N AI personalities" or "pick one of N visual themes" type setting; it's documented here as the canonical implementation.

## Cross-domain considerations

### A. Three new prompt templates need authoring

A67 below introduces three prompt templates: `voice_response_conservative.md`, `voice_response_balanced.md`, `voice_response_playful.md`. Each is a brief Ollama instruction that shapes the assistant turn output. Authoring is engineering work, not design work, but the design intent for each tone (Decision 2) is the input.

The same three-template approach extends to session title generation (A11 prompts) and Voice tab empty-state copy generation. Total: roughly 9 prompt templates (3 tones × 3 contexts).

### B. Backwards compatibility — existing `notification_outbox` and audit log

Existing voice intents already use `voice_response_balanced`-equivalent prompts (effectively, Pilot's standard professional voice). When A67 introduces the tone-specific renderer, all existing tenants are on `balanced` (the system default) so behavior doesn't change. Tenants who explicitly choose `conservative` or `playful` see new behavior; everyone else is unchanged.

Audit log captures `voice_persona_tone` setting changes per Settings IA framework Cross-Domain G.

### C. Voice readback in customer-facing contexts

Per Decision 2, voice persona tone does NOT affect customer-facing SMS (Tier 1.5) or transactional emails. This is a deliberate scope cut to keep customer-facing surfaces consistent across tenants. A "playful" tenant doesn't have their playful tone leak into customer SMS templates.

If a tenant wants playful voice tone but conservative customer messaging, that's the supported model. The opposite (conservative voice but playful customer messaging) is also supported. The two surfaces are independent.

### D. Voice commands themselves — phrasing the tech uses doesn't change

The tech says "create quote" or "tell Tom I'm 20 out" regardless of the tenant's persona tone. Tone affects only the AI's output, not the user's input. This is the right model — forcing techs to phrase voice commands differently per tone would be hostile UX.

### E. Phase 2 deferrals (locked)

- **Per-context override** — different tone for customer-facing voice readback vs. internal voice readback. Phase 2.
- **Custom prompt templates** — tenants edit their own prompt template (e.g., "use my brand voice"). Phase 2; significant engineering work plus moderation concerns.
- **Voice synthesis voice model selection** — different TTS voice (male/female, accent variants). Phase 2; depends on TTS infrastructure choice.
- **A/B preview** — play two tones back-to-back for comparison. Phase 2; current single-play model is adequate.
- **Tone preview from voice intent itself** — user says "let me hear the playful tone" and AI demos. Phase 2.
- **Customer-overhearing context detection** — AI auto-falls-back to balanced when tech is at a customer site (vs. in the truck alone). Phase 2; requires location/job-context heuristics.
- **Tenant policy preset library** — "apply 'professional services' policy" or "apply 'casual trades' policy" sets multiple meta-toggles at once. Phase 2.

### F. Settings catalog integration

The settings catalog (A52 from Tier 2 #4) extends to include `voice_persona_tone`. The catalog entry includes the enum values, current effective value, current scope, and revertibility. Settings search affordance can find this setting via "tone," "voice," "persona," "AI personality" synonyms.

### G. Onboarding integration (Tier 3 #10)

The onboarding flow does NOT walk new tenants through voice persona tone setup. The default (`balanced`) is appropriate for the vast majority of tenants. Tenants who want to deviate find the setting at any time. Adding voice tone to onboarding would slow the onboarding flow without meaningful value for most tenants.

The setting is mentioned in onboarding-end "things you can customize later" callouts (Tier 3 #10 surface) but is not a required step.

## Deferred items (Phase 2 / for future iteration)

See Cross-Domain E for the full list. All items deferred reflect decisions to keep MVP scope tight; none reflect uncertainty about whether the items are valuable.

## Validation checklist

Before implementation begins:

- [ ] Data type committed as three-position enum (`conservative | balanced | playful`) per Decision 1
- [ ] Three-tier resolution chain (user → tenant → system → fallback) implemented per Decision 1
- [ ] Three tones defined per Decision 2 — engineering team aligned on what each tone means
- [ ] Three preview clips authored and recorded — same factual content rendered in three tones
- [ ] Two web pages implemented per Decision 4: personal preference (all roles) + team defaults (owner-only)
- [ ] Tenant meta-toggle `voice_persona_tone_user_override_allowed` implemented per Decision 9 (default: true)
- [ ] Audio preview component implemented with single-play behavior (web and mobile)
- [ ] Mobile three-card vertical-stack editable display implemented per Decision 5
- [ ] Mobile fallback-to-read-only when tenant disables per-user override per Decision 5
- [ ] Per-user resolution at runtime in voice renderer per Decision 6
- [ ] Session title generation locked to creator's tone per Decision 7
- [ ] Voice tab empty-state copy resolves per viewing user's tone per Decision 8
- [ ] A67 backend addition specified including per-user resolution and meta-toggle behavior
- [ ] Three voice response prompt templates authored
- [ ] Three session title prompt templates authored
- [ ] Three empty-state copy variants authored
- [ ] Settings catalog (A52) entry added for `voice_persona_tone` and `voice_persona_tone_user_override_allowed`
- [ ] Audit log captures persona tone changes per Settings IA framework Cross-Domain G
- [ ] Audit log captures meta-toggle changes per Decision 9

## Backend addition (new for Tier 2 #6)

### A67. Voice Persona Tone Renderer + Preview Audio Generation + Per-User Resolution

**Triggered by**: Decisions 1, 2, 3, 4, 5, 6, 7, 8, 9 — bringing A13's reserved schema field into MVP scope with the renderer infrastructure plus audio preview plus per-user override and tenant meta-toggle.

**Scope**:

**Schema**:
- Tenant setting `voice_persona_tone` (existing per A13 reservation; values now committed to enum `conservative | balanced | playful`)
- System default: `balanced`
- User-level setting via `user_setting_override` table (per A53 from Tier 2 #4) — same schema, key = `voice_persona_tone`
- New tenant setting `voice_persona_tone_user_override_allowed` (boolean; default `true`; tenant-only — no system default override needed since this is tenant policy)
- Settings catalog entries per A52 (from Tier 2 #4) for both keys

**Voice persona renderer** (`services/voice_persona_renderer.py`):
- New module that wraps Ollama prompt rendering
- Takes a structured response payload (intent name, response context) plus a `user_id`
- Resolves the user's effective `voice_persona_tone` via three-tier chain (per A53 from Tier 2 #4):
  1. Check if tenant has `voice_persona_tone_user_override_allowed = true` (default)
  2. If yes: look up user override; if exists, use it
  3. Else fall through to tenant override
  4. Else fall through to system default (`balanced`)
- Selects the appropriate prompt template (`voice_response_{tone}.md`)
- Returns final TTS-ready text
- Called from every voice intent handler that produces voice output (refactor pass)
- Cache: prompt template files loaded once per worker process; effective-tone resolution cached per (user_id, tenant_id) for the duration of a single request

**Three voice response prompt templates** (in `prompts/voice/`):
- `voice_response_conservative.md`
- `voice_response_balanced.md` (existing prompts get refactored into this template)
- `voice_response_playful.md`

**Three session title generation prompt templates** (in `prompts/voice/`):
- `session_title_conservative.md`
- `session_title_balanced.md`
- `session_title_playful.md`
- A11 (session title generation) refactored to use the **session creator's** tone (per Decision 7), not the viewer's tone. Title is generated once at session creation; subsequent viewers see the title as the creator's AI rendered it.

**Three empty-state copy variants**:
- Stored as a static map in `services/voice_persona_renderer.py` (not LLM-generated; static text variants per tone)
- Voice tab empty-state component reads the map at render time using the **viewing user's** effective tone (per Decision 8)

**Preview audio generation** (`services/voice_preview_audio.py`):
- One-time generation: at deployment, three preview audio files generated using the configured TTS pipeline (or a dedicated TTS service if voice synthesis isn't ready)
- Each preview is ~5–8 seconds of representative AI output per tone
- Output stored in S3 as static MP3 files: `s3://pilot-static/voice-preview/{tone}.mp3`
- Cached at CDN edge; new preview audio only regenerates when the prompt templates change (rare; manual trigger via deployment script)
- Preview audio is universal — same three files served to all tenants and all users

**APIs**:
- `GET /api/v1/settings/voice-persona-tone` — returns the requesting user's effective tone, the team default, available enum values, preview audio URLs, whether user override is allowed by tenant policy
- `PUT /api/v1/settings/voice-persona-tone` — set the requesting user's tone (creates or updates `user_setting_override` row); returns 403 if tenant has disabled per-user override
- `DELETE /api/v1/settings/voice-persona-tone` — clear the user override; falls back to tenant default
- `GET /api/v1/settings/tenant/voice-persona-tone` — returns tenant default and meta-toggle state (RBAC: any role; data is read-only for non-owners)
- `PUT /api/v1/settings/tenant/voice-persona-tone` — set tenant-level tone (RBAC: owner only)
- `DELETE /api/v1/settings/tenant/voice-persona-tone` — revert tenant tone to system default
- `PUT /api/v1/settings/tenant/voice-persona-tone-user-override-allowed` — set the meta-toggle (RBAC: owner only); audit log entry per Decision 9

**Refactor pass over existing voice intent handlers**: all existing handlers in `api/voice/intents.py` updated to call `voice_persona_renderer.render(payload, user_id)` instead of producing direct text responses. Backwards-compatible because all existing tenants and users default to `balanced`.

**Effort estimate**: Medium — 4–6 days. Renderer with three-tier resolution + three prompt templates per context (voice response, session title) = 6 templates of moderate complexity. Refactor pass over existing intent handlers + the meta-toggle infrastructure + the user-override APIs are the cost drivers. Preview audio generation is one-time deployment work, not ongoing. Per-user resolution adds modest complexity (mostly already handled by A53's three-tier helper).

### Total Tier 2 #6 backend additions

A67 (4–6 days) = **4–6 days**.

---

## What this surface does NOT cover

- Voice intent grammar changes — not affected by tone setting
- Customer-facing SMS template tone — fixed regardless of tenant tone
- Transactional email tone — fixed regardless of tenant tone
- TTS voice model selection — Phase 2 (uses configured pipeline regardless of tone setting)
- Custom prompt templates — Phase 2
- Customer-overhearing context detection — Phase 2 (auto-fallback when tech is at customer site)
- Onboarding integration as a required step — explicitly skipped

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A67 added (1 addition). Cumulative through Tier 2 #6: A1–A67 with all numbering filled.

**Backend day estimate update**:
- Pre-Tier-2-#6 cumulative remaining MVP: 183–243.5 days
- Tier 2 #6 additions: 4–6 days
- New cumulative remaining MVP: **187–249.5 days**

**Framework doc**: Tier 2 #6 status flips from `pending` to `locked` in Pass 4 progress detail. Tier 2 #7 (account settings — profile, password, MFA enrollment, integrations management) becomes the next surface.

**No new arch doc patterns**: Tier 2 #6 doesn't introduce new platform-level patterns. The card-based selection with audio preview is documented here but doesn't warrant a §16 entry — it's setting-UI specific. If a Phase 2 surface needs a similar pattern, it can reference Tier 2 #6 as the prior art.

**No new PRD additions**: voice persona tone was already mentioned in PRD §3.13 (Voice AI). Tier 2 #6 just adds the UI; the product behavior was always present in the PRD.

## Next: Tier 2 #7 — Account Settings (Profile, Password, MFA, Integrations Management)

Tier 2 #7 closes Tier 2. It's user-personal (vs. tenant-shared) settings, which is a meaningfully different scope than #4–#6. Includes profile editing, password change, MFA enrollment (Cognito MFA), active sessions list, data export request, and the integrations management sub-surface (read connection state for QuickBooks and Calendar; disconnect/reconnect actions).

Estimated 250–350 lines per the Shape C deliverable definition. The MFA enrollment flow is the substantive new design problem; everything else is straightforward CRUD with familiar patterns.

After Tier 2 #7 closes, Tier 2 is complete. Tier 3 begins (states catalog + onboarding).
