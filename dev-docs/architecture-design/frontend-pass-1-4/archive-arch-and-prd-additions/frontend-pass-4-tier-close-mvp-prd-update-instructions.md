# PRD v3.1 (final) — Audit Report and Update Instructions

**Date**: April 30, 2026
**Audited file**: `mvp-prd.md` (your current uploaded version)
**Current state**: v3.1 interim (per version history, captured Tier 1.5 only)
**Target state**: v3.1 final — consolidates all Pass 4 product decisions through Tier 4 close

---

## Audit summary

Your PRD captured the Pass 3 close + Tier 1.5 well. Section 3.7 (Notifications & Comms) is in particularly good shape because we worked on it directly during the Tier 1.5 update instructions. Section 3.11 has the SMS quota tier rows.

**What's missing breaks down into seven categories:**

1. **§3.5 Identity** — three placeholder rows ("<<need to complete>>") for MFA, MFA policy, active sessions
2. **§3.6 Invoicing & Billing** — Stripe one-time payment + variance, customer comments on payment, public invoice link details
3. **§3.7 Notifications & Comms** — notification preference matrix (Tier 2 #5), in-app banner channel, customer SMS opt-out flagged but not the comment storage Tier 4 #13
4. **§3.9 QuickBooks Integration** — still says "deferred to Pass 4"; Tier 1 #2 is closed
5. **§3.10 Sales & Quoting** — customer accept/decline with comment, public quote link details
6. **§3.11 Subscriptions** — major gap — multi-tier model, trial-as-tier, Stripe subscription billing, operator overrides
7. **§3.13 Voice AI** — voice persona tone moved from Post-MVP to MVP (per Tier 2 #6)
8. **§3.15 Mobile Offline Operations** — owner-side mobile-conflict resolution UI is now done (Tier 1 #1); background sync is now in MVP (Tier 1 #3); should reference these as resolved instead of "deferred to Pass 4"
9. **§4.1 Platform UX Vocabulary** — three Tier 1 patterns missing (mobile-to-web escalation, bilateral integration conflict resolution formalized, background sync execution); plus the in-flight sync indicator from Tier 4 #12; intro paragraph says "Pass 3 design surfaced" should reflect Pass 4 additions
10. **New §3.16 Help & Support domain** — entirely new (Tier 4 #14)
11. **New §3.17 Onboarding domain** OR substantial additions to §3.5 — Tier 3 #10 onboarding flow, trial expiration, etc.
12. **§4 Customer-Facing Public Surfaces** — entirely new pattern category (Tier 4 #13) covering public quote/invoice pages, signed URLs, email branding
13. **Version history table** — missing v3.1 final row
14. **TOC** — needs new section entries

**Estimated edit time: 60–90 minutes** — substantial paste work but most blocks are content-complete and ready.

---

## Edit 1 — Version history bump (line 13–21)

**Find** the existing version history table.

**Add a new row** at the top (above the v3.1 interim row):

```markdown
| 3.1 (final) | Apr 30, 2026 | Pass 4 design phase complete. Consolidates v3.1 interim plus all Tier 1, 1.5, 2, 3, 4 product decisions. Major additions: multi-tier subscription model with trial-as-tier framing and Stripe integration; multi-method MFA (TOTP/SMS/Email) with tenant-required policy and 7-day grace period; notification preference center with per-user × per-category × per-channel matrix and forced-minimum push for safety-critical categories; owner-side mobile-conflict resolution UI; QuickBooks conflict resolution UI (resolves prior deferral); background sync for mobile (pulled forward from Phase 2); voice persona tone surfaced to UI with three-position enum and per-user override; account settings (profile, password, MFA, sessions, data export); customer-facing public quote/invoice link pages with Stripe one-time payment, customer comments stored entity-bound, and tenant email branding customization; AI-mediated help system with RAG retrieval over markdown corpus and chat session capture for training data; in-flight sync indicator with pending count generalized as platform pattern; Tier 3 onboarding wizard plus post-wizard checklist; mobile push notification permission flow; states catalog covering empty/loading/error treatments. Six new platform UX patterns formalized in §4.1. New §3.16 Help & Support domain. Pass 4 close: all 14 surfaces + Tier 1.5 + Settings IA framework locked. Cumulative backend work A1–A88. |
```

**Note**: keep the v3.1 interim row in the table for change-log fidelity. Don't remove it.

If you'd rather the version label stay simply `3.1` with the interim row absorbed, you can replace the interim row with this consolidated row. My recommendation: keep both rows (interim + final) for audit trail; readers can see how the doc evolved.

---

## Edit 2 — TOC additions (around line 24–63)

**Find** the existing TOC. **Add these new entries** under Section 3:

After the existing line `- [3.15 Mobile Offline Operations](#315-mobile-offline-operations)`:

```markdown
    - [3.16 Help \& Support](#316-help--support)
```

If you decide to add a separate Onboarding section (vs. integrating into §3.5), also add:

```markdown
    - [3.17 Onboarding \& Tenant Lifecycle](#317-onboarding--tenant-lifecycle)
```

My recommendation: integrate onboarding content into §3.5 as new feature rows rather than create a new top-level section. Keeps the section count manageable and conceptually onboarding is part of identity/access management. So no new §3.17.

Also under Section 4, the existing TOC has entries for §4.1, §4.2, §4.3. Add a new entry for the new customer-facing surfaces category if you decide to give it its own subsection — see Edit 12 for that question.

---

## Edit 3 — §3.5 Identity, Access & Tenant Management (line 322–340)

This section has three placeholder rows that need to be filled in, plus several missing rows for Tier 3 #10 onboarding.

**Find** the three placeholder rows:

```markdown
| **MFA Enrollment** | <<need to complete with details from flow specs>> |
| **Tenant MFA Policy with Grace Period** | <<need to complete with details from flow specs>> |
| **Active Sessions** | <<need to complete with details from flow specs>> |
```

**Replace those three rows with these completed rows plus additional rows for onboarding-related identity features**:

```markdown
| **Multi-Method MFA Enrollment (TOTP + SMS + Email)** | Users can enroll any combination of three MFA methods: authenticator app (TOTP), SMS, and email. Self-service multi-method enrollment is encouraged at first setup to prevent lockouts. At login, the user picks which enrolled method to use for that session. 10 single-use recovery codes generated at first enrollment as ultimate fallback; regenerable on demand. Method cards surface security trade-offs honestly (TOTP labeled "Most secure. Recommended.") without forcing the choice. |
| **Tenant-Required MFA Policy with 7-Day Grace Period** | Owners can enable tenant-wide MFA-required policy at `Settings > Users & Roles > Security policy`. When enabled, all tenant users have a 7-day grace period to enroll at least one MFA method. During grace, warning banners and daily reminders escalate. Login-trigger enforcement: any login during grace activates immediate enrollment for that session; after 7 days, all unenrolled users are forced into enrollment on next login. Existing authenticated sessions continue working until next login (preserves in-flight tech work). When tenant disables MFA-required, existing user MFA stays on; new users aren't required. |
| **Owner Reset of User MFA (Support Escape Hatch)** | Owners can reset MFA for any user via `Settings > Users & Roles > [user detail] > Reset MFA`, removing all enrolled methods + recovery codes. The user re-enrolls on next login. Notified user receives email + push confirmation. Audit log captures the reset event with actor and target identities. Owner self-reset of own MFA is also supported (with password re-verification) for the rare case where the owner has lost access to all enrolled methods. |
| **Active Sessions Management** | Users can view all currently-logged-in sessions for their account at `My Account > Security > Active sessions` with device + browser + last-active timestamp + approximate location. Per-session revoke and "Revoke all other sessions" affordances. The latter is the user's primary self-service security action when suspecting compromise. Revoke immediately invalidates the refresh token; next API request from that session forces re-login. |
| **Profile Management (Name, Photo, Phone, Time Zone)** | User-personal profile editing at `My Account > Profile`: display name, profile photo (upload + crop), phone number (used for SMS MFA when enrolled), email (read-only in MVP; account migration is Phase 2), language preference (English only in MVP), time zone (auto-detected default; user-overridable). Phone number changes require re-verification of SMS MFA method if enrolled. |
| **Password Change with Cross-Device Session Invalidation** | Password change at `My Account > Password` requires current password verification + new password meeting tenant policy (12+ chars, complexity, history). On successful change, all sessions other than the current one are auto-revoked as a security best practice. User stays logged in on the changing device; other devices require re-login. |
| **Personal Data Export Request** | Users can request a full export of their accessible tenant data (RBAC-scoped — owners get full tenant; technicians get only their own jobs/time/expenses/communications) at `My Account > Data export`. Background job generates CSV files per entity type, bundled into a ZIP with manifest, delivered via email with a 7-day signed download URL. Frequency limit: one export per user per 24 hours. |
| **Tenant Signup Wizard (5-Step)** | New tenant signup uses a minimum-required wizard: (1) Account creation with email/password/business info; (2) Legal acceptance for ToS/Privacy/EULA with versioned hashing; (3) Optional phone verification (only required if user wants SMS notifications or SMS MFA — customer SMS messaging works regardless via tenant Telnyx number); (4) Subscription tier selection with Trial pre-selected; (5) Confirmation and routing to dashboard (or Stripe payment if paid tier picked). Email verification decoupled from wizard completion to avoid blocking on email delivery delays. |
| **Resumable Wizard State** | Users who abandon mid-wizard return to where they left off on next login. State persisted per-tenant; pre-filled fields where state is known; users can navigate back through completed steps. |
| **Post-Wizard Setup Checklist (Pinned Dashboard Widget)** | After wizard completion, users land on the standard dashboard with a pinned "Setup checklist" widget. Eight items: account/legal/tier (auto-completed during wizard), add first customer, set up catalog, connect QuickBooks, connect calendar, invite team. Auto-completion detection: items mark done when completed via any path (e.g., adding a customer via voice marks the checklist item done). Hide, skip individual items, or dismiss permanently options. Persists per-tenant across users. |
| **Mobile Setup Phase on First Mobile Login** | When any user logs into mobile for the first time, brief mobile setup phase fires: welcome screen, push notification permission request (with pre-explainer screen before OS prompt — see §3.7), brief tutorial cards on Today tab and voice mic. Skippable. Routes to Today tab on completion. |
| **Tax Setup Just-In-Time Sub-Flow** | Tax setup is the only onboarding step that gates downstream functionality — users cannot generate invoices without tax rates configured. Rather than forcing it in the wizard, Pilot uses a contextual sub-flow: when the user attempts to convert a quote to invoice or generate an invoice directly, the "Set up tax rates first" sub-flow appears with auto-detected tax jurisdiction (from ZIP), default rate suggestion, and tax-exempt opt-in. Once configured, subsequent invoices use saved tax setup. |
| **Pass 4 RBAC Additions** | New permissions added at Pass 4: `field_issue.view`, `field_issue.resolve` (owner, accountant) — Tier 1 #1; `qb_conflict.view`, `qb_conflict.resolve` (owner, accountant) — Tier 1 #2; `notification_preference.tenant_default.edit` (owner), `notification_preference.user_override.edit` (all) — Tier 2 #5; `voice_persona_tone.tenant_default.edit` (owner), `voice_persona_tone.user_override.edit` (all when allowed), `voice_persona_tone.user_override_policy.edit` (owner) — Tier 2 #6; `mfa.enroll_self`, `mfa.reset_self` (all), `mfa.reset_user`, `mfa.policy.edit` (owner) — Tier 2 #7; `account.session.revoke_own`, `account.data_export.request` (all) — Tier 2 #7; `subscription.view` (owner, accountant), `subscription.tier.change` (owner) — Tier 3 #10; `legal_acceptance.accept`, `tenant.signup.complete` (auto during signup) — Tier 3 #10; `onboarding_checklist.skip_item`, `onboarding_checklist.dismiss` (owner, accountant) — Tier 3 #10; `mobile_push_permission.update` (all on own device) — Tier 3 #11; `email_branding.edit` (owner, accountant) — Tier 4 #13; `public_link.revoke` (owner, accountant) — Tier 4 #13; `feedback.submit` (all) — Tier 4 #14; `help_chat.delete_own_history` (all; Phase 2 surface stub) — Tier 4 #14. |
| **Operator Role (Pilot Platform-Level)** | A special platform-level role outside tenant RBAC, exclusively for Pilot operator (Tom). Manages cross-tenant settings via hidden Pilot routes. Operator-controlled values include: per-tenant trial length override, per-tenant subscription tier override (force a tier without payment), tenant suspension/restoration, tenant deletion with data purge, system default settings. For MVP, operator-admin functions are managed via direct DB updates; hidden Pilot routes are deferred operator infrastructure. |
```

This expands §3.5 from 8 features to 21 features, covering all Pass 4 identity-and-onboarding additions. The replacement is a single block — find the three placeholder rows, replace with the 13 new rows above.

---

## Edit 4 — §3.6 Invoicing & Billing (line 343–358)

**Find** the existing §3.6 features table.

**Add these new feature rows** at the bottom of the table (below the existing "QuickBooks Invoice & Payment Push Sync" row):

```markdown
| **Stripe One-Time Payment for Invoices** | Customers paying via the public invoice link use Stripe Elements (PCI-compliant card collection; Pilot servers never see raw card data). Same Stripe account as subscription billing; parallel API surface (Stripe Payment Intents). Customer can adjust payment amount up or down from invoice total — when amount differs, a comment is required explaining the variance ("paying 90% per agreed discount"; "tip for Tom"). Stripe webhook confirms payment success; invoice balance updates accordingly. Failed payments surface inline with retry option. |
| **Customer Payment Comments (Entity-Bound)** | Comments left by customers on the public invoice payment surface are stored on the payment record (`payment.customer_payment_comment`), not routed into customer comm threads. Visible on the payment detail and on the related invoice detail in Pilot. Tenant notification per Tier 2 #5 "Billing" category. One-way for MVP; if tenant wants to respond, they use existing Customer Comms (§3.7). |
| **Variance Payment Accounting Integrity** | Underpayments preserve the unpaid balance on the invoice; overpayments are flagged for tenant review. Stripe captures the actual amount paid; Pilot records `amount_variance_cents`. QuickBooks sync (§3.9) handles partial payments natively. Tenant decides handling for overpayment (refund, credit forward, accept). |
| **Public Invoice Link with 90-Day Signed URL** | Each invoice generates a signed-URL public page that customers access without a Pilot login. URL expires 90 days from generation; customer accessing an expired link sees a "contact tenant for fresh link" page. Tenant can manually revoke. Already-paid invoices show paid status with payment history; partially-paid invoices show remaining balance with both "Pay remaining" and "Pay different amount" affordances. State-aware revisit handling prevents accidental double-actions. |
| **Customer-Facing Page Tenant Branding** | Public invoice pages render with the tenant's email branding settings: logo, brand color, signature line, custom footer text. "Powered by Pilot for Trades" small footer link. Branding settings managed at `Settings > Communications > Email branding`. Default rendering uses tenant name in heavy text + Pilot brand-indigo if no custom branding configured. |
```

This adds 5 new rows, bringing §3.6 from 7 features to 12.

---

## Edit 5 — §3.7 Notifications & Communications additions (line 365–388)

§3.7 already has the SMS/Tier 1.5 content and is in good shape. **What's missing is the Tier 2 #5 notification preference center plus a few smaller additions**.

**Add these new feature rows** at the bottom of the §3.7 table (below the existing "A2P 10DLC Compliance as Pre-Launch Hygiene" row):

```markdown
| **Notification Preference Matrix (Per-User × Per-Category × Per-Channel)** | Each user controls notification preferences at `Settings > Notifications > Preferences` via an 8-category × 3-channel matrix (push / email / in-app banner). Categories: Quote approvals, Field issues, Sync conflicts, Job activity, Customer activity, Billing, Background sync alerts, System announcements. Three-tier resolution chain: user override → tenant default → system default. Per-row revert and per-cell revert affordances. Page-level "Mute all push (non-critical)" / "Mute all email" / "Reset to tenant defaults" controls. |
| **Forced-Minimum Push for Safety-Critical Categories** | Four categories have forced-minimum push that cannot be muted by user override: Field issues (all users), Job activity assignment-only sub-trigger (the tech being assigned), System announcements critical-only sub-trigger (all users), Customer activity inbound-SMS-reply sub-trigger (the originating tech in conversation only — not other recipients). User-context-asymmetric semantics for Customer activity is a new pattern: same category, different forced-minimum based on whether user is the tech in conversation or another user receiving ambient awareness. |
| **Tenant-Level Notification Defaults** | Owners set tenant-level default policies at `Settings > Notifications > Tenant defaults` separate from personal preferences. Same matrix structure; edits affect tenant defaults, not the owner's user override. RBAC: owner-only access. |
| **In-App Banner Notification Channel** | New channel for in-app real-time delivery via Server-Sent Events. Slim slide-down notification at top of active page; auto-dismiss after 6 seconds (12 seconds for critical); manually dismissable; click-to-navigate to relevant entity. Notification center bell in app shell shows unread count from last 24 hours + history of last 50. Shared component across web and mobile. ARIA accessibility for screen reader announcement. |
| **Notification Category Registry** | All backend notification firing sites classify into one of the 8 categories with optional sub-trigger metadata. Category registry seeded at deployment with category metadata (display label, description, forced-minimum push policy). Sub-triggers (e.g., `customer_activity.inbound_sms_reply`, `job_activity.assignment`) drive the asymmetric forced-minimum behavior. |
| **Delivery Dispatcher Preference Gate** | The notification delivery dispatcher consults user preferences before dispatching each channel for each recipient. Per-recipient evaluation handles the user-context-asymmetric forced-minimum (e.g., the tech in a conversation gets forced push for inbound SMS replies; the owner watching ambient does not). Compose with rate limiting: a notification must clear both rate limit (existing) and user preferences to be delivered. |
| **Push Deep-Link Routing** | Push notifications include deep-link metadata routing the user to the relevant entity when tapped. Per-category deep-link mapping: Quote approvals → quote detail; Field issues → field issue resolution; Sync conflicts → integration conflicts queue; Job activity → job detail; Customer activity → comm history thread; Billing → invoices/subscription; Background sync alerts → mobile sync queue; System announcements → announcements archive (Phase 2 surface route reserved). |
```

This adds 7 new rows for the Tier 2 #5 notification preference center.

---

## Edit 6 — §3.9 QuickBooks Integration update (line 415–428)

**Find** the existing "Conflict Resolution (Duplicate Matching)" row that says "deferred to Pass 4."

**Replace it** (the entire row) with:

```markdown
| **Conflict Resolution UI (Bilateral Integration Conflict Pattern)** | When sync detects a conflict (both Pilot and QuickBooks modified the same entity since last sync), the conflict is captured in `integration_sync_conflict` with both snapshots plus the last-shared-state baseline for accurate field-level diff. Resolution UI at `Settings > Integrations > QuickBooks > Conflicts` renders side-by-side two-column diff (master direction-aware: Pilot-left for Quote conflicts, QB-left for Invoice conflicts; tenant override for Customer/Expense). Field-level track-changes vocabulary (amber/green/red). Two primary action buttons with master-aware primary-button treatment. Deletion-conflict variants use distinct verb-based treatment. Pre-commit staleness check with three 409 payload types (server changed, auto-recovered, stale). Voice scope: status query only (no voice resolution due to accounting integrity stakes). |
```

**Add these new rows** at the bottom of §3.9:

```markdown
| **Per-Entity Auto-Expiry Configuration (Tenant Opt-In)** | Auto-expiry is OFF by default for all four bilateral entity types (Customers, Quotes, Invoices, Expenses) — opposite of calendar's default-ON because QB has heterogeneous masters and accounting recovery cost is higher. Tenants opt in per entity type with paired enable + direction (`accept_local | accept_remote`) settings: `qb_auto_expire_customer_enabled` + `qb_auto_expire_customer_direction` (and parallel for quote, invoice, expense). When enabled, auto-expiry timing uses `qb_auto_expire_days` (default 60; longer than calendar's 30 because accounting cadence is quarterly) and `qb_pre_warning_days` (default 14). Save-on-group-complete pattern in the settings UI prevents half-baked enable-without-direction state. |
| **Invoice-Specific Financial-Delta Callout** | For invoice conflicts only, the resolution view includes a financial-delta callout above the diff showing total amount delta, AR impact preview, tax-period spanning warning when applicable, and a deep-link out to the invoice in QB's web UI. This recognizes that invoice conflicts have downstream consequences (AR balances, customer statements, tax filing) that calendar conflicts don't have. |
| **In-Flight Sync Indicator with Pending Count** | The QuickBooks sync indicator extends the platform-level In-Flight Sync Indicator pattern (§4.1): shows synced state plus a count of pending operations in either direction. Five compositional states: synced-idle, synced-with-pending, syncing-active, sync-error, sync-paused. Hover/tap surfaces individual pending entity changes (capped at 5 with "+N more"). Manual sync trigger inline in the indicator. Tunable threshold (`tenant_sync_indicator_pending_amber_threshold`, default 5) shifts visual emphasis to amber when pending count is operationally meaningful. |
```

---

## Edit 7 — §3.10 Sales & Quoting additions (line 432–460)

**Find** the existing §3.10 features table.

**Add these new feature rows** at the bottom (below "Change Order Management"):

```markdown
| **Public Quote Link with 90-Day Signed URL** | Each quote generates a signed-URL public page customers access without Pilot login. URL expires 90 days from generation. Already-acted-upon revisits show acceptance/decline confirmation rather than action buttons. State-aware rendering prevents double-actions. |
| **Customer Quote Acceptance with Optional Comment** | Customer accepts the quote from the public link; an optional comment field captures context ("Let's get started ASAP — when can you begin?"). Comment stored on the quote record (`quote.customer_acceptance_comment`), visible prominently on the quote detail in Pilot. Tenant notified per Tier 2 #5 "Customer activity" category. |
| **Customer Quote Decline with Reason + Comment** | Customer declines with a structured reason (Pricing / Scope / Timing / Other contractor / Other) plus optional free-text comment. Stored on the quote record (`quote.customer_decline_comment`, `quote.customer_decline_reason`). Tenant notified with comment in body. Once declined, quote stays in declined state — tenant generates a new quote if they revise based on feedback. |
| **Customer-Facing Page Tenant Branding** | Public quote pages use the tenant's email branding settings (logo, brand color, signature, custom footer) — same configuration as customer-facing emails. Subtle "Powered by Pilot for Trades" footer; tenant brand prominent. |
| **Quote Already-Acted-Upon Handling** | Customer revisiting a public link after taking action sees the resulting state (accepted with date and comment; declined with reason and comment; expired). No accidental re-actions possible. |
```

This adds 5 new rows for Tier 4 #13 customer-facing quote functionality.

---

## Edit 8 — §3.11 Subscriptions & Usage major expansion (line 464–484)

§3.11 has SMS quota content but is missing the multi-tier subscription model, trial-as-tier framing, and Stripe integration. **This is the largest single section update.**

**Add these new feature rows** at the bottom of §3.11 (below "SMS Overage Billing"):

```markdown
| **Multi-Tier Subscription Model** | Pilot supports multiple subscription tiers backed by the `subscription_tier` table. Tier metadata (name, price, included user count, included SMS segments, etc.) is data-driven — adding/editing tiers is a DB update, not a code change. MVP launches with four tiers: Trial (full features, $0, time-bounded), Starter, Professional, Enterprise. Differentiation in MVP is by user count only (Trial/Starter: up to 5 users; Professional: up to 15; Enterprise: up to 50). Feature differentiation between tiers is Phase 2. |
| **Trial-as-Tier Framing** | The trial is a subscription tier with `is_trial=true`, $0 price, time-bounded duration. Full feature parity with Starter. Inherits Starter's user limit so trial users see an accurate Starter experience. No special "trial mode" branching in the codebase — every code path that asks "what tier is this tenant on?" gets a clean answer via the tier system. |
| **Operator-Controlled Trial Length** | Trial duration is a Pilot operator setting (not a tenant setting), default 14 days, with per-tenant override capability. Operator manages via hidden Pilot routes (or DB updates for MVP). System default `system_default_trial_length_days` and per-tenant `tenant_tier_override.override_trial_length_days`. Different tenants can have different trial lengths based on operator decision (e.g., extending for a high-value prospect). |
| **Trial Expiration with Read-Only Paywall** | When a trial ends without conversion, the tenant enters "trial expired" state with read-only access to existing data plus a paywall surface. New data creation, SMS sending, voice creation operations blocked with paywall prompt. Pre-expiration warnings at 7 days, 3 days, 1 day, and on expiration day (email + push + in-app banner). Data preserved through expiration so dormant trials can resurrect easily on conversion. |
| **Stripe Integration for Subscription Billing** | Stripe Subscriptions for recurring billing of paid tiers. Stripe Elements for PCI-compliant card collection at signup or trial conversion. Stripe Customer Portal deferred to Phase 2; MVP has read-only billing display at `Settings > Subscription & Billing` with "Upgrade plan" affordance opening tier picker + Stripe Elements. Stripe webhooks handle subscription events (created, updated, deleted, payment success, payment failure). |
| **Trial-to-Paid Conversion Flow** | At any point during trial (or at expiration), tenant can convert to paid tier via the tier picker UI (same component as wizard step 4). Stripe payment + tier change + tenant resumes/continues normal operation. Stripe Customer record created on first paid conversion; reused for subsequent tier changes. |
| **Tier Limit Enforcement** | User-add flow checks `current_user_count >= max_users` for the tenant's current tier; if reached, returns Er3-class error with "Upgrade tier" CTA. SMS-send flow uses the existing quota model (per-tier `max_sms_segments_per_month`). Phase 2 adds feature-based limits as tier differentiation expands beyond user count. |
| **Subscription Usage Tracking (Users + SMS Segments)** | MVP tracks two usage metrics per tenant: current user count and current SMS segment count (the latter integrates with §3.7 SMS quota model). Period-aligned to subscription billing cycle. Tracked metrics extend to other dimensions in Phase 2 as tier differentiation evolves. |
| **Operator-Controlled Tier Overrides** | For special cases (high-value prospects, support escalations, comp accounts), operator can override a tenant's tier without payment. Stored in `tenant_tier_override.override_tier_id` with required `override_reason`. Audit-logged. Same pattern as trial length override. |
```

This adds 9 new rows for the multi-tier subscription model. §3.11 grows from 12 features to 21.

---

## Edit 9 — §3.13 Voice AI updates (line 504–530)

**Find** the existing "Voice Persona Tone Configuration *(Post-MVP — captured for roadmap)*" row.

**Replace** with the actual MVP-scope feature row plus related additions:

```markdown
| **Voice Persona Tone (Three-Position Enum with Per-User Override)** | Tenant-level setting `voice_persona_tone` controls AI personality across voice readback, session titles, assistant turn responses, and Voice tab empty states. Three positions: `conservative` (formal, brief), `balanced` (default), `playful` (warmer, conversational). Per-user override allowed by default; tenant can disable per-user override via meta-toggle. Three-tier resolution: user override → tenant override → system default → fallback. Each tone has dedicated Ollama prompt templates (one per voice context). Three preview audio clips (one per tone) are server-cached MP3s playable from the settings UI. Session titles use the session creator's tone (creation-time artifact). Empty-state copy uses the viewing user's tone. Customer-facing surfaces (SMS templates, transactional emails) explicitly NOT affected by tone — fixed branding regardless of tenant tone. |
```

**Add these new rows** for AI-mediated help (Tier 4 #14):

```markdown
| **AI-Mediated Help (RAG over Markdown Corpus)** | Help is delivered via AI chat conversation using the same Llama 3.x infrastructure as voice intents (separate prompt + RAG context). Help corpus is markdown files in S3 with structured frontmatter; chunks embedded into pgvector for semantic retrieval. User queries trigger top-K chunk retrieval; chunks injected into prompt as grounding context. Chat sessions captured (90 days unscrubbed, then anonymized) for training data. AI knowledge boundaries explicitly enforced — does not take actions, does not access tenant data, does not give legal/financial advice. Three escalation triggers route stuck users to feedback submission. |
| **Context-Aware Help Opener** | When user opens help from inside a settings page or flow, AI receives a minimal context payload (current route, entity type if applicable, recent action types in last 5 minutes, user role, tenant metadata) for grounded responses. Action types only — no entity contents — for privacy. AI initial message reflects context: "I see you're on the QuickBooks integration page — how can I help?" |
| **Help Voice Intent + Voice-Driven Mode** | Voice intent grammar extends with `open_help` and `ask_help_question` intents. Users can interact with help entirely via voice — voice input on chat composition, TTS readback of AI responses (using user's effective voice persona tone for consistency), continued voice-only flow until user types or taps to switch to text. |
| **Past Conversations Recall** | Users can review prior help chat sessions at `Help > Past conversations` with AI-generated brief titles per session (reuses A11 session title infrastructure). Tapping opens the session's full chat history; user can continue where they left off (within 90-day retention). |
```

§3.13 grows from 15 features (with one Post-MVP) to 18 features (with persona tone now in MVP plus three help-related rows).

---

## Edit 10 — §3.15 Mobile Offline Operations updates (line 565–582)

**Find** the existing "Owner Escalation Path" row and the "Sync Triggers" row.

**Replace the "Owner Escalation Path" row** with this updated version (the deferral note is now resolved):

```markdown
| **Owner Escalation Path with Loop Closure** | Conflicts classified as `owner_escalation` route to the owner via push notification + `notification_outbox` entry plus an entry in the web `Dashboard > Approvals > Field issues` queue. Owner-side resolution UI on web shows full diff with track-changes vocabulary, two-button bottom action bar with deletion-conflict variants, pre-commit staleness check with three 409 payload types. Resolution loops back to the originating tech with status update, push notification, and persistent activity log entry on tech mobile. Voice resolution active for binary cases with confirm-as-turn safeguard. The mobile-to-web escalation pattern is now formalized as a platform pattern (§4.1) — generalizable to future tech-submitted activities (time-off requests, safety incidents, catalog requests, etc.). |
```

**Replace the "Sync Triggers" row** with:

```markdown
| **Sync Triggers (Foreground + Background)** | Foreground sync runs on: app foreground transition; OS network state change to online; periodic check every 30 seconds while app active and online; manual trigger from the queue surface. Background sync (when app is closed) is now in MVP scope (pulled forward from Phase 2): server-initiated silent push as primary trigger (rate-limited per tenant-effective `background_sync_push_interval_minutes`, default 5); OS-scheduled opportunistic execution as fallback (BGAppRefreshTask on iOS, WorkManager periodic on Android). Background sync handles only the data sync queue — photos, voice audio, and periodic data refresh remain foreground-only for battery reasons. Auto-resolves only in background; tech-resolvable conflicts defer to foreground. Failure visibility on next app open. |
```

**Add these new rows** at the bottom:

```markdown
| **Field Issues Web Queue at `Dashboard > Approvals > Field issues`** | Owners review pending mobile-conflict escalations in a paginated table at `/dashboard/approvals/field-issues` with filtering by tech active status, operation type, and resolution status. Sort by escalation creation time descending by default. Empty state teaches normalcy ("No field issues to resolve. Your team's captures are all syncing cleanly."). Recent issue history available alongside pending queue. |
| **Background Sync Settings (Tenant + User Override)** | Four tenant settings control background sync behavior: `background_sync_enabled` (default TRUE; user override allowed), `background_sync_wifi_only` (default FALSE), `background_sync_battery_floor_pct` (default 20; range 5–50), `background_sync_push_interval_minutes` (default 5; range 1–60; system default + tenant override). Mobile users see read-only display of WiFi-only and battery floor settings; per-user override of master enabled toggle is editable on mobile per the three-question inclusion rule from Settings IA. |
```

§3.15 grows by ~2 net rows (replacements + 2 new).

---

## Edit 11 — §4.1 Platform UX Vocabulary expansion (line 596–650)

This section already has the three Tier 1.5 patterns (carrier-agnostic adapter, subscription quota, lazy provisioning). **Missing**: the three Tier 1 patterns plus the in-flight sync indicator from Tier 4 #12.

**First**, update the §4 introduction paragraph (line 594):

**Find**:

```markdown
Pass 3 design surfaced and formalized a set of cross-cutting patterns that now constitute Pilot's UX vocabulary at the platform level. These are not implementation details — they are product requirements, because they define how the platform behaves consistently across surfaces. New domains added in Phase 2 inherit these patterns by default; deviations require explicit justification.
```

**Replace with**:

```markdown
Pass 3 and Pass 4 design surfaced and formalized a set of cross-cutting patterns that now constitute Pilot's UX vocabulary at the platform level. These are not implementation details — they are product requirements, because they define how the platform behaves consistently across surfaces. New domains added in Phase 2 inherit these patterns by default; deviations require explicit justification. Sixteen patterns total: eight from Pass 3, six new in Pass 4 (Tier 1 + Tier 1.5 + Tier 4 #12), plus two visual-treatment extensions of existing patterns (system-default-with-tenant-override visual, three-tier resolution chain).
```

**Then add these new pattern blocks** at the bottom of §4.1 (after the existing "Lazy Provisioning of External Resource at First Use Pattern"):

```markdown
**Bilateral Integration Conflict Resolution Pattern (Formalized)**

The pattern that emerged from calendar sync conflict resolution (Pass 3 Flow 6) generalized through QuickBooks conflict resolution (Pass 4 Tier 1 #2). Common structure: paginated queue list sorted by urgency, side-by-side two-column diff with track-changes vocabulary, two-button bottom action bar with master-aware primary treatment, deletion-conflict variants with distinct verb-based treatment, pre-commit staleness check, modal-feeling but URL-routed, audit-but-no-undo, empty state teaches normalcy, mobile owner status row + deep-link, and system-default + tenant-override auto-expiry where applicable.

Pattern attributes that are domain-determined rather than fixed: auto-expiry default (ON when master is unambiguous like calendar; OFF when masters are heterogeneous like QuickBooks); voice resolution scope (full active resolution when stakes permit; status-query-only for accounting-data domain); column ordering and primary-button treatment (master-aware when masters are heterogeneous; uniform when single master).

Reference instances: calendar sync (§3.14), QuickBooks sync (§3.9). Future bilateral integrations (Salesforce, HubSpot, generic webhooks) inherit by default.

**Mobile-to-Web Escalation Pattern**

When mobile-originated activity requires owner judgment that the tech cannot or should not make autonomously, the activity is paused at the mobile origin, escalated to a web-side queue with push notification to the owner, resolved by the owner on web (or via voice for binary cases), and looped back to the originating tech with the resolution outcome reflected in their mobile experience. Resolution honors the pre-commit staleness check pattern. Audit trail records both originator and resolver.

Pattern characteristics: origin in a mobile-side action that classifies into the four-class severity model's `owner_escalation` class; routing via persistent server-side queue + push notification + entry in web `Approvals` sub-surface; resolution via web-only diff view inheriting the bilateral integration conflict resolution pattern's two-column treatment, with voice resolution for binary cases; loop closure with status update + push notification + persistent activity log entry to the originating tech; auditability of both originator and resolver.

Reference instance: Pass 4 Tier 1 #1 (owner-side mobile-conflict resolution). Future Phase 2 surfaces inheriting: tech-submitted time-off requests, tech-flagged safety incidents, tech-requested catalog item additions, tech-flagged customer issues, tech-requested expense limit overrides.

Distinct from the read-only "mobile owner status row + deep-link" pattern — this is full round-trip (mobile creates, web resolves, mobile reflects).

**Background Sync Execution Pattern**

When a mobile queue requires execution outside of foreground app sessions, the platform uses an asymmetric implementation strategy with a uniform user experience. Primary trigger is server-initiated push (silent push on iOS, high-priority FCM on Android), rate-limited per device with a tenant-configurable interval. Fallback trigger is OS-scheduled opportunistic execution (BGAppRefreshTask on iOS, WorkManager periodic on Android) when push delivery is delayed or throttled. Execution scope is lightweight operations only — heavy operations (photos, voice audio, periodic data refresh) remain foreground-only unless explicitly upgraded. Conflict handling: auto-resolves only in background; anything requiring user judgment defers to foreground. Failure visibility: every background run reports outcome to a tech-visible "last attempt" indicator on next app open; persistent failures (>3 consecutive) trigger a foreground notification.

Reference instance: Pass 4 Tier 1 #3 (background sync for mobile data queue). Future Phase 2 surfaces inheriting: periodic data refresh, background photo upload (if upgraded from foreground), tech-to-tech messaging delivery.

**In-Flight Sync Indicator with Pending Count**

A sync surface (calendar, QuickBooks, mobile, background) renders its current state plus a count of pending operations. Five compositional states cover synced-idle, synced-with-pending, syncing-active, sync-error, sync-paused. Hover/tap surfaces individual pending items as ambient awareness (capped at 5 with "+N more"). Manual sync trigger inline for owner-initiated immediate sync where applicable. Tunable threshold (`tenant_sync_indicator_pending_amber_threshold`, default 5) shifts visual emphasis to amber when pending count is operationally meaningful. Real-time updates via SSE.

Reference instances: calendar sync, QuickBooks sync, mobile data sync, background sync. Future Phase 2 surfaces: any future bilateral-sync integration.
```

This adds 4 new pattern blocks plus the intro update. §4.1 grows from 11 patterns to 15 (8 original Pass 3 + 4 from Pass 4 Tier 1/1.5 + 4 new from this update).

---

## Edit 12 — Optional new section §4.x for Customer-Facing Public Surfaces

This is a substantial new pattern category from Tier 4 #13 that doesn't quite fit existing §4.1 because it's not "platform UX vocabulary" — it's a different kind of pattern (customer-facing rather than internal-user-facing).

Three options:
- **(a) Skip it** — the customer-facing scope is captured in §3.6, §3.10, and email-related rows in §3.7. No additional patterns section needed.
- **(b) Add a new §4.4 Customer-Facing Public Surface Patterns** — formalizes the patterns explicitly.
- **(c) Add the patterns into §4.1** as additional vocabulary entries.

I'd recommend **(a) skip it** for MVP. The patterns are documented adequately in the feature rows. Phase 2 may want to formalize them as the customer-facing surface area grows, but for now the cross-section coverage is sufficient.

If you want option (b), let me know and I'll provide the full block.

---

## Edit 13 — New §3.16 Help & Support domain

This is a brand new domain section for Tier 4 #14.

**Insert after §3.15** (around line 590):

```markdown
### 3.16 Help & Support

**Domain Purpose**: Provide AI-mediated, context-aware help that scales with Pilot's growth and reduces solo-founder support burden. Pilot's voice-first AI-first identity extends into help: users open help and have a chat-style conversation with AI that knows the product, retrieves relevant articles for grounding, and walks them through what they need.

**MVP Features**:

| Feature | Description |
| :--- | :--- |
| **AI-Mediated Help with RAG** | Users open help (from main nav, settings, or contextual "?" anchors throughout the app) and engage with AI in a chat-style interface. AI uses the same Llama 3.x infrastructure as voice intents (separate prompt + RAG context). RAG retrieval over markdown help corpus stored in S3, embedded into pgvector for semantic search. Top-K chunks retrieved at query time and injected into prompt as grounding context. |
| **Markdown Corpus in S3 with Frontmatter Metadata** | Help articles are markdown files in S3 with structured frontmatter (article_id, title, category, related_concepts, ui_surfaces, related_articles, last_updated, audience). Same files serve both AI retrieval and direct article reading. Audience filtering applied during retrieval (e.g., owner-only articles excluded for technician queries). MVP corpus targets ~60 articles across 12 categories. |
| **Three Help Entry Points** | Main navigation (persistent "?" icon in app shell — non-contextual), settings sub-page (`Settings > Help & About`), and selective contextual "?" icons next to specific labels and concepts on complex surfaces (sync conflicts, MFA enrollment, voice intents, etc.). Contextual entry passes minimal context payload (route, entity type if applicable, recent action types, role, tenant metadata) to AI for grounded responses. |
| **Web Side-Drawer Chat / Mobile Full-Screen Chat** | Help chat panel is a slide-out drawer from right edge of viewport on web (400px wide; doesn't block main app); full-screen view on mobile. Chat history scrolls; latest message at bottom. Composition zone at bottom with voice mic + text input + send. AI messages have AI avatar; user messages have user avatar. Suggested follow-up action buttons within AI messages (Read full article, Walk me through it, That answered it, Still confused). |
| **Voice Input + Voice-Only Mode** | Voice button in chat composition initiates Whisper capture; transcribed text appears in input field for editing before send. Voice readback of AI responses available via "🔊 Listen" icon (uses user's effective voice persona tone). Voice intent grammar extends with `open_help` and `ask_help_question` intents — user can interact with help entirely via voice. |
| **AI Knowledge Boundaries** | AI is scoped to "how to use Pilot" knowledge plus surface context. Explicitly does NOT take actions on user's behalf, does NOT access tenant-specific data, does NOT provide financial/legal/compliance advice, does NOT make product roadmap commitments, does NOT operate outside Pilot domain. Three escalation triggers route stuck users to feedback submission: explicit user request for human help, low AI confidence after 3 turns, question outside scope. |
| **Past Conversations Recall** | Users can review prior help sessions with AI-generated brief titles. Within-session continuity preserved across surface navigation. Cross-session reset on full close or sign-out. Per-device isolation (no cross-device sync in MVP). |
| **Chat Session Capture for Training Data** | Sessions captured by default with anonymization at training-pipeline stage. Three-tier retention: active session (until close), recent unscrubbed (90 days for debugging + history recall + training source), permanent training corpus (anonymized). Anonymization pipeline runs at 90-day boundary: PII detection (emails, phones, names, business names, addresses, IDs) + tenant-identifying data scrubbing. User-facing transparency: "Pilot uses help conversations to improve our help content. Personal information is removed before use." |
| **Selective Contextual Help Anchors** | "?" icons placed at specific complex surfaces: settings (sync auto-expiry, sync direction, notification preferences with forced-minimum, background sync, voice persona, SMS quota cap, margin buckets, tax configuration), feature surfaces (MFA methods, field issues queue severity, calendar/QuickBooks conflict resolution, quote approval, onboarding tax setup). Selective placement keeps content authoring scope manageable. |
| **About / Version / Legal Surface** | At `Settings > Help & About > About`: Pilot logo, web version, mobile version (build), API version, support contact info, three quick paths to help (chat, feedback, support email), legal links (ToS, Privacy, EULA, OSS licenses), copyright notice. Mobile renders same content in vertical stack. |
| **Structured Feedback Submission** | At `Settings > Help & About > Send feedback`. Required category (Bug report / Feature request / Question / General feedback) + required text (5000 char max) + auto-filled reply-to email. Submission creates email to support inbox with subject prefix `[Pilot Feedback - {Category}]`, full feedback body + tenant info + user role + timestamp, reply-to user's email. Confirmation page after submit. From-help-chat escalation pre-fills category as "Question" and conversation context. |
| **Email Intake for Feedback (MVP); Ticket System Phase 2** | Feedback submissions go via email to `support@pilotfortrades.com` (configurable). Solo founder operational reality — the inbox is the support channel for the foreseeable future. Phase 2 introduces a ticket system when volume justifies the infrastructure overhead. |
| **Diagnostic Data Attachment for Bug Reports (Phase 2)** | Currently feedback is text-only. Phase 2 will add opt-in diagnostic data attachment for bug reports: recent actions, browser info, error logs, screenshots. MVP relies on user's free-text description; Tom replies via email asking for more info if unclear. |
```

This is the full §3.16 section. 13 features.

Don't forget to update the TOC entry per Edit 2.

---

## Edit 14 — Update §6 MVP Success Criteria for Pass 4 outcomes

**Find** §6.1 MVP Success Criteria section (line 760–784).

This section may need a small update reflecting Pass 4 outcomes — not strictly required but recommended for accuracy. Without seeing the current state I can't give specific paste-ready blocks, but the kinds of additions worth considering:

- "Tenant signup wizard completion rate ≥ 80% of started signups" (onboarding metric)
- "MFA enrollment rate among multi-user tenants ≥ 60% within 30 days of signup" (security adoption metric)
- "Help chat session resolution rate ≥ 70% of user queries answered without escalation to feedback" (help system effectiveness metric)

These are illustrative — Tom should set actual targets based on competitive benchmarks and product intuition. If the success criteria section is generally aspirational rather than measurable, no update is strictly required at Pass 4 close.

---

## Verification checklist after edits

- [ ] Version history bumped with v3.1 final row (Edit 1)
- [ ] TOC includes new §3.16 entry (Edit 2)
- [ ] §3.5 placeholder rows replaced and 13 new identity/onboarding rows added (Edit 3)
- [ ] §3.6 has 5 new invoicing/payment rows (Edit 4)
- [ ] §3.7 has 7 new notification preference center rows (Edit 5)
- [ ] §3.9 conflict row updated (no longer "deferred to Pass 4") + 3 new rows (Edit 6)
- [ ] §3.10 has 5 new customer-facing public quote rows (Edit 7)
- [ ] §3.11 has 9 new subscription tier rows (Edit 8)
- [ ] §3.13 voice persona row updated to MVP scope + 3 new help-related rows (Edit 9)
- [ ] §3.15 owner escalation row updated + sync triggers row updated + 2 new rows (Edit 10)
- [ ] §4.1 intro paragraph updated + 4 new pattern blocks added (Edit 11)
- [ ] §3.16 Help & Support new section inserted (Edit 13)
- [ ] §6 success criteria optional review (Edit 14)

After applying, the PRD reads as the comprehensive Pass 4 close artifact. Approximate growth: from 822 lines to ~1100–1150 lines.

---

## Items I want to flag as "decided in chat but not formally settled in design specs"

A few items came up in our chat conversations during Pass 4 that are reflected in the audit above but worth surfacing explicitly so you're aware they made it into the PRD updates:

1. **Operator role with hidden Pilot routes** (mentioned during Tier 3 #10 scoping; per-tenant trial length override, tier override, etc.) — captured as a §3.5 row in Edit 3 and as an operator-controlled feature in §3.11
2. **Customer phone is opt-in for SMS notifications/MFA only** — captured in §3.5 wizard step 3 description in Edit 3
3. **Tenant Telnyx number separate from owner's personal phone** — already captured in §3.7 from earlier; reinforced in Edit 3
4. **Stripe Connect deferred to Phase 2** — single Stripe account model for MVP — captured in §3.11 Edit 8 and §3.6 Edit 4
5. **Trial-as-tier framing eliminating special-case branching** — captured as a feature row in §3.11 Edit 8
6. **Three-question mobile inclusion rule from Settings IA** — captured implicitly in feature descriptions referencing "tenant-level edit on web; mobile read-only or per-user override based on inclusion criteria"
7. **Email branding is structured customization, not full template editing** — captured in Edit 4 (§3.6) and would also benefit from a feature row in §3.7

I missed adding a §3.7 row specifically for email branding in Edit 5. Adding here as Edit 5b:

**Edit 5b — Add to §3.7 (after the rows in Edit 5)**:

```markdown
| **Tenant Email Branding (Structured Customization)** | At `Settings > Communications > Email branding`, tenants customize their customer-facing email branding: logo upload, brand color picker, signature text, optional custom footer text. Live preview + test-send-to-my-address. Customer-facing emails (quote sent, invoice sent, payment received, etc.) render with tenant branding; internal emails (welcome, password reset, MFA reset, etc.) use Pilot standard branding. Full template editing deferred to Phase 2. |
| **16 Transactional Email Templates** | MVP ships with 16 transactional email templates organized by category: welcome, email verification code, quote sent, quote accepted, quote declined, quote expiring, invoice sent, payment received (tenant + customer receipt), payment failed, subscription renewal, subscription payment failed, trial expiring soon, trial expired, password reset, MFA reset by owner, data export ready. Single consistent template framework with per-template content slots. Variable substitution (customer name, quote total, signed URL, etc.) at render time. Content authoring is Tom-owned pre-launch hygiene work. |
```

---

## Next doc recommendation

After applying these PRD edits, the natural next doc is `mvp-arch.md` — the heaviest of the three remaining audits. It will need:

- New §17 SMS Infrastructure chapter (per the v4.2 patches we did)
- New §18 (or extension) for Customer-Facing Public Surfaces
- New §19 (or extension) for Help System Architecture
- New §20 (or extension) for Subscription Tier + Stripe Integration Architecture
- §16 patterns updated with all 7 new Pass 4 platform patterns
- §16.5 settings list extended
- Cost analysis updates

Estimated 600–800 lines of arch doc additions. After that, the framework doc rewrite is the smallest remaining task.

Upload `mvp-arch.md` whenever you're ready to start that audit.
