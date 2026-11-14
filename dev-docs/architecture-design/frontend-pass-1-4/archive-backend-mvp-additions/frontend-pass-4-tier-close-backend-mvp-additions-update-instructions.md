# Backend MVP Additions — Audit Report and Update Instructions

**Date**: April 30, 2026
**Audited file**: `frontend-backend-mvp-additions-latest.md` (your current uploaded version)
**Audit scope**: Verify completeness against all 13 Pass 4 spec docs + Tier 1.5 + Settings IA framework + Pass 1–3 baseline

---

## Audit summary — the good news first

Your file is in **excellent shape**. The audit found:

- ✅ All 87 additions present (A2–A88), contiguous, no gaps
- ✅ TOC entries present and correctly anchored for all additions
- ✅ All 87 effort estimates present in the Rough Effort Estimate table
- ✅ Subtotal arithmetic correct (259–334.5 days matches my running calculation)
- ✅ A67 includes the per-user resolution amendment we made (good catch on remembering that update)
- ✅ Section headers correctly group by Pass/Tier
- ✅ Audit log capture references and other cross-cutting patterns appear consistently

The structural integrity is solid. What's missing is content in the **two summary tables** (Tenant Settings + RBAC Permissions) — both still scoped to "Pass 2 + Pass 3" without Pass 4 additions. Plus a few small bookkeeping items (status tracker, version header, section-header naming).

**Total estimated edit time: 15–25 minutes.**

---

## Edit 1 — Status tracker (line 135–147)

Three Pass 4 phases are missing from the status tracker.

**Find** the existing status tracker block (lines 135–147). The last three lines currently read:

```markdown
- Pass 4 Tier 1 additions (A47–A51): this update
- Pass 4 Tier 2 #4 additions (A52–A55): this update
- Pass 4 Tier 1.5 additions (A59–A66): this update
```

**Replace those last three lines with**:

```markdown
- Pass 4 Tier 1 additions (A47–A51): documented in this file
- Pass 4 Tier 2 #4 additions (A52–A55): documented in this file
- Pass 4 Tier 2 #5 additions (A56–A58): documented in this file
- Pass 4 Tier 1.5 additions (A59–A66): documented in this file
- Pass 4 Tier 2 #6 additions (A67): documented in this file
- Pass 4 Tier 2 #7 additions (A68–A71): documented in this file
- Pass 4 Tier 3 #8/#9 additions (A72): documented in this file
- Pass 4 Tier 3 #10/#11 additions (A73–A78): documented in this file
- Pass 4 Tier 4 #12 additions (A79): documented in this file
- Pass 4 Tier 4 #13 additions (A80–A83): documented in this file
- Pass 4 Tier 4 #14 additions (A84–A88): documented in this file
- **Pass 4 design phase complete: 87 cumulative additions A1–A88**
```

I also changed "this update" to "documented in this file" for consistency with how Pass 3 entries read — since this file is now consolidated, every entry is documented in the file.

---

## Edit 2 — Version header bump (line 4–5)

**Find** (line 4–5):

```markdown
**Version**: 5.2 (extended through Pass 4 Tier 1.5 Flow 4 complete and Tier 2 Flow 5 complete; Tier 2 #6 next)
**Last Updated**: April 29, 2026 (Pass 4 Tier 2 #5 additions (A56–A58), Tier 1.5 additions (A59-A66): this update)
```

**Replace with**:

```markdown
**Version**: 6 (Pass 4 design phase complete — A1–A88 cumulative; consolidates all interim versions v5.x; ready as backend implementation source of truth)
**Last Updated**: April 30, 2026 (Pass 4 close: all 14 surfaces + Tier 1.5 + Settings IA framework locked)
```

This bumps to v6 per the framework doc's planned versioning at Pass 4 close.

---

## Edit 3 — Section header naming corrections in TOC and body

A few of your section headers don't match the framework's tier/surface conventions. These are minor but worth fixing for traceability.

### Body fix #1 (around line 2044)

**Find**:

```markdown
## Additions from Pass 4 Tier 2 (Flow 6 Calendar Conflict Resolution)
```

This is wrong on two counts: (a) it says "Flow 6" but A67 is voice persona tone (Tier 2 #6, not Flow 6 calendar conflict), and (b) calendar conflict was Pass 3 Flow 6, not Pass 4. **Replace with**:

```markdown
## Additions from Pass 4 Tier 2 #6 (Voice Persona Tone)
```

### Body fix #2 (around line 2045 area where A68 starts)

**Find**:

```markdown
## Additions from Pass 4 Tier 2 (Flow 7 Account Settings)
```

The "Flow 7" framing is misleading — Flow 7 was Pass 3 (Offline-to-Online Sync). A68–A71 are Tier 2 #7 (Account Settings). **Replace with**:

```markdown
## Additions from Pass 4 Tier 2 #7 (Account Settings)
```

### Body fix #3 (around line 2204 area where A72 starts)

Find the section header for A72 (it's in the TOC at line 102):

```markdown
## Additions from Pass 4 Tier 3 (Flow 8 & 9 States Catalog + First-Time-User States)
```

**Replace with**:

```markdown
## Additions from Pass 4 Tier 3 #8 + #9 (States Catalog + First-Time-User States)
```

### Body fix #4 (around line 2226 area where A73 starts)

```markdown
## Additions from Pass 4 Tier 3 (Flow 10 + 11 Onboarding and Push Permissions)
```

**Replace with**:

```markdown
## Additions from Pass 4 Tier 3 #10 + #11 (Onboarding Flow and Mobile Push Permission)
```

### Body fix #5 (around line 2446 area where A79 starts)

```markdown
## Additions from Pass 4 Tier 3 (Flow 12 In Flight Sync Indicator)
```

This is wrong — Tier 4 #12, not Tier 3. **Replace with**:

```markdown
## Additions from Pass 4 Tier 4 #12 (In-Flight Sync Indicator with Pending Count)
```

### Body fix #6 (around line 2499 area where A80 starts)

```markdown
## Additions from Pass 4 Tier 4 (Flow 13 Customer Facing Public Link Styling)
```

**Replace with**:

```markdown
## Additions from Pass 4 Tier 4 #13 (Customer-Facing Public Quote/Invoice Link Styling)
```

### Body fix #7 (around line 2669 area where A84 starts)

```markdown
## Additions from Pass 4 Tier 4 (Flow 14 Help, About and Feedback)
```

**Replace with**:

```markdown
## Additions from Pass 4 Tier 4 #14 (Help / About / Feedback Surfaces)
```

### TOC anchor updates

The TOC anchors (lines 95–123) need to match the renamed headers. Find each TOC entry and update the anchor link to match the new header naming. For example:

```markdown
  - [Additions from Pass 4 Tier 2 (Flow 6 Calendar Conflict Resolution)](#additions-from-pass-4-tier-2-flow-6-calendar-conflict-resolution)
```

**Becomes**:

```markdown
  - [Additions from Pass 4 Tier 2 #6 (Voice Persona Tone)](#additions-from-pass-4-tier-2-6-voice-persona-tone)
```

The pattern: the anchor is the lowercased header with `#` chars replaced by hyphens, spaces replaced with hyphens, and special chars stripped per Markdown's anchor convention.

For all 7 TOC entries that need anchor updates, the safest approach is: render the doc in a Markdown viewer after the body fixes, then click each TOC link to verify it scrolls to the right section. If any are broken, the anchor format is the issue.

---

## Edit 4 — Summary of New Tenant Settings table (line 1413)

**This is the biggest content gap in your file.** The summary table only covers Pass 2 + Pass 3 (14 settings). Pass 4 added 16+ more.

**Locate** the section header at line 1413: `## Summary of New Tenant Settings (Pass 2 + Pass 3)`.

**Replace the entire section** (header + table, lines 1413–1430) with this expanded version:

```markdown
## Summary of New Tenant Settings (Pass 2 + Pass 3 + Pass 4)

| Setting | Default | Purpose | Source |
| :--- | :--- | :--- | :--- |
| `require_approval_for_tech_quotes` | ON (multi-user), OFF (solo) | Quote approval workflow | A2 |
| `max_discount_pct_owner` | 15% | Margin cap for owner-applied discounts | A3 |
| `voice_persona_tone` | `balanced` | AI personality tone (enum: conservative \| balanced \| playful); per-user override allowed | A13 / A67 |
| `voice_persona_tone_user_override_allowed` | TRUE | Whether per-user override of voice persona is allowed (tenant policy) | A67 |
| `report_chart_threshold` | 8 | Min jobs to render charts vs table in reports | A15 |
| `etc_variance_note_required_pct` | 10% | ETC override note required when increase exceeds this | A14/A16 |
| `etc_variance_owner_notify_pct` | 50% | Owner notified when projected exceeds quote by this | A16 |
| `margin_bucket_boundaries` | `[10, 20, 30]` | Bucket boundaries for profitability charts | A17 |
| `margin_target_pct` | 20% | Target margin for below-target indicators | A17 |
| `tech_color_palette` | 12-hue system default | Custom color palette for tech identity | A18 |
| `calendar_conflict_auto_expire_days` | system default (30); nullable to disable | Days before unresolved calendar sync conflict auto-resolves to Pilot version | A34 |
| `calendar_conflict_pre_warning_days` | system default (7); nullable to disable | Days before calendar auto-expiry to send pre-warning notification | A34 |
| `photo_upload_wifi_only` | TRUE | Restrict photo uploads to WiFi connections | A41 |
| `photo_local_retention_days` | 7 | How long synced photos remain on device before auto-purge | A41 |
| `offline_hard_limit_hours` | 72 (nullable for unlimited) | Hours of offline operation before app blocks new captures | Flow 7 D13 |
| `voice_offline_audio_storage_limit_mb` | 500 | Max on-device storage for offline-captured voice audio | A42 / Tier 2 #4 |
| **Pass 4 Tier 1 / Tier 1.5 / Tier 2 / Tier 4 additions below** | | | |
| `qb_auto_expire_customer_enabled` | FALSE | Per-entity QB auto-expiry opt-in for customer conflicts | A50 |
| `qb_auto_expire_customer_direction` | (set when enabled) | `accept_local \| accept_remote` for customer auto-expiry direction | A50 |
| `qb_auto_expire_quote_enabled` | FALSE | Per-entity QB auto-expiry opt-in for quote conflicts | A50 |
| `qb_auto_expire_quote_direction` | (set when enabled) | `accept_local \| accept_remote` for quote auto-expiry direction | A50 |
| `qb_auto_expire_invoice_enabled` | FALSE | Per-entity QB auto-expiry opt-in for invoice conflicts | A50 |
| `qb_auto_expire_invoice_direction` | (set when enabled) | `accept_local \| accept_remote` for invoice auto-expiry direction | A50 |
| `qb_auto_expire_expense_enabled` | FALSE | Per-entity QB auto-expiry opt-in for expense conflicts | A50 |
| `qb_auto_expire_expense_direction` | (set when enabled) | `accept_local \| accept_remote` for expense auto-expiry direction | A50 |
| `qb_auto_expire_days` | system default (60); nullable to disable | Days before unresolved QB sync conflict auto-resolves | A50 |
| `qb_pre_warning_days` | system default (14); nullable to disable | Days before QB auto-expiry to send pre-warning notification | A50 |
| `qb_sync_preference_customer` | `user_choice` | Default master direction for customer sync conflicts | A50 / §5.3 |
| `qb_sync_preference_expense` | `user_choice` | Default master direction for expense sync conflicts | A50 / §5.3 |
| `background_sync_enabled` | TRUE (user override allowed) | Master toggle for mobile background sync | A51 |
| `background_sync_wifi_only` | FALSE | Restrict background sync to WiFi connections | A51 |
| `background_sync_battery_floor_pct` | 20 (range 5–50) | Battery percentage below which background sync is skipped | A51 |
| `background_sync_push_interval_minutes` | 5 (range 1–60); system default + tenant override | Min interval between server-initiated silent push triggers | A51 |
| `sms_quota_cap_policy` | `soft` | SMS quota cap behavior: soft (overage billing) or hard (block at limit) | A65 |
| `tenant_mfa_required` | FALSE | Whether MFA is required for all tenant users | A68 |
| `tenant_mfa_required_grace_period_starts_at` | NULL | Timestamp when MFA-required policy was enabled (drives 7-day grace window) | A68 |
| `tenant_mfa_grace_period_days` | 7 | Length of grace window for MFA enrollment after policy enabled | A68 |
| `tenant_sync_indicator_pending_amber_threshold` | 5 (range 1–100); system default + tenant override | Pending count above which sync indicator shifts to amber visual emphasis | A79 |
| `tenant_email_branding.logo_s3_path` | NULL | Tenant logo for customer-facing email branding | A82 |
| `tenant_email_branding.brand_color_hex` | NULL (defaults to Pilot brand-indigo) | Brand color for customer-facing email accents | A82 |
| `tenant_email_branding.email_signature` | NULL | Multi-line tenant signature appended to customer-facing emails | A82 |
| `tenant_email_branding.custom_footer` | NULL | Optional custom footer text (e.g., license numbers) | A82 |

**Pass 4 close adds 28 new tenant settings** to the inventory, bringing the total Pass 1–4 tenant settings to approximately 44.

**Operator-controlled overrides** (Pilot operator only — managed via DB updates for MVP per Tier 3 #10 Cross-Domain D):

| Setting | Default | Purpose |
| :--- | :--- | :--- |
| `system_default_trial_length_days` | 14 (or per Tom's choice) | System-wide default trial length |
| `tenant_tier_override.override_trial_length_days` | NULL | Per-tenant override of trial length |
| `tenant_tier_override.override_tier_id` | NULL | Force a specific subscription tier without payment |
| `tenant_tier_override.override_reason` | NULL | Operator note for the override |
```

This expanded table now includes all Pass 4 settings with their default values, purposes, and source addition references.

---

## Edit 5 — Summary of New RBAC Permissions table (line 1432)

Same problem as Edit 4 — the RBAC summary covers only Pass 2 + Pass 3.

**Locate** the section header at line 1432: `## Summary of New RBAC Permissions (Pass 2 + Pass 3)`.

**Replace the entire section** with this expanded version:

```markdown
## Summary of New RBAC Permissions (Pass 2 + Pass 3 + Pass 4)

| Permission | Roles | Purpose | Source |
| :--- | :--- | :--- | :--- |
| `quote.submit_for_approval` | technician | Submit tech-created quote for owner review | A2 |
| `quote.approve` | owner, accountant | Approve or reject pending quotes | A2 |
| `quote.apply_discount` | owner, accountant | Apply time-limited discounts within margin cap | A3 |
| `voice.provide_feedback` | owner, accountant | Flag voice misrecognitions, provide corrections | A6 |
| `schedule.manage` | owner, accountant | Dispatch, assignments (implemented in Pass 2) | A1 |
| `schedule.view_own` | technician | View own assigned schedule (implemented in Pass 2) | A1 |
| `voice.manage_own_sessions` | all | Rename, delete, open own conversation sessions | A10 |
| `quote_template.create` | owner, accountant | Save quote as template, create new tenant templates from scratch | A27 |
| `quote_template.edit` | owner, accountant | Edit existing tenant templates | A25 |
| `quote_template.fork_system` | owner, accountant | Fork system templates to tenant ownership | A25 |
| **Pass 4 additions below** | | | |
| `field_issue.view` | owner, accountant | View mobile-conflict escalation queue | A47 |
| `field_issue.resolve` | owner, accountant | Resolve mobile-conflict escalations | A48 |
| `qb_conflict.view` | owner, accountant | View QuickBooks sync conflict queue | A49 |
| `qb_conflict.resolve` | owner, accountant | Resolve QuickBooks sync conflicts | A50 |
| `notification_preference.tenant_default.edit` | owner | Set tenant-level notification defaults | A57 |
| `notification_preference.user_override.edit` | all | Edit own notification preferences within tenant policy | A57 |
| `voice_persona_tone.tenant_default.edit` | owner | Set tenant-level voice persona tone default | A67 |
| `voice_persona_tone.user_override.edit` | all (when allowed by tenant policy) | Edit own voice persona tone | A67 |
| `voice_persona_tone.user_override_policy.edit` | owner | Toggle whether per-user override is allowed | A67 |
| `mfa.enroll_self` | all | Enroll own MFA methods | A69 |
| `mfa.reset_self` | all | Reset own MFA methods (with password re-verification) | A69 |
| `mfa.reset_user` | owner | Reset another user's MFA methods (support escape hatch) | A69 |
| `mfa.policy.edit` | owner | Enable or disable tenant-required MFA policy | A68 |
| `account.session.revoke_own` | all | Revoke own active sessions | A70 |
| `account.data_export.request` | all | Request data export of own accessible scope | A71 |
| `subscription.view` | owner, accountant | View subscription tier, usage, and billing | A75 |
| `subscription.tier.change` | owner | Change subscription tier (initiates Stripe flow) | A76 |
| `legal_acceptance.accept` | (auto on signup) | Accept ToS/Privacy/EULA at tenant creation | A74 |
| `tenant.signup.complete` | (auto during signup) | Complete tenant onboarding wizard | A73 |
| `onboarding_checklist.skip_item` | owner, accountant | Skip individual onboarding checklist items | A77 |
| `onboarding_checklist.dismiss` | owner, accountant | Dismiss the post-wizard checklist permanently | A77 |
| `mobile_push_permission.update` | all (own device) | Update push permission state for own mobile device | A78 |
| `email_branding.edit` | owner, accountant | Customize tenant email branding (logo, color, signature) | A82 |
| `public_link.revoke` | owner, accountant | Manually revoke a customer-facing public link | A80 |
| `feedback.submit` | all | Submit feedback to support | A87 |
| `help_chat.delete_own_history` | all | Request deletion of own help chat history (Phase 2 surface; backend stub) | A88 |

**Operator role** (special platform-level role outside tenant RBAC; managed via hidden Pilot routes per Tier 3 #10 Cross-Domain D):

| Permission | Purpose |
| :--- | :--- |
| `operator.tenant.override_trial_length` | Set per-tenant trial length override |
| `operator.tenant.override_subscription_tier` | Force a tenant onto a specific subscription tier without payment |
| `operator.tenant.suspend` | Suspend a tenant's access (e.g., for non-payment, ToS violation) |
| `operator.tenant.delete` | Permanently delete a tenant and all associated data |
| `operator.help_content.edit` | (Phase 2) Admin UI for editing help corpus directly |
| `operator.email_template.edit` | (Phase 2) Admin UI for editing email templates directly |
| `operator.subscription_tier.create_or_edit` | Manage available subscription tiers |
| `operator.feature_flag.toggle` | Operator-level feature flag management |

**Pass 4 close adds 25 new tenant-RBAC permissions plus 8 operator-role permissions** to the inventory.
```

This expanded table now captures every permission introduced through Pass 4 with its role mapping, purpose, and source addition reference.

---

## Edit 6 — Footer reference update (line 2997)

The footer says the document is "regenerated at the end of each design pass" — true in spirit but slightly stale wording.

**Find** (line 2997):

```markdown
*This document is regenerated at the end of each design pass. See the corresponding design spec for the UI decisions that triggered each addition.*
```

**Replace with**:

```markdown
*This document is the consolidated Pass 4 close ledger. v6 is the design-phase frozen version; backend implementation should treat this as authoritative. See the corresponding design spec for the UI decisions that triggered each addition. Future ledger updates will track implementation progress and any post-launch additions.*
```

This reframes the doc from "running design log" to "frozen implementation backlog" which is its actual role at Pass 4 close.

---

## Edit 7 — Optional: Add a "Pass 4 Close — What This Means for Implementation" section

This is optional but useful for future-you and for any backend dev (or AI agent) starting work. Insert after the Overview section (after line 149, before "MVP Additions Already Implemented").

```markdown
---

## Pass 4 Close — What This Means for Implementation

As of April 30, 2026, the Pass 4 design phase is complete. All 14 design surfaces plus the Tier 1.5 customer comms extension plus the Settings IA framework are locked. This ledger covers the cumulative backend work A1–A88.

**For backend implementation starting now:**

1. **A1 is already done** (Scheduling & Dispatch implementation completed 4-24-2026). All other additions are pending.

2. **A2–A55 are safe to start in parallel** as Pass 4 design has no further changes affecting these. Patterns from arch doc §16 are stable.

3. **A56–A88 are also safe to start** but reference patterns and infrastructure from prior additions — recommend implementing roughly in numbered order to avoid forward dependencies.

4. **Heavy infrastructure additions to schedule first**:
   - A39 Idempotency UUIDs (foundation for many Pass 3 additions)
   - A40 Conflict Severity Classification (foundation for sync surfaces)
   - A53 Three-tier resolution chain (used by A67, A78, and others)
   - A75 Subscription tier infrastructure (used by A76, A65 quota, etc.)
   - A85 Markdown corpus + embedding pipeline (used by A84 help AI)

5. **External dependencies that block delivery** (non-engineering):
   - A2P 10DLC registration with Telnyx (4–6 weeks; blocks SMS deliverability)
   - Stripe account setup and webhook configuration
   - Domain registration (`pilotfortrades.com`, `pilot.tr` short-link domain if used)
   - SendGrid (or chosen email provider) sender domain setup with SPF/DKIM/DMARC
   - Legal copy authoring (ToS, Privacy, EULA) for A74 acceptance flow
   - Help content authoring (~60 articles) for A85 corpus

6. **Implementation phasing recommendation**:
   - **Wave 1** (foundational): A39, A40, A53, A52, A55 — patterns used everywhere
   - **Wave 2** (Pass 3 features): A2–A46 — bulk of MVP feature backlog
   - **Wave 3** (Pass 4 Tier 1): A47–A51, A59–A66 — conflict resolution surfaces and SMS
   - **Wave 4** (Pass 4 Tier 2/3): A56–A58, A67–A78 — settings, account, onboarding
   - **Wave 5** (Pass 4 Tier 4): A79–A88 — polish, customer-facing, help

Estimated total backend MVP work: **259–334.5 days**, or approximately **38–48 weeks** depending on team parallelism. Pre-launch hygiene (10DLC, content authoring, legal review) runs in parallel.

---
```

This gives any backend implementer a clean starting point for navigating the ledger as a work plan rather than as a chronological log.

---

## Verification checklist after edits

- [ ] Doc header version bumped to v6 with Pass 4 close framing (Edit 2)
- [ ] Status tracker updated with all Pass 4 phases (Edit 1)
- [ ] All 7 section headers in body renamed correctly (Edit 3 body fixes)
- [ ] All 7 corresponding TOC entries updated to match new headers (Edit 3 TOC)
- [ ] Tenant Settings summary table expanded to ~44 settings (Edit 4)
- [ ] RBAC Permissions summary table expanded with Pass 4 + operator permissions (Edit 5)
- [ ] Footer reference updated to Pass 4 close framing (Edit 6)
- [ ] Optional implementation phasing section added (Edit 7) — your call whether to include

After applying, the ledger reads cleanly as the consolidated Pass 4 close artifact. v6 is the design-frozen version that backend implementation works from.

---

## What I did NOT find missing — reassurance items

A few things you might worry about that are actually fine:

- **Cross-references between additions** (e.g., A48 references A35 for rate limiting; A86 references A53 for resolution chain) — all present and accurate.
- **Effort estimate per-addition** — every A2–A88 has its estimate inline within the addition body, and the same estimate appears in the bottom table. Numerically consistent.
- **Schema definitions** — every addition that introduces new tables has the schema spec. Consistent across additions.
- **API endpoint specs** — every addition that introduces APIs has the endpoint paths and request/response shapes.

The audit was thorough. Your file is in good shape; the gaps are summary-level, not content-level.

---

## Next doc recommendation

After you apply these edits to the backend ledger, I'd recommend tackling the canonical docs in this order:

1. **`mvp-prd.md`** — middle complexity. Several feature row additions across §3.5, §3.6, §3.7, §3.10, §3.11. Possibly a new §3.16 for help/feedback. Plus updating the cross-cutting platform UX patterns section.

2. **`mvp-arch.md`** — heaviest. Need to add 7 new §16 patterns (the existing 9 plus the 7 from Pass 4 = 16 total), plus new chapters for SMS infrastructure (§17), customer-facing public surfaces, help system architecture, subscription tier + Stripe integration architecture. Probably 400–600 lines of additions.

3. **`frontend-mvp-design-framework.md`** — full rewrite per the framework doc's own update model. Captures Pass 4 close state and pivots toward implementation phase. Smallest of the three.

I'd recommend doing PRD next because it's medium-effort and validates that Pass 4's design decisions made it into product requirements cleanly. Arch doc is the heaviest and benefits from being last so any patterns that need refining are already settled in the PRD.

Upload your current `mvp-prd.md` whenever you're ready and I'll start the audit.
