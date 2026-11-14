# Arch Doc v5 — Update Instructions Round 2A

**Date**: April 30, 2026
**Scope**: New chapters §18 Customer-Facing Public Surfaces Architecture and §19 Help System Architecture, plus TOC updates and cross-reference fixes.
**Prerequisite**: Round 1 already applied (v5 header, §16 patterns, §4.5 MFA expansion, §5.4 QB updates, §6.2 voice intents, §3.2 Celery tasks, §16.5 settings, cost analysis).

This round adds two new top-level chapters covering the genuinely new architectural domains from Pass 4 Tier 4 #13 and #14. Round 2B (subsequent) covers subscription/onboarding/notification/account settings.

---

## Edit 1 — Insert §18 Customer-Facing Public Surfaces Architecture

**Insertion point**: After §17 closes (after line 3146 in your post-Round-1 doc, which will be the last line of §17.12 Phase 2 Roadmap), and before `## Cost Analysis` chapter.

**Content to insert**:

```markdown
## 18. Customer-Facing Public Surfaces Architecture

Pass 4 Tier 4 #13 introduced the customer-facing public surfaces — pages that customers (non-Pilot users) access via signed-URL links sent in emails or SMS. This chapter covers the architecture supporting these surfaces: signed URL infrastructure, Stripe one-time payment for invoices with amount variance, email template rendering with tenant brand customization, customer comment storage on entities, and the short-link redirect infrastructure.

### 18.1 Strategic Direction

Customer-facing surfaces are the only Pilot surfaces a non-tenant user sees. Three architectural principles drive the design:

- **Tenant-branded, not Pilot-branded**: pages render with the tenant's logo, brand color, signature, and footer. Pilot brand presence is limited to a small "Powered by Pilot for Trades" footer link. The customer's mental model is "I'm interacting with [tenant]," not "I'm using Pilot."
- **Signed URL is the only authentication**: the customer's email inbox is the implicit verification mechanism — clicking the link from email implies access to that email account. No additional 6-digit-code dance. URLs expire 90 days from generation.
- **Comments are entity-bound, not communication-channel-bound**: customer comments on accept/decline/payment are stored on the entity (quote, payment) — not routed into customer comm threads. This matches the semantics: comments ARE the action context, not separate messages.

### 18.2 Signed URL Infrastructure

Public URLs use HMAC-signed tokens with embedded payload validation:

- **URL format**: `https://app.pilotfortrades.com/q/{signed_token}` (quote) or `/i/{signed_token}` (invoice)
- **Token payload**: `link_id` (UUID), `link_type` (quote | invoice), `expiration` (ISO timestamp), `customer_id` (for verification)
- **Signature**: HMAC-SHA256 with per-deployment secret stored in Secrets Manager (per §9.1)
- **Expiration**: 90 days from generation
- **Revocation**: tenant can manually revoke any link via `POST /api/v1/quotes/{id}/public-link/revoke` — invalidates the token immediately; subsequent access shows expired page

**Schema** (extends existing `quote_public_link` and `invoice_public_link`):

```sql
ALTER TABLE quote_public_link ADD COLUMN signed_token TEXT NOT NULL;
ALTER TABLE quote_public_link ADD COLUMN expires_at TIMESTAMPTZ NOT NULL;
ALTER TABLE quote_public_link ADD COLUMN revoked_at TIMESTAMPTZ NULL;
ALTER TABLE quote_public_link ADD COLUMN created_by_user_id UUID NOT NULL;

-- (parallel ALTERs for invoice_public_link)
```

**Verification at request time**:

1. Decode signed token; validate HMAC signature against deployment secret
2. Check `expiration < now()` → return expired page if true
3. Check `revoked_at IS NULL` → return expired page if revoked
4. Look up entity (quote or invoice) by `link_id`; verify `customer_id` matches the entity's customer
5. Render page with current entity state (state-aware revisit handling per §18.6)

**No tenant authentication** on these requests — the signed URL is the credential. Each request hits a public route handler that does not require Cognito JWT.

### 18.3 Short-Link Redirect Infrastructure

When a tenant sends a quote or invoice via SMS (per §17), the SMS body includes a shortened URL to reduce segment count:

- **Domain**: `pilot.tr` (or similar; Pilot-owned)
- **Short code format**: 5–8 character base62 random; collision-checked at generation
- **Resolution**: `GET /api/v1/short/{short_code}` resolves to full signed URL and 302-redirects

**Schema**:

```sql
public_link_short_code (
    short_code           TEXT PRIMARY KEY,    -- base62 random
    link_type            TEXT NOT NULL,        -- 'quote' | 'invoice'
    link_id              UUID NOT NULL,        -- references quote_public_link or invoice_public_link
    created_at           TIMESTAMPTZ NOT NULL,
    click_count          INTEGER NOT NULL DEFAULT 0,
    last_clicked_at      TIMESTAMPTZ NULL
)
```

**Click tracking** captures user-agent, IP, timestamp on each redirect (denormalized counter on the row plus optional `public_link_click_log` for full audit). Phase 2 analytics surface this data; for MVP it's captured but not surfaced.

**MVP fallback**: if the `pilot.tr` domain isn't ready at MVP launch, full URLs in SMS are acceptable (just longer). Short-link infrastructure is forward-compatible — switching SMS templates to use short links is a content change, not an architectural change.

### 18.4 Public Page Routing

Public pages live at separate routes that bypass standard Cognito authentication middleware:

| Route | Purpose |
| :--- | :--- |
| `GET /api/v1/public/quotes/{signed_token}` | Returns quote payload for rendering |
| `POST /api/v1/public/quotes/{signed_token}/accept` | Customer accepts with optional comment |
| `POST /api/v1/public/quotes/{signed_token}/decline` | Customer declines with reason + comment |
| `GET /api/v1/public/invoices/{signed_token}` | Returns invoice payload for rendering |
| `POST /api/v1/public/invoices/{signed_token}/payment-intent` | Initiates Stripe Payment Intent (per §18.5) |
| `POST /api/v1/public/invoices/{signed_token}/confirm-payment` | Frontend confirms Stripe Elements payment |

**Middleware stack for public routes**:

- Standard rate limiting (per §7.5) — applied per-IP since no tenant context yet
- Idempotency keys (per §7.6) for write operations
- Request ID tracing (per §7.7)
- **Skipped**: Cognito JWT validation, RBAC permission decorators

The `require_permission()` FastAPI dependency is NOT applied to these routes. Authorization is purely the signed URL.

### 18.5 Stripe One-Time Payment for Invoices with Amount Variance

Customers pay invoices via the public link using Stripe Elements (PCI-compliant; raw card never touches Pilot servers). Same Stripe account and customer record as subscription billing (§20). Different API surface — Payment Intents instead of Subscriptions.

**Payment flow**:

1. Customer clicks "Pay this invoice" on public invoice page
2. Frontend calls `POST /api/v1/public/invoices/{token}/payment-intent` with the customer-entered amount
3. Backend creates Stripe Payment Intent via Stripe API; returns client_secret
4. Frontend uses Stripe Elements with client_secret to collect card details and submit payment
5. Stripe processes payment; webhook fires
6. Backend records payment with actual amount paid + variance + comment
7. Frontend redirects to confirmation page

**Amount variance handling**:

- Customer can adjust the payment amount (up or down) from the invoice total
- When amount differs from invoice total, frontend requires a comment field (2000 char max) explaining the variance
- Backend validates: comment is required if `customer_amount != invoice_total`; payment is not processed without comment
- Variance is recorded on the payment record:

```sql
ALTER TABLE payment ADD COLUMN stripe_payment_intent_id TEXT;
ALTER TABLE payment ADD COLUMN customer_payment_comment TEXT NULL;
ALTER TABLE payment ADD COLUMN amount_variance_cents INTEGER NULL;
ALTER TABLE payment ADD COLUMN paid_via TEXT;  -- 'stripe' | 'check' | 'bank_transfer' | 'other'
```

**Underpayment**: invoice balance updates to `invoice_total - amount_paid`; remaining balance recorded as receivable. QuickBooks sync (§5) handles partial payments natively.

**Overpayment**: variance recorded with positive value; tenant reviews via UI and decides handling (refund via Stripe, credit forward, accept). UI shows "Customer paid $X over invoice total — review."

**Stripe webhook handler** (extends the webhook endpoint introduced in §20 for Subscriptions):

- `payment_intent.succeeded` → record payment, update invoice balance, trigger Customer Activity notification
- `payment_intent.payment_failed` → surface failure to customer-facing UI; payment retries handled by Stripe; tenant notified after final failure
- Webhook signature verified using Stripe webhook signing secret stored in Secrets Manager

**Stripe Connect consideration** (Phase 2 review point): for MVP, Pilot uses a single Stripe account; customer payments accumulate in Pilot's account; disbursement to tenants is a separate financial process (TBD). Stripe Connect would route payments directly to tenant Stripe accounts — cleaner architecture but more complex setup. Worth reviewing before MVP launch given financial implications.

### 18.6 State-Aware Revisit Handling

Customers revisiting a public link after taking action see the resulting state, not the original action buttons. Routing logic at the public page handler:

| Entity state | Renders |
| :--- | :--- |
| Quote `sent` (not yet acted) | Accept/Decline buttons visible |
| Quote `accepted` | Confirmation page with date + customer comment |
| Quote `declined` | Decline confirmation with reason + comment |
| Quote `expired` | Expired page; suggest contacting tenant for fresh link |
| Invoice unpaid | Pay button + alternative payment methods |
| Invoice partially paid | Payment history + remaining balance + "Pay remaining" / "Pay different amount" |
| Invoice fully paid | Paid confirmation with payment history |

This prevents accidental double-actions. The signed URL is the same; the page renders state-aware.

### 18.7 Customer Comment Storage (Entity-Bound)

Comments are stored on the entity, not in communication threads. Implementation per A83:

**Quote acceptance**:

```sql
ALTER TABLE quote ADD COLUMN customer_acceptance_comment TEXT NULL;
ALTER TABLE quote ADD COLUMN customer_accepted_at TIMESTAMPTZ NULL;
ALTER TABLE quote ADD COLUMN customer_email_at_action TEXT NULL;
```

**Quote decline**:

```sql
ALTER TABLE quote ADD COLUMN customer_decline_comment TEXT NULL;
ALTER TABLE quote ADD COLUMN customer_decline_reason TEXT NULL;
  -- enum: 'pricing' | 'scope' | 'timing' | 'other_contractor' | 'other'
ALTER TABLE quote ADD COLUMN customer_declined_at TIMESTAMPTZ NULL;
```

**Invoice payment**:

```sql
-- Already added in §18.5: customer_payment_comment, amount_variance_cents
```

**UI integration**: quote detail page surfaces the customer's comment prominently when present:

```
┌────────────────────────────────────────────┐
│ Quote QU-1024 — ACCEPTED                   │
│                                            │
│ Accepted by Sarah Johnson                  │
│ on April 27, 2026 at 2:14 PM               │
│                                            │
│ Customer comment:                          │
│ "Let's get started ASAP — when can you     │
│ begin?"                                    │
└────────────────────────────────────────────┘
```

**Notifications**: comment events trigger Customer Activity notifications per Tier 2 #5 (covered in §22 Notification Preference Center, Round 2B). Notification body includes the comment text.

**One-way for MVP**: tenant cannot reply to a customer comment from this entity-bound surface. If tenant wants to respond, they use existing Customer Comms (§17 SMS or §3.7 email). Phase 2 may add reply infrastructure if user demand justifies.

### 18.8 Email Template Rendering Pipeline

Per A82, MVP ships with 16 transactional email templates rendered through a unified pipeline that applies tenant branding to customer-facing templates while using Pilot standard branding for internal templates.

**Schema**:

```sql
email_template (
    template_id          TEXT PRIMARY KEY,    -- 'quote_sent', 'invoice_sent', 'welcome', etc.
    display_name         TEXT NOT NULL,
    category             TEXT NOT NULL,        -- 'customer_facing' | 'internal'
    subject_template     TEXT NOT NULL,        -- with variable substitution
    body_html_template   TEXT NOT NULL,
    body_plain_template  TEXT NOT NULL,        -- text fallback
    variables            JSONB NOT NULL,       -- supported variables
    is_active            BOOLEAN NOT NULL DEFAULT TRUE
)

tenant_email_branding (
    tenant_id            UUID PRIMARY KEY,
    logo_s3_path         TEXT NULL,
    brand_color_hex      TEXT NULL,            -- defaults to Pilot brand-indigo
    email_signature      TEXT NULL,            -- 500 char max
    custom_footer        TEXT NULL,            -- 200 char max
    updated_at           TIMESTAMPTZ NOT NULL
)
```

**Rendering pipeline** (`services/email_template_renderer.py`):

1. Take `template_id` + context payload (customer name, quote total, signed URL, etc.)
2. Resolve variables from context
3. For `customer_facing` category: apply tenant branding (logo, color, signature, footer) from `tenant_email_branding`
4. For `internal` category: use Pilot standard branding
5. Render HTML body and plain text body
6. Return ready-to-send payload for SendGrid

**16 MVP templates**:

| ID | Audience | Trigger |
| :--- | :--- | :--- |
| `welcome` | Tenant owner | Tenant signup completion |
| `email_verification` | Any user | Email verification request |
| `quote_sent` | Customer | Tenant sends quote |
| `quote_accepted` | Tenant | Customer accepts quote |
| `quote_declined` | Tenant | Customer declines quote |
| `quote_expiring` | Customer | 3 days before quote expiration |
| `invoice_sent` | Customer | Tenant sends invoice |
| `payment_received_tenant` | Tenant | Stripe payment success |
| `payment_received_customer` | Customer | Stripe payment success (receipt) |
| `payment_failed` | Customer | Stripe payment failure |
| `subscription_renewal` | Tenant | Stripe subscription renewal |
| `subscription_payment_failed` | Tenant | Stripe subscription payment failure |
| `trial_expiring` | Tenant | Per Tier 3 #10 trial expiration warnings |
| `trial_expired` | Tenant | Per Tier 3 #10 trial expiration |
| `password_reset` | Any user | Password reset request |
| `mfa_reset_by_owner` | Affected user | Per §4.5 owner reset of user MFA |
| `data_export_ready` | Requesting user | Per §4.5 / Tier 2 #7 data export completion |

**Tenant branding settings UI**: lives at `Settings > Communications > Email branding`. Owner-only edit. Provides:

- Logo upload via S3 presigned URL pattern (consistent with §15.5 photo upload)
- Brand color picker (validates contrast against white background)
- Signature multi-line text input
- Custom footer text input
- Live preview using sample template
- "Send test email to my address" affordance for verification

**Customer-facing branding policy**: customer-facing templates render with tenant branding to feel like the tenant's communication. Internal templates (welcome, password reset, MFA reset, etc.) use Pilot standard branding because the tenant is the recipient — they don't need their own brand back at them.

### 18.9 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── public_quotes.py          # /api/v1/public/quotes/* — signed-URL routes
│   │   ├── public_invoices.py        # /api/v1/public/invoices/* — signed-URL routes
│   │   ├── public_short_redirect.py  # /api/v1/short/{short_code} — short-link redirect
│   │   ├── webhooks_stripe.py        # Stripe webhook handler (extends from §20)
│   │   └── tenant_email_branding.py  # tenant branding CRUD
│   └── ...
├── services/
│   ├── public_link_signer.py         # HMAC token sign/verify
│   ├── short_link_resolver.py        # short code generation + resolution
│   ├── email_template_renderer.py    # template + branding rendering
│   ├── stripe_payment.py             # one-time payment integration
│   └── ...
└── tasks/
    └── stripe_cleanup.py              # cleanup_incomplete_stripe_payment_intents (per §3.2)
```

### 18.10 Audit Logging

Every customer-side action is captured in audit log per §16.5 audit log convention. Captured events:

- Quote viewed via public link (with customer email at access time)
- Quote accepted (timestamp, comment, customer email)
- Quote declined (timestamp, reason, comment, customer email)
- Invoice viewed via public link
- Invoice payment attempted (success or failure; amount; variance)
- Public link revoked (actor, link, reason)

Customer email captured at action time provides the audit trail for "who acted on this quote." No Pilot user account exists for customers, but the audit log captures what email was used to act on the entity.

### 18.11 Phase 2 Considerations

Out of MVP scope per Tier 4 #13:

- Customer registration with full account access (explicitly removed)
- Comment replies from tenant back to customer (use Customer Comms for now)
- Full template editing by tenants (structured customization only in MVP)
- PDF or print-friendly view of public quote/invoice
- Multi-language customer-facing pages
- Custom domain for tenant short links (MVP uses pilot.tr or similar Pilot-owned domain)
- Stripe Connect for direct-to-tenant payment routing (architectural review point)
- Customer-facing analytics ("opened quote 3 times before accepting")
- Bulk quote/invoice send to customer list
- Quote / invoice expiration custom intervals (currently fixed at 90 days)
```

This adds approximately 320 lines.

---

## Edit 2 — Insert §19 Help System Architecture

**Insertion point**: Immediately after §18 closes (after the §18.11 Phase 2 Considerations section), before `## Cost Analysis` chapter.

**Content to insert**:

```markdown
## 19. Help System Architecture

Pass 4 Tier 4 #14 introduced AI-mediated help with RAG retrieval over a markdown corpus. This chapter covers the architecture: corpus storage and structure, embedding pipeline, help AI agent, RAG retrieval, chat session management, anonymization pipeline, and voice integration.

### 19.1 Strategic Direction

Help should feel like a continuation of how Pilot users already interact with the product, not a separate paradigm. Pilot is voice-first AI-first; help is too. Three architectural principles:

- **Markdown in S3 is both the corpus AND the human articles**: same files serve AI retrieval (chunked + embedded) and direct article reading (rendered when surfaced as "Read full article")
- **Same Llama 3.x infrastructure as voice intents**: separate prompt + RAG context, not a separate model. Compute capacity shared; routing happens at the prompt layer
- **Capture for training data with anonymization at the pipeline stage**: sessions retained 90 days unscrubbed for debugging + history; then anonymized and rolled into training corpus

### 19.2 Markdown Corpus Storage and Structure

Help articles are markdown files in S3 with structured frontmatter. The structure works for both human reading and AI retrieval.

**S3 structure**:

- Bucket: `pilot-help-content` (with versioning enabled)
- Path: `s3://pilot-help-content/{language}/{category}/{article_id}.md`
- Public read: disabled — articles served via authenticated API
- IAM policy: Lambda + Celery worker can read; Tom can write via console or programmatic upload

**Frontmatter schema**:

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

# Article content in markdown follows
```

**Frontmatter field semantics**:

| Field | Purpose |
| :--- | :--- |
| `article_id` | Unique slug for cross-references and stable URLs |
| `title` | Human-readable title |
| `category` | Top-level grouping (integrations, voice-ai, settings, billing, onboarding, etc.) |
| `related_concepts` | Tags for cross-article retrieval |
| `ui_surfaces` | App routes / anchors where article is contextually relevant (drives context-aware help opener — see §19.5) |
| `related_articles` | Explicit cross-references for "see also" suggestions |
| `last_updated` | ISO date of last content update |
| `audience` | Roles this article is relevant for (used for retrieval filtering) |

**Initial corpus scope** (MVP target ~60 articles, Tom-owned content authoring):

| Category | Approximate article count |
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

### 19.3 Embedding Pipeline

Articles are chunked at section boundaries (each `##` heading starts a new chunk) and embedded into pgvector for semantic retrieval.

**Schema**:

```sql
help_article (
    article_id              TEXT PRIMARY KEY,
    s3_path                 TEXT NOT NULL,
    title                   TEXT NOT NULL,
    category                TEXT NOT NULL,
    frontmatter_metadata    JSONB NOT NULL,
    last_content_hash       TEXT NOT NULL,           -- sha256 of content for change detection
    last_processed_at       TIMESTAMPTZ NOT NULL,
    last_updated            DATE NOT NULL,
    audience                TEXT[] NOT NULL          -- array of role names
)

help_article_chunk (
    chunk_id                    UUID PRIMARY KEY,
    article_id                  TEXT NOT NULL REFERENCES help_article(article_id),
    chunk_order                 INTEGER NOT NULL,    -- preserve original order
    section_title               TEXT NOT NULL,       -- the ## heading
    chunk_text                  TEXT NOT NULL,
    chunk_text_with_metadata    TEXT NOT NULL,       -- frontmatter + section + content; what gets embedded
    embedding                   vector(1536) NOT NULL,
    token_count                 INTEGER NOT NULL
)

CREATE INDEX help_article_chunk_embedding_hnsw_idx ON help_article_chunk
    USING hnsw (embedding vector_cosine_ops);
```

**Chunking rules**:

- Minimum chunk size: 100 tokens (very short sections merged with adjacent)
- Maximum chunk size: 800 tokens (long sections split at sub-section or paragraph boundaries)
- Each chunk includes article frontmatter as a context header (so retrieved chunks carry their metadata)

**Embedding model**: OpenAI `text-embedding-3-small` for MVP (1536 dimensions, low cost — ~$0.00002 per 1K tokens). Estimated cost at MVP scale: $0.60 one-time for full corpus + $0.10/month for query embeddings at moderate usage. Open-source alternative (Sentence-BERT family) is feasible if avoiding OpenAI dependency is preferred.

**Pipeline trigger**:

- S3 event notification on article upload/update (via S3 event → SQS → Celery)
- Manual trigger via admin endpoint
- Weekly scheduled re-embedding pass (catches missed events)

**Pipeline steps** (`tasks/help_corpus.py::process_help_article`):

1. Fetch markdown from S3
2. Parse frontmatter
3. Chunk by section boundaries
4. Compute content hash; skip if unchanged from `last_content_hash`
5. Embed each chunk via OpenAI API
6. Store/update chunks in `help_article_chunk` (delete old chunks for changed articles, insert new)
7. Update `help_article` with new hash and `last_processed_at`

**Update latency**: total time from edit-and-upload to AI-aware is typically 1–2 minutes (S3 event → Celery worker → OpenAI embedding API → pgvector write).

### 19.4 Help AI Agent

The help agent uses the same Llama 3.x infrastructure as voice intents (per §6) with a distinct prompt template and RAG context injection.

**Prompt template** (`prompts/help/help_agent.md`):

```
You are Pilot's help assistant — a friendly, concise guide for users navigating
Pilot for Trades, an AI-first SaaS platform for small electrical contractors.

[System constraints — see §19.7 knowledge boundaries]

[RAG retrieved chunks injected here as Pilot product knowledge]

[User's surface context payload injected here, if available]

[Conversation history]

User question: {user_message}

Respond in {voice_persona_tone} tone. Keep responses concise; offer follow-up
actions where appropriate (Read full article, Walk me through it).
```

Three tone variants per voice persona (per §16.5 / Tier 2 #6): `help_agent_conservative.md`, `help_agent_balanced.md`, `help_agent_playful.md`.

**Routing**: voice intent registry routes `open_help` and `ask_help_question` intents to the help endpoint (`POST /api/v1/help/chat`). Same Ollama model serves both voice intents and help queries; routing happens at the prompt layer.

**Streaming response support**: HTTP chunked transfer encoding for token-by-token rendering on client. For MVP, full response can be returned non-streamed if streaming infrastructure isn't ready.

### 19.5 RAG Retrieval

When a user query arrives:

1. **Embed user query** via OpenAI embedding API
2. **Filter chunks by audience role** (technician queries don't pull owner-only chunks)
3. **Optional category filter** if context payload suggests a category
4. **pgvector cosine similarity search** returns top-K (default K=5) most-relevant chunks
5. **Inject chunks into prompt** as Pilot product knowledge context

**Retrieval API** (internal to A84):

```
POST /api/v1/help/retrieve
Request:  { query_embedding: vector, role: text, category_hint: text?, k: int }
Response: { chunks: [{ article_id, section_title, chunk_text, score }, ...] }
```

**Context-aware help opener**: when user opens help from a settings page or flow surface, frontend sends a context payload to the AI for grounded responses:

```json
{
    "route": "/settings/integrations/quickbooks",
    "entity_type": null,
    "recent_actions": ["viewed_qb_conflict", "opened_settings", "changed_setting"],
    "user_role": "owner",
    "tenant_metadata": { "size": "small", "trade": "electrical" }
}
```

**Privacy boundary on context**: action *types* only, never entity contents. No quote numbers, customer names, amounts, etc. The action-type vocabulary is a small enumerated list captured client-side ephemerally — not stored server-side.

This context lets the AI ground its initial message: "I see you're on the QuickBooks integration page. What can I help you with?" — much better than cold context.

### 19.6 Chat Session Management

Help conversations are organized into sessions persisted server-side.

**Schema**:

```sql
help_chat_session (
    session_id              UUID PRIMARY KEY,
    tenant_id               UUID NOT NULL,
    user_id                 UUID NOT NULL,
    started_at              TIMESTAMPTZ NOT NULL,
    last_activity_at        TIMESTAMPTZ NOT NULL,
    title                   TEXT NULL,                -- auto-generated via A11 pattern
    outcome                 TEXT NULL,                -- 'resolved' | 'escalated' | 'abandoned'
    message_count           INTEGER NOT NULL DEFAULT 0,
    anonymized_at           TIMESTAMPTZ NULL          -- set when anonymization pipeline runs
)

help_chat_message (
    message_id              UUID PRIMARY KEY,
    session_id              UUID NOT NULL REFERENCES help_chat_session,
    role                    TEXT NOT NULL,             -- 'user' | 'assistant'
    content                 TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL,
    context_payload         JSONB,                     -- user messages: surface context
    retrieved_chunks        JSONB,                     -- assistant messages: which chunks fed RAG
    voice_used              BOOLEAN NOT NULL DEFAULT FALSE
)
```

**Session continuity**:

- **Within-session**: opening help, asking question, navigating elsewhere, opening help again — same conversation continues
- **Cross-session**: full close (✕) or sign-out → next help session opens clean
- **Multi-device**: sessions are per-device in MVP; not synced across user's devices

**Session title generation**: reuses A11 (Ollama-generated session titles) with help-specific prompt. Titles render in the "Past conversations" surface for user recall.

### 19.7 AI Knowledge Boundaries and Escalation

The help AI is scoped via system prompt to "how to use Pilot" knowledge plus surface context. Explicit boundaries:

- Does NOT take actions on behalf of the user
- Does NOT access tenant-specific data (no "show me my last quote" — that's voice intent system)
- Does NOT provide financial / legal / compliance advice
- Does NOT make product roadmap commitments
- Does NOT operate outside Pilot domain

**Three escalation triggers** route stuck users to feedback submission:

1. User explicitly asks for human help ("I want to talk to a real person")
2. AI low-confidence after 3 turns (the AI has tried twice; user is still stuck)
3. Question outside Pilot scope (legal, financial, technical issues with user's specific data)

In all cases, AI surfaces feedback submission flow with category pre-set to "Question" and conversation context pre-filled.

### 19.8 Voice Integration

Help is voice-accessible. Voice intent grammar from §6.2:

| Intent | Behavior |
| :--- | :--- |
| `open_help` | Opens help chat panel (web) or full-screen (mobile); AI prompts "What can I help you with?" |
| `ask_help_question` | Routes the user's utterance directly as the first help query |

**Voice readback of AI responses**: uses the user's effective voice persona tone (per §16.5 / Tier 2 #6). Per §6.6 confirm-as-turn, no destructive actions in help — pure information retrieval — so no confirm-before-commit needed. Always-preview-before-send (§16.7) doesn't apply for the same reason.

**Voice-only mode**: user invokes help via voice; AI responds via TTS automatically; ongoing conversation can stay voice-only until user types or taps to switch to text.

### 19.9 Anonymization Pipeline (Training Data Capture)

Per Tier 4 #14 Decision 13, help chat sessions are captured for training data with anonymization at the 90-day boundary.

**Three-tier retention model**:

| Tier | Duration | Purpose |
| :--- | :--- | :--- |
| Active session | Until user closes chat | Real-time conversation state |
| Recent (unscrubbed) | 90 days | Debugging, user history recall, training pipeline source |
| Training corpus (anonymized) | Permanent | Model fine-tuning and content improvement |

**Anonymization pipeline** (`tasks/help_corpus.py::anonymize_help_sessions`, daily):

1. Identify sessions where `last_activity_at <= now() - 90 days` AND `anonymized_at IS NULL`
2. For each session:
   - Iterate messages
   - Run PII detection (regex + NER)
   - Replace PII with placeholders: `[email]`, `[phone]`, `[person]`, `[business]`, `[address]`, `[id]`
   - Strip tenant_id and user_id references
   - Save anonymized version to `help_training_corpus` (separate table)
   - Set `anonymized_at` on original session
   - After all messages processed, delete original `help_chat_session` and `help_chat_message` rows

**`help_training_corpus` schema**:

```sql
help_training_corpus (
    corpus_id                       UUID PRIMARY KEY,
    original_session_id_hash        TEXT NOT NULL,    -- one-way hash; tracking but not reversal
    anonymized_message_history      JSONB NOT NULL,
    anonymized_context_payload      JSONB,
    category_inferred               TEXT NULL,        -- AI-classified for filtering training data
    outcome                         TEXT NOT NULL,
    anonymized_at                   TIMESTAMPTZ NOT NULL
)
```

**PII detection rules** (initial set, refined during testing):

- Email addresses (regex `[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}`) → `[email]`
- Phone numbers (US format detection) → `[phone]`
- Names (NER model or simple capitalized-word heuristic) → `[person]`
- Business names (capitalized phrases ending in business suffixes) → `[business]`
- Addresses (street number + word + street suffix) → `[address]`
- Long alphanumeric IDs (UUIDs, account numbers) → `[id]`

**User-facing transparency**: small note in help chat panel: "Pilot uses help conversations to improve our help content. Personal information is removed before use. [Learn more]" — link opens a help article explaining the pipeline.

**User deletion request** (Phase 2 surface; backend stub for MVP): `POST /api/v1/help/sessions/delete-all` deletes all help chat sessions for the requesting user. Stub endpoint exists; full UX is Phase 2.

### 19.10 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── help_chat.py              # /api/v1/help/chat — main chat endpoint
│   │   ├── help_sessions.py          # session list / detail / mark-read
│   │   ├── help_articles.py          # GET /api/v1/help/articles/{id} — article delivery
│   │   └── feedback.py               # /api/v1/feedback — submission endpoint
│   └── voice/
│       └── intents.py                # open_help, ask_help_question intent handlers added
├── services/
│   ├── help_agent.py                 # prompt rendering + Ollama calling for help AI
│   ├── help_retrieval.py             # RAG retrieval via pgvector
│   ├── help_corpus.py                # corpus management
│   └── pii_anonymizer.py             # PII detection + replacement utilities
├── tasks/
│   └── help_corpus.py                # process_help_article (event-driven) + anonymize_help_sessions (daily)
└── prompts/
    └── help/
        ├── help_agent_conservative.md
        ├── help_agent_balanced.md
        └── help_agent_playful.md
```

### 19.11 Selective Contextual Help Anchors

Per Tier 4 #14 Decision 1, "?" icons are placed selectively on complex surfaces rather than universally. Anchor placement list:

| Surface | Help anchors |
| :--- | :--- |
| `Settings > Integrations > QuickBooks` | next to "Auto-expire" toggle, "Sync direction" picker |
| `Settings > Integrations > Calendar` | next to "Auto-expire" toggle |
| `Settings > Notifications > Preferences` | inline annotation explainer + "Why is this locked?" |
| `Settings > Sync & Storage > Background sync` | next to "Push interval" setting |
| `Settings > Voice AI > Persona tone` | next to the tone cards |
| `Settings > Subscription & Billing > SMS quota` | next to "Cap policy" setting |
| `Settings > Operations > Margin buckets` | next to bucket boundary editor |
| `Settings > Tax configuration` | next to tax rate field |
| `My Account > MFA methods` | next to each method type card |
| Field issues queue | next to severity class indicator |
| Calendar conflict resolution | next to deletion-conflict treatment buttons |
| QuickBooks conflict resolution | next to master direction indicator |
| Quote approval queue | next to "Approval required" annotation |
| Onboarding — Tax setup sub-flow | inline help on jurisdiction selection |

Selective placement keeps content authoring scope manageable. Tom owns content for each contextual help target.

### 19.12 Phase 2 Considerations

Out of MVP scope per Tier 4 #14:

- Diagnostic data attachment for bug reports (text-only feedback in MVP)
- Ticket system replacing email feedback intake
- Multi-language help content
- Help chat session sync across devices
- Community forum / user-to-user help
- AI-generated article suggestions (AI suggests new articles based on common queries with no good RAG match)
- Admin UI for help content editing (S3 + repo workflow for MVP)
- Help analytics dashboard for Tom (most-common queries, articles never retrieved, low-confidence answers)
- User-initiated help chat data deletion self-service (backend stub in MVP)
- Voice-only proactive help suggestions
- Real-time conversation streaming with progressive token rendering (full response for MVP if streaming infrastructure not ready)
- AI confidence scoring exposed to users
- Personalized help suggestions based on user history
```

This adds approximately 350 lines.

---

## Edit 3 — TOC additions

**Find** the existing TOC (around lines 12–177).

**Add new entries** under Section 17 SMS Infrastructure entries, before Cost Analysis entry. The exact lines depend on your post-Round-1 TOC structure, but the pattern:

```markdown
- [18. Customer-Facing Public Surfaces Architecture](#18-customer-facing-public-surfaces-architecture)
  - [18.1 Strategic Direction](#181-strategic-direction)
  - [18.2 Signed URL Infrastructure](#182-signed-url-infrastructure)
  - [18.3 Short-Link Redirect Infrastructure](#183-short-link-redirect-infrastructure)
  - [18.4 Public Page Routing](#184-public-page-routing)
  - [18.5 Stripe One-Time Payment for Invoices with Amount Variance](#185-stripe-one-time-payment-for-invoices-with-amount-variance)
  - [18.6 State-Aware Revisit Handling](#186-state-aware-revisit-handling)
  - [18.7 Customer Comment Storage (Entity-Bound)](#187-customer-comment-storage-entity-bound)
  - [18.8 Email Template Rendering Pipeline](#188-email-template-rendering-pipeline)
  - [18.9 Backend Module Structure](#189-backend-module-structure)
  - [18.10 Audit Logging](#1810-audit-logging)
  - [18.11 Phase 2 Considerations](#1811-phase-2-considerations)
- [19. Help System Architecture](#19-help-system-architecture)
  - [19.1 Strategic Direction](#191-strategic-direction)
  - [19.2 Markdown Corpus Storage and Structure](#192-markdown-corpus-storage-and-structure)
  - [19.3 Embedding Pipeline](#193-embedding-pipeline)
  - [19.4 Help AI Agent](#194-help-ai-agent)
  - [19.5 RAG Retrieval](#195-rag-retrieval)
  - [19.6 Chat Session Management](#196-chat-session-management)
  - [19.7 AI Knowledge Boundaries and Escalation](#197-ai-knowledge-boundaries-and-escalation)
  - [19.8 Voice Integration](#198-voice-integration)
  - [19.9 Anonymization Pipeline (Training Data Capture)](#199-anonymization-pipeline-training-data-capture)
  - [19.10 Backend Module Structure](#1910-backend-module-structure)
  - [19.11 Selective Contextual Help Anchors](#1911-selective-contextual-help-anchors)
  - [19.12 Phase 2 Considerations](#1912-phase-2-considerations)
```

Insert these in TOC at the appropriate alphabetical/numerical position relative to Cost Analysis entry.

---

## Verification checklist after Round 2A

- [ ] §18 Customer-Facing Public Surfaces Architecture chapter inserted between §17 and Cost Analysis (Edit 1)
- [ ] §19 Help System Architecture chapter inserted after §18, before Cost Analysis (Edit 2)
- [ ] TOC entries added for §18 (11 sub-entries) and §19 (12 sub-entries) (Edit 3)
- [ ] All cross-references resolve (e.g., §16.5 audit log convention referenced in §18.10; §6.6 confirm-as-turn referenced in §19.8)
- [ ] Document growth: approximately 670 lines added (320 for §18, 350 for §19)

After Round 2A, your arch doc grows from ~3700 lines (post-Round-1) to ~4370 lines.

---

## What's next: Round 2B

Round 2B covers the remaining new architectural content:

- Subscription Tier + Stripe Subscriptions Integration (extends §1 or new chapter)
- Onboarding State Machine (extends §4 Authentication or new chapter)
- Notification Preference Center (extends §3 Background Processing or new chapter)
- Account Settings extension (consolidates with §4.5 MFA expansion from Round 1)
- Operator role + hidden Pilot routes (extends §4.3 RBAC)

Per the Q1 hybrid choice, my proposal for Round 2B:

- **Extend §3** with notification dispatcher + preference matrix architecture
- **Extend §4** with onboarding state machine + operator role + account settings consolidation
- **New §20 Subscription Tier + Stripe Integration Architecture** — genuinely new domain warranting chapter

Estimated Round 2B size: ~500–700 lines of additions.

Apply Round 2A first, verify the new chapters integrate cleanly, then we generate Round 2B. Tell me when you've applied Round 2A and want to proceed.
