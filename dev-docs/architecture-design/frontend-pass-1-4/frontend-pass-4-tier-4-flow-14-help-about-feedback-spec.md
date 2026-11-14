# Pilot for Trades Design System — Pass 4, Tier 4 #14: Help / About / Feedback Surfaces

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: AI-mediated help system with RAG retrieval over markdown corpus, About / version / legal surface, structured feedback submission with email intake. Final Pass 4 surface.
**Depends On**: Pass 1 design tokens · Voice AI infrastructure (`mvp-arch.md` §6) · pgvector for embeddings (§2.3) · Ollama Llama 3.x · all Pass 1–3 + Pass 4 specs (help articles cover the full product surface)
**Backend additions**: A84 (Help AI agent + RAG + chat session management), A85 (Markdown corpus + embedding pipeline + S3 storage), A86 (Contextual help anchor metadata + opener context payload), A87 (Feedback submission with email intake), A88 (Anonymization pipeline for training data capture)
**Deliverable shape**: Shape A (Full flow spec) per Pass 4 framework doc — substantially larger than originally projected because of AI-mediated complexity

---

## Purpose

The help system is the difference between a solo founder spending hours per week on support tickets and a solo founder spending minutes. For Pilot — a product whose user base will grow faster than your direct support capacity — this matters.

The strategic frame: **help should feel like a continuation of how Pilot users already interact with the product, not a separate paradigm**. Pilot is voice-first AI-first. Help should be too. Users open help and have a chat-style conversation with AI that knows the product, retrieves relevant articles for grounding, and walks them through what they need.

This is meaningfully different from traditional B2B SaaS help systems (knowledge base + ticket system + community forum). Three workstreams in #14:

1. **AI-mediated help** with RAG retrieval, contextual opener (knows what the user is looking at), and chat session capture for training data — the central deliverable
2. **About / version / legal surface** — system info, build version, legal links, support contact
3. **Feedback submission** — structured category + text; email intake for MVP, ticket system in Phase 2

Plus the markdown corpus structure that doubles as RAG context AND as the source of truth for help content. The corpus structure is intentionally designed so AI retrieval and human reading work from the same files.

## Strategic direction

### AI-mediated help is the right design, not a futurist gimmick

Pilot is voice-first AI-first. Users already engage with AI for quote creation, voice readback, intent recognition. Help should feel like the same conversational paradigm. The alternative — a traditional knowledge base where users browse hierarchical categories and read static articles — would feel jarring against the rest of the product.

AI-mediated help also scales the support model. Tom-the-solo-founder can update the markdown corpus once and have it propagate to every user query. Real-time answers don't require Tom to be in his inbox.

### Markdown in S3 is the corpus, but it's also the human help articles

The markdown files serve two consumers:
- **AI retrieval**: chunks get embedded into pgvector; semantic search retrieves relevant chunks for any query
- **Human reading**: when the user asks for an explicit article, the AI surfaces the article text directly via the chat interface

Same files. Same content. The structure works for both because the metadata schema (per Q3 in scoping) is designed for both retrieval and rendering.

### Context-aware help is a meaningful product differentiator

When a user opens help from inside a settings page or a flow, the AI knows what they're looking at. "I see you're on the QuickBooks integration page — how can I help?" This is materially better than the user typing "How do I connect QuickBooks?" into a search box.

The context payload is intentionally minimal (action types, not entity contents) for privacy. Action-type-only is enough for grounded responses without exposing business data.

### Chat sessions are training data, with anonymization at the pipeline stage

Every help conversation is captured for later use as fine-tuning data or as input to improve markdown content. Users see this transparently ("Pilot uses help conversations to improve our help content. Personal information is removed before use."). Anonymization happens before training use, not at capture time — short-term sessions remain unscrubbed in `help_chat_session` for 90 days for debugging, then get anonymized and rolled into training data.

### Feedback intake via email for MVP, ticket system Phase 2

Solo founder economics: your inbox is the support channel for the foreseeable future. Feedback submissions become emails to your support inbox. When volume justifies a ticket system (likely 6–12 months post-launch), Phase 2 introduces it.

## Locked design decisions — Help System

### 1. Help opener — entry points and context

**Decision**: Help is accessible from three entry points:

#### (a) Main navigation — non-contextual

Web: a "?" icon in the top-right of the app shell, persistent across all pages. Tap opens the chat panel.

Mobile: a "Help" item in the More menu (overflow nav on mobile). Tap opens the chat screen.

Non-contextual entry: AI opens with "Hi! What can I help you with?" — no current-page context.

#### (b) Settings sub-page — accessible always

`Settings > Help & About` (combined sub-page; About content per Decision 11 lives here too). Always accessible from the settings tree. Equivalent to non-contextual entry from main nav.

#### (c) Inline contextual help — selective placement

A "?" icon next to specific labels and concepts on complex surfaces. Inline placement is selective per the original Q3 framework — not every UI element gets a "?" icon, only the genuinely complex ones.

Inline contextual help opens with the AI primed with surface context. Initial AI message reflects the context: "I see you're on the QuickBooks integration page. What can I help you with?" — or for very specific concepts, the AI may proactively explain the concept the user clicked on.

#### Contextual help anchor placements (selective)

| Surface | Help anchors |
| :--- | :--- |
| Settings → Integrations → QuickBooks (auto-expiry, sync direction) | next to "Auto-expire" toggle, next to "Sync direction" picker |
| Settings → Integrations → Calendar | next to "Auto-expire" toggle |
| Settings → Notifications → Preferences (forced-minimum cells) | inline annotation explainer plus "?" icon for "Why is this locked?" |
| Settings → Sync & Storage → Background sync | next to "Push interval" setting |
| Settings → Voice AI → Persona tone | next to the tone cards |
| Settings → Subscription & Billing → SMS quota | next to "Cap policy" setting |
| Settings → Operations → Margin buckets | next to bucket boundary editor |
| Settings → Tax configuration | next to tax rate field |
| Account settings → MFA methods | next to each method type card |
| Field issues queue | next to severity class indicator |
| Calendar conflict resolution | next to deletion-conflict treatment buttons |
| QuickBooks conflict resolution | next to master direction indicator |
| Quote approval queue | next to "Approval required" annotation |
| Onboarding — Tax setup sub-flow | inline help on jurisdiction selection |

Selective placement keeps content authoring scope manageable. Tom owns content for each contextual help target.

**Rationale**: three entry points cover the realistic ways users seek help. Non-contextual when they're proactively researching ("how does Pilot handle X?"); contextual when they're stuck on a specific concept. Inline placement on selective complex surfaces gives help where it's most likely needed without contextual-help-icon proliferation.

### 2. Chat panel layout — web

**Decision**: Help chat panel is a slide-out drawer from the right edge of the viewport (web).

```
┌────────────────────────────────────┐  ┌─────────────────────────┐
│                                    │  │ Help                  ✕ │
│    [Main app surface continues     │  │ ─────                   │
│     in left portion]               │  │                         │
│                                    │  │ AI 14:32                │
│                                    │  │ Hi! What can I help     │
│                                    │  │ you with?               │
│                                    │  │                         │
│                                    │  │ ─                       │
│                                    │  │                         │
│                                    │  │ You 14:32               │
│                                    │  │ How do I connect QB?    │
│                                    │  │                         │
│                                    │  │ AI 14:33                │
│                                    │  │ Sure — to connect       │
│                                    │  │ QuickBooks Online:      │
│                                    │  │                         │
│                                    │  │ 1. Go to Settings >     │
│                                    │  │    Integrations >       │
│                                    │  │    QuickBooks           │
│                                    │  │ 2. Click "Connect"      │
│                                    │  │ 3. Follow the OAuth     │
│                                    │  │    flow with your QB    │
│                                    │  │    account              │
│                                    │  │                         │
│                                    │  │ Want me to walk you     │
│                                    │  │ through this? Or read   │
│                                    │  │ the full article?       │
│                                    │  │                         │
│                                    │  │ [📄 Read full article]  │
│                                    │  │ [Walk me through it]    │
│                                    │  │                         │
│                                    │  │ ─────────────────────   │
│                                    │  │ [🎤] [Type message...]│➤│
│                                    │  └─────────────────────────┘
└────────────────────────────────────┘
```

#### Layout details

- Drawer width: 400px on desktop; full-width on tablet
- Drawer slides in from right with 200ms ease-out animation
- Main app surface remains visible and interactive — drawer doesn't block it
- Close X in drawer top-right; clicking outside the drawer also closes it
- Chat history scrolls; latest message at bottom
- Composition zone fixed at bottom: voice mic button + text input + send arrow
- AI messages have AI avatar (small Pilot icon); user messages have user avatar (initials)
- Timestamps on each message
- Action buttons within AI messages (e.g., "Read full article," "Walk me through it") trigger contextual sub-flows

#### Suggested follow-up actions

When the AI responds, it can offer follow-up action buttons inline:
- **"Read full article"** — surfaces the relevant article content in a fuller card within the chat
- **"Walk me through it"** — AI provides step-by-step procedural guidance
- **"That answered it, thanks"** — closes the conversation gracefully (positive feedback signal)
- **"Still confused"** — escalation prompt; AI tries different framing or surfaces alternative articles

These buttons help structure conversations and capture user-intent signals (helpful for training data quality).

**Rationale**: side drawer is the right pattern for help — keeps user in their current context (no full-page modal navigation away). Width is generous enough for readable conversation. Action buttons within messages structure the chat without forcing users into a rigid flow.

### 3. Chat screen layout — mobile

**Decision**: Help chat is a full-screen view on mobile (no side drawer; mobile screens are too narrow for sidebars).

```
┌─────────────────────────────────┐
│ ← Help                          │
│ ─────────                       │
│                                 │
│ AI 14:32                        │
│ Hi! What can I help you         │
│ with?                           │
│                                 │
│ ─                               │
│                                 │
│ You 14:32                       │
│ How do I create a quote?        │
│                                 │
│ AI 14:33                        │
│ Easiest way is voice — say      │
│ "create quote for [customer     │
│ name]" and I'll walk you        │
│ through it.                     │
│                                 │
│ Or you can use the form:        │
│                                 │
│ 1. Tap Quotes in bottom nav     │
│ 2. Tap "+" to create new        │
│ 3. Pick customer or add new     │
│ ...                             │
│                                 │
│ [📄 Full article]               │
│ [Walk me through it]            │
│                                 │
│ ─────────────────────────       │
│ [🎤]  [Type message...]   ➤     │
└─────────────────────────────────┘
```

Mobile layout differences from web:
- Full-screen instead of side drawer
- Back arrow in top-left returns to where user came from (the surface they invoked help from)
- Larger text and tap targets (mobile readability)
- Voice input button is more prominent (mobile primary input)
- Timestamps shown more compactly

**Rationale**: full-screen is necessary on phone width for readable chat. Voice button prominence reflects mobile users' preference for voice input.

### 4. Voice input integration

**Decision**: The chat composition zone supports both text and voice input. Voice button (mic icon) tap initiates voice capture using the existing Whisper infrastructure (per arch doc §6 voice pipeline).

#### Voice flow

1. User taps mic
2. Mic indicator pulses (per Pass 1 voice state machine)
3. Whisper captures audio
4. Transcribed text appears in the input field
5. User can edit the transcription before sending (helpful for misrecognitions)
6. User taps send (or presses Enter on web)
7. Message dispatches to AI

#### Voice readback of AI responses

User can tap a small "🔊 Listen" icon on any AI message to have it read aloud via TTS. Useful for hands-busy contexts (mid-task, driving safely, etc.). TTS uses the user's effective voice persona tone per Tier 2 #6 (so help responses sound consistent with rest of Pilot's voice interactions).

#### Voice-only mode (fully voice-driven)

Users can interact with help entirely via voice. Voice intent grammar from Flow 1 includes a help intent: "Open help" or "I have a question" → opens the help chat panel. After opening, ongoing voice input continues the conversation. AI responses are read aloud automatically (TTS) when in voice-driven mode, until the user types or taps to switch back to text mode.

**Rationale**: voice-first product needs voice-first help. Mobile users especially benefit. Voice readback handles hands-busy contexts. Voice-only mode is the natural extension for users who prefer to never look at the screen.

### 5. Chat session state and continuity

**Decision**: Help chat sessions are persistent within a session and across surface navigation. Three behaviors:

#### Within-session continuity

User opens help, asks question, gets answer, navigates to a different page, opens help again — same conversation continues. The drawer/screen reopens with prior chat history.

#### Cross-session reset

When the user fully closes the chat (✕) or signs out, the next help session starts fresh. Prior conversations remain in history (Decision 6) but new session opens clean.

#### Multi-device behavior

Help conversations are not synced across devices. Chat on web is independent from chat on mobile. Each device has its own ephemeral conversation. (Phase 2 may sync if user demand justifies.)

**Rationale**: within-session continuity feels natural — user shouldn't have to re-explain context if they switch surfaces. Cross-session reset prevents stale conversations from accumulating. Per-device isolation simplifies the data model.

### 6. Conversation history and recall

**Decision**: A "Past conversations" surface accessible from the chat panel header lets users review prior help sessions. Layout:

```
┌─────────────────────────┐
│ Past conversations      │
│ ─────────────────       │
│                         │
│ Today                   │
│ • How do I connect QB?  │
│   2 hours ago           │
│                         │
│ • Walk through onboard… │
│   4 hours ago           │
│                         │
│ Last 7 days             │
│ • What's a sync conf… │
│   2 days ago            │
│                         │
│ Older                   │
│ • Pricing questions     │
│   2 weeks ago           │
└─────────────────────────┘
```

Each session has an AI-generated brief title (similar to A11 from Pass 3 voice session titles). Tapping an entry opens that session's full chat history; user can continue the conversation from where they left off (within retention window — per Decision 13).

**Rationale**: helpful for users who said "I had this conversation last week, what did the AI suggest?" — common in help contexts. Title generation reuses existing A11 infrastructure.

### 7. AI knowledge boundaries — what the help AI can and can't do

**Decision**: The help AI is scoped to "how to use Pilot" knowledge plus surface context. It explicitly does NOT:

- Take actions on behalf of the user (e.g., "Connect QuickBooks for me" → the AI tells the user how, doesn't do it)
- Access tenant-specific data (no "show me my last quote" — that's the regular voice intent system)
- Provide financial / legal / compliance advice ("Should I charge sales tax on labor?" → AI provides general guidance and recommends consulting a professional)
- Make product roadmap commitments ("When will feature X ship?" → AI says "I don't know; submit a feature request")
- Operate outside Pilot domain ("What's the weather?" → AI politely redirects)

#### When the AI should escalate to human support

Three escalation triggers:
1. **User explicitly asks for human help**: "I want to talk to a real person"
2. **AI confidence is low** after 3 turns (the AI has tried twice and the user is still stuck)
3. **Question is outside scope**: legal, financial, technical issues with the user's specific data

In all three cases, the AI surfaces the feedback submission flow with category pre-set to "Question" and the conversation context pre-filled.

**Rationale**: clear knowledge boundaries prevent the AI from overpromising or hallucinating. Escalation paths give users a way out when the AI can't help. Pre-filling feedback context streamlines the handoff.

## Locked design decisions — Markdown Corpus

### 8. Markdown file structure and metadata

**Decision**: Markdown files in S3 follow this structure:

```yaml
---
article_id: setup-quickbooks-integration
title: Connect QuickBooks Online to Pilot
category: integrations
related_concepts: [sync, oauth, accounting, mapping]
ui_surfaces: [/settings/integrations/quickbooks, /onboarding/checklist#quickbooks]
related_articles: [resolve-qb-sync-conflicts, qb-sync-troubleshooting]
last_updated: 2026-04-27
audience: [owner, accountant]
---

# Connect QuickBooks Online to Pilot

QuickBooks integration syncs your customers, quotes, invoices, and payments
between Pilot and QuickBooks Online. This avoids double-entry and keeps your
books current.

## Before you start

You'll need:
- An active QuickBooks Online subscription (any tier)
- Owner or accountant role in Pilot

## Connect the integration

1. Go to **Settings > Integrations > QuickBooks**
2. Click **Connect QuickBooks**
3. You'll be taken to QuickBooks to sign in
4. Authorize Pilot to access your QuickBooks data
5. You'll return to Pilot with the integration connected

## What syncs automatically

- Customers (bidirectional)
- Quotes (Pilot → QB as Estimates)
- Invoices (bidirectional)
- Payments (QB → Pilot)
- Expenses (bidirectional)
- Tax components (Pilot → QB)

## What requires setup

- Tax mapping (one-time setup; Pilot guides you)
- Account mapping (Pilot maps automatically; review for accuracy)
- Customer mapping (Pilot matches by email + phone; review duplicates)

## Common issues

If sync errors appear, see Resolve QuickBooks Sync Conflicts.
```

#### Frontmatter metadata schema

| Field | Purpose |
| :--- | :--- |
| `article_id` | Unique slug; used for cross-references and stable URLs |
| `title` | Human-readable title |
| `category` | Top-level grouping (integrations, voice-ai, settings, billing, onboarding, etc.) |
| `related_concepts` | Tags used for cross-article retrieval and concept-based queries |
| `ui_surfaces` | App routes / anchors where this article is contextually relevant |
| `related_articles` | Explicit cross-references for "see also" suggestions |
| `last_updated` | ISO date of last content update |
| `audience` | Roles this article is relevant for (owner, accountant, technician, all) |

#### Storage in S3

- Bucket: `s3://pilot-help-content/`
- Path: `s3://pilot-help-content/{language}/{category}/{article_id}.md`
- Versioning: S3 versioning enabled; old versions kept for rollback
- Public read access: NO — articles are served via API, not directly from S3
- The API layer respects role-based audience filtering (technician shouldn't see owner-only articles)

#### Authoring workflow

- Tom edits markdown files locally (or via S3 console for quick fixes)
- Files committed to a content repo (separate from app codebase) or uploaded directly to S3
- On commit/upload, embedding pipeline (per A85) regenerates embeddings for changed chunks
- AI immediately uses updated content on next query

**Rationale**: markdown is the right format — editable by you in any text editor, renders cleanly when surfaced as articles, structures well for RAG chunking. S3 is the right storage — cheap, accessible by both web and mobile, scales easily. Frontmatter metadata makes both retrieval and rendering work from the same file.

### 9. Article chunking for RAG

**Decision**: Markdown articles are chunked at section boundaries (each `##` heading starts a new chunk) for embedding. Chunk size targets:

- Minimum: 100 tokens (very short sections are merged with adjacent ones)
- Maximum: 800 tokens (long sections are split at sub-section or paragraph boundaries)
- Each chunk includes the article's frontmatter metadata as a context header

#### Chunk metadata

Each chunk in pgvector has:
- `chunk_id` UUID
- `article_id` reference
- `section_title` (the `##` heading)
- `chunk_text` (the markdown content of the section)
- `chunk_text_with_metadata` (frontmatter + section title + content; what gets embedded)
- `embedding` vector(1536) (or whatever Pilot's chosen model produces)
- `token_count`

#### Retrieval at query time

1. User query is embedded
2. pgvector cosine similarity search returns top-K chunks (default K=5)
3. Filtered by audience role (technician queries don't pull owner-only chunks)
4. Optionally filtered by category if context payload suggests one
5. Top-K chunks injected into prompt as context for help AI

**Rationale**: section-boundary chunking preserves semantic coherence. Chunk size targets balance retrieval precision (smaller = more precise) with context preservation (larger = more grounded). Audience filtering is a security boundary (can't accidentally surface admin content to techs).

### 10. Initial corpus scope — what articles need to exist for MVP

**Decision**: MVP corpus targets approximately 60 articles covering the realistic help surface for an electrical contractor onboarding to Pilot. Categorized:

| Category | Article count (approximate) |
| :--- | :--- |
| Getting started / onboarding | 8 |
| Voice AI / voice intents | 6 |
| Quote workflow | 8 |
| Job management / dispatch | 8 |
| Customer management | 6 |
| Customer messaging (SMS, email) | 5 |
| Invoicing & billing | 6 |
| QuickBooks integration | 4 |
| Calendar integration | 3 |
| Settings & configuration | 4 |
| Mobile-specific (offline, sync) | 4 |
| Account & security (MFA, password) | 4 |
| **Total** | **~66** |

Tom owns content authoring per pre-launch hygiene track. The article list with stub titles can be generated from the spec system as a writing checklist.

**Rationale**: ~60 articles is enough to cover the breadth of MVP product without exhausting authoring capacity. Quality over quantity — better to have well-written articles for the most-asked questions than thin coverage of everything.

## Locked design decisions — About / Version / Legal

### 11. About sub-page layout

**Decision**: A single sub-page at `Settings > Help & About > About` (web) or `Mobile > Settings > About` displaying:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ About Pilot for Trades                                                   │
│ ─────────────────────                                                    │
│                                                                          │
│ [Pilot logo]                                                             │
│                                                                          │
│ Pilot for Trades                                                         │
│ Web app version: 1.4.2                                                   │
│ Mobile app version: 1.4.0 (build 142)                                    │
│ API version: 5.2                                                         │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ Need help?                                                               │
│ • Help & support → [opens help chat]                                     │
│ • Send feedback → [opens feedback form]                                  │
│ • support@pilotfortrades.com                                             │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ Legal                                                                    │
│ • Terms of Service                                                       │
│ • Privacy Policy                                                         │
│ • End User License Agreement                                             │
│ • Open-source licenses (full list)                                       │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ © 2026 Pilot for Trades. All rights reserved.                            │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Content sections

- **Logo + product name**
- **Version info** — web app version, mobile app version (build), API version. Useful for support — "I'm on version X" speeds up debugging.
- **Need help section** — three quick paths to help
- **Legal links** — open inline modal or external links to legal documents
- **Open-source licenses** — list of OSS dependencies and their licenses (legal requirement)
- **Copyright notice**

#### Mobile differences

Mobile renders the same content in vertical stack. Logo prominent at top. Version info in a single block. Help and legal sections collapsible.

**Rationale**: standard about-page pattern. Version info gates support efficiency. Legal links are required for compliance. Open-source license list is a legal requirement most products fulfill.

## Locked design decisions — Feedback Submission

### 12. Feedback form — structured category + text

**Decision**: A single-page form at `Settings > Help & About > Send feedback` (web) or accessible from the help chat ("Send feedback") and from the About page.

#### Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Send feedback                                                            │
│ ──────────────                                                           │
│                                                                          │
│ Help us improve Pilot. Your feedback goes directly to the team.          │
│                                                                          │
│ Category *                                                               │
│ ◯ Bug report                                                             │
│ ◯ Feature request                                                        │
│ ◯ Question                                                               │
│ ● General feedback                                                       │
│                                                                          │
│ Your feedback *                                                          │
│ ┌──────────────────────────────────────────────────────────────────┐    │
│ │                                                                  │    │
│ │                                                                  │    │
│ │                                                                  │    │
│ │                                                                  │    │
│ └──────────────────────────────────────────────────────────────────┘    │
│ 0 / 5000 characters                                                      │
│                                                                          │
│ Reply to:                                                                │
│ mike@johnson-electric.example.com                                                │
│ (we may follow up by email)                                              │
│                                                                          │
│ ─                                                                        │
│                                                                          │
│ [Cancel]                                              [Send feedback]    │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Field details

| Field | Required | Notes |
| :--- | :--- | :--- |
| Category | Yes | Bug report / Feature request / Question / General feedback |
| Feedback text | Yes | 5000 char max |
| Reply-to email | Auto-filled from user account | Display only; user knows where reply will land |

#### Submission behavior

On submit, request posts to A87. Server sends an email to `support@pilotfortrades.com` (or whichever support email Tom configures) with:
- Sender: user's email
- Subject: `[Pilot Feedback - {Category}] {first-line-of-feedback}`
- Body: full feedback text + tenant info + user role + timestamp
- Reply-to: user's email (so Tom can reply directly)

User sees confirmation page: "Thanks for your feedback! We'll get back to you at mike@... within a few business days."

#### Diagnostic data — Phase 2

The original Q4 in scoping considered including diagnostic data attachment for bug reports. Per your direction, this is deferred to Phase 2.

For MVP, bug reports rely on the user's free-text description. If the description is unclear, Tom replies via email asking for more info. Not optimal but acceptable for the early-customer support model.

#### From-help-chat escalation

When the help AI can't answer (per Decision 7 escalation triggers), it offers to send the conversation as feedback. The "Send feedback" affordance pre-fills:
- Category: "Question"
- Text: previous conversation summary plus "the AI couldn't help with this"
- User confirms and submits

This streamlines the help-to-feedback handoff so users don't have to re-type their question.

**Rationale**: simple structured form is the right MVP scope. Email intake matches solo founder operational reality. Phase 2 can introduce ticket system and diagnostic data attachment when volume justifies.

## Locked design decisions — Chat Session Capture

### 13. Session retention and anonymization pipeline

**Decision**: Help chat sessions are captured for training data with anonymization at the pipeline stage (per Q5 (c) in our scoping):

#### Storage tiers

| Tier | Retention | Purpose |
| :--- | :--- | :--- |
| Active session | Until user closes chat | Real-time conversation state |
| Recent (90 days) | 90 days unscrubbed | Debugging support issues, user history recall (Decision 6), training pipeline source |
| Training corpus | Permanent | Anonymized, used for model fine-tuning and content improvement |

#### Anonymization pipeline (runs at end of 90-day window)

For each chat session at the 90-day boundary, the anonymization pipeline:

1. **PII detection**: scan messages for emails, phone numbers, addresses, person names, business names. Replace with generic placeholders (`[email]`, `[phone]`, `[address]`, `[person]`, `[business]`).
2. **Tenant-identifying data**: strip tenant_id, user_id, any direct references to the tenant's customers, jobs, quotes, etc.
3. **Sanitized session is added** to training corpus.
4. **Original session is deleted** after anonymization completes.

#### User-facing transparency

A small note in the help chat panel: "Pilot uses help conversations to improve our help content. Personal info is removed before use. [Learn more]" — link opens a help article explaining the pipeline.

Users can request deletion of their help chat history at any time via `My Account > Privacy` (a small Phase 2 surface; for MVP, request via support email).

**Rationale**: anonymization-at-pipeline-stage gives meaningful training data without sustained privacy exposure. 90-day retention balances debugging needs against data minimization. User-facing transparency builds trust.

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| AI-mediated help with RAG retrieval | **NEW** | Voice AI infrastructure (§6 of arch doc) |
| Markdown corpus structure for both human + AI consumption | **NEW** | — |
| Context-aware help opener with surface-context payload | **NEW** | — |
| Section-boundary chunking for RAG | **NEW** | pgvector infrastructure (§2.3) |
| Slide-out side drawer for help (web) | **NEW** | — |
| Full-screen chat (mobile) | **NEW** | Tier 1.5 customer comm thread screen pattern |
| Chat session capture with anonymization-at-pipeline | **NEW** | — |
| Suggested follow-up action buttons within AI messages | **NEW** | — |
| Voice-only fully voice-driven help mode | **NEW** | Voice intent grammar, voice readback infrastructure |
| AI knowledge boundaries with explicit escalation triggers | **NEW** | — |
| Past conversations surface with AI-generated titles | Reused | A11 session title generation |
| Voice readback of AI responses with persona tone | Reused | Tier 2 #6 voice persona tone |
| Save-on-blur for feedback (auto-saves draft) | Reused | Settings IA framework Decision 5 |

11 new patterns. The AI-mediated help paradigm is the central new contribution — it's a substantially different help model from traditional B2B SaaS knowledge bases.

## Cross-domain considerations

### A. Help AI infrastructure shares with voice intent system

Per Q1, the help AI uses the same Llama 3.x infrastructure as voice intents. Three implications:

- **Compute capacity**: the existing Ollama deployment handles both voice intents and help queries. Capacity planning needs to account for both. If observed load shows help queries competing with voice latency, Phase 2 can split into separate instances.
- **Model serving**: same LLM model file; different system prompts; different RAG context. Routing happens at the API layer — voice intents go to one prompt template; help queries go to another.
- **Monitoring**: existing latency / error metrics extend to track help query performance.

### B. RAG embedding deployment

For your understanding (per Q2): pgvector is already in the stack. At deploy time:

1. Markdown files in S3 are processed by an embedding pipeline (Celery task)
2. Pipeline uses an embedding model (likely OpenAI `text-embedding-3-small` or similar; can be swapped) to generate embeddings for each chunk
3. Embeddings + chunk metadata are written to `help_article_chunk` table with a vector column
4. HNSW index on the vector column enables fast similarity search

Updating an article: edit markdown → save to S3 → S3 event triggers re-embedding of changed file → updated chunks replace old ones in pgvector. Total time from edit to AI-aware: typically 1–2 minutes.

**Embedding model choice**: A85 below recommends OpenAI `text-embedding-3-small` for MVP because it produces high-quality embeddings at low cost (~$0.00002 per 1K tokens). For ~60 articles × ~500 tokens each = ~30K tokens for full corpus = $0.60 one-time cost plus ~$0.10/month for query embeddings at moderate usage. Open-source alternative (Sentence-BERT, etc.) is feasible if you prefer to avoid OpenAI dependency.

### C. Help articles inform onboarding

Tier 3 #10's onboarding flow can deep-link to specific help articles when relevant. For example, the wizard step explaining tax setup can include a "[Read more about tax setup]" link that opens the relevant help article in the chat panel with context: "User is in the onboarding tax-setup step."

This creates a virtuous loop: onboarding → help article → AI explanation → user understanding. The same article serves multiple use cases.

### D. Settings IA framework Cross-Domain D fulfilled

The Settings IA framework Decision 7 mentioned "small ? icons next to settings open contextual help articles." Tier 4 #14 Decision 1 (c) covers this — selective contextual help anchors throughout settings surfaces. The Settings IA framework's intent is realized.

### E. PRD §3.7 (Notifications & Comms) — feedback as new feature

PRD touch-up at Pass 4 close: §3.7 needs new feature row for "User feedback submission with category + text + email intake (Phase 2: structured ticket system + diagnostic data attachment)." Currently no feedback feature in the PRD.

### F. Onboarding — help intent as part of voice intent grammar

Voice intent grammar (Flow 1, arch doc §6) extends with a help intent: "Open help" / "I have a question" / "Help me with X" → routes to help AI with the user's utterance as the initial query. Existing voice intent infrastructure handles this; A84 below specifies the help intent registration.

### G. Audit log captures help interactions selectively

Help chat conversations are NOT in the audit log (audit_log is for tenant-data-changing actions; help is read-only AI conversation). However, the following help-related events ARE audited:
- Feedback submission (audit row with category + truncated text excerpt)
- Help chat data deletion request (Phase 2 surface)
- Anonymization pipeline runs (audit row with session count anonymized)

### H. Mobile chat session SSE handling

Help chat doesn't require SSE for real-time updates — the user is always actively interacting; there's no third-party event triggering chat changes. Standard request/response model is sufficient.

The exception: if the user's chat session has streaming AI responses (token-by-token typing animation), that uses HTTP streaming (SSE-like) for the response itself. This is a UX choice — typed-out-token-by-token feels more human than waiting for the full response. Implementation detail in A84.

### I. Voice persona tone applies to TTS readback

When the user enables voice readback (Decision 4), TTS uses the user's effective voice persona tone (Tier 2 #6). A "playful" tone user hears playful help responses; "conservative" hears conservative. Consistency across the product.

### J. Account settings → "Reset all my MFA" cross-link

When a user opens help and asks "I'm locked out, how do I reset my MFA?", the AI surfaces the relevant help article. The article includes a deep-link to the Account settings → MFA reset flow (Tier 2 #7 Decision 10). Tom owns ensuring help content includes appropriate cross-links to actionable surfaces.

## Deferred items (Phase 2 / for future iteration)

- **Diagnostic data attachment for bug reports** — Phase 2 (per Q4 in scoping)
- **Ticket system replacing email intake** — Phase 2 hybrid model (Q5)
- **Voice-driven help interaction** with full conversational depth — partially in MVP via voice input + readback; Phase 2 can deepen with proactive voice suggestions, multi-turn conversational help
- **Multi-language help content** — Phase 2 with multi-language UI
- **Help chat session sync across user's devices** — Phase 2 if observed demand
- **Community forum / user-to-user help** — Phase 2; not in solo-founder model
- **AI-generated help article suggestions** — AI suggests new articles based on common queries with no good RAG match — Phase 2
- **Help chat data deletion self-service** — `My Account > Privacy` surface — Phase 2
- **Real-time conversation streaming with progressive token rendering** — nice-to-have UX; Phase 2 if MVP feels too "snappy / instant"
- **Admin UI for help content editing (vs S3/repo workflow)** — Phase 2 once content authoring volume justifies dedicated UI
- **AI confidence scoring exposed to users** — "I'm 70% sure about this answer" — Phase 2; may add or may stay internal
- **Help analytics for Tom** — most-common queries, articles never retrieved, low-confidence answers — Phase 2 dashboard
- **Personalized help suggestions based on user history** — "users with similar usage often ask about X" — Phase 2
- **Voice-only opt-out of TTS readback** — currently always available; Phase 2 can add per-user preference

## Validation checklist

Before implementation begins:

- [ ] Three help entry points implemented per Decision 1 (main nav "?" icon, settings sub-page, contextual "?" anchors)
- [ ] Selective contextual help anchor placements specified per Decision 1 list
- [ ] Web side-drawer chat panel implemented per Decision 2
- [ ] Mobile full-screen chat implemented per Decision 3
- [ ] Voice input integration in chat composition per Decision 4
- [ ] Voice readback option for AI responses per Decision 4
- [ ] Voice-only mode implemented per Decision 4
- [ ] Within-session continuity tested per Decision 5
- [ ] Past conversations surface implemented per Decision 6
- [ ] AI knowledge boundaries enforced per Decision 7
- [ ] Three escalation triggers implemented per Decision 7
- [ ] Markdown frontmatter schema validated per Decision 8
- [ ] S3 storage with versioning configured per Decision 8
- [ ] Section-boundary chunking pipeline implemented per Decision 9
- [ ] Audience-role filtering on chunk retrieval per Decision 9
- [ ] Initial corpus authoring underway (Tom-owned) per Decision 10
- [ ] About sub-page implemented per Decision 11
- [ ] Feedback form implemented per Decision 12
- [ ] Email intake configured per Decision 12
- [ ] Help-to-feedback handoff with pre-fill per Decision 12
- [ ] Three-tier session retention model per Decision 13
- [ ] Anonymization pipeline runs at 90-day boundary per Decision 13
- [ ] User-facing transparency note in help chat per Decision 13
- [ ] Help intent added to voice intent grammar per Cross-Domain F

## Backend additions (new for Tier 4 #14)

### A84. Help AI Agent + RAG + Chat Session Management

**Triggered by**: Decisions 1–7, 13 — AI-mediated help system with retrieval, conversation state, and session capture.

**Scope**:

**Help AI prompt template**:
- New prompt template `prompts/help/help_agent.md`
- System prompt establishes:
  - Pilot product knowledge boundaries
  - Conversational style (tone-aware per user's voice persona setting)
  - RAG context insertion point
  - Escalation trigger awareness
- Variants per voice persona tone (conservative / balanced / playful) — same as voice intent system

**Help endpoint**:
- `POST /api/v1/help/chat` — sends a message in a help conversation
  - Request: `{session_id: UUID?, message: text, context_payload: {...}}` — session_id null on first message
  - Server retrieves relevant chunks via pgvector (per A85)
  - Server constructs prompt with system template + RAG context + conversation history + user message
  - Server calls Llama 3.x via existing Ollama infrastructure
  - Server streams response back via HTTP streaming (or returns whole response if streaming infrastructure isn't ready for MVP)
  - Server persists message exchange to `help_chat_session` and `help_chat_message`
- `GET /api/v1/help/sessions` — returns user's recent help sessions (Decision 6)
- `GET /api/v1/help/sessions/{session_id}` — returns full message history for a session
- `POST /api/v1/help/sessions/{session_id}/feedback` — captures user feedback signals ("That answered it" / "Still confused" — per Decision 2)

**Schema**:
- New table `help_chat_session`
  - `session_id` UUID PK
  - `tenant_id`, `user_id` UUID FK
  - `started_at`, `last_activity_at` TIMESTAMPTZ
  - `title` TEXT NULL — auto-generated via A11 pattern
  - `outcome` TEXT NULL — `resolved | escalated | abandoned` (set when session closes)
  - `message_count` INTEGER
  - `anonymized_at` TIMESTAMPTZ NULL — set when anonymization pipeline runs
- New table `help_chat_message`
  - `message_id` UUID PK
  - `session_id` UUID FK
  - `role` TEXT (`user | assistant`)
  - `content` TEXT
  - `created_at` TIMESTAMPTZ
  - `context_payload` JSONB — for user messages, captures the surface context at time of message
  - `retrieved_chunks` JSONB NULL — for assistant messages, captures which chunks were used as RAG context (for debugging and training)
  - `voice_used` BOOLEAN — whether voice input/output was used

**Help intent in voice intent grammar**:
- New intent `open_help` / `ask_help_question`
- Voice grammar matches "open help," "I have a question," "help me with [X]"
- Routes utterance to A84 chat endpoint with `context_payload` from current voice session

**Streaming response support**:
- HTTP streaming (chunked transfer encoding) for token-by-token response rendering
- Client renders tokens as they arrive (typing animation effect)
- For MVP, full response can be returned non-streamed if streaming infrastructure isn't ready

**Effort estimate**: Medium-Large — 5–7 days. RAG integration + prompt template + session persistence + streaming + voice intent integration. Not every piece is novel infrastructure but the integration is meaningful work.

### A85. Markdown Corpus + Embedding Pipeline + S3 Storage

**Triggered by**: Decisions 8–10, Cross-Domain B — markdown corpus storage, embedding pipeline, content delivery.

**Scope**:

**S3 storage**:
- Bucket `pilot-help-content` with versioning enabled
- Path structure: `s3://pilot-help-content/{language}/{category}/{article_id}.md`
- Public read disabled (article delivery via authenticated API)
- IAM policy allows Lambda or Celery worker to read; Tom can write via S3 console or programmatic upload

**Schema**:
- New table `help_article`
  - `article_id` TEXT PK
  - `s3_path` TEXT
  - `title`, `category` TEXT
  - `frontmatter_metadata` JSONB
  - `last_content_hash` TEXT — sha256 of content; used for change detection
  - `last_processed_at` TIMESTAMPTZ
  - `last_updated` DATE
  - `audience` TEXT[] — array of role names
- New table `help_article_chunk`
  - `chunk_id` UUID PK
  - `article_id` TEXT FK
  - `chunk_order` INTEGER — preserve original order
  - `section_title` TEXT
  - `chunk_text` TEXT
  - `chunk_text_with_metadata` TEXT — what gets embedded
  - `embedding` vector(1536)
  - `token_count` INTEGER
  - HNSW index on `embedding`

**Embedding pipeline**:
- Celery task `process_help_article` triggered on:
  - S3 event when an article is uploaded/updated
  - Manual trigger via admin endpoint
  - Scheduled re-embedding pass (weekly, for catching missed events)
- Pipeline:
  1. Fetch markdown from S3
  2. Parse frontmatter
  3. Chunk by section boundaries (per Decision 9)
  4. Compute hash; skip if unchanged
  5. Embed each chunk via OpenAI `text-embedding-3-small` (or alternative)
  6. Store/update chunks in pgvector
  7. Update `help_article` with new hash and timestamp

**Retrieval API**:
- `POST /api/v1/help/retrieve` — internal API used by A84
  - Request: `{query_embedding: vector, role: text, category_hint: text?, k: int}`
  - Response: top-K chunks with metadata
  - Audience filtering applied based on user's role

**Article delivery API**:
- `GET /api/v1/help/articles/{article_id}` — returns full markdown for surfacing as "Read full article"
- Audience filtering applied — returns 403 if user doesn't have access

**Embedding model decision**:
- Recommended: OpenAI `text-embedding-3-small` (1536 dimensions, low cost)
- Alternative: open-source Sentence-BERT models if avoiding OpenAI dependency is required
- Decision can be deferred — both options work with the schema

**Effort estimate**: Medium — 4–5 days. S3 setup + schema + embedding pipeline + retrieval API. The pipeline is standard RAG work; the cost is in tuning chunk boundaries and audience filtering correctness.

### A86. Contextual Help Anchor Metadata + Opener Context Payload

**Triggered by**: Decisions 1, Cross-Domain D — selective contextual help anchors and surface context for AI grounding.

**Scope**:

**Schema**:
- Help anchor metadata is mostly client-side configuration (which UI elements have "?" icons)
- Per Decision 1's contextual help anchor table, frontend components register their help context

**Context payload structure**:
- When user opens help from any entry point, frontend collects:
  - `route`: current path (e.g., `/settings/integrations/quickbooks`)
  - `entity_type`: type of entity user is viewing (if applicable)
  - `recent_actions`: last 5 minutes of action types only — no entity contents (per privacy decision in scoping)
  - `user_role`: owner / accountant / technician
  - `tenant_metadata`: size, trade
- Payload sent to A84 with first message; influences AI response grounding
- Recent actions are tracked client-side via lightweight event capture; no backend storage

**Recent action types tracked** (action labels only, no entity contents):
- `viewed_quote`, `created_quote`, `accepted_quote`
- `viewed_invoice`, `paid_invoice`
- `assigned_job`, `completed_job`
- `synced_calendar`, `viewed_qb_conflict`
- `opened_settings`, `changed_setting`
- (etc. — small enumerated list of action types from across the app)

**Audit logging**: action type capture is client-side ephemeral; not audit-logged. This is a help-grounding feature, not an audit feature.

**Effort estimate**: Small — 2 days. Mostly client-side event tracking and payload assembly + small server-side schema for help_chat_message context payload column.

### A87. Feedback Submission Endpoint with Email Intake

**Triggered by**: Decision 12 — structured feedback with category + text; email intake.

**Scope**:

**Schema**:
- New table `feedback_submission`
  - `submission_id` UUID PK
  - `tenant_id`, `user_id` UUID FK
  - `category` TEXT (`bug | feature_request | question | general`)
  - `body` TEXT
  - `submitted_at` TIMESTAMPTZ
  - `from_help_chat_session_id` UUID NULL — when escalated from help chat (per Decision 12 from-help-chat escalation)
  - `email_sent_to` TEXT — captures the support email that received the submission
  - `email_message_id` TEXT NULL — SendGrid message ID for tracking

**APIs**:
- `POST /api/v1/feedback` — submit feedback
  - Request: `{category, body, from_help_chat_session_id: UUID?}`
  - Server creates submission record
  - Server sends email to support email address (configured per-deployment via env var):
    - Subject: `[Pilot Feedback - {Category}] {first-line-of-body}`
    - Body: full feedback + tenant_id + user info + role + timestamp
    - Reply-to: user's email
  - Returns confirmation; user sees confirmation page

**Configuration**:
- `SUPPORT_EMAIL_ADDRESS` env var (e.g., `support@pilotfortrades.com`) — destination for feedback emails
- Audit log captures submission per Cross-Domain G

**Effort estimate**: Small — 2 days. Schema + endpoint + email integration via existing SendGrid infrastructure.

### A88. Anonymization Pipeline for Training Data Capture

**Triggered by**: Decision 13 — chat session retention with anonymization at 90-day boundary.

**Scope**:

**Anonymization pipeline** (`tasks/anonymize_help_sessions.py`):
- Celery scheduled task runs daily
- Identifies `help_chat_session` rows where `last_activity_at <= now() - 90 days` AND `anonymized_at IS NULL`
- For each session:
  1. Iterate through messages
  2. Run PII detection on message content (regex + named entity recognition)
  3. Replace PII with placeholders (`[email]`, `[phone]`, etc.)
  4. Strip tenant_id and user_id references
  5. Save anonymized version to `help_training_corpus` table (separate from the original)
  6. Set `anonymized_at` on the original session
  7. After all messages processed, delete the original `help_chat_session` and `help_chat_message` rows

**Schema**:
- New table `help_training_corpus`
  - `corpus_id` UUID PK
  - `original_session_id_hash` TEXT — one-way hash of original UUID; allows tracking but not reversal
  - `anonymized_message_history` JSONB — array of {role, content, retrieved_chunks_summary}
  - `anonymized_context_payload` JSONB
  - `category_inferred` TEXT NULL — auto-classified by AI for filtering training data
  - `outcome` TEXT — copied from session
  - `anonymized_at` TIMESTAMPTZ

**PII detection rules** (initial set; can be refined):
- Email addresses (regex: `[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}` → `[email]`)
- Phone numbers (US format detection → `[phone]`)
- Names (NER model or simple capitalized-word heuristic → `[person]`)
- Business names (capitalized phrases ending in common business suffixes → `[business]`)
- Addresses (street number + word + street suffix → `[address]`)
- Long alphanumeric IDs (UUIDs, account numbers → `[id]`)

**User deletion request** (Phase 2 surface; backend stub):
- `POST /api/v1/help/sessions/delete-all` — deletes all help chat sessions for the requesting user
- Stub endpoint exists in MVP; full UX is Phase 2

**Effort estimate**: Medium — 3–4 days. Schema + anonymization pipeline + PII detection rules + Celery scheduled task. The PII detection is the cost driver — getting it accurate enough to actually anonymize without false positives requires testing.

### Total Tier 4 #14 backend additions

A84 (5–7) + A85 (4–5) + A86 (2) + A87 (2) + A88 (3–4) = **16–20 days**.

This is the second-largest single Tier 4 backend addition cluster. The AI-mediated help paradigm is genuinely substantial infrastructure.

---

## What this surface does NOT cover

- Diagnostic data attachment for feedback — Phase 2
- Ticket system replacing email intake — Phase 2
- Multi-language help content — Phase 2
- Help chat session sync across devices — Phase 2
- Community forum — Phase 2
- AI-generated article suggestions — Phase 2
- Admin UI for help content editing — Phase 2 (S3 + repo workflow for MVP)
- Help analytics dashboard — Phase 2
- User-initiated help chat data deletion — Phase 2 surface; backend stub in MVP
- Voice-only proactive help suggestions — Phase 2

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A84–A88 added (5 additions). Cumulative through Tier 4 #14: A1–A88.

**Backend day estimate update**:
- Pre-Tier-4-#14 cumulative remaining MVP: 243–314.5 days
- Tier 4 #14 additions: 16–20 days
- New cumulative remaining MVP: **259–334.5 days**

**Tier 4 closes here. Pass 4 closes.**

All 14 Pass 4 surfaces locked plus the Settings IA framework prerequisite plus the Tier 1.5 Flow 4 customer comms extension.

**Framework doc**: Tier 4 #14 status flips to ✓ locked. Tier 4 in aggregate flips to complete. Pass 4 in aggregate flips to complete.

**Arch doc touch-up needed at Pass 4 close**: a section on Help System Architecture covering AI-mediated help, RAG retrieval over markdown corpus, S3 storage for help content, anonymization pipeline. Plus voice intent grammar extension for help intent.

**PRD touch-up needed at Pass 4 close**: §3.7 (Notifications & Comms) extension for feedback submission. New "Help & Support" feature scope possibly as a new section §3.16 or under §3.7.

**Pre-launch hygiene track (substantial accumulation)**: ~60 help articles authored (Tom-owned), Pilot for Trades support email setup, S3 bucket configuration, embedding model decision (OpenAI vs open-source).

## What comes next: Pass 4 closes

This is the last Pass 4 design spec. Substantial post-Pass-4 work begins:

1. **Full v3.1 PRD issued** — consolidates all interim PRD updates from Pass 4
2. **Full v5 arch doc issued** — consolidates v4.1, v4.2, v4.3 patches plus Pass 4 close additions (help system architecture, customer-facing public surfaces, etc.)
3. **Full v6 backend additions ledger** — cumulative A1–A88
4. **Framework doc third and final rewrite** — captures the full Pass 4 outcome and pivots toward implementation phase
5. **Doc consolidation pass per your direction** — you provide your updated canonical docs; I review against everything we've locked across Pass 4 and produce update instructions for content gaps
6. **Pre-launch hygiene completion check** — extensive list accumulated during Pass 4 (10DLC, legal copy, marketing site, help articles, etc.)
7. **Backend implementation scale-up** — substantial backend work pipeline (~259–334.5 days remaining MVP)
8. **Beta testing prep** — tester recruitment, onboarding playbook, support runbook

The Pass 4 design phase is complete. The design framework has produced 14 surface specs plus the Tier 1.5 customer comms extension plus the Settings IA framework — covering the full MVP surface area. 88 backend additions documented. Five new platform UX patterns formalized. Multiple cross-cutting concerns surfaced and resolved.

Time to ship.
