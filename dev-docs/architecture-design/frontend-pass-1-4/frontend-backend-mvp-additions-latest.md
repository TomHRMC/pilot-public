# Pilot for Trades — Backend MVP Additions

**Status**: Running list — updated as UI design progresses
**Version**: 6.2 (Phase 4.2 traceability remediation — A89–A94 added per findings FIND-055, FIND-056, FIND-063, FIND-076, FIND-078, FIND-083. A59 TCPA opt-out timestamp clarification added per FIND-141.)
**Last Updated**: May 15, 2026 (Phase 4.2 traceability remediation — new A89–A94 entries appended; see Phase 4.2 additions section)
**Purpose**: Track backend/database/API changes required by UI design decisions
**Handoff**: This document is the authoritative list of backend work required before UI coding begins

---

## Table of Contents

- [Pilot for Trades — Backend MVP Additions](#pilot-for-trades--backend-mvp-additions)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Cross-Check Update Notes (April 30, 2026)](#cross-check-update-notes-april-30-2026)
    - [MVP Additions Already Implemented](#mvp-additions-already-implemented)
  - [Pass 4 Close — What This Means for Implementation](#pass-4-close--what-this-means-for-implementation)
    - [A2. Quote Approval Workflow](#a2-quote-approval-workflow)
    - [A3. Time-Limited Discounts with Margin Cap](#a3-time-limited-discounts-with-margin-cap)
    - [A4. Templated Customer Communications](#a4-templated-customer-communications)
    - [A5. Reports Domain with Pin-to-Dashboard](#a5-reports-domain-with-pin-to-dashboard)
    - [A6. Voice AI Feedback Loop](#a6-voice-ai-feedback-loop)
    - [A7. Field Mode Support (Web App Infrastructure)](#a7-field-mode-support-web-app-infrastructure)
    - [A8. Communication History on Customer](#a8-communication-history-on-customer)
  - [Additions from Pass 3 Flow 1 (Voice Quote Creation)](#additions-from-pass-3-flow-1-voice-quote-creation)
    - [A9. Session Number Computation](#a9-session-number-computation)
    - [A10. Voice Command Grammar for Session Management](#a10-voice-command-grammar-for-session-management)
    - [A11. Ollama-Generated Session Titles](#a11-ollama-generated-session-titles)
    - [A12. Conversation Message Structured Content Payload with Live/Snapshot Modes](#a12-conversation-message-structured-content-payload-with-livesnapshot-modes)
    - [A13. Voice Persona Tone Configuration (Post-MVP — Captured for Roadmap)](#a13-voice-persona-tone-configuration-post-mvp--captured-for-roadmap)
  - [Additions from Pass 3 Flow 2 (Real-Time Job Profitability)](#additions-from-pass-3-flow-2-real-time-job-profitability)
    - [A14. ETC (Estimate to Complete) Capture System](#a14-etc-estimate-to-complete-capture-system)
    - [A15. Chart-or-Table Threshold Setting](#a15-chart-or-table-threshold-setting)
    - [A16. ETC Variance Notification System](#a16-etc-variance-notification-system)
    - [A17. Margin Bucket Configuration](#a17-margin-bucket-configuration)
  - [Additions from Pass 3 Flow 3 (Dispatch Board)](#additions-from-pass-3-flow-3-dispatch-board)
    - [A18. Tech Color Assignment \& Configuration](#a18-tech-color-assignment--configuration)
    - [A19. Dispatch Board API Endpoints (Optimistic Locking + Real-Time Updates)](#a19-dispatch-board-api-endpoints-optimistic-locking--real-time-updates)
    - [A20. Drive-Time Caching Verification](#a20-drive-time-caching-verification)
  - [Additions from Pass 3 Flow 4 (Customer Communications)](#additions-from-pass-3-flow-4-customer-communications)
    - [A21. Per-Message Channel Override](#a21-per-message-channel-override)
    - [A22. Voice Intent Grammar for Customer Communications](#a22-voice-intent-grammar-for-customer-communications)
    - [A23. Communication Preview Endpoint (Pre-Send Validation)](#a23-communication-preview-endpoint-pre-send-validation)
  - [Additions from Pass 3 Flow 5 Architectural Pre-Work (Quote Line Item Architecture)](#additions-from-pass-3-flow-5-architectural-pre-work-quote-line-item-architecture)
    - [A24. Quote Line Item Schema Extension (Visibility + Hierarchy)](#a24-quote-line-item-schema-extension-visibility--hierarchy)
    - [A25. Quote Template Schema with Style and Versioning](#a25-quote-template-schema-with-style-and-versioning)
    - [A26. System Template Update Notification Flow](#a26-system-template-update-notification-flow)
    - [A27. Save Quote as Template](#a27-save-quote-as-template)
    - [A28. Multi-Line Description Editing UI Support](#a28-multi-line-description-editing-ui-support)
  - [Additions from Pass 3 Flow 5 (Quote Approval Workflow)](#additions-from-pass-3-flow-5-quote-approval-workflow)
    - [A29. Pending Edit Storage During Owner Review](#a29-pending-edit-storage-during-owner-review)
    - [A30. Approval Comment \& Annotation System](#a30-approval-comment--annotation-system)
    - [A31. Voice Intent Grammar for Approval Actions](#a31-voice-intent-grammar-for-approval-actions)
  - [Additions from Pass 3 Flow 6 (Calendar Conflict Resolution)](#additions-from-pass-3-flow-6-calendar-conflict-resolution)
    - [A32. Calendar Conflict Diff Payload](#a32-calendar-conflict-diff-payload)
    - [A33. Pre-Resolution Staleness Check](#a33-pre-resolution-staleness-check)
    - [A34. Auto-Expiry of Stale Conflicts (System Default + Tenant Override)](#a34-auto-expiry-of-stale-conflicts-system-default--tenant-override)
    - [A35. Mobile Pending-Conflicts Status \& Notification Rate Limiting](#a35-mobile-pending-conflicts-status--notification-rate-limiting)
    - [A36. Voice Intent Grammar for Calendar Conflict Resolution](#a36-voice-intent-grammar-for-calendar-conflict-resolution)
  - [Additions from Pass 3 Flow 7 (Offline-to-Online Sync)](#additions-from-pass-3-flow-7-offline-to-online-sync)
    - [A37. Offline-Capable Operations API Contract](#a37-offline-capable-operations-api-contract)
    - [A38. Sync Queue State Model (Server-Side Visibility)](#a38-sync-queue-state-model-server-side-visibility)
    - [A39. Idempotency UUIDs for Offline Operations](#a39-idempotency-uuids-for-offline-operations)
    - [A40. Conflict Severity Classification Engine](#a40-conflict-severity-classification-engine)
    - [A41. Resumable Photo Upload Pipeline](#a41-resumable-photo-upload-pipeline)
    - [A42. Voice Command Offline Capture \& Deferred Processing](#a42-voice-command-offline-capture--deferred-processing)
    - [A43. Force-Quit Recovery State Persistence](#a43-force-quit-recovery-state-persistence)
    - [A44. Auth Expiry Offline Handling](#a44-auth-expiry-offline-handling)
    - [A45. Tech-Resolvable Conflict UI Endpoints](#a45-tech-resolvable-conflict-ui-endpoints)
    - [A46. Owner Escalation Routing \& Notification](#a46-owner-escalation-routing--notification)
  - [Summary of New Tenant Settings (Pass 2 + Pass 3 + Pass 4)](#summary-of-new-tenant-settings-pass-2--pass-3--pass-4)
  - [Summary of New RBAC Permissions (Pass 2 + Pass 3 + Pass 4)](#summary-of-new-rbac-permissions-pass-2--pass-3--pass-4)
  - [Additions from Pass 4 Tier 1 (Owner Mobile-Conflict UI, QuickBooks Conflict UI, Background Sync)](#additions-from-pass-4-tier-1-owner-mobile-conflict-ui-quickbooks-conflict-ui-background-sync)
    - [A47. Owner-Side Mobile-Conflict Escalation Queue Endpoints](#a47-owner-side-mobile-conflict-escalation-queue-endpoints)
    - [A48. Owner-Side Mobile-Conflict Resolution Write Path](#a48-owner-side-mobile-conflict-resolution-write-path)
    - [A49. QuickBooks Conflict Queue Endpoints + Schema Extension](#a49-quickbooks-conflict-queue-endpoints--schema-extension)
    - [A50. QuickBooks Conflict Resolution Write Path + Auto-Expiry Celery Extension](#a50-quickbooks-conflict-resolution-write-path--auto-expiry-celery-extension)
    - [A51. Background Sync Infrastructure](#a51-background-sync-infrastructure)
  - [Additions from Pass 4 Tier 2 #4 (Settings UIs for Configurable Thresholds)](#additions-from-pass-4-tier-2-4-settings-uis-for-configurable-thresholds)
    - [A52. Settings Catalog Endpoint](#a52-settings-catalog-endpoint)
    - [A53. Effective-Value Resolution Endpoint (Three-Tier Extension)](#a53-effective-value-resolution-endpoint-three-tier-extension)
    - [A54. Tenant Settings Write Endpoints](#a54-tenant-settings-write-endpoints)
    - [A55. Per-User Override Write Endpoints](#a55-per-user-override-write-endpoints)
    - [A56. Notification Category Registry](#a56-notification-category-registry)
    - [A57. Notification Preference Matrix Endpoints + In-App Banner Component](#a57-notification-preference-matrix-endpoints--in-app-banner-component)
    - [A58. Delivery Dispatcher Preference Gate](#a58-delivery-dispatcher-preference-gate)
  - [Additions from Pass 4 Tier 1.5 (Flow 4 Customer Communications Extension — Inbound SMS, Threading, Replies)](#additions-from-pass-4-tier-15-flow-4-customer-communications-extension--inbound-sms-threading-replies)
    - [A59. Telnyx Webhook Handler + Carrier-Agnostic Adapter Layer + TCPA Opt-In/Opt-Out Tracking](#a59-telnyx-webhook-handler--carrier-agnostic-adapter-layer--tcpa-opt-inopt-out-tracking)
    - [A60. Customer Communication Threading Schema and Routing](#a60-customer-communication-threading-schema-and-routing)
    - [A61. Telnyx Number Provisioning at First Use](#a61-telnyx-number-provisioning-at-first-use)
    - [A62. Free-Form Reply Composition Endpoints](#a62-free-form-reply-composition-endpoints)
    - [A63. Voice-to-Text Reply Integration](#a63-voice-to-text-reply-integration)
    - [A64. Owner Visibility Surfaces — Web Comm History Extension and Dashboard Widget](#a64-owner-visibility-surfaces--web-comm-history-extension-and-dashboard-widget)
    - [A65. SMS Quota Tracking and Cap Enforcement](#a65-sms-quota-tracking-and-cap-enforcement)
    - [A66. Mobile Inbox "Customer Messages" Sub-Section + Conversation Thread Screen](#a66-mobile-inbox-customer-messages-sub-section--conversation-thread-screen)
  - [Additions from Pass 4 Tier 2 #6 (Voice Persona Tone)](#additions-from-pass-4-tier-2-6-voice-persona-tone)
    - [A67. Voice Persona Tone Renderer + Preview Audio Generation + Per-User Resolution](#a67-voice-persona-tone-renderer--preview-audio-generation--per-user-resolution)
  - [Additions from Pass 4 Tier 2 #7 (Account Settings)](#additions-from-pass-4-tier-2-7-account-settings)
    - [A68. Tenant MFA Policy + Grace Period Enforcement](#a68-tenant-mfa-policy--grace-period-enforcement)
    - [A69. Multi-Method MFA Enrollment + Method Management + Recovery Codes](#a69-multi-method-mfa-enrollment--method-management--recovery-codes)
    - [A70. Active Sessions List + Revoke](#a70-active-sessions-list--revoke)
    - [A71. Data Export Request Pipeline](#a71-data-export-request-pipeline)
  - [Additions from Pass 4 Tier 3 #8 + #9 (States Catalog + First-Time-User States)](#additions-from-pass-4-tier-3-8--9-states-catalog--first-time-user-states)
    - [A72. First-Session Detection for First-Time-User States](#a72-first-session-detection-for-first-time-user-states)
  - [Additions from Pass 4 Tier 3 #10 + #11 (Onboarding Flow and Mobile Push Permission)](#additions-from-pass-4-tier-3-10--11-onboarding-flow-and-mobile-push-permission)
    - [A73. Trial State Machine + Tenant Signup](#a73-trial-state-machine--tenant-signup)
    - [A74. Legal Acceptance Recording](#a74-legal-acceptance-recording)
    - [A75. Subscription Tier Infrastructure](#a75-subscription-tier-infrastructure)
    - [A76. Stripe Integration for Paid Conversion](#a76-stripe-integration-for-paid-conversion)
    - [A77. Onboarding State Tracking + Checklist Resumability](#a77-onboarding-state-tracking--checklist-resumability)
    - [A78. Mobile Push Permission Tracking + Degraded-Mode Fallback](#a78-mobile-push-permission-tracking--degraded-mode-fallback)
  - [Additions from Pass 4 Tier 4 #12 (In-Flight Sync Indicator with Pending Count)](#additions-from-pass-4-tier-4-12-in-flight-sync-indicator-with-pending-count)
    - [A79. Unified Pending-Count Exposure for Sync Surfaces](#a79-unified-pending-count-exposure-for-sync-surfaces)
  - [Additions from Pass 4 Tier 4 #13 (Customer-Facing Public Quote/Invoice Link Styling)](#additions-from-pass-4-tier-4-13-customer-facing-public-quoteinvoice-link-styling)
    - [A80. Signed URL Infrastructure for Public Quote/Invoice Links](#a80-signed-url-infrastructure-for-public-quoteinvoice-links)
    - [A81. Stripe One-Time Payment for Invoices with Amount Variance](#a81-stripe-one-time-payment-for-invoices-with-amount-variance)
    - [A82. Email Template Rendering Pipeline + Tenant Brand Customization](#a82-email-template-rendering-pipeline--tenant-brand-customization)
    - [A83. Quote/Payment Customer Comment Storage with Notifications](#a83-quotepayment-customer-comment-storage-with-notifications)
  - [Additions from Pass 4 Tier 4 #14 (Help / About / Feedback Surfaces)](#additions-from-pass-4-tier-4-14-help--about--feedback-surfaces)
    - [A84. Help AI Agent + RAG + Chat Session Management](#a84-help-ai-agent--rag--chat-session-management)
    - [A85. Markdown Corpus + Embedding Pipeline + S3 Storage](#a85-markdown-corpus--embedding-pipeline--s3-storage)
    - [A86. Contextual Help Anchor Metadata + Opener Context Payload](#a86-contextual-help-anchor-metadata--opener-context-payload)
    - [A87. Feedback Submission Endpoint with Email Intake](#a87-feedback-submission-endpoint-with-email-intake)
    - [A88. Anonymization Pipeline for Training Data Capture](#a88-anonymization-pipeline-for-training-data-capture)
    - [A89. LOTO (Lock Out / Tag Out) Confirmation Table + Configurable Voice Guard](#a89-loto-lock-out--tag-out-confirmation-table--configurable-voice-guard)
    - [A90. Category-Specific Markup Management Endpoints](#a90-category-specific-markup-management-endpoints)
    - [A91. Labor Rate Version Management Endpoints + jobs.py Wiring](#a91-labor-rate-version-management-endpoints--jobspy-wiring)
    - [A92. Authenticated Invoice CRUD Endpoints + Router Cleanup](#a92-authenticated-invoice-crud-endpoints--router-cleanup)
    - [A93. Expo Push Delivery](#a93-expo-push-delivery)
    - [A94. Customer Communication Template Type Lookup Table](#a94-customer-communication-template-type-lookup-table)
    - [A95. Voice Command Entity Link Table](#a95-voice-command-entity-link-table)
    - [A96. Receipt OCR Pipeline (RapidOCR + Llama 3.1 8B)](#a96-receipt-ocr-pipeline-rapidocr--llama-31-8b)
  - [Rough Effort Estimate (Remaining MVP Additions)](#rough-effort-estimate-remaining-mvp-additions)


---

## Overview

As UI design progresses through Passes 2, 3, and 4, decisions surface that require backend changes beyond what's currently in `mvp-arch.md` and the PRD. This document captures those requirements in one place so the dev team has a single source of truth for MVP backend work.

**Workflow**: Each addition below is triggered by a specific design decision. When UI design is complete (end of Pass 4), this document is frozen and becomes the backend work plan. Tom completes backend MVP work before UI coding begins.

**Status tracker**:
- Pass 2 additions (A1–A8): previously documented; A1 Scheduling & Dispatch has since been implemented per `frontend-pass-2-sched-feat-plan.md`
- Pass 3 Flow 1 additions (A9–A13): documented in this file
- Pass 3 Flow 2 additions (A14–A17): documented in this file
- Pass 3 Flow 3 additions (A18–A20): documented in this file
- Pass 3 Flow 4 additions (A21–A23): documented in this file
- Pass 3 Flow 5 architectural pre-work (A24–A28): documented in this file — see also `quote-line-item-architecture.md`
- Pass 3 Flow 5 additions (A29–A31): documented in this file
- Pass 3 Flow 6 additions (A32–A36): documented in this file
- Pass 3 Flow 7 additions (A37–A46): documented in this file
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

---

## Cross-Check Update Notes (April 30, 2026)

A formal cross-check of `mvp-prd.md` v3.1 (final) and `mvp-arch.md` v5 against the backend additions A2–A88 was performed at Pass 4 close. The cross-check identified 12 findings, all addressed in this v6.1 update. Findings fall into three categories:

**Category 1 — Confirmed scope additions** (real new work added to existing additions; no net-new addition numbers):

- **A59 expanded** — TCPA SMS STOP keyword detection + opt-out handler + 5 new `customer` table columns (`sms_opted_out`, `sms_opt_out_at`, `sms_opt_in_consent`, `sms_opt_in_at`, `sms_opt_in_source`). **TCPA legal compliance gap; must be implemented before B11 is considered complete.**
- **A65 extended** — outbound block when `customer.sms_opted_out = TRUE` (`check_quota` returns blocked); ensures Pilot doesn't send SMS to opted-out customers.
- **A76 expanded** — `stripe_webhook_event_processed` dedup table + handler check before processing webhook events. **Stripe data integrity gap; gates correct payment recording.**
- **A70 + B13 integration note** — password change endpoint must call A70's `revoke-others` logic on success. Cross-device session invalidation per arch doc §4.8.1.

**Category 2 — Verification before implementing** (notes added to relevant batches; not new scope until verification confirms missing):

- **G1 (Receipt OCR)** — verify pre-existing pipeline before B3 starts; if missing, becomes A89.
- **G2 + G3 (Profile/Password endpoints)** — verify existing endpoints before B13 starts; existing endpoints likely sufficient with the A70 integration note above.
- **G4 (Tax Setup JIT 412 response)** — verify existing invoice endpoint returns 412 with structured payload when tax not configured; precondition check for tax setup.
- **G7 (Automated Dunning)** — verify pre-existing Celery task before B5 or B15 starts; if missing, add to relevant batch scope.
- **G9 (Schedule History per Job endpoint)** — verify dedicated `GET /api/v1/jobs/{job_id}/schedule-history` endpoint exists; if missing, add to B3 scope.

**Category 3 — Doc cleanup / scope clarification** (no new code; clarifies existing scope):

- **G8 (Trial Expiration Warning Sequence)** — A73 scope note clarifies the 4-step warning cadence (7d, 3d, 1d, 0d) per arch doc §4.7.5.
- **G10 (Calendar auto-expire mechanism)** — A34 scope note clarifies that arch doc §13.5 uses BOTH a separate `calendar_conflict_auto_expire_enabled` boolean AND nullable days integer; implementation must include both.
- **A6 (Arch doc §15.13 stale title)** — documentation-only fix; no code impact. Arch doc §15.13 title should be updated from "No Background Sync in MVP" to "Sync Triggers (Foreground + Background)" — implementation reference is §16.12, not §15.13.

**Pre-batch verification checklist** (run via postgres-local MCP before starting relevant batches):

1. **Before B3**: `SELECT routine_name FROM information_schema.routines WHERE routine_name LIKE '%receipt%' OR routine_name LIKE '%ocr%'` — resolves G1
2. **Before B3**: Check `api/routes/jobs.py` for schedule-history endpoint — resolves G9
3. **Before B5 or B15**: Check `tasks/` directory for dunning-related Celery task — resolves G7
4. **Before B11**: `SELECT column_name FROM information_schema.columns WHERE table_name = 'customer' AND column_name LIKE 'sms%'` — resolves G5/G6 (verifies which TCPA columns already exist; informs A59 migration scope)
5. **Before B13**: Check `api/routes/` directory for `profile.py`, `password.py`, or equivalent — resolves G2/G3
6. **Before B14**: Check existing invoice endpoint for 412 precondition response on missing tax setup — resolves G4

The cross-check report itself lives in: `pilot-app-prd-arch-cross-check-w-backend-adds.md` v2.0.

---

### MVP Additions Already Implemented

- **A1 Scheduling & Dispatch** — implemented per `frontend-pass-2-sched-feat-plan.md` (completed 4-24-2026)

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

### A2. Quote Approval Workflow

**Triggered by**: Quote approval workflow decision in Pass 2.

**Scope**:
- Quote state machine update: add `pending_approval` and `approved` states
  - Full state machine: `draft → pending_approval → approved → sent → accepted / declined / expired → converted`
  - When approval setting is OFF, tech-created quotes skip directly from `draft → sent`
- New tenant setting: `require_approval_for_tech_quotes`
  - Default ON for multi-user tenants, OFF for solo operators
  - Lives in `tenant_settings` or equivalent
- API endpoint: `POST /api/v1/quotes/{id}/submit-for-approval`
- API endpoint: `POST /api/v1/quotes/{id}/approve` (and `/reject`)
- Notification: push + email to owner when tech submits quote for approval
- Audit log: record approval/rejection with approver identity and any modifications

**Affected existing features**: quote version control (must handle approval modifications as new version), RBAC (tech role needs new `quote.submit_for_approval` permission; owner/accountant roles need `quote.approve`)

**Effort estimate**: Medium — 3–5 days.

---

### A3. Time-Limited Discounts with Margin Cap

**Triggered by**: Owner-only discount action in Pass 2 (mobile + web).

**Scope**:
- New tenant setting: `max_discount_pct_owner` (default 15%)
- New quote line item type: `discount_line` (or extend existing line items with `is_discount` flag)
  - Fields: `discount_pct`, `discount_amount_cents`, `discount_expires_at`
- Applies as new immutable quote version (leverages existing version control)
- Celery Beat task: transition discount to expired at `discount_expires_at`
- API validation: reject requests where `discount_pct > tenant.max_discount_pct_owner`
- API endpoint: `POST /api/v1/quotes/{id}/apply-discount`
- RBAC: `quote.apply_discount` permission — owner/admin only, not tech

**Effort estimate**: Small-Medium — 2–3 days.

---

### A4. Templated Customer Communications

**Triggered by**: Customer comms feature in Pass 2 (tech-to-customer messaging).

**Scope**:
- New database table: `customer_communication`
  - Fields: tenant_id, customer_id, job_id (nullable), sender_user_id, template_code, rendered_message, channel (sms/email), status, sent_at
  - Full audit trail per message sent
- New lookup table: `communication_template`
  - Fields: template_code, channel, subject (for email), body_template (with placeholders)
- Template variable substitution engine (ETA from route data, customer name, job number, etc.)
- API endpoint: `POST /api/v1/communications/send` with template_code and variables
- Voice intent handler: `send_customer_communication` — parses "Tell Johnson I'm 20 out" into template_code + variables
- Integration: uses existing `notification_outbox` for reliable dispatch
- Web route: `Customers > [customer] > Comm history` reads from this table

**MVP template set**:
- `on_my_way` — "On my way, ETA [eta]"
- `running_late` — "Running [minutes] min late"
- `arrived` — "Arrived, starting work"
- `job_complete` — "Job complete, invoice to follow"
- `parts_delay` — "Parts delay, will update when resolved"
- `confirm_appointment` — "Please confirm appointment [date/time]"

**Effort estimate**: Medium — 4–6 days.

---

### A5. Reports Domain with Pin-to-Dashboard

**Triggered by**: Reports promoted to top-level nav with dashboard customization in Pass 2.

**Scope**:
- New API endpoints per report type (all read-only aggregations):
  - `GET /api/v1/reports/profitability`
  - `GET /api/v1/reports/revenue`
  - `GET /api/v1/reports/ar-aging`
  - `GET /api/v1/reports/tech-productivity`
  - `GET /api/v1/reports/tax-liability`
  - `GET /api/v1/reports/voice-analytics`
- All reports support common query params: date_range, tenant_scope (auto), filter_by, group_by
- Dashboard customization:
  - New table: `user_dashboard_widget`
    - Fields: user_id, tenant_id, widget_type, widget_config_json, position_x, position_y, width, height
  - API: `GET/POST/PATCH/DELETE /api/v1/dashboard/widgets`
- Report caching: consider materialized views or Redis-cached aggregates for performance (not blocking; add if needed)

**Effort estimate**: Medium-Large — 5–7 days (individual reports are small; the mass of them adds up).

---

### A6. Voice AI Feedback Loop

**Triggered by**: Voice AI feedback mechanism decision in Pass 2.

**Scope**:
- New table: `voice_feedback`
  - Fields: tenant_id, user_id, transcript_id, original_transcription, corrected_text, intent_misparsed (boolean), feedback_notes
- API endpoint: `POST /api/v1/voice/feedback` — owner flags a transcript as misrecognized, provides correction
- API endpoint: `GET /api/v1/voice/transcripts` — searchable transcript history
- API endpoint: `GET /api/v1/voice/feedback` — list flagged items for training export
- Training data export: nightly Celery task writes corrected pairs to S3 in model fine-tuning format (format TBD based on training pipeline choice)
- RBAC: `voice.provide_feedback` permission — owner/admin only

**Strategic note**: This is the data pipeline for future Llama fine-tuning. Treat it as a first-class feature, not a debug tool. The data it captures creates a long-term moat.

**Effort estimate**: Medium — 3–4 days (excludes fine-tuning pipeline, which is Phase 2).

---

### A7. Field Mode Support (Web App Infrastructure)

**Triggered by**: Tablet strategy decision in Pass 2 — Field mode infrastructure in MVP.

**Scope**:
- New user preference: `field_mode_enabled` (boolean, defaults off for owner, on for technician on tablet viewport)
- Viewport detection: server-side via user agent + client-side viewport measurement
- Route-level RBAC enforcement: technician role + field mode = hide admin routes at API and UI layer
- API endpoint: `PATCH /api/v1/users/me/preferences` — toggle field_mode_enabled
- Backend validation: prevent tech + field mode from calling admin endpoints (belt-and-suspenders; UI already hides them)

**Note**: Most of this is frontend work. Backend scope is minimal — just the preference field and the route-level guards.

**Effort estimate**: Small — 1–2 days backend.

---

### A8. Communication History on Customer

**Triggered by**: Customer Comm history route under Customers section (Pass 2).

**Scope**: Mostly covered by A4 (communications table). This item is just the API endpoint to read the history by customer:
- `GET /api/v1/customers/{id}/communications` with pagination

**Effort estimate**: Trivial — half a day, folds into A4.

---

## Additions from Pass 3 Flow 1 (Voice Quote Creation)

### A9. Session Number Computation

**Triggered by**: Per-day-reset session numbering for voice addressability in the session history drawer.

**Scope**:
- Derived property (not a stored column). Computed via SQL window function at query time.
- Session number = `ROW_NUMBER() OVER (PARTITION BY DATE(created_at AT TIME ZONE tenant.timezone), user_id ORDER BY created_at ASC)`
- Tenant timezone must be honored — midnight rollover is local, not UTC
- API response: `GET /api/v1/voice/sessions` returns session number alongside each session record
- Voice addressability:
  - "Chat 2" → today's session #2 for current user
  - "Yesterday's chat 3" → day-scoped lookup
  - Missing reference → AI asks rather than guesses (see A10)

**Performance note**: for users with many sessions per day, consider materialized view or cached daily number if query becomes expensive at scale. Not a concern at MVP launch volume; flag for monitoring.

**Effort estimate**: Small — 1 day (query construction + test coverage).

---

### A10. Voice Command Grammar for Session Management

**Triggered by**: Voice-based session operations (rename, delete, open, query).

**Scope**:
- Additions to `voice_action_router.py` handler registry:
  - `rename_session` — updates `conversation_session.context_summary`
  - `delete_session` — soft-deletes a session (with confirm-as-turn flow)
  - `open_session` — switches the active session in the UI
  - `query_session_summary` — AI reads back a session's summary + recent messages
- Each handler validates the numeric reference against the per-day window (A9)
- Missing-reference path: handler returns a disambiguation response for the AI to voice, rather than executing on a guess
- Confirm-as-turn implementation for destructive actions: `delete_session` returns a pending-confirmation state in `context_window_json`; next user turn with affirmative intent commits, any other response cancels

**Intent → action mapping** (authoritative list for voice_action_router.py):

| Intent | Example | Target |
| :--- | :--- | :--- |
| `rename_session` | "rename chat 2 to Johnson panel" | `conversation_session.context_summary` |
| `delete_session` | "delete chat 4" | `conversation_session.is_active = FALSE` |
| `open_session` | "open chat 3" | UI state change (client-side) |
| `query_session_summary` | "what did I work on in chat 1?" | Read-only response |

**Effort estimate**: Small-Medium — 2–3 days (handler implementations + test coverage for each + disambiguation flows).

---

### A11. Ollama-Generated Session Titles

**Triggered by**: `conversation_session.context_summary` populated automatically after the first meaningful turn.

**Scope**:
- New Celery task: `generate_session_title` — enqueued after the first substantive assistant message in a session
- Calls Ollama with a prompt pattern like: "Summarize this brief conversation in 3-5 words, suitable as a scannable title in a chat history list. Conversation: [...]"
- Updates `conversation_session.context_summary` with the result
- Only fires once per session, and only if `context_summary` is still NULL (user-set titles take precedence)
- Fallback: if Ollama fails or times out, `context_summary` remains NULL; UI shows "Untitled session" with the first few words of the first user message as a soft fallback

**Configuration** (for future voice persona tone slider — see A13):
- Prompt template is a tenant-level config value (default conservative phrasing for MVP)
- Template variable placeholder: `{tone}` → currently hardcoded to "neutral, descriptive"

**Effort estimate**: Small — 1–2 days (Celery task + prompt engineering + tests).

---

### A12. Conversation Message Structured Content Payload with Live/Snapshot Modes

**Triggered by**: Inline rendering of structured artifacts (quote cards) as assistant messages within the conversation thread, plus historical accuracy requirements for completed sessions and cross-context quote viewing.

**Scope**:
- Extend `conversation_message` (schema decision left to dev team: add `structured_content JSONB` column OR leverage existing content_text with a type discriminator) to support structured assistant output
- Assistant turns can carry either plain text OR a structured payload:
  - `artifact_type` — e.g., `quote_preview`, `job_preview`, `schedule_preview`, `comm_preview`
  - `entity_id` — the referenced entity (e.g., quote.id)
  - `entity_version_id` — nullable; populated only for snapshot mode
  - `render_mode` — `live` | `snapshot`
  - `snapshot_payload` — nullable JSONB; populated only for snapshot mode, contains frozen entity state as of capture time
  - `render_hints` — UI hints like which line items are newly added (for visual differentiation)
- Mobile app renders based on `render_mode`:
  - `live` → fetch current entity state by `entity_id`
  - `snapshot` → render directly from `snapshot_payload`
- Plain text messages render as standard chat bubbles

**Live vs snapshot logic**:

| When created | Initial render_mode |
| :--- | :--- |
| New assistant turn during active authoring (pre-submission) | `live` |
| New assistant turn in a session where quote was already submitted | `snapshot` |

**Freeze triggers — two events only**:

1. **Submission** (primary trigger): when the user successfully executes Submit for approval (tech) or Send (owner) on a quote, a synchronous freeze operation runs before the API call returns. This iterates all quote_preview messages in the session with `render_mode = 'live'`, captures the final submitted `quote_version` state as `snapshot_payload`, and flips `render_mode` to `snapshot`. The user is returned to the home screen only after the freeze is complete. No Celery task — synchronous for consistency (the freeze must be visible before the user can navigate away and return).

2. **New artifact turn during active authoring** (secondary trigger): when the assistant emits a new quote_preview turn (e.g., after "add five breakers"), the prior quote_preview messages in the same session freeze to `snapshot` at that moment, capturing their state as of that moment. Only the newly emitted turn remains `live`. This preserves the "each card shows what it showed at that moment" principle without waiting for submission.

**Not a trigger**: session age, session inactivity timeout, archival, or any abstract "session completion" notion. Abandoned sessions keep their `live` cards until either (a) the user returns and submits, or (b) the underlying draft quote is garbage-collected by retention policy. If the quote is garbage-collected, the UI renders the message as "this quote was discarded" rather than attempting to render from a dangling reference.

**Critical correctness constraint**: A message never transitions from `snapshot` back to `live`. Once frozen, always frozen. This guarantees historical accuracy.

**Rationale**: Treating structured artifacts as conversation messages (rather than separate out-of-band UI state) preserves the chat metaphor and makes session replay correct. The live-vs-snapshot split honors the two distinct mental models users have: "the current thing I'm building" (live, ephemeral) vs "what the AI showed me at that moment" (snapshot, immutable). This also aligns with the existing `quote_version` immutability architecture.

**Historical context consistency**: the same `snapshot` rendering contract is used for quotes viewed from customer records, quote lists, approval queues, and audit surfaces. A single rendering primitive covers both "scrollback in a session" and "historical quote review from customer page" — neither should ever show live state against an immutable version.

**Effort estimate**: Medium — 4–6 days (schema decision, rendering contract, freeze-task implementation, scrollback freeze-on-new-turn logic, API changes, mobile renderer, comprehensive tests for the state transitions).

---

### A13. Voice Persona Tone Configuration (Post-MVP — Captured for Roadmap)

**Triggered by**: Future UX refinement — giving tenants control over AI personality tone.

**Scope**:
- Tenant setting: `voice_persona_tone` (numeric scale 0–100, default 50; or enum `conservative | balanced | playful`)
- Affects:
  - Ollama prompts for session title generation (A11)
  - Ollama prompts for assistant turn responses
  - Empty-state welcome text in the Voice tab
- Owner-configurable from web Settings > Voice AI > Configuration
- Client-side preview: owner hears three example interactions at different slider positions before committing

**Status**: Post-MVP. Noted here so it doesn't get lost when we're heads-down on MVP.

**Effort estimate**: Small — 2–3 days (post-MVP).

---

## Additions from Pass 3 Flow 2 (Real-Time Job Profitability)

### A14. ETC (Estimate to Complete) Capture System

**Triggered by**: Real-time projected margin calculation requires forward-looking labor estimates beyond actuals-to-date. Captures the tech's own assessment of remaining work to convert lagging margin signals into leading ones.

**Scope**:

**Schema changes**:
- New columns on `job_time_entry` (or equivalent existing time-tracking table):
  - `hours_remaining_estimate NUMERIC(6,2) NULL` — tech's ETC at the moment of this time entry
  - `hours_remaining_was_overridden BOOLEAN NULL` — true if tech changed the auto-populated value
  - `override_note TEXT NULL` — required when override increases hours by more than tenant threshold
- New optional FK `quote_line_id UUID NULL → quote_line(id)` on `job_time_entry` — when present, ETC is per-task; when null, ETC is per-job

**Mobile UX**:
- ETC prompt appears at two trigger points (per spec):
  1. **End-of-day clock-out** — before the tech can finalize their workday, prompt for ETC on each job they touched today
  2. **Mid-day task completion** — when tech marks a labor line complete and moves to the next one, prompt for ETC on the next task
- Auto-populated value = `quoted_hours - (prior_logged_hours + just-entered_hours)`
- One-tap "Confirm" button when value is unchanged
- Override flow:
  - Increase > tenant threshold → require note (cannot save without)
  - Decrease > tenant threshold → optional note
  - Within ±threshold → optional note regardless of direction

**Latest-ETC query pattern** for projected margin computation:

```sql
-- Per task
SELECT DISTINCT ON (job_id, quote_line_id)
       job_id, quote_line_id, hours_remaining_estimate, created_at
  FROM job_time_entry
 WHERE tenant_id = :tenant_id
   AND hours_remaining_estimate IS NOT NULL
 ORDER BY job_id, quote_line_id, created_at DESC;

-- Per job (when no quote_line_id)
SELECT DISTINCT ON (job_id)
       job_id, hours_remaining_estimate, created_at
  FROM job_time_entry
 WHERE tenant_id = :tenant_id
   AND quote_line_id IS NULL
   AND hours_remaining_estimate IS NOT NULL
 ORDER BY job_id, created_at DESC;
```

**Backward compatibility**: tenants existing pre-implementation have time entries without ETC values. The projected margin calculation for those jobs falls back to: `projected_total_hours = MAX(quoted_hours, hours_worked_so_far)`. Once any tech enters an ETC for that job, the system uses the ETC.

**API endpoints**:
- `POST /api/v1/jobs/{id}/time-entries` — accepts new ETC fields
- `GET /api/v1/jobs/{id}/projected-margin` — computed projected margin endpoint

**Cross-check verification before B3 starts** (April 30, 2026):

- **G1 (Receipt OCR Automation)**: PRD §3.4 mentions Textract/GPT-4V receipt parsing pipeline. Verify pre-existing — run `SELECT routine_name FROM information_schema.routines WHERE routine_name LIKE '%receipt%' OR routine_name LIKE '%ocr%'` plus check `tasks/` directory for OCR-related Celery tasks. If missing, add as A89 to B3 scope (estimated 3–5 days: async Celery task + Textract integration + cost_cents auto-fill + retry handling). Likely pre-existing.
- **G9 (Schedule History per Job endpoint)**: PRD §3.14 mentions "Dispatch board supports a 'history' view per job." Verify dedicated `GET /api/v1/jobs/{job_id}/schedule-history` endpoint exists. If missing, add to B3 scope (estimated 0.5–1 day: endpoint reading from existing `audit_log` filtered for job entity).

**Effort estimate**: Medium-Large — 6–8 days (schema, mobile prompt UX, validation logic, latest-ETC query patterns, projected margin computation).

---

### A15. Chart-or-Table Threshold Setting

**Triggered by**: Profitability page's chart-vs-table threshold pattern; will be reused across all reports.

**Scope**:
- Tenant setting: `report_chart_threshold` — integer (default 8)
- Applied at API layer: report endpoints return `display_mode: 'chart' | 'table'` based on returned row count vs threshold
- Frontend reads this and renders accordingly
- Editable via Settings → Reports

**Effort estimate**: Trivial — half a day. Just a setting and an API computation.

---

### A16. ETC Variance Notification System

**Triggered by**: Owner needs immediate notification when projected job hours significantly exceed original quote.

**Scope**:
- Tenant setting: `etc_variance_owner_notify_pct` — integer percent (default 50)
- Tenant setting: `etc_variance_note_required_pct` — integer percent (default 10)
- Trigger: every time a `job_time_entry` is saved with an ETC value, evaluate if the projected total exceeds the threshold
- Comparison: `(current_projected_total_hours / original_quoted_hours - 1) * 100`
- When threshold exceeded AND owner has not already been notified for this job's variance:
  - Push notification to owner
  - Email to owner (using existing notification_outbox infrastructure from Pass 2 A4)
  - Mark job as `variance_owner_notified_at` (prevents repeat notifications until variance worsens further)
- Notification content includes: job name, customer, original quote, current projected, percent over

**Re-notification logic**: if variance worsens past the next threshold band (e.g., from 50% over to 80% over), notify again. Implementation detail to be designed by dev team — suggest tracking last notified percentage and re-notifying when it grows by another threshold-amount.

**Effort estimate**: Small-Medium — 2–3 days.

---

### A17. Margin Bucket Configuration

**Triggered by**: Tenant-configurable margin boundaries for the profitability bar charts.

**Scope**:
- Tenant setting: `margin_bucket_boundaries` — JSON array of integers (default `[10, 20, 30]`)
- Tenant setting: `margin_target_pct` — integer (default 20) — used for "below target" indicators
- API: report endpoints use these boundaries when computing bucket counts/revenue
- Frontend: chart axis labels reflect tenant's actual boundaries
- Settings UI: Settings → Reports → Margin buckets — edit boundaries with preview of current data redistributed

**Validation**: boundaries must be ascending integers between 0 and 100. Length determines bucket count (3 boundaries = 4 buckets, 2 boundaries = 3 buckets, etc.).

**Effort estimate**: Small — 1–2 days.

---

## Additions from Pass 3 Flow 3 (Dispatch Board)

### A18. Tech Color Assignment & Configuration

**Triggered by**: Color-coded tech identity throughout the dispatch board (filter dots, avatar fills, job block borders, job block backgrounds).

**Scope**:
- New column on `user` table (or equivalent identity table): `display_color VARCHAR(7) NULL` — hex color code, e.g., `#3B43D6`
- Color is auto-assigned at user creation from a default palette of 8–12 hues, cycling to ensure no two active users share the same color
- Owner can override color per tech in Settings → Users
- API: tech color returned with user object on all relevant endpoints
- Frontend: dispatch board, Today tab on mobile, scheduling reports all consume this color

**Default palette**: 12 distinct hues drawn from extending the Pass 1 brand color ramps, with WCAG AA contrast verified for both white-text-on-color and color-on-white-background usage.

**Tenant setting**: `tech_color_palette` — array of hex codes (default = system palette of 12). Tenants with custom branding can override.

**Effort estimate**: Small — 1–2 days.

---

### A19. Dispatch Board API Endpoints (Optimistic Locking + Real-Time Updates)

**Triggered by**: Dispatch board's high-frequency drag-and-drop interactions and the requirement to reflect external calendar changes within minutes.

**Scope**:

**API endpoints** (most already specced in `mvp-arch.md` §13.7, but with additional behavior):
- `GET /api/v1/schedule/board` — extended to include drive-time data computed from cache when possible, fresh map provider call when cache miss
- `POST /api/v1/schedule/jobs/{id}/move` — atomic operation accepting both new tech and new time-window. Performs conflict check before commit. Returns either success or structured conflict response.
- `POST /api/v1/schedule/jobs/{id}/check-conflicts` — preview-only endpoint for what-if checks during drag operations. No commit.

**Optimistic concurrency control**:
- `job` and `job_tech_assignment` records carry a `version` integer column
- Move endpoints accept `expected_version` parameter
- Concurrent modification (two owners on the same board, or owner + voice command) returns 409 Conflict with the current state
- Frontend handles 409 by refreshing the affected job and offering retry

**Real-time push for external changes**:
- Server-sent events (SSE) endpoint: `GET /api/v1/schedule/board/stream` — emits change events when:
  - Calendar pull task processes external changes
  - Another owner makes a change
  - Voice command applies a change
  - Tech checks in / completes a job (state change)
- Frontend listens and applies smooth updates to the affected cells
- Falls back to 60-second polling if SSE unavailable

**Effort estimate**: Medium-Large — 6–8 days (endpoint refinement, optimistic locking on existing schema, SSE infrastructure).

---

### A20. Drive-Time Caching Verification

**Triggered by**: Dispatch board's drag-and-drop interactions can trigger many drive-time recomputations. Ensure caching prevents API cost overrun.

**Scope**:
- Verify that the existing `compute_customer_etas` task (per `mvp-arch.md` §13.6) and any related drive-time computation paths use a Redis-cached lookup keyed on `(origin_lat, origin_lng, dest_lat, dest_lng, hour_of_day)`
- Cache TTL: 24 hours (per architecture spec)
- Cache hit on dispatch board drag operations means same-day rearrangements are free after the first compute
- Add metric: `map_provider.cache_hit_ratio` to monitoring dashboard
- Add alarm: cache hit ratio < 70% over 1 hour (suggests cache key mismatch or TTL too short)

**Note**: this isn't strictly a new feature — it's a verification + observability item. Worth calling out because dispatch board UX depends on it being correct.

**Effort estimate**: Small — 1–2 days (verification, metric instrumentation, alarm setup).

---

## Additions from Pass 3 Flow 4 (Customer Communications)

Flow 4 builds heavily on Pass 2 A4 (Templated Customer Communications). The schema (`customer_communication`, `communication_template`), the API endpoint (`POST /api/v1/communications/send`), the voice intent handler, and the notification dispatch are already specced in A4. The additions below are the design-driven refinements that Flow 4 made explicit.

### A21. Per-Message Channel Override

**Triggered by**: Tech ability to override customer's stored preferred channel for a single message without changing the customer's stored preference.

**Scope**:
- Extend `customer_communication` table to record:
  - `customer_preferred_channel` (the customer's stored preference at send time)
  - `actual_channel` (the channel actually used)
  - `channel_override_flag` (boolean — true when these differ)
- API endpoint `POST /api/v1/communications/send` accepts an optional `channel_override` parameter (`'sms' | 'email'`) which forces the actual_channel regardless of customer preference
- Customer record's preferred channel field is unchanged by override
- Web comm history surfaces channel overrides as visible metadata (per spec — "channel overridden from SMS to email")

**Schema confirmation needed**: confirm that the `customer` table has a `preferred_contact_channel` field. If not, add it (`VARCHAR(10)` enum: `'sms' | 'email'`, NOT NULL DEFAULT `'sms'`).

**Effort estimate**: Small — 1–2 days (schema additions, API parameter, history rendering).

---

### A22. Voice Intent Grammar for Customer Communications

**Triggered by**: Voice describes intent (not template name) — "tell Johnson I'm 20 out" must map to `on_my_way` template with computed ETA, not require Mike to say a template name.

**Scope**:
- Additions to `voice_action_router.py` handler registry (per Pass 2 A4 baseline, now expanded with Flow 4 patterns):
  - `send_customer_communication` — top-level intent
  - Intent matcher routes utterance fragments to template codes:
    - "I'm [X] out" / "[X] minutes away" / "[X] minutes" → `on_my_way` with ETA = now + X minutes
    - "running [X] late" / "[X] minutes late" → `running_late` with delay = X
    - "I'm here" / "I just arrived" / "starting work" → `arrived`
    - "the job's done" / "we're done" / "all finished" / "job complete" → `job_complete`
    - "parts delay" / "waiting on parts" → `parts_delay`
    - "confirm [date/time]" → `confirm_appointment`
- Confidence threshold for ambiguous utterances — when intent matching falls below threshold, AI asks for clarification rather than picking
- Variable extraction:
  - Time durations ("20 out", "30 late") parsed and converted to ETAs/delays
  - Customer names extracted, matched against tenant's customer DB, disambiguated if ambiguous (per Flow 1 disambiguation pattern)
- Customer resolution priority (per Flow 4 spec):
  1. Explicit context (voice triggered from customer/job page)
  2. Named in utterance
  3. Disambiguation prompt when name ambiguous
  4. Customer prompt when no name and no context

**Effort estimate**: Medium — 4–5 days. The intent matching is non-trivial — requires Llama prompt engineering for variable extraction and confidence scoring, plus integration with the disambiguation conversation pattern.

---

### A23. Communication Preview Endpoint (Pre-Send Validation)

**Triggered by**: Always-preview-before-send rule means the UI needs to render the exact message that will be sent, with all variables substituted, before the user confirms.

**Scope**:
- New API endpoint: `POST /api/v1/communications/preview`
- Request: `template_code`, `customer_id`, `variables` (object), `channel_override` (optional)
- Response:
  - `rendered_subject` (for email)
  - `rendered_body` (the actual message text)
  - `recipient_name`
  - `recipient_address` (phone number for SMS, email for email)
  - `actual_channel`
  - `editable_variables` (array of variable names with their current values, used by the inline-edit UI to know what's editable)
- This endpoint does NOT log to `customer_communication` and does NOT dispatch the message — it's read-only template rendering
- Same template engine as the send endpoint (A4), just no dispatch

**Rationale**: Frontend can't reliably render templates client-side (variable substitution rules, channel-specific rendering, opt-out footer compliance text, etc.). Server-side rendering ensures the preview matches what gets sent.

**Effort estimate**: Small — 1–2 days. Largely a refactor of the existing template rendering logic into a separate endpoint that doesn't dispatch.

---

## Additions from Pass 3 Flow 5 Architectural Pre-Work (Quote Line Item Architecture)

These items are foundational schema/architectural changes triggered by the quote-style decisions documented in `quote-line-item-architecture.md`. They must be implemented before Flow 5's UI can be built, and they affect Flow 1 (voice quote creation) and Flow 2 (profitability calculations).

### A24. Quote Line Item Schema Extension (Visibility + Hierarchy)

**Triggered by**: Need to support component, deliverable, and lump-sum quote styles with one flexible data model.

**Scope**:

**Schema additions to `quote_line` (or equivalent existing table)**:
- `customer_visible BOOLEAN NOT NULL DEFAULT TRUE` — if false, line is internal cost-tracking only, never shown to customer
- `parent_line_id UUID NULL REFERENCES quote_line(id) ON DELETE RESTRICT` — when present, this line is a child of another line for cost roll-up purposes
- `display_order INT NOT NULL` — explicit ordering, separate from creation order, allowing lines to be reordered without timestamp manipulation
- `is_section_header BOOLEAN NOT NULL DEFAULT FALSE` — when true, line renders as a visual section divider (e.g., "Services", "Materials") with no price column

**Description field verification**: confirm `description` is `TEXT` with no length cap. Real-world quotes have descriptions running 700+ characters with bullet formatting. If currently `VARCHAR` with a cap, migrate to `TEXT`.

**Constraints**:
- A child line (`parent_line_id IS NOT NULL`) cannot be customer-visible if its parent is not (children inherit at-most the parent's visibility — enforced via CHECK constraint or trigger)
- A section header line (`is_section_header = TRUE`) must have `parent_line_id IS NULL`
- A line cannot be its own parent or create a cycle (parent_line_id depth ≤ 1 for MVP — single level of hierarchy)

**Roll-up semantics** (documented for dev team):
- A parent line's customer-facing total is the value stored in its own `total_amount` field (NOT auto-computed from children)
- A parent line's *cost basis* is the sum of children's `total_amount` values
- Margin = parent's `total_amount` − sum_of_children's_amounts

**Effort estimate**: Medium — 3–4 days (schema migration, constraint logic, application code updates for line item CRUD, PDF rendering pipeline updates to handle visibility flags and section headers).

---

### A25. Quote Template Schema with Style and Versioning

**Triggered by**: Per-template style selection and system-template-versioning model.

**Scope**:

**Naming convention**: rename existing "quote template" references in code to use the full prefix `quote_template` to disambiguate from `communication_template` (Pass 2 A4). Audit existing schema, API routes, and code paths.

**Schema for quote templates**:
```
quote_template
  id                        UUID PRIMARY KEY
  tenant_id                 UUID NULL  -- NULL means system template; UUID means tenant-owned
  name                      TEXT NOT NULL
  description               TEXT NULL
  style                     TEXT NOT NULL  -- 'component' | 'deliverable' | 'lump_sum'
  category                  TEXT NULL  -- e.g., 'service_call', 'installation', 'inspection'
  system_template_id        UUID NULL  -- when this is a tenant fork, references the system template
  forked_from_version       INT NULL  -- the version of the system template at fork time
  current_version           INT NOT NULL DEFAULT 1
  is_active                 BOOLEAN NOT NULL DEFAULT TRUE
  is_system_template        BOOLEAN NOT NULL DEFAULT FALSE
  created_at                TIMESTAMPTZ
  updated_at                TIMESTAMPTZ
  created_by_user_id        UUID NULL
```

**Companion table for template line items**:
```
quote_template_line
  -- mirrors quote_line structure including customer_visible, parent_line_id,
  -- display_order, is_section_header, description, default_quantity, default_amount
  -- with template-variable placeholders allowed in text fields ({customer_name}, {site_address}, etc.)
```

**API endpoints**:
- `GET /api/v1/quote-templates` — list with filters (style, category, system vs. tenant)
- `POST /api/v1/quote-templates` — create tenant template
- `POST /api/v1/quote-templates/{id}/fork` — fork a system template to tenant ownership
- `POST /api/v1/quote-templates/{id}/disable` — soft-disable a tenant template
- `POST /api/v1/quotes/from-template/{template_id}` — instantiate a new quote from a template

**System template seed**:
- Pilot ships at least three system templates as MVP defaults:
  - `service_call_basic` (component-style)
  - `installation_standard` (deliverable-style)
  - `fixed_bid_simple` (lump-sum-style)
- Seeded into the database via a migration on initial deploy and per new tenant creation
- System templates have `tenant_id = NULL` and `is_system_template = TRUE`
- New tenants automatically have these visible in their template list as read-only references

**Effort estimate**: Medium-Large — 5–7 days (schema, fork mechanism, seed data, API endpoints, naming refactor).

---

### A26. System Template Update Notification Flow

**Triggered by**: Locked decision that system template version updates notify tenants but don't auto-push.

**Scope**:
- New nightly Celery task: `check_system_template_updates`
  - For each active tenant template with a non-null `system_template_id`, check if `forked_from_version < current_version` of the source system template
  - If yes, generate an in-app notification: "Pilot has released v{N} of [Template Name] — review changes"
  - Notifications dedup per (tenant_id, system_template_id, system_template_version) so a tenant isn't re-pinged about the same update
- Settings UI: "Template updates available" section showing pending updates with a "View changes" link
- Pull mechanism: when tenant clicks "Pull v2," create a new tenant template forked from the new system template version; old tenant template is preserved (and optionally disabled by tenant)
- Quotes already created from the old tenant template continue to render correctly because each quote's line items are immutable per existing quote_version pattern

**Effort estimate**: Small-Medium — 2–3 days.

---

### A27. Save Quote as Template

**Triggered by**: Locked decision allowing owners to save any quote as a tenant template.

**Scope**:
- API endpoint: `POST /api/v1/quotes/{id}/save-as-template`
- Request: `name`, `category` (optional), `style` (defaults from quote's style if it has one)
- Server-side processing:
  1. Copy all customer-visible and hidden lines from the quote into a new `quote_template_line` set
  2. Replace customer-specific values with template variables: `customer_name`, `site_address`, `customer_phone`, `customer_email`, dates, quote numbers
  3. Strip transaction-specific data (the actual `quote_id`, the specific final total)
  4. Preserve material quantities and labor hours as defaults but mark them as override-able
- The variable namespace for templating must match existing variable conventions used by communication templates (Pass 2 A4) where overlapping
- RBAC: `quote_template.create` permission — owner/admin only (techs cannot save quotes as templates)

**Open question for dev team review**: define the complete variable namespace. Initial set:
```
{customer_name}        — full customer name
{customer_first_name}  — customer first name
{site_address}         — site street address
{site_city_state_zip}  — site city/state/zip line
{job_date}             — scheduled job date
{quote_date}           — quote creation date
```

**Effort estimate**: Medium — 3–4 days (API endpoint, variable substitution logic, scrubbing rules, RBAC integration).

---

### A28. Multi-Line Description Editing UI Support

**Triggered by**: Real-world quotes have line item descriptions running 700+ characters with bullet formatting (e.g., Contractor A "Generator Install Air-Cooled" with 12 bullets).

**Scope**:
- **Backend**: confirm `quote_line.description` and `quote_template_line.description` are `TEXT` (not `VARCHAR(255)` or similar). If migration needed, do it as part of A24.
- **Mobile editing UI**: multi-line text area replacing any current single-line input. For MVP, plain `<textarea>` is sufficient — bullet auto-formatting on `-` keystroke is Phase 2 polish.
- **Web editing UI**: same multi-line area, more screen space. Phase 2 could upgrade to a markdown-aware editor (e.g., simple Markdown preview).
- **PDF rendering**: customer-facing quote PDF must preserve newlines and render bullet-prefixed lines (`- `, `* `) as visual bullets.
- **Voice editing constraint**: composing 700-character descriptions verbally is impractical. Voice handles short edits; long descriptions are template-derived and edited via touch. This is a UX constraint, not a code path.

**Effort estimate**: Small — 1–2 days (mostly the PDF rendering update; mobile/web editor changes are minor).

---

## Additions from Pass 3 Flow 5 (Quote Approval Workflow)

Flow 5 builds on Pass 2 A2 (Quote Approval Workflow baseline) and the architectural pre-work (A24–A28). The schema for the `pending_approval` and `approved` quote states, the basic submission endpoints, and the notification dispatch are already specced in A2. The additions below are the design-driven refinements that Flow 5's UI requires.

### A29. Pending Edit Storage During Owner Review

**Triggered by**: Owner can make multiple edits to a quote during review and commit them all at once via "Approve with edits." Edits must persist across page reloads but remain invisible to the tech until commit.

**Scope**:

**Schema additions**:
- New table or extension to existing quote storage: `quote_pending_edit`
  ```
  quote_pending_edit
    id                  UUID PRIMARY KEY
    tenant_id           UUID NOT NULL
    quote_id            UUID NOT NULL → quote(id)
    quote_version_id    UUID NOT NULL → quote_version(id)  -- the version being reviewed
    editor_user_id      UUID NOT NULL → user(id)  -- the owner doing the editing
    edit_type           TEXT NOT NULL  -- 'modify_line' | 'add_line' | 'delete_line' | 'edit_notes'
    target_line_id      UUID NULL → quote_line(id)  -- for modify/delete; null for add
    edit_payload        JSONB NOT NULL  -- the proposed change (new values, new line content, etc.)
    annotation          TEXT NULL  -- optional explanation provided by owner
    created_at          TIMESTAMPTZ
    updated_at          TIMESTAMPTZ
  ```

**Lifecycle**:
- Pending edits are created when the owner makes a modification on the review surface
- They persist across page reloads (server-side, scoped to editor + quote version)
- "Cancel my edits" deletes all pending edits for that owner on that quote version
- "Approve with edits" applies all pending edits as a single atomic operation, creating a new quote version, then deletes the pending edit records
- If the owner abandons the review without explicit action, pending edits expire after 24 hours (Celery cleanup task)

**API endpoints**:
- `GET /api/v1/quotes/{id}/pending-edits` — list current owner's pending edits for this quote
- `POST /api/v1/quotes/{id}/pending-edits` — create a pending edit
- `PATCH /api/v1/quotes/{id}/pending-edits/{edit_id}` — modify a pending edit
- `DELETE /api/v1/quotes/{id}/pending-edits/{edit_id}` — revert an individual pending edit
- `DELETE /api/v1/quotes/{id}/pending-edits` — cancel all pending edits
- `POST /api/v1/quotes/{id}/approve-with-edits` — atomic: apply all pending edits, create new version, transition to approved state

**Concurrency**: when two owners review the same quote simultaneously, each has their own `quote_pending_edit` rows scoped by `editor_user_id`. The first to commit wins; the second receives a 409 Conflict and must refresh.

**Effort estimate**: Medium — 4–5 days (schema, atomic apply logic, concurrency handling, cleanup task, API endpoints).

---

### A30. Approval Comment & Annotation System

**Triggered by**: Kickback workflow requires inline comments on specific lines + overall comment; reject requires overall comment; approve-with-edits supports optional per-edit annotations.

**Scope**:

**Schema**:
- New table: `quote_approval_comment`
  ```
  quote_approval_comment
    id                    UUID PRIMARY KEY
    tenant_id             UUID NOT NULL
    quote_id              UUID NOT NULL → quote(id)
    quote_version_id      UUID NOT NULL  -- which version this comment is anchored to
    target_line_id        UUID NULL → quote_line(id)  -- null for overall comment
    author_user_id        UUID NOT NULL → user(id)
    comment_type          TEXT NOT NULL  -- 'kickback' | 'rejection' | 'edit_annotation'
    content               TEXT NOT NULL
    created_at            TIMESTAMPTZ
  ```

**Visibility**:
- Comments visible to the original tech submitter, the owner, the approver (if different), and any user with `quote.view` permission
- Comments persist forever (audit trail) — no soft delete from the comment side
- If a quote line referenced by a comment is later deleted, the comment is preserved with line context captured at comment creation

**API endpoints**:
- `GET /api/v1/quotes/{id}/comments` — list all approval comments for this quote
- `POST /api/v1/quotes/{id}/kickback` — atomic: transition quote to draft state with provided comments
- `POST /api/v1/quotes/{id}/reject` — atomic: transition quote to rejected state with required overall comment

**Required-comment validation**:
- Kickback request must include either at least one line-level comment OR a non-empty overall comment (or both)
- Reject request must include a non-empty overall comment
- Approve-with-edits has no required comments (annotations are optional per-edit)

**Effort estimate**: Small-Medium — 3–4 days.

---

### A31. Voice Intent Grammar for Approval Actions

**Triggered by**: Owner can voice-trigger approval actions from any Pilot surface ("approve Mike's panel quote", "show me Mike's pending quotes", "kick back the panel quote").

**Scope**:
- Additions to `voice_action_router.py` handler registry:
  - `approve_quote` — atomic approval with no edits
  - `reject_quote` — requires spoken comment which is captured as the rejection reason
  - `kickback_quote` — requires spoken comment which is captured as the overall kickback comment (line-level comments not voice-supported per spec; touch required for those)
  - `list_pending_quotes` — read-only, returns spoken summary of pending approvals
- Disambiguation pattern: when multiple quotes match the voice command (e.g., "Mike's quote" with two pending), AI asks "Which one — the panel upgrade or the service call?"
- Voice cannot commit complex inline edits — voice handlers reject any utterance that attempts line-level modification ("change the labor to 8 hours") with a response routing the owner to web: "I can approve, reject, or kick back the quote, but line edits need to happen on web. Open quote on web?"

**Constraint rationale**: voice-driven complex edits are too error-prone given Whisper accuracy in field conditions and the financial implications of wrong edits to a customer-facing quote.

**Effort estimate**: Small-Medium — 2–3 days (intent matching, disambiguation, refusal-with-redirect logic).

---

## Additions from Pass 3 Flow 6 (Calendar Conflict Resolution)

Flow 6 designs the UI for resolving bi-directional calendar sync conflicts. The architecture (`mvp-arch.md` §13.5) and base endpoints (`mvp-arch.md` §13.7 — `GET /api/v1/calendar/conflicts`, `POST /api/v1/calendar/conflicts/{id}/resolve`) are already specced; the additions below are design-driven refinements: a richer conflict payload for diff rendering, optimistic-locking-style staleness check, configurable auto-expiry, mobile parity, and voice resolution intent grammar.

### A32. Calendar Conflict Diff Payload

**Triggered by**: Resolution view (web and voice readback) requires server-rendered field-level diff plus base-state context for accurate "what changed since last sync" framing.

**Scope**:

> **📌 Column name clarification (FIND-118, Phase 4.2)**: This spec uses `pilot_snapshot`/`external_snapshot` terminology. The **live DB column names** are `local_snapshot` (Pilot state) and `remote_snapshot` (external calendar state). For frontend/API consumers: "local = Pilot", "remote = external provider". API and PRD documentation use `pilot_snapshot`/`external_snapshot` as conceptual labels; live schema uses `local_snapshot`/`remote_snapshot`. No schema change is needed — this is a naming alignment note only.

- Extend `calendar_sync_conflict` schema:
  - `local_snapshot` (live DB name; "pilot_snapshot" in spec) — current Pilot state at conflict detection
  - `remote_snapshot` (live DB name; "external_snapshot" in spec) — current calendar state at conflict detection
  - `base_snapshot` (NEW, JSONB NULL) — last shared state before conflict; populated at detection time from the most recent successful sync log entry
  - `pilot_modified_by_user_id` (NEW, UUID NULL) — who made the Pilot-side change
  - `pilot_modified_at` (NEW, TIMESTAMPTZ NOT NULL)
  - `external_modified_at` (NEW, TIMESTAMPTZ NOT NULL)
  - `urgency_score` (NEW, INT computed) — derived from related job's `scheduled_start_at` proximity for sort order
  - `related_job_id` (NEW, UUID NULL → field_ops.job)

- Extend `GET /api/v1/calendar/conflicts/{id}` response:
  - All snapshot fields above
  - `field_diffs`: server-computed list of fields that differ. For each field: `field_name`, `pilot_value`, `external_value`, `base_value`, `pilot_change` (`unchanged | modified | added | removed`), `external_change` (same enum)
  - This pre-computes the diff so the client doesn't need diff logic, voice readback can render from the same payload, and rendering stays consistent

**Effort estimate**: Small-Medium — 2–3 days (schema additions, base-snapshot capture in detection task, server-side diff computation, API response shape).

---

### A33. Pre-Resolution Staleness Check

**Triggered by**: Conflicts may be modified between detection and the owner's resolve action. Without a check, the owner can silently overwrite a state they didn't see. Applies to both web and voice resolution paths.

**Scope**:

- `POST /api/v1/calendar/conflicts/{id}/resolve` accepts `expected_pilot_modified_at` and `expected_external_modified_at` parameters
- Server re-evaluates: if either timestamp on the live conflict record exceeds the expected, returns 409 Conflict with the refreshed conflict payload
- Frontend handles 409 by refreshing the resolution view and surfacing a "this conflict has been updated" banner; owner re-decides
- Voice handler (A36) handles 409 by aborting confirmation, announcing the change, and routing to web with a deep link
- Same pattern as the dispatch board's optimistic locking from A19

**Effort estimate**: Small — 1 day (API parameter validation, refresh pattern reuse from A19; voice handler integration is in A36's scope).

---

### A34. Auto-Expiry of Stale Conflicts (System Default + Tenant Override)

**Triggered by**: Conflicts unresolved for long periods clutter the conflict count and degrade the metric's signal value. Two-tier configuration (platform-wide default; per-tenant override) gives both Pilot and individual tenants tuning control.

**Scope**:

**System-level configuration** (file/config-based for MVP; admin UI is Phase 2):
- `SYSTEM_CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS` — default `30`
- `SYSTEM_CALENDAR_CONFLICT_PRE_WARNING_DAYS` — default `7`
- These live in application settings; a deploy is required to change them in MVP

**Tenant-level overrides** (UI editable per tenant):
- `calendar_conflict_auto_expire_days` — integer; UNSET (no row) falls back to system default; tenant can explicitly set to NULL via UI to disable auto-expiry entirely (NULL is a sentinel, distinct from UNSET)
- `calendar_conflict_pre_warning_days` — integer; UNSET falls back to system default; explicitly nullable via UI to disable pre-warning
- Validation: when both are set, `pre_warning_days < auto_expire_days` enforced server-side; reject with 400 otherwise
- Settings UI: Settings → Integrations → Calendar → "Auto-resolution" subsection, with two integer inputs and explicit "Use system default" / "Disable" toggles

**Resolution logic** (server-side, when evaluating a conflict's age):
```
expire_days = tenant.calendar_conflict_auto_expire_days
if UNSET (no row): use SYSTEM default
if NULL (explicit disable): no auto-expiry for this tenant
otherwise: use the tenant value
```
Same logic for `pre_warning_days`.

**New Celery Beat task**: `expire_stale_calendar_conflicts` (daily)
- For each conflict, compute its applicable `expire_days` and `pre_warning_days` per the resolution logic above
- If conflict age >= `expire_days - pre_warning_days` and pre-warning not yet sent for this conflict: enqueue notification "N conflicts will auto-resolve in [pre_warning_days] days"
- If conflict age >= `expire_days`: invoke the existing resolve endpoint internally with `accept_local`, log to `calendar_sync_log` with `auto_resolved_stale = TRUE`, send notification

**Audit query**: `auto_resolved_stale = TRUE` flag distinguishes auto-resolutions from owner-initiated ones in any future investigation.

**Implementation note for dev team**: the system-default mechanism is new infrastructure if Pilot doesn't already have a "system config registry" pattern. Suggested implementation for MVP: a single `system_config.py` module exposing typed constants, loaded at app startup from environment variables with config-file values as fallback. Phase 2 may upgrade this to an admin-tier database table editable by Pilot support staff.

**Cross-check finding G10 clarification (April 30, 2026)** — per arch doc §13.5, the calendar auto-expiry implementation uses BOTH mechanisms together:

- `calendar_conflict_auto_expire_enabled` — boolean (default TRUE); FALSE disables auto-expiry entirely for the tenant regardless of days setting
- `calendar_conflict_auto_expire_days` — integer NULL; NULL = use system default of 30; integer = use this value
- `calendar_conflict_pre_warning_days` — integer NULL; NULL = use system default of 7

Effective resolution logic:
1. If `calendar_conflict_auto_expire_enabled = FALSE` → skip auto-expiry entirely; conflicts persist until manually resolved
2. If TRUE → apply `calendar_conflict_auto_expire_days` (NULL → use system default of 30)
3. Pre-warning sent at `(auto_expire_days - pre_warning_days)` (NULL pre-warning → use system default of 7)

A34 implementation includes all three columns. The boolean is the on/off switch; the nullable integer is the value override.

**Effort estimate**: Medium — 3–4 days (task implementation, two-tier resolution logic, settings UI plumbing for both fields with default/disable/override states, audit flagging, system-config infrastructure if not present).

---

### A35. Mobile Pending-Conflicts Status & Notification Rate Limiting

**Triggered by**: Mobile Owner tab needs a status row showing pending conflict count for parity with the QuickBooks pattern; notification storms during outage recovery need rate limiting.

**Scope**:

- `GET /api/v1/calendar/status` (existing, per `mvp-arch.md` §13.7) extended to return:
  - `connection_status: 'connected' | 'syncing' | 'error' | 'disconnected'`
  - `last_successful_sync_at`
  - `pending_conflicts_count`
  - `requires_reconnect: boolean` (true when token-expired error)
- Mobile Owner tab consumes this for the "Calendar sync" row rendering (parallel to the existing QuickBooks sync row)
- Push notifications on conflict detection use existing `notification_outbox` infrastructure (per `mvp-arch.md` §13.5)
- Rate limit: max 4 conflict-detection notifications per tenant per hour. Exceeding the limit collapses subsequent detections into a single batched notification ("3 more conflicts detected — resolve on web")

**Effort estimate**: Small — 1 day (response shape additions, rate-limit logic; frontend consumption is design only).

---

### A36. Voice Intent Grammar for Calendar Conflict Resolution

**Triggered by**: Decision 11 in the Flow 6 spec — voice can actively resolve modified-modified conflicts via the confirm-as-turn pattern, with explicit route-to-web for deletion conflicts and post-staleness recovery.

**Scope**:

**New voice intents** (added to `voice_action_router.py`):

| Intent | Example utterances | Handler behavior |
| :--- | :--- | :--- |
| `list_pending_calendar_conflicts` | "Do I have any pending sync conflicts?" / "What conflicts are pending?" | Read-only; AI announces count + brief urgency summary |
| `resolve_calendar_conflict` | "Resolve the Johnson conflict — accept Pilot" / "Accept the calendar version of the Williams conflict" | Identifier match, disambiguation, confirm-as-turn, then commit via existing resolve endpoint |

**Identifier matching**: handler looks up conflicts by:
1. Customer name (e.g., "Johnson")
2. Job title (e.g., "panel upgrade")
3. Scheduled date qualifier (e.g., "Thursday's" or "next week's")

If multiple match → AI asks disambiguating question following Flow 1's disambiguation pattern: "You have two Johnson conflicts — the panel upgrade or the inspection?"

**Confirm-as-turn copy template** (read by AI before committing):

```
"Accepting the [side] version of [conflict_identifier].
[That keeps:] [summary of what's preserved from chosen side].
[That discards:] [summary of what's lost from the rejected side].
Confirm?"
```

The summary text is rendered server-side using the field-level diff payload from A32 — the same payload that drives the visual diff. This keeps web and voice presentations consistent: what the diff highlights visually is what the readback announces verbally.

**Confirm-as-turn flow** (per Flow 1's `delete_session` pattern):
1. AI returns a pending-confirmation state in `context_window_json`
2. Owner's next utterance evaluated for affirmative intent ("yes" / "confirm" / "do it" / "go ahead")
3. Affirmative → API call with the resolve action
4. Anything else → cancel; AI offers "Want to see it on web instead?" with a push notification deep link

**Pre-staleness check integration** (per A33): if the resolve API returns 409 between identification and confirmation, AI announces "the conflict has changed since you last looked at it — opening the diff view on web" and pushes the deep link via `notification_outbox`.

**Refusal-with-redirect for unsupported cases**:
- Deletion conflicts → "That's a deletion conflict — it needs the diff view to be safe. I'll open it on web." Push notification with deep link.
- Multi-resolution attempts ("resolve all my conflicts") → "I can do them one at a time — which one first?" routes to per-conflict resolution.
- Field-level edits ("change the time to 3pm in the Johnson conflict") → "I can pick a side, but I can't edit the values via voice. Want me to open it on web?"

**RBAC**: existing `integrations.manage` permission is sufficient; voice handler honors the same RBAC check as the web endpoint.

**Effort estimate**: Medium — 4–5 days (intent matching, identifier disambiguation, server-side voice readback rendering using A32 diff payload, confirm-as-turn flow integration with `context_window_json` from A12, refusal-with-redirect logic, integration tests covering the staleness-check race).

---

## Additions from Pass 3 Flow 7 (Offline-to-Online Sync)

Flow 7 is the most backend-intensive Pass 3 flow because offline-capable mobile is essentially new infrastructure. Ten additions across data model, API contract, conflict classification, upload pipeline, voice deferred processing, force-quit recovery, auth, and owner escalation.

### A37. Offline-Capable Operations API Contract

**Triggered by**: Decision 1 of Flow 7 — explicit set of operations must be supported by both client SDK and backend with consistent contracts.

**Scope**:
- Document each offline-capable operation as accepting client-generated idempotency UUIDs
- Each endpoint validates idempotency on receipt
- Schema additions: `client_capture_at TIMESTAMPTZ NULL` on tables for offline-capturable operations (`job_time_entry`, `expense`, `photo`, `change_order`, `loto_check`, `job_status_change`, `job_note`) — distinct from `created_at` which is server-side
- Audit log captures both timestamps for offline-captured operations; the gap (`server_received_at - client_capture_at`) becomes a queryable metric for offline-duration analysis

**Operations covered** (per Flow 7 Decision 1):
- Clock in / clock out
- Time entry creation (with ETC fields per A14)
- Expense capture (with attached photo via A41)
- Photo capture (separate upload pipeline via A41)
- Status changes on already-assigned jobs
- LOTO check confirmation
- Voice audio capture (deferred processing via A42)
- Free-text notes on a job
- Change order creation against an already-assigned job

**Effort estimate**: Small-Medium — 2–3 days (mostly schema additions and contract documentation; idempotency already exists per §7.6).

---

### A38. Sync Queue State Model (Server-Side Visibility)

**Triggered by**: Decision 4 of Flow 7 — sync queue surface needs a server-side counterpart for cross-device visibility (tenant owner reviewing tech's sync state, support troubleshooting, audit).

**Scope**:
- New table: `mobile_sync_event` — append-only log of sync attempts per device per operation
  ```
  mobile_sync_event
    id                          UUID PRIMARY KEY
    tenant_id                   UUID NOT NULL
    user_id                     UUID NOT NULL
    device_id                   TEXT NOT NULL  -- client-reported device identifier
    operation_type              TEXT NOT NULL  -- 'time_entry' | 'expense' | 'photo' | etc.
    operation_payload_summary   JSONB  -- non-PII summary of what was synced
    status                      TEXT NOT NULL  -- 'pending' | 'syncing' | 'succeeded' | 'failed' | 'conflict'
    conflict_severity           TEXT NULL  -- 'auto_silent' | 'auto_notice' | 'tech_resolvable' | 'owner_escalation'
    client_capture_at           TIMESTAMPTZ NOT NULL
    synced_at                   TIMESTAMPTZ NULL
    error_detail                JSONB NULL
    idempotency_uuid            UUID NOT NULL
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
  ```
- API: `GET /api/v1/mobile-sync/state/{user_id}` — admin view (owner/support) of a tech's sync state, paginated
- Retention: 30 days hot, then archived consistent with audit log policy (per §3.1 audit lifecycle)
- Index: `(tenant_id, user_id, status)` for fast queries by status

**Effort estimate**: Medium — 3–4 days.

---

### A39. Idempotency UUIDs for Offline Operations

**Triggered by**: Decisions 1, 9 of Flow 7 — every offline-capable operation needs a client-generated UUID for safe retry, plus extension of idempotency window for the 72-hour offline scenario.

**Scope**:
- Document the idempotency contract: every offline-capable endpoint accepts `Idempotency-Key` header with a client-generated UUID v4
- Server-side: existing idempotency-key infrastructure (per §7.6) handles deduplication on retry; expand coverage to all offline-capable endpoints from A37
- **24-hour idempotency window adequacy review**: a tech could capture at hour 0, force-quit at hour 23, come back online at hour 50. The 24-hour idempotency window has expired but the sync still hasn't completed.
- **Mitigation — natural-key dedup**: server uses both the idempotency window AND a longer-window check on natural keys for offline-capable operations:
  - Time entry: `(user_id, job_id, clock_in_at)` unique on a 7-day window
  - Expense: `(user_id, job_id, captured_at, amount_cents)` unique on a 7-day window
  - LOTO check: `(user_id, job_id, captured_at)` unique on a 7-day window
  - Photo: `(user_id, job_id, captured_at, file_hash)` unique on a 30-day window
- Client SDK: generate UUID at capture time, persist with operation in local queue, send with sync attempt. UUID stays stable across retries.

**Effort estimate**: Small-Medium — 3–4 days (client SDK pattern + server-side natural-key dedup enhancement for offline-capable operations).

---

### A40. Conflict Severity Classification Engine

**Triggered by**: Decision 5 of Flow 7 — four severity classes need a server-side classifier that runs during sync.

**Scope**:
- New module: `services/mobile_sync_conflict.py`
- Per operation type, define classification rules: which conditions are auto-silent, auto-with-notice, tech-resolvable, owner-escalation
- API: classification runs during sync attempt; returns `SyncResolution` object with:
  ```
  severity: 'auto_silent' | 'auto_notice' | 'tech_resolvable' | 'owner_escalation'
  auto_resolved: bool
  tech_action_required: bool
  owner_escalation_required: bool
  payload: dict  # the resolution data, conflict description, etc.
  ```
- Per-operation classification matrix (data-driven, in a configuration table for runtime tuning):

  | Operation | Trigger | Severity |
  | :--- | :--- | :--- |
  | Time entry | Job still assigned to tech, no time overlap | `auto_silent` |
  | Time entry | Job reassigned to different tech | `tech_resolvable` |
  | Time entry | Job deleted while tech worked it | `owner_escalation` |
  | Time entry | Time overlaps existing entry (same tech) | `tech_resolvable` |
  | Expense | Category exists, under limit | `auto_silent` |
  | Expense | Category was renamed server-side | `auto_notice` |
  | Expense | Exceeds tenant per-item limit | `tech_resolvable` |
  | Expense | Job deleted while expense captured | `owner_escalation` |
  | Photo | Job exists | `auto_silent` |
  | Photo | Storage limit exceeded | `tech_resolvable` |
  | Photo | Job deleted while photo captured | `owner_escalation` |
  | Status change | Tech-assigned job, normal transition | `auto_silent` |
  | Status change | Job already completed by another tech | `owner_escalation` |
  | Change order | Quote version still active | `auto_silent` |
  | Change order | Quote version superseded | `tech_resolvable` |
  | LOTO check | Job still in progress | `auto_silent` |
  | LOTO check | Job completed before LOTO sync arrived | `auto_notice` |

- Configuration table allows Pilot admins to tune the classification matrix without code deploys (e.g., reclassify a specific trigger from `tech_resolvable` to `auto_notice` based on operational data)

**Effort estimate**: Medium-Large — 5–7 days (per-operation classification logic, comprehensive test coverage for each row in the matrix, configuration table, all four severity paths).

---

### A41. Resumable Photo Upload Pipeline

**Triggered by**: Decision 6 of Flow 7 — resumable chunked uploads to handle network interruption; separate queue from data sync.

**Scope**:

**Implementation choice**: S3 multipart upload directly from client with signed URLs. Rationale: offloads heavy lifting to S3, avoids Pilot as a chunk-relay middleman, scales better at any tenant volume.

**API endpoints**:
- `POST /api/v1/photos/initiate-upload`
  - Request: `tenant_id` (from JWT), `job_id`, `expense_id` (optional), `file_size_bytes`, `mime_type`, `client_capture_at`, `idempotency_uuid`
  - Response: S3 multipart upload session ID, list of presigned chunk URLs (one per chunk), `pilot_photo_id`
- `POST /api/v1/photos/complete-upload`
  - Request: `pilot_photo_id`, `s3_session_id`, `chunk_etags` (list)
  - Response: photo record with final URL
  - Server-side: validates all chunks present, calls S3 CompleteMultipartUpload, records the photo

**Client SDK**:
- Track per-chunk completion in local state
- Resume from last-completed chunk on retry (skip already-uploaded chunks)
- Configurable chunk size (default 5MB)

**WiFi/cellular preference**:
- Client-side scheduling; server doesn't enforce
- Tenant setting `photo_upload_wifi_only` (default TRUE)
- User override: "Upload on cellular when offline > 24 hours" — client-side configurable

**Server-side cleanup**:
- Incomplete uploads expire after 24 hours via S3 lifecycle rule
- Celery task `cleanup_incomplete_photo_uploads` validates and removes orphaned `photo` records weekly

**Local cleanup** (per Flow 7 cross-domain F):
- Tenant setting `photo_local_retention_days` (default 7)
- Local photos kept this long after server confirmation, then auto-purged from device
- Client SDK manages this; server tracks confirmation timestamps

**Effort estimate**: Medium — 4–5 days (S3 multipart integration, chunk management, signed URL generation, client SDK chunked upload logic, local cleanup logic).

---

### A42. Voice Command Offline Capture & Deferred Processing

**Triggered by**: Decision 7 of Flow 7 — voice audio captured offline, transcribed when online.

**Scope**:

**Schema extensions to `voice_command_log`**:
- `captured_at TIMESTAMPTZ NOT NULL` — when audio was captured (client-side)
- `uploaded_at TIMESTAMPTZ NULL` — when audio reached server
- `transcribed_at TIMESTAMPTZ NULL` — when Whisper completed
- `parsed_at TIMESTAMPTZ NULL` — when Llama completed
- `processing_status TEXT NOT NULL` — `pending_upload | uploading | transcribing | parsing | completed | failed`
- `audio_object_key TEXT` — S3 key for the uploaded audio file (existing field; verify present)
- `idempotency_uuid UUID NOT NULL` — for safe retry

**API endpoints**:
- `POST /api/v1/voice/upload-audio`
  - Accepts: audio file (multipart), `captured_at` timestamp, `idempotency_uuid`, optional context (which screen, active conversation_session_id)
  - Returns: `voice_command_log_id`, processing status pointer
  - Queues a Celery task for processing
- `GET /api/v1/voice/command/{id}` — poll for processing status and result

**Celery task**: `process_voice_audio_async`
- Loads audio from S3
- Runs Whisper transcription
- Runs Llama intent parsing
- Routes to intent handler (existing flow)
- Updates `voice_command_log.processing_status` through state machine
- If intent requires confirmation (per Flow 1 confirm-as-turn), enqueue notification rather than blocking

**Confirmation deferred flow**:
- If intent processing produces a destructive action, the result is held in a "pending confirmation" state
- Notification fires to the originating user: "Your voice command 'delete the Davis chat' is ready to confirm"
- Tap → opens Voice tab with confirmation prompt; tech responds yes/no in normal voice or touch flow
- Confirmation timeout: 24 hours; after that, the deferred command is auto-cancelled with a notification

**Client SDK**:
- Store audio locally when offline; upload via this endpoint when online
- UI shows "queued" state in sync queue (per Flow 7 Decision 4)

**Effort estimate**: Medium — 4–5 days (schema, async pipeline, deferred-confirmation flow, client SDK, integration with existing voice intent flow).

---

### A43. Force-Quit Recovery State Persistence

**Triggered by**: Decision 9 of Flow 7 — sync queue must survive force-quit and resume.

**Scope**:

**Client-side** (mostly):
- Local queue persists in device storage
  - iOS: Core Data with synchronous writes for queue mutations
  - Android: Room with transactional writes
  - Expo / cross-platform: shared persistence layer (likely SQLite via Expo's persistence APIs)
- Each queue item carries: client UUID, operation type, payload (full request body), status, retry count, last error, last attempt timestamp
- On app launch: load queue from storage, mark "syncing" items as "pending" (idempotency keys handle the duplicate-protection on retry)

**Server-side** (minimal):
- Honor idempotency on retry per A39 (largely existing)
- Verify `mobile_sync_event` (A38) records prior sync attempts for the same `idempotency_uuid` to enable client-side awareness of "this might already be synced; check before retry"

**Cross-platform behavior tests required** (per Flow 7 validation checklist):
- iOS: app force-quit → relaunch → queue resumes
- iOS: app backgrounded > 30 minutes → relaunch → queue resumes
- Android: app force-stop → relaunch → queue resumes
- Android: app killed by OS memory pressure → relaunch → queue resumes
- Both: device reboot mid-sync → relaunch → queue resumes

**Effort estimate**: Medium — 4–5 days client SDK (persistence layer, lifecycle integration, tests across iOS/Android/Expo); minimal backend.

---

### A44. Auth Expiry Offline Handling

**Triggered by**: Decision 10 of Flow 7 — graceful re-auth after token expiry preserves captured data.

**Scope**:

**Refresh token TTL verification**:
- Cognito refresh token TTL must be at least 7 days (default 30 days — adequate for 72-hour hard limit per Flow 7 Decision 13)
- Document this in operational runbook so it's not accidentally lowered

**Client SDK behavior**:
- On sync attempt with expired access token: attempt refresh
- If refresh succeeds: sync resumes silently
- If refresh fails:
  - Surface re-auth prompt while preserving local queue
  - Captured data remains in local storage; not deleted
  - Tech enters credentials → new tokens issued → sync resumes from queue

**Edge case — tenant disabled the user mid-offline**:
- Re-auth fails permanently (not a token issue, an account issue)
- UI: "Account disabled — contact your owner. Captured data is saved locally."
- Export affordance: "Email me a JSON copy of unsynced data" — tech enters an external email address; client SDK assembles a JSON dump and sends via local mail client (not via Pilot API since the account is disabled)
- After 30 days locally, captured data auto-purges to prevent indefinite local retention

**Effort estimate**: Small-Medium — 2–3 days (refresh flow client SDK, account-disabled UX, JSON export client-side).

---

### A45. Tech-Resolvable Conflict UI Endpoints

**Triggered by**: Decision 11 of Flow 7 — tech resolves conflicts on phone with proper API support.

**Scope**:

**API endpoints**:
- `GET /api/v1/mobile-sync/conflicts/{conflict_id}` — returns the conflict detail:
  - Tech's captured version (full payload)
  - Server's current version (full payload)
  - Severity classification (per A40)
  - Classification reason (human-readable, e.g., "Job reassigned to different tech")
  - Field-level diff (per A32 pattern from Flow 6, adapted for mobile sync conflicts)
- `POST /api/v1/mobile-sync/conflicts/{conflict_id}/resolve`
  - Accepts: `resolution: 'use_local' | 'use_server' | 'escalate_to_owner'`
  - For `use_local`: applies tech's version, may push to other affected entities
  - For `use_server`: discards tech's version, marks the corresponding queue item as resolved
  - For `escalate_to_owner`: creates `mobile_sync_owner_escalation` row (per A46), notifies owner

**Pre-resolution staleness check** (per A33 pattern from Flow 6):
- API accepts `expected_server_version_id` parameter
- If server state changed between conflict surface and resolution attempt, returns 409 with refreshed conflict payload
- Client refreshes the resolution screen with new state

**Audit**: every resolution logged to `mobile_sync_event` with status `succeeded` (with `resolution_action` field capturing which path was taken).

**Effort estimate**: Small-Medium — 2–3 days (largely follows A33 pattern; field-level diff logic mostly reusable from A32).

---

### A46. Owner Escalation Routing & Notification

**Triggered by**: Decision 12 of Flow 7 — owner-escalated conflicts surface in owner's queue with notification; web UI deferred to Pass 4.

**Scope**:

**New table**: `mobile_sync_owner_escalation`
```
mobile_sync_owner_escalation
  id                       UUID PRIMARY KEY
  tenant_id                UUID NOT NULL
  originating_user_id      UUID NOT NULL  -- the tech
  conflict_id              UUID NOT NULL  -- → mobile_sync_event(id)
  escalated_at             TIMESTAMPTZ NOT NULL
  escalation_reason        TEXT NOT NULL  -- 'auto_severity' | 'tech_chose'
  status                   TEXT NOT NULL  -- 'pending' | 'resolved' | 'rejected'
  resolved_by_user_id      UUID NULL
  resolved_at              TIMESTAMPTZ NULL
  resolution_action        TEXT NULL  -- 'used_local' | 'used_server' | 'manual_edit' | 'rejected'
  resolution_payload       JSONB NULL  -- if owner did a manual edit, the resulting state
```

**API endpoints**:
- `GET /api/v1/owner/mobile-sync-escalations` — list pending escalations for owner; filter by user, date range, operation type
- `GET /api/v1/owner/mobile-sync-escalations/{id}` — escalation detail with full conflict context
- `POST /api/v1/owner/mobile-sync-escalations/{id}/resolve` — owner resolves; accepts `resolution_action` and optional `resolution_payload` for manual edits

**Notification flow**:
- On escalation creation: push + `notification_outbox` entry to owner per existing infrastructure
- On owner resolution: push to originating tech ("Your conflict was resolved by Sarah — your local data was kept" or similar)

**Web UI for resolution**: deferred to Pass 4 per Flow 7 cross-domain consideration D. The design language is largely inheritable from Flow 6's two-column diff pattern adapted for the mobile-sync-conflict source.

**Effort estimate**: Medium — 3–4 days backend (table, endpoints, notification integration); UI deferred to Pass 4.

---

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

## Additions from Pass 4 Tier 1 (Owner Mobile-Conflict UI, QuickBooks Conflict UI, Background Sync)

### A47. Owner-Side Mobile-Conflict Escalation Queue Endpoints

**Triggered by**: Pass 4 Tier 1 #1 Decisions 1, 2, 11 — queue list with filtering, escalation detail with explainer copy, history archive.

**Scope**:
- `GET /api/v1/owner/field-issues` — list pending escalations for the requesting owner's tenant
  - Query parameters: `status` (default `pending`; accepts `pending | auto_recovered | stale | all`), `tech_active_within_hours` (default 24, accepts `null` for all), `operation_type` (multi-value), `sort` (default `-escalated_at`; accepts `-escalated_at | escalated_at | -captured_at | captured_at`), `limit`, `offset`
  - Response: paginated list with `{escalation_id, tech_user_id, tech_name, tech_role, tech_last_active_at, operation_type, operation_summary, escalation_reason_explainer, captured_at, escalated_at, status, server_state_summary}` per row
- `GET /api/v1/owner/field-issues/{escalation_id}` — full escalation detail for resolution view
  - Response: full diff payload with `tech_local_snapshot` (JSONB), `server_state_snapshot` (JSONB), `field_diffs` (computed), `escalation_reason_explainer` (server-generated copy), `escalation_type` (`field_diff | deletion_conflict_tech_captured_against_deleted | deletion_conflict_status_change_collision | permission_revoked_capture`), `available_resolutions` (enum array based on type), audit context
- `GET /api/v1/owner/field-issues/history` — historical archive
  - Same shape as queue list but with status filter defaulting to resolved states
  - Additional response fields: `resolved_at`, `resolved_by_user_id`, `resolution_action`, `resolution_channel` (`web | voice`)

**Server-Sent Events extension** (per arch doc §13.11): the existing SSE channel for `Dashboard` adds escalation-list-state events so an owner viewing the queue sees real-time updates when new escalations arrive or when auto-recovery fires.

**Server-generated explainer copy** is computed at escalation creation time (in A46) and stored in `mobile_sync_owner_escalation.escalation_reason_explainer TEXT`. This deviates from the calendar conflict pattern (where diff is computed live) because the originating context can be lost between creation and resolution.

**Effort estimate**: Medium — 4–6 days (three endpoints, SSE extension, explainer copy templates per escalation reason, comprehensive test coverage).

### A48. Owner-Side Mobile-Conflict Resolution Write Path

**Triggered by**: Pass 4 Tier 1 #1 Decisions 5, 6, 8, 10 — resolution commit with pre-commit staleness check, three distinct 409 payload types, loop-closure to originating tech, audit log capture.

**Scope**:
- `POST /api/v1/owner/field-issues/{escalation_id}/resolve` — commits the resolution
  - Request body: `{resolution: 'use_tech' | 'use_server' | 'restore_and_accept' | 'override_with_tech' | 'discard_tech' | 'accept_authorized_at_capture' | 'reject_unauthorized', expected_server_state_at_view_time: ISO8601_timestamp}`
  - Response 200: `{committed: true, resolution_outcome: <enum>, post_commit_state: <JSONB>, originator_notification_dispatched: bool}`
  - Response 409 with `payload.staleness_type = 'server_changed'`: `{refreshed_escalation: <full detail payload>, message: "..."}`
  - Response 409 with `payload.staleness_type = 'auto_recovered'`: `{auto_recovery_outcome: <enum>, message: "..."}`
  - Response 409 with `payload.staleness_type = 'stale'`: `{tech_force_discarded: true, message: "..."}`
- Pre-commit staleness check follows A33 pattern from Flow 6 with the three distinct payload types
- Resolution write path:
  - For `use_tech` / `restore_and_accept` / `override_with_tech` / `accept_authorized_at_capture`: commit tech's captured operation to the appropriate domain (time entry, expense, photo, status change, LOTO, voice command); update originator queue item to `resolved_in_favor_of_tech` (or `resolved_with_action` for restore-and-accept variants)
  - For `use_server` / `discard_tech` / `reject_unauthorized`: discard tech's captured operation (purge from `mobile_sync_pending_operation`); update originator queue item to `resolved_in_favor_of_server`
- Loop closure:
  - Update `mobile_sync_event.status` and `mobile_sync_event.resolution_*` fields on the originating queue item
  - Insert push notification to originating tech via existing `notification_outbox` infrastructure (rate-limited per A35; aggregation when multiple resolved in a window)
  - Insert persistent activity log entry on originating tech mobile via `mobile_sync_event_log` (extends existing schema with `resolution_*` fields)
- Audit:
  - Insert `mobile_sync_event_audit` entry capturing `escalation_id`, `originator_user_id`, `resolver_user_id`, `resolution_action`, `resolution_channel`, `tech_local_snapshot_at_commit`, `server_state_snapshot_at_commit`, `post_commit_state`, `resolved_at`

**Voice channel routing**: when resolution comes in via voice (per Tier 1 #1 Decision 7), the same endpoint handles it; `resolution_channel` is set on the audit entry. Voice intent handler `resolve_field_issue` calls this endpoint internally.

**Mobile activity log retention** (per Tier 1 #1 Cross-Domain C): tech mobile keeps last 90 days of activity log entries locally; older entries fetched from server on demand.

**Effort estimate**: Medium-Large — 5–7 days. The variation across resolution types per operation is the main cost (each type needs domain-specific commit logic). The 409 payload differentiation, loop-closure event emission, and audit capture are smaller incremental costs.

### A49. QuickBooks Conflict Queue Endpoints + Schema Extension

**Triggered by**: Pass 4 Tier 1 #2 Decisions 1, 2, 12 — queue list with filters, conflict detail with master-aware payload, history archive. Also resolves the Pass 4 work flagged in arch doc §5.4.

**Scope**:
- `GET /api/v1/integrations/quickbooks/conflicts` — list pending conflicts for the requesting owner's tenant
  - Query parameters: `entity_type` (multi-value: `customer | quote | invoice | expense`), `master` (multi-value: `pilot | quickbooks | user_choice`), `sort` (default `-financial_impact,-detected_at`), `limit`, `offset`
  - Response: paginated list per row with `{conflict_id, entity_type, entity_identifier, entity_summary, master_direction, pilot_change_summary, qb_change_summary, detected_at, financial_delta_cents (nullable, populated for invoices), affected_entity_url}`
- `GET /api/v1/integrations/quickbooks/conflicts/{id}` — full conflict detail
  - Response: `{conflict_id, entity_type, base_snapshot, pilot_snapshot, qb_snapshot, field_diffs (server-computed), master_direction, master_recommended_action, conflict_subtype (`field_diff | deleted_in_pilot_modified_in_qb | modified_in_pilot_deleted_in_qb`), available_resolutions, financial_delta_payload (for invoices), tax_period_warning (boolean, for invoices spanning closed period)}`
- `GET /api/v1/integrations/quickbooks/conflicts/history` — historical archive with filters

**Server-Sent Events extension** (per arch doc §13.11): existing SSE channel for `Settings > Integrations > QuickBooks` adds conflict-list-state events for real-time queue updates.

**Schema extension to `integration_sync_conflict`**:
- `base_snapshot JSONB NOT NULL` — last shared state at successful prior sync
- `field_diffs JSONB NOT NULL` — server-computed field-level diff array
- `pilot_modified_at TIMESTAMPTZ NOT NULL`
- `pilot_modified_by_user_id UUID NULL`
- `qb_modified_at TIMESTAMPTZ NOT NULL`
- `qb_modified_by_external_user_label TEXT NULL` — when QB metadata exposes the modifying user
- `auto_expire_at TIMESTAMPTZ NULL` — populated when tenant opts in per entity type
- `pre_warning_at TIMESTAMPTZ NULL`

**Effort estimate**: Medium — 4–5 days. Schema extension + three endpoints + SSE wiring + diff computation per entity type. Computation per entity type is the main cost (each entity type has a different shape and field set).

### A50. QuickBooks Conflict Resolution Write Path + Auto-Expiry Celery Extension

**Triggered by**: Pass 4 Tier 1 #2 Decisions 5, 7, 11 — resolution commit with pre-commit staleness check, two 409 payload types, audit log capture. Also Decision 9 — auto-expiry off by default but tenant-configurable per entity type.

**Scope**:
- `POST /api/v1/integrations/quickbooks/conflicts/{id}/resolve` — commits the resolution
  - Request body: `{resolution: 'accept_local' | 'accept_remote' | 'restore_and_accept_remote' | 'recreate_and_keep_local' | 'delete_both', expected_pilot_modified_at: ISO8601, expected_qb_modified_at: ISO8601}`
  - Response 200: `{committed: true, resolution_outcome, post_commit_state, push_to_other_side_dispatched: bool}`
  - Response 409 with `staleness_type = 'server_changed'`: `{refreshed_conflict, message}`
  - Response 409 with `staleness_type = 'auto_recovered'`: `{auto_recovery_outcome, message}`
- Pre-commit staleness check pattern from A33 (Flow 6); same shape applied to QB
- Resolution write path:
  - For `accept_local`: push Pilot snapshot to QB via existing sync mechanism; update mapping `external_version_token`
  - For `accept_remote`: write QB snapshot to Pilot's domain entity; update mapping `internal_version_token`
  - For deletion-conflict variants: combination of restore + push, or delete + push, depending on the variant
  - Update `integration_sync_conflict.status` to `resolved`
- Audit:
  - Insert `integration_sync_log` entry capturing `conflict_id`, `resolver_user_id`, `resolution_action`, `resolution_channel` (always `'web'` for MVP since voice resolution is explicitly out of scope per Tier 1 #2 Decision 8), `pre_commit_pilot_snapshot`, `pre_commit_qb_snapshot`, `post_commit_state`, `resolved_at`

**Auto-expiry Celery task extension**:
- Existing pattern from A34 (Flow 6's calendar auto-expiry) extends to QB
- New Celery Beat task `auto_expire_qb_conflicts_per_tenant` runs hourly
- For each conflict where `auto_expire_at <= now()`, commits the tenant-configured direction
- Pre-warning task fires `notification_outbox` entry at `pre_warning_at`
- Per-entity-type tenant settings for opt-in: `qb_auto_expire_customer_enabled`, `qb_auto_expire_quote_enabled`, `qb_auto_expire_invoice_enabled`, `qb_auto_expire_expense_enabled` (all default FALSE per Tier 1 #2 Decision 9); paired direction settings `qb_auto_expire_*_direction` (`accept_local | accept_remote`)
- Default expiry interval: 60 days (vs Flow 6's 30; accounting cadence is quarterly)
- Default pre-warning: 14 days (vs Flow 6's 7)

**Voice intent registry extension**: arch doc §6 adds `list_pending_qb_conflicts` (status query only). No `resolve_qb_*` intents in MVP per Tier 1 #2 Decision 8.

**Effort estimate**: Medium — 4–5 days. The variation across entity types and resolution types is the main cost (each entity needs domain-specific commit logic). Auto-expiry Celery extension is small additional work.

### A51. Background Sync Infrastructure

**Triggered by**: Pass 4 Tier 1 #3 Decisions 1, 2, 4, 9 — push token registry, silent push handlers, sync session management, frequency cap enforcement (tenant-configurable).

**Scope**:

**Push token registry** (canonical infrastructure for future reuse beyond background sync):
- Schema: new table `mobile_device_push_token`
  - `tenant_id`, `user_id`, `device_id` (client-generated UUID), `platform` (`ios | android`), `push_token` (APNs or FCM), `app_version`, `os_version`, `registered_at`, `last_seen_at`, `notification_permission_granted` (boolean, current value), `revoked_at`
  - Unique constraint on (`tenant_id`, `user_id`, `device_id`)
- API: `POST /api/v1/mobile/push-tokens` — register or refresh device push token (called on every app launch)
- API: `DELETE /api/v1/mobile/push-tokens/{device_id}` — revoke token (called on logout or token invalidation)
- Token rotation: when APNs/FCM returns "invalid token" on send, the token is marked revoked and the next push attempt to that device is skipped

**Silent push dispatcher**:
- New module `services/mobile_background_sync.py`
- Detects when a device's queue has pending items >15 minutes old → triggers silent push
- Detects retryable failure on prior attempt → triggers silent push at next exponential backoff window
- Detects field-issue resolution loop closure (per Tier 1 #1 Decision 8) → triggers silent push to originating tech
- Per-device frequency cap: at most 1 silent push per tenant-effective `background_sync_push_interval_minutes` (default 5; system default + tenant override per arch doc §16.5; rate limit table `mobile_push_rate_limit`)
- iOS payload shape: `{aps: {content-available: 1}, sync_session_id: "..."}`
- Android payload shape: high-priority FCM with `data` payload `{sync_session_id: "..."}`

**Sync session management**:
- Schema: new table `mobile_sync_session`
  - `session_id` (UUID), `tenant_id`, `user_id`, `device_id`, `triggered_by` (`silent_push | os_opportunistic | foreground | manual`), `started_at`, `completed_at`, `outcome` (`success | partial | failed | throttled`), `items_attempted`, `items_committed`, `items_deferred`, `items_failed`, `failure_reason`
- Client reports session telemetry on completion via `POST /api/v1/mobile/sync-sessions/{session_id}/complete`
- Server-side aggregation: this telemetry feeds the queue surface row from Tier 1 #3 Decision 5 (the "last background sync · X items synced" status) on next app open

**Frequency cap enforcement**:
- Server-side rate limiting on silent push dispatch (Tier 1 #3 Decision 1, Decision 4: 1 per tenant-effective `background_sync_push_interval_minutes`, default 5)
- New platform setting `system_background_sync_push_interval_minutes` (default 5) and tenant setting `background_sync_push_interval_minutes` (nullable; null inherits system default) per arch doc §16.5 system-default-with-tenant-override pattern
- Server-side detection of OS throttling (Tier 1 #3 Decision 9: backend detects no sync attempts for >2 hours despite queued items, surfaces "Background sync delayed by your phone" to client on next sync)

**Tenant settings introduced** (per Tier 1 #3 Decision 4):
- `background_sync_enabled` (boolean; default TRUE; user override allowed)
- `background_sync_wifi_only` (boolean; default FALSE; tenant-only)
- `background_sync_battery_floor_pct` (integer; default 20; range 5–50; tenant-only)
- `background_sync_push_interval_minutes` (integer; default 5; range 1–60; tenant-only; system-default-with-tenant-override per §16.5)

**Effort estimate**: Medium-Large — 6–8 days. The push token registry and silent push dispatcher are the largest pieces (3–4 days). Sync session management and frequency cap enforcement are smaller (2–3 days). Platform-specific testing across iOS and Android adds 1 day.

## Additions from Pass 4 Tier 2 #4 (Settings UIs for Configurable Thresholds)

### A52. Settings Catalog Endpoint

**Triggered by**: Settings IA framework Decision 7 (settings search) and the canonical mockups in Tier 2 #4.

**Scope**:
- `GET /api/v1/settings/catalog` — returns a tenant-scoped catalog of all settings with metadata
- Response: array of `{key, label, description, sub_surface_path, data_type, validation_rules, system_default, current_effective_value, current_scope (system | tenant | user), revertible, requires_role}`
- Cached per-tenant on the server (invalidated on settings change)
- Loaded once per settings session on the frontend; powers search and per-page rendering
- Response includes only settings the requesting user has read permission for (per RBAC gating from Settings IA framework Decision 8)

**Effort estimate**: Small-Medium — 2–3 days. Mostly a metadata aggregator over existing settings tables.

### A53. Effective-Value Resolution Endpoint (Three-Tier Extension)

**Triggered by**: Tier 2 #4 Mockup C (per-user override resolution).

**Scope**:
- Extend existing `get_effective_setting()` helper in `services/setting_resolver.py` to accept optional `user_id` parameter
- Three-tier resolution: user override (if exists and tenant allows) → tenant override → system default → fallback constant
- New table: `user_setting_override`
  - `tenant_id`, `user_id`, `setting_key`, `value` (JSONB), `created_at`, `updated_at`
  - Unique constraint on (`tenant_id`, `user_id`, `setting_key`)
- Endpoint: `GET /api/v1/settings/{key}/effective?user_id=...` — returns effective value with scope annotation (`{value, scope: 'user' | 'tenant' | 'system' | 'fallback'}`)
- Server-side enforcement: when a setting does not allow per-user override, the user override layer is skipped during resolution even if a row exists in `user_setting_override` (defense in depth)

**Architectural pattern**: extends arch doc §16.5's two-tier resolution (tenant → system → fallback) to three-tier (user → tenant → system → fallback) when the setting metadata permits per-user override. Future arch doc v4.2 update will formalize this.

**Effort estimate**: Small-Medium — 2 days.

### A54. Tenant Settings Write Endpoints

**Triggered by**: All tenant settings in Tier 2 #4 Decisions 2–10 (18 distinct settings across 7 sub-surfaces).

**Scope**:
- `PUT /api/v1/settings/{key}` — write a tenant-level setting (creates or updates `tenant_setting` row)
  - Request body: `{value: <setting-typed>}` with optional `expected_updated_at` for staleness check
  - Response 200: `{value, effective_value, scope: 'tenant', updated_at}`
- `DELETE /api/v1/settings/{key}` — remove tenant override (revert to system default)
  - Response 200: `{value: null, effective_value: <system_default>, scope: 'system'}`
- Per-setting validation enforced server-side:
  - Range checks (e.g., `background_sync_battery_floor_pct` between 5 and 50)
  - Monotonicity (e.g., `margin_bucket_boundaries` ascending)
  - Cross-field rules (e.g., `*_pre_warning_days < *_auto_expire_days`)
  - Custom rules per setting (per the Tier 2 #4 spec's per-setting locked specs)
- Special-case handling per Tier 2 #4 spec:
  - Toggling `require_approval_for_tech_quotes` from ON to OFF when pending-approval quotes exist: response includes `pending_quote_count`; frontend surfaces confirmation per Tier 2 #4 setting I2 spec
  - Save-on-group-complete category settings (e.g., QB per-entity auto-expiry): atomic write of paired fields; partial saves rejected
- Audit log entry for every write per Settings IA framework Cross-Domain G:
  - `audit_log` row with `setting_key`, `previous_value`, `new_value`, `scope: 'tenant'`, `changed_by_user_id`, `changed_at`
- RBAC gate: requires `owner` or `accountant` role per Settings IA framework Decision 8
- Optimistic UI: 200 response includes the new effective value for the frontend to confirm

**Effort estimate**: Medium — 3–4 days. Per-setting validation is the cost; many setting keys means many validation rules. The save-on-group-complete atomic-write logic is small additional work.

### A55. Per-User Override Write Endpoints

**Triggered by**: Tier 2 #4 Mockup C and setting C1 (`background_sync_enabled` per-user override).

**Scope**:
- `PUT /api/v1/settings/{key}/user-override` — write a user-level override
  - Request body: `{value: <setting-typed>}`
  - Response 200: `{value, effective_value, scope: 'user', updated_at}`
  - Response 403 if the tenant does not allow per-user override for this setting
- `DELETE /api/v1/settings/{key}/user-override` — revert user override to inherit tenant value
  - Response 200: `{value: null, effective_value: <tenant_or_system_value>, scope: 'tenant' | 'system'}`
- Server-side check that tenant allows per-user override before accepting the write (returns 403 if not, with explanatory error)
- Audit log entry per Settings IA framework Cross-Domain G:
  - `audit_log` row with `setting_key`, `previous_value`, `new_value`, `scope: 'user'`, `changed_by_user_id`, `changed_at`
- Authentication: user can only write their own overrides (no admin write-on-behalf-of-user in MVP); enforced via `user_id` from auth token vs. URL parameter
- Mobile-side: per-user override writes from mobile use the same endpoint; mobile UI invokes them per Tier 2 #4 Mockup C mobile view

**Effort estimate**: Small — 1–2 days. Light wrapper over A53/A54 infrastructure.

### A56. Notification Category Registry

**Triggered by**: Decision 2's eight-category classification, Decision 4's forced-minimum semantics, and Cross-Domain G's audit-pass requirement.

**Scope**:
- New table: `notification_category`
  - `category_id` TEXT PRIMARY KEY (e.g., `quote_approvals`, `field_issues`, `sync_conflicts`, `job_activity`, `customer_activity`, `billing`, `background_sync_alerts`, `system_announcements`)
  - `display_label` TEXT NOT NULL — user-facing label shown in the matrix UI
  - `description` TEXT NOT NULL — helper text shown below the category row
  - `category_group_id` TEXT NULL — Phase 2 forward-compatibility for grouping
  - `display_order` INTEGER NOT NULL — display order in the matrix UI
- New table: `notification_category_sub_trigger`
  - `sub_trigger_id` TEXT PRIMARY KEY (e.g., `customer_activity.inbound_sms_reply`, `job_activity.assignment`, `system_announcements.critical`)
  - `category_id` TEXT FK
  - `display_label` TEXT (for help/admin surfaces; not shown in matrix UI)
  - `forced_minimum_push_uniform` BOOLEAN NOT NULL DEFAULT FALSE — applies to all users
  - `forced_minimum_push_recipient_only` BOOLEAN NOT NULL DEFAULT FALSE — applies only to the originating recipient (e.g., tech in conversation)
- Schema extension to `notification_outbox`:
  - Add `category_id` TEXT NOT NULL FK
  - Add `sub_trigger_id` TEXT NULL FK
  - Add `recipient_user_id_originating` UUID NULL — the user the notification "belongs to" for forced-minimum-recipient-only semantics (e.g., the tech in the conversation thread)
- Audit pass: every `notification_outbox.create()` call site reviewed and assigned a category + sub_trigger. Estimated 8 firing sites in the v5.2 codebase.
- New table: `notification_default_policy`
  - `tenant_id` UUID NULL (NULL = Pilot system default)
  - `category_id` TEXT FK
  - `channel` TEXT (`push` | `email` | `in_app`)
  - `enabled` BOOLEAN NOT NULL
  - Unique constraint on (`tenant_id`, `category_id`, `channel`)
  - System defaults seeded per Decision 3 with tenant_id NULL
- API: `GET /api/v1/notifications/categories` — returns the registry with current effective tenant defaults
- API: `GET /api/v1/notifications/sub-triggers` — returns sub-triggers (mostly used by admin / debugging)

**Effort estimate**: Medium — 4 days. The category registry itself is a small schema; the audit pass over existing firing sites is the cost driver. Each firing site needs a code change to declare its category and (where applicable) sub-trigger.

**Audit pass deliverable** (per A56): a checklist tracked alongside this addition listing each of the ~8 existing `notification_outbox.create()` call sites with assigned `category_id` and `sub_trigger_id`. This deliverable is part of A56 completion criteria — A56 is not done until every existing firing site has a category. Categorization choices should follow the 8 categories defined in Tier 2 #5 spec Decision 2.

### A57. Notification Preference Matrix Endpoints + In-App Banner Component

**Triggered by**: Decisions 5, 6, 7, 8 — the matrix UI's read and write paths plus the in-app banner channel infrastructure.

**Scope**:

**Preference matrix endpoints**:
- New table: `notification_preference`
  - `tenant_id` UUID NOT NULL
  - `user_id` UUID NULL (NULL = tenant-level override of system default; non-NULL = user-level override)
  - `category_id` TEXT FK
  - `channel` TEXT (`push` | `email` | `in_app`)
  - `enabled` BOOLEAN NOT NULL
  - `created_at`, `updated_at` TIMESTAMPTZ
  - Unique constraint on (`tenant_id`, `user_id`, `category_id`, `channel`) with NULL handling
- API: `GET /api/v1/notifications/preferences?user_id=...` — returns the user's full effective matrix (8 × 3 = 24 cells), each with `effective_value`, `scope` (`system | tenant | user | locked`), and the inheritance chain
- API: `PUT /api/v1/notifications/preferences/{category}/{channel}` — write a user-level preference
  - Request: `{enabled: bool}`
  - Response 200 with new effective value
  - Response 403 if attempting to disable a forced-minimum push (Decision 4) — for user-context-asymmetric categories, the 403 only applies when the user's context triggers the forced-minimum
- API: `DELETE /api/v1/notifications/preferences/{category}/{channel}` — clear user override (revert to tenant or system default)
- API: `PUT /api/v1/notifications/tenant-policy/{category}/{channel}` — owner sets tenant-level default (RBAC: owner only)
- API: `DELETE /api/v1/notifications/tenant-policy/{category}/{channel}` — clear tenant override (revert to system default)
- API: `POST /api/v1/notifications/preferences/mute-all-push-non-critical` — bulk-mute all non-forced-minimum push for the requesting user
- API: `POST /api/v1/notifications/preferences/mute-all-email` — bulk-mute all email for the requesting user
- API: `POST /api/v1/notifications/preferences/reset-to-tenant-defaults` — clear all user overrides for the requesting user
- Audit log entry on every write per Cross-Domain E

**In-app banner component**:
- Server-Sent Events channel `/sse/notifications` per arch doc §13.11 streams in-app notifications to the active session
- New endpoint: `POST /api/v1/notifications/in-app/mark-read` — mark notification(s) as read
- New endpoint: `GET /api/v1/notifications/in-app/recent?limit=50` — returns last 50 in-app notifications for the bell panel
- Shared web/mobile component: `<NotificationBanner />` slides down from top with auto-dismiss (6s standard / 12s critical), click-to-navigate, ARIA `role="alert"` accessibility
- Notification center bell component: badge count of unread; panel with last 50; mark-as-read on click
- New table: `in_app_notification`
  - `notification_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID
  - `category_id` TEXT FK
  - `body` TEXT
  - `deep_link_target` TEXT (per Cross-Domain J)
  - `priority` TEXT (`standard | critical`)
  - `created_at`, `read_at` TIMESTAMPTZ NULL

**Effort estimate**: Medium — 5–6 days. The endpoints are simple CRUD; the in-app banner component (shared between web and mobile, with SSE integration, accessibility, and bell archive) is the cost driver.

### A58. Delivery Dispatcher Preference Gate

**Triggered by**: Cross-Domain H — the existing dispatcher must respect preferences and forced-minimum semantics.

**Scope**:
- Update `tasks/notification_worker.py::poll_pending_notifications` to consult `notification_preference` and forced-minimum rules before dispatching
- For each pending `notification_outbox` entry, for each potential recipient, for each channel:
  1. Look up the recipient's effective preference for `(category_id, channel)` via the three-tier resolution chain
  2. If `enabled = FALSE`, check forced-minimum rules:
     - If the channel is push AND the category-sub-trigger is forced-minimum-uniform → override and dispatch
     - If the channel is push AND the category-sub-trigger is forced-minimum-recipient-only AND `recipient_user_id_originating == this_recipient_user_id` → override and dispatch
     - Otherwise → skip the channel
  3. If all channels are skipped for a recipient, log the suppression and skip the recipient
- Emit a structured log entry when a notification is filtered by preferences (for support / debugging)
- Forced-minimum push (Decision 4) bypasses the gate for push only — email and in-app still respect preferences
- Per-recipient evaluation is critical: a single notification may have multiple recipients (e.g., owner + tech), each with different forced-minimum context
- Performance: cache effective preferences per (user, category, channel) for the duration of a single dispatcher poll cycle

**Effort estimate**: Medium — 3–4 days. The logic is small but the per-recipient evaluation across multiple users adds complexity. Testing surface is large — every existing firing site needs end-to-end verification that preference filtering doesn't accidentally suppress something it shouldn't, and that forced-minimum overrides work for both uniform and asymmetric cases.

## Additions from Pass 4 Tier 1.5 (Flow 4 Customer Communications Extension — Inbound SMS, Threading, Replies)

### A59. Telnyx Webhook Handler + Carrier-Agnostic Adapter Layer + TCPA Opt-In/Opt-Out Tracking

**Triggered by**: Tier 1.5 Decisions 3, 13 — inbound SMS receive infrastructure with carrier abstraction. **Cross-check finding G5/G6 (April 30, 2026) added TCPA opt-in/opt-out scope to this addition** — these are legal compliance requirements per TCPA law and A2P 10DLC carrier rules.

**Scope**:
- New module `services/sms_carrier.py` with abstract `SmsCarrier` interface
  - Methods: `provision_number()`, `send_message()`, `verify_webhook_signature()`, `parse_inbound_webhook()`, `get_delivery_status()`, `release_number()`
- `TelnyxSmsCarrier(SmsCarrier)` implementation:
  - Webhook signature verification using Telnyx's public-key signature scheme
  - `parse_inbound_webhook()` extracting sender, recipient, body, timestamp, carrier_message_id
  - **STOP keyword detection** — detect: STOP, STOPALL, UNSUBSCRIBE, QUIT, CANCEL, END, ARRET (case-insensitive); exact-match on body content (no partial-match — "I want to STOP working on this" should not trigger opt-out)
  - `send_message()` calling Telnyx send API
  - `provision_number()` calling Telnyx number search + acquire APIs
  - `release_number()` calling Telnyx number release API
  - `get_delivery_status()` calling Telnyx message status API
- `MockSmsCarrier(SmsCarrier)` for integration testing — captures calls without making real API requests; supports STOP-keyword test injection
- New API endpoint: `POST /api/v1/webhooks/sms/telnyx-inbound` — receives Telnyx webhook
- Configuration: `SMS_CARRIER` env var (`telnyx | mock`); same carrier for all tenants on a deployment
- Failure handling: signature verification failure returns 401 (Telnyx will retry); routing failure parks inbound in unrouted queue per A60

**Schema additions to `customer` table** (TCPA compliance — verify with postgres-local MCP before writing migration; columns may partially pre-exist):

```sql
ALTER TABLE customer ADD COLUMN sms_opted_out BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE customer ADD COLUMN sms_opt_out_at TIMESTAMPTZ NULL;
ALTER TABLE customer ADD COLUMN sms_opt_in_consent BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE customer ADD COLUMN sms_opt_in_at TIMESTAMPTZ NULL;
ALTER TABLE customer ADD COLUMN sms_opt_in_source TEXT NULL;
    -- 'explicit_checkbox' | 'inbound_initiated' | 'verbal_captured'
```

**STOP routing flow**:
- STOP-detected inbound bypasses normal threading (`route_inbound_message()` per A60)
- Routes directly to new handler `handle_sms_opt_out(customer_id, opt_out_message)`:
  - Sets `customer.sms_opted_out = TRUE`
  - Sets `customer.sms_opt_out_at = NOW()`
  - Records opt-out event in audit log
  - Sends confirmation reply per Telnyx requirements ("You've been unsubscribed. Reply START to opt back in.")
- Future inbound from this customer: continue to be received and threaded normally; outbound is blocked (per A65 quota check extension)

**Opt-in tracking** — non-STOP inbound from previously opted-out customer triggers opt-in re-establishment:
- If `customer.sms_opted_out = TRUE` and inbound contains "START" or "UNSTOP" or "YES" (case-insensitive exact-match)
- Sets `customer.sms_opted_out = FALSE`; clears `sms_opt_out_at`
- Sets `customer.sms_opt_in_consent = TRUE`; `sms_opt_in_at = NOW()`; `sms_opt_in_source = 'inbound_initiated'`
- Sends confirmation reply ("You've been resubscribed.")

**Opt-in capture during normal flow** — for new customers being added to the tenant:
- Customer creation form must include opt-in checkbox (UI work; backend stores result)
- Sets `customer.sms_opt_in_consent` based on checkbox; `sms_opt_in_at` to creation time; `sms_opt_in_source = 'explicit_checkbox'`
- For verbally-captured opt-in (e.g., during a service call), tenant can update via customer record edit; sets `sms_opt_in_source = 'verbal_captured'`

**Audit log capture**:
- All STOP / opt-out events written to `audit_log` with event type `sms_opt_out`
- All opt-in events written with event type `sms_opt_in`
- TCPA-required: audit log must be queryable for compliance review

**Architectural pattern**: carrier-agnostic adapter — generalizable to other external service integrations (payment processors, email services, mapping providers). Future Phase 2 surfaces inherit this approach.

**Effort estimate**: Medium — 4–5 days (interface + Telnyx implementation + Mock implementation + webhook endpoint + signature verification + STOP detection + opt-in/opt-out flow + 5 customer schema columns + audit log integration). **+1.5–2 days versus original A59 estimate due to TCPA additions per cross-check finding G5/G6.**

### A60. Customer Communication Threading Schema and Routing

**Triggered by**: Tier 1.5 Decision 4 — threading model.

**Scope**:
- New table `customer_communication_thread`:
  - `thread_id` UUID PK
  - `tenant_id` UUID
  - `customer_id` UUID
  - `tech_id` UUID
  - `tenant_phone_number_id` UUID FK → `tenant_phone_number` (per A61)
  - `status` TEXT (`active | archived`)
  - `first_message_at`, `last_message_at` TIMESTAMPTZ
  - `message_count` INT
  - `created_at`, `updated_at` TIMESTAMPTZ
- New table `customer_communication_message`:
  - `message_id` UUID PK
  - `thread_id` UUID FK
  - `direction` TEXT (`outbound | inbound`)
  - `channel` TEXT (`sms`; MMS Phase 2)
  - `body` TEXT
  - `segment_count` INT (for billing/quota)
  - `status` TEXT (`pending_send | sent | delivered | failed | received`)
  - `carrier_message_id` TEXT (Telnyx's message ID for status polling)
  - `sent_at`, `delivered_at`, `received_at` TIMESTAMPTZ
  - `composition_method` TEXT (`template | free_form_text | free_form_voice`)
  - `template_id` UUID NULL (for templated outbound; references existing `communication_template` table from A4)
  - `voice_audio_id` UUID NULL (for voice-dictated replies; references `voice_command_log.id`)
  - `audit_user_id` UUID (the tech who sent for outbound; the tech the inbound was routed to for inbound)
- New table `customer_communication_unrouted` for inbound messages that couldn't be matched to an existing thread (per Decision 3 edge case)
- New module `services/customer_communication_threading.py`:
  - `route_inbound_message(inbound: InboundMessage) -> ThreadingResult`
  - Match by sender phone + recent outbound thread + 7-day window
  - Fallback: customer's `last_assigned_tech_id` if no recent outbound
  - If still no match: park in unrouted queue with owner notification
- API: `GET /api/v1/communications/unrouted` — owner-only surface to review and manually route unrouted messages
- API: `POST /api/v1/communications/unrouted/{id}/assign-to-thread` — owner manually assigns an unrouted inbound to a thread
- Schema migrations including coexistence with existing `customer_communication` table (A4) — the threading model wraps the flat table; existing outbound rows backfill into threads at deployment time

**Effort estimate**: Medium — 4 days (schema + migration + routing logic + unrouted handling + tests).

### A61. Telnyx Number Provisioning at First Use

**Triggered by**: Tier 1.5 Decision 12 — lazy provisioning of tenant phone numbers.

**Scope**:
- New table `tenant_phone_number`:
  - `phone_number_id` UUID PK
  - `tenant_id` UUID FK
  - `phone_number` TEXT (E.164 format)
  - `area_code` TEXT
  - `carrier` TEXT (`telnyx`)
  - `carrier_provisioning_id` TEXT (Telnyx's reference for the provisioning record)
  - `monthly_fee_cents` INT (for billing tracking and reconciliation)
  - `provisioned_at`, `released_at` TIMESTAMPTZ
  - `status` TEXT (`active | released | provisioning_failed`)
- New module `services/sms_provisioning.py`:
  - `provision_for_tenant(tenant_id) -> ProvisioningResult` — handles area code selection, Telnyx API call, billing integration
  - Default area code: tenant's primary office area code from address
  - Fallback: suggest 3 nearby area codes if primary is unavailable
  - Failure handling: queue SMS attempt; notify owner to retry
- Provisioning trigger: first SMS attempt for a tenant without `tenant_phone_number.status = 'active'` invokes provisioning before send
- Pre-provisioning UI affordance: API endpoint `POST /api/v1/tenants/{tenant_id}/phone-numbers/provision` invokable from `Settings > Integrations > SMS messaging > Set up SMS messaging`
- Subscription billing integration: provisioned number adds `monthly_fee_cents` to tenant's recurring billing line items (existing subscription billing infrastructure handles the addition)
- API: `GET /api/v1/tenants/{tenant_id}/phone-numbers` — list assigned numbers (active and released history)

**Effort estimate**: Medium — 3 days (schema + provisioning service + Telnyx integration + billing integration + failure handling).

### A62. Free-Form Reply Composition Endpoints

**Triggered by**: Tier 1.5 Decision 7 — free-form tech reply UI.

**Scope**:
- API: `POST /api/v1/communications/threads/{thread_id}/reply` — send a free-form reply
  - Request body: `{body: str, composition_method: 'free_form_text' | 'free_form_voice', voice_audio_id: UUID?}`
  - Validates: body within segment limits; tenant within quota (per A65); thread status is `active`
  - Computes `segment_count` from body (160 GSM chars per segment for plain ASCII; 70 chars for Unicode)
  - Pre-commit staleness check per arch doc §16.4 (concurrent thread modifications)
  - Dispatches via `SmsCarrier.send_message()` (per A59)
  - Updates `customer_communication_message` and `customer_communication_thread.last_message_at`, `.message_count`
  - Decrements tenant quota (per A65)
  - Audit log entry per Tier 1.5 Decision 14
- Optimistic UI support: 200 response includes the new message in the thread payload
- Validation rules:
  - Body cannot be empty
  - Body length cap: 1600 characters (10 segments) — protects against runaway voice transcriptions
  - Quota check returns 402 if hard cap reached; 200 with overage flag if soft cap; 200 normal if within quota
- Real-time delivery to other tenant users via SSE per arch doc §13.11

**Effort estimate**: Small — 2 days.

### A63. Voice-to-Text Reply Integration

**Triggered by**: Tier 1.5 Decisions 7, 9 — voice-to-text composition flow and `reply_to_customer_sms` voice intent.

**Scope**:
- New voice intent `reply_to_customer_sms` added to voice intent registry (`api/voice/intents.py`)
- Intent handler:
  - Extract customer identifier from utterance (most recent active thread by default; explicit by name/job context if specified)
  - Extract message body
  - If ambiguous (sounds like template + free-form), AI clarifies: "Is this a template or free-form?"
  - Call `customer_communication_preview_service.render(...)` with composition_method `free_form_voice`
  - Render preview: "I'll send to [customer]: '[body].' That's [segment_count] segments, you have [remaining] left this month. Confirm?"
  - On confirmation, invoke A62 `POST /threads/{thread_id}/reply` with `voice_audio_id` populated
- Voice anywhere: voice composition can be initiated from any screen per Flow 4 Decision 7's "Voice override anywhere" pattern
- The voice composition path on mobile reply UI (per Tier 1.5 Decision 7) calls the same intent flow
- `voice_audio_id` references `voice_command_log.id` to maintain audit trail
- Confirm-as-turn safeguard per arch doc §16.3
- Always-preview-before-send safeguard per arch doc §16.7

**Effort estimate**: Small-Medium — 2–3 days (intent handler + preview rendering + integration with A62).

### A64. Owner Visibility Surfaces — Web Comm History Extension and Dashboard Widget

**Triggered by**: Tier 1.5 Decision 6 — owner visibility.

**Scope**:
- Web `Customers > [customer] > Comm history` surface extended:
  - Two-direction message rendering (outbound: brand-indigo left-aligned; inbound: neutral right-aligned; chat-style bubbles)
  - Threaded by `thread_id`; multiple threads per customer when multiple techs have communicated
  - API: `GET /api/v1/customers/{customer_id}/communication-history` — returns threaded message list grouped by thread
  - Real-time updates via SSE per arch doc §13.11
- New dashboard widget: "Recent customer messages"
  - API: `GET /api/v1/dashboard/widgets/recent-customer-messages?limit=10` — returns last N messages across the tenant (cross-customer, cross-tech)
  - Each row shows: customer name, tech name, direction, last message preview, time
  - Widget config (per Pass 2 §5 pin-to-dashboard pattern): owner pins to dashboard, configurable `limit`
  - Real-time updates via SSE
- Mobile owner: per Tier 2 #5 default policy for Customer activity category (push ON for owners by default; can be muted)

**Effort estimate**: Small-Medium — 2–3 days.

### A65. SMS Quota Tracking and Cap Enforcement

**Triggered by**: Tier 1.5 Decision 8 — subscription quota model.

**Scope**:
- New table `sms_quota_period`:
  - `period_id` UUID PK
  - `tenant_id` UUID FK
  - `period_start`, `period_end` TIMESTAMPTZ (aligned to subscription billing cycle)
  - `included_segments` INT (computed: 100 base + 100 per active add-on number)
  - `used_segments` INT (incremented atomically per outbound send)
  - `overage_segments` INT (computed: max(0, used - included); for billing)
  - `cap_policy` TEXT (`soft | hard`; copied from tenant setting at period start to lock in policy mid-period)
- New tenant setting `sms_quota_cap_policy` (`soft | hard`; default `soft`; owner-only edit)
- Setting placement: `Settings > Subscription & Billing > SMS quota`
- New module `services/sms_quota.py`:
  - `check_quota(tenant_id, requested_segments) -> QuotaCheckResult` — returns `{allowed: bool, overage: bool, blocked_reason: str?}`
  - `consume_quota(tenant_id, segments)` — atomic increment; rolls back on send failure
  - Hard cap: `check_quota` returns `allowed: False, blocked_reason: 'monthly_quota_reached'` when used + requested > included
  - Soft cap: `check_quota` always returns `allowed: True`; flags `overage: True` when crossing the threshold
- Periodic notification dispatch:
  - 80% usage: push + email to owner via `notification_outbox` (Billing category from Tier 2 #5)
  - 100% usage: push + email; if soft cap, includes overage rate; if hard cap, includes "techs cannot send more SMS until [billing date]"
  - Celery task `monitor_sms_quota_thresholds` runs hourly to detect threshold crossings
- Period rollover: scheduled Celery task `rollover_sms_quota_periods` runs daily; creates new `sms_quota_period` row for tenants whose subscription cycle just rolled
- Billing integration: at month-end, `overage_segments × $0.05` added to tenant invoice
- API: `GET /api/v1/sms/quota` — returns current period status (used, remaining, projected month-end based on current pace, policy)
- Failed send refund: if `SmsCarrier.send_message()` returns failure, `consume_quota` is rolled back atomically
- **TCPA opt-out enforcement** (per A59): `check_quota()` first checks `customer.sms_opted_out` for the recipient customer. If TRUE, returns `{allowed: false, blocked_reason: 'customer_opted_out'}`. Outbound SMS to opted-out customers is blocked at the quota layer regardless of available segments. This ensures Pilot does not send SMS to customers who have opted out, satisfying TCPA legal requirements.
- Audit log entry on blocked-by-opt-out attempts for compliance review

**Effort estimate**: Medium — 4 days (schema + quota service + billing integration + period rollover + notifications + Celery tasks).

### A66. Mobile Inbox "Customer Messages" Sub-Section + Conversation Thread Screen

**Triggered by**: Tier 1.5 Decisions 7, 10 — mobile UI surfaces.

**Scope**:
- API: `GET /api/v1/mobile/inbox/customer-threads` — returns recent threads for the requesting tech
  - Default: last 5 threads, ordered by `last_message_at` desc
  - Paginated for full inbox view
  - Response per thread: `{thread_id, customer_name, last_message_preview (first 80 chars), last_message_at, unread_count, originating_job_context (if available)}`
- API: `GET /api/v1/communications/threads/{thread_id}/messages?limit&before` — returns full message history for a thread, paginated
- API: `POST /api/v1/communications/threads/{thread_id}/mark-read` — marks all unread messages in thread as read; updates per-user read state
- New table `customer_communication_message_read_state`:
  - `(message_id, user_id)` composite PK
  - `read_at` TIMESTAMPTZ
- Real-time updates via SSE per arch doc §13.11 — when a new inbound arrives in an open thread, it appears immediately
- Push notification deep-link target: tapping a customer-message push opens the conversation thread screen for that thread
  - Push payload includes `thread_id` for deep-link routing
- Unread count computation: COUNT of inbound messages without a read_state row for the requesting user

**Effort estimate**: Medium — 3–4 days (multiple endpoints + read state schema + SSE integration + push deep-link).

## Additions from Pass 4 Tier 2 #6 (Voice Persona Tone)

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

## Additions from Pass 4 Tier 2 #7 (Account Settings)

### A68. Tenant MFA Policy + Grace Period Enforcement

**Triggered by**: Decisions 8, 9 — tenant policy toggle + grace period + login-trigger enforcement.

**Scope**:

**Schema**:
- New tenant settings:
  - `tenant_mfa_required` BOOLEAN DEFAULT false
  - `tenant_mfa_required_grace_period_starts_at` TIMESTAMPTZ NULL — set when policy toggles on; remains NULL when off
  - `tenant_mfa_grace_period_days` INTEGER DEFAULT 7 — tenant-overridable but standard
- Setting placement: `Settings > Users & Roles > Security policy` per Settings IA framework
- Owner-only edit per Settings IA framework Decision 8

**Login-trigger enforcement middleware**:
- New middleware in API request pipeline: after authentication, before route handling
- Check: if `tenant_mfa_required = true` AND user has no enrolled MFA methods AND request is a login event OR user is in grace period AND has logged in since grace started
- If check passes: redirect / 403 with `enrollment_required: true` payload that frontend uses to route to MFA enrollment flow
- Existing authenticated sessions: not affected by enforcement until next login (per Decision 9)

**Grace period tracking**:
- New table `mfa_grace_period_tracking`
  - `tenant_id` UUID
  - `user_id` UUID
  - `grace_started_at` TIMESTAMPTZ
  - `enrolled_at` TIMESTAMPTZ NULL
  - `enforcement_activated_at` TIMESTAMPTZ NULL — set when user logs in mid-grace, activating immediate enforcement
  - Unique constraint on (tenant_id, user_id)
- Created when user is in tenant during grace period; updated on enrollment or enforcement activation

**Daily reminder Celery task**:
- New task `notify_mfa_grace_period_reminders` runs daily at 9 AM tenant local time
- Identifies tenants with active grace period; for each tenant with unenrolled users, dispatches notification (push + email + in-app banner)
- Reminder copy escalates by day: gentle days 0–3, urgent days 4–6, critical day 7
- Day 7 reminder uses forced-minimum push per Tier 2 #5 critical sub-trigger

**APIs**:
- `PUT /api/v1/settings/tenant/mfa-required` — set tenant policy (RBAC: owner only)
- `GET /api/v1/users/me/mfa-status` — returns enrolled methods + tenant policy + grace period state for the requesting user
- Login endpoint (existing) extended to return `enrollment_required` flag when applicable

**Cross-check verification before B13 starts** (April 30, 2026):

- **G2 (User Profile Management endpoints)**: PRD §3.5 + arch doc §4.8 imply profile management uses existing user model. Verify endpoints exist: `PATCH /api/v1/users/me/profile` (display name, time zone, phone, language); `POST /api/v1/users/me/profile/photo` (S3 presigned URL upload). Likely pre-existing.
- **G3 (Password change cross-device session invalidation)**: per A70 expanded scope above, B13 must wire the password change endpoint to A70's revoke-others logic. Verify password change endpoint exists; add the integration hook in B13 (0.5 day).
- **G4 (Tax Setup JIT 412 response)**: arch doc §4.7.6 specifies invoice generation returns 412 (Precondition Required) with structured payload when tax setup is incomplete. Verify existing invoice creation endpoint enforces this precondition. If missing, add to B14 (or earliest invoice-related batch) scope (estimated 0.5–1 day: precondition check before invoice creation).

**Effort estimate**: Medium — 4–5 days. Schema + middleware + grace period state machine + Celery reminder task + API endpoints. The login-trigger logic with grace period state interaction is the cost driver.

### A69. Multi-Method MFA Enrollment + Method Management + Recovery Codes

**Triggered by**: Decisions 4, 5, 10 — three-method enrollment with self-service + login-time method selection + recovery codes + owner reset.

**Scope**:

**Schema**:
- New table `user_mfa_method`
  - `mfa_method_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID
  - `method_type` TEXT (`totp | sms | email`)
  - `enrolled_at` TIMESTAMPTZ
  - `last_used_at` TIMESTAMPTZ NULL
  - `cognito_method_id` TEXT — Cognito's reference for this method
  - `verification_status` TEXT (`verified | needs_reverification`) — needs_reverification when phone changes per Cross-Domain B
  - `metadata` JSONB — method-specific (e.g., last 4 digits of phone for SMS display)
  - Unique constraint on (tenant_id, user_id, method_type) — one of each method per user max
- New table `user_mfa_recovery_code`
  - `code_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID
  - `code_hash` TEXT — hashed recovery code (never stored plaintext after initial display)
  - `generated_at` TIMESTAMPTZ
  - `used_at` TIMESTAMPTZ NULL
  - `set_id` UUID — group of 10 codes generated together
- Recovery codes generated as cryptographically random 10-character codes; hashed via bcrypt before storage

**APIs**:
- `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-start` — initiate enrollment for a method (returns QR code for TOTP, sends code for SMS/Email)
- `POST /api/v1/users/me/mfa/methods/{method_type}/enroll-confirm` — confirm enrollment with code; method becomes active
- `DELETE /api/v1/users/me/mfa/methods/{method_id}` — remove method (with safeguards from Decision 4)
- `POST /api/v1/users/me/mfa/recovery-codes/generate` — generate new set of 10 codes; return plaintext (only time they're visible); invalidate any unused codes from prior set
- `GET /api/v1/users/me/mfa/recovery-codes/status` — returns count of unused codes
- `POST /api/v1/users/me/mfa/login-challenge/initiate` — initiate MFA challenge after password verification; returns enrolled methods
- `POST /api/v1/users/me/mfa/login-challenge/verify` — verify code from chosen method; on success, completes login
- `POST /api/v1/admin/users/{user_id}/mfa/reset` — owner reset of user MFA (RBAC: owner only); deletes all methods + recovery codes; sends notification to user

**Cognito integration**:
- Each method type maps to Cognito's MFA configuration
- Cognito handles the actual code verification and challenge flow
- Pilot stores the metadata + tracks state; Cognito stores the cryptographic material

**Effort estimate**: Large — 7–9 days. Schema + Cognito integration for three method types + enrollment flows + login challenge flow + recovery codes + owner reset. The Cognito MFA integration for three methods is the cost driver — each method has slightly different Cognito API patterns.

### A70. Active Sessions List + Revoke

**Triggered by**: Decision 6 — active sessions UX.

**Scope**:

**Schema**:
- Existing Cognito session tracking + refresh token storage already captures most needed metadata
- New table `user_session_metadata` (extension of existing token storage)
  - `session_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID
  - `device_fingerprint` TEXT — User-Agent + other characteristics
  - `display_label` TEXT — e.g., "Chrome on macOS" or "Pilot mobile on iPhone"
  - `ip_address` INET
  - `geolocation` TEXT — city/state from IP geolocation (approximate)
  - `created_at`, `last_active_at` TIMESTAMPTZ
  - `revoked_at` TIMESTAMPTZ NULL
- Populated on login from User-Agent parsing + IP geolocation lookup

**APIs**:
- `GET /api/v1/users/me/sessions` — list all active sessions for requesting user
- `DELETE /api/v1/users/me/sessions/{session_id}` — revoke a specific session (invalidate refresh token; clear access token cache)
- `POST /api/v1/users/me/sessions/revoke-others` — bulk revoke all sessions except the current one

**Password change cross-device session invalidation** (per cross-check finding G3 / arch doc §4.8.1): when implementing B13, the password change endpoint (likely pre-existing per cross-check finding A4 — verify via `/api/v1/users/me/change-password` or equivalent) must be wired to call the same logic as `revoke-others` on successful password change. This ensures all sessions other than the current one are auto-revoked when password changes — security best practice.

**B13 implementation note**: pre-batch verification finds the existing password change endpoint; B13 adds the post-success hook to call `revoke-others` logic (extracted from the API handler into a shared service function so both the API and the password-change hook can call it). Estimated 0.5 day of integration work in B13 scope.

**Geolocation provider**: existing Pilot infrastructure can use a lightweight IP-to-location service (MaxMind GeoLite2 free tier, or similar). City-level accuracy is adequate; this isn't security-critical, just informational.

**Effort estimate**: Small-Medium — 3 days (schema extension + APIs + geolocation lookup integration + User-Agent parsing).

### A71. Data Export Request Pipeline

**Triggered by**: Decision 7 — data export request flow.

**Scope**:

**Schema**:
- New table `data_export_request`
  - `export_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID — the requesting user
  - `requested_at` TIMESTAMPTZ
  - `status` TEXT (`pending | processing | ready | expired | failed`)
  - `s3_path` TEXT NULL — set when ready
  - `signed_url` TEXT NULL — set when ready; signed S3 URL with 7-day expiration
  - `expires_at` TIMESTAMPTZ NULL — 7 days after ready
  - `data_scope` TEXT — `full_tenant` (owner) or `user_specific` (technician)
  - `failure_reason` TEXT NULL
- Frequency limit: max one pending or recent (within 24h) request per user

**Export pipeline** (`tasks/data_export_pipeline.py`):
- Celery task that processes pending exports
- Queries data per RBAC scope
- Streams to S3 in chunks (avoids in-memory bloat for large tenants)
- Generates CSV files per entity type: customers.csv, jobs.csv, quotes.csv, invoices.csv, time_entries.csv, expenses.csv, communications.csv, etc.
- Bundles into ZIP with MANIFEST.json containing metadata
- Generates signed S3 URL with 7-day expiration
- Sends email to requesting user with download link
- Updates `data_export_request.status` to `ready`

**APIs**:
- `POST /api/v1/users/me/data-exports` — request a new export (subject to 24h frequency limit)
- `GET /api/v1/users/me/data-exports` — list recent exports for the requesting user
- `GET /api/v1/users/me/data-exports/{export_id}` — get specific export status

**Email template**: new transactional email "Your data export is ready" with download link + expiration date.

**Effort estimate**: Medium — 4–5 days. The export pipeline itself is the cost driver — handling large datasets (some tenants may have years of data) without memory bloat requires careful streaming. Email integration uses existing notification infrastructure.

## Additions from Pass 4 Tier 3 #8 + #9 (States Catalog + First-Time-User States)

### A72. First-Session Detection for First-Time-User States

**Triggered by**: Cross-Domain B — first-time-user state rendering requires backend tracking of session history.

**Scope**:
- New table `user_session_history`
  - `tenant_id` UUID
  - `user_id` UUID
  - `first_login_at` TIMESTAMPTZ
  - `total_session_count` INTEGER DEFAULT 0
  - `last_login_at` TIMESTAMPTZ
  - Unique on (tenant_id, user_id)
- Increment `total_session_count` on every successful login
- Set `first_login_at` only on the row's first creation
- API: `GET /api/v1/users/me/session-history` — returns the user's first_login_at and total_session_count
- Frontend uses this on app load to determine first-time-user status:
  - `isFirstTime = total_session_count <= 3 || first_login_at >= 7 days ago`
- Cached on the frontend for the session duration; refreshed on next login

**Effort estimate**: Small — 1–2 days. Schema + endpoint + login-flow integration.

## Additions from Pass 4 Tier 3 #10 + #11 (Onboarding Flow and Mobile Push Permission)

### A73. Trial State Machine + Tenant Signup

**Triggered by**: Decisions 2, 5, 10, 11 — trial-as-tier framing, tenant signup, trial expiration, wizard resumability.

**Scope**:

**Schema**:
- New table `tenant_signup`
  - `tenant_id` UUID PK
  - `signup_state` TEXT (`step1_account | step2_legal | step3_phone | step4_tier | step5_confirm | complete`)
  - `signup_started_at` TIMESTAMPTZ
  - `signup_completed_at` TIMESTAMPTZ NULL
  - `business_name`, `trade`, `business_size`, `zip`, `time_zone` — collected during step 1
- Tenant table extended with:
  - `current_subscription_tier_id` FK → subscription_tier
  - `trial_started_at` TIMESTAMPTZ NULL
  - `trial_ends_at` TIMESTAMPTZ NULL
  - `trial_length_days_override` INTEGER NULL — set by operator if differs from system default
  - `stripe_customer_id` TEXT NULL — populated on first paid conversion

**Services**:
- `services/tenant_signup.py` — handles the wizard state machine
- `services/trial_management.py` — handles trial expiration, paywall enforcement, conversion

**Trial expiration enforcement**:
- New Celery task `enforce_trial_expirations` runs hourly
- For tenants where `trial_ends_at <= now()` and tier is still trial, transitions to `trial_expired` state
- Sends paywall notification (push + email + in-app banner)

**Pre-expiration warning sequence** (per cross-check finding G8 / arch doc §4.7.5): four scheduled warning notifications fire before expiration to give tenants time to convert:

| Days before expiration | Notification urgency | Channels | Notes |
| :--- | :--- | :--- | :--- |
| 7 days | Gentle | Push + email + in-app banner | "Your trial ends in 7 days. Pick a plan to keep using Pilot." |
| 3 days | More urgent | Push + email + in-app banner | Same channels, more urgent copy |
| 1 day | Final | Push + email + in-app banner | Final notice |
| 0 days (day of expiration) | Critical | Push + email + in-app banner; paywall activates | Tenant transitions to trial_expired state at scheduled hour |

Implementation: `enforce_trial_expirations` Celery task runs hourly and dispatches the appropriate warning based on time-to-expiration. Notification routes through `notification_outbox` per Tier 2 #5 "Billing" or "System announcements" category (final decision per Pilot operator).

In-app banner persistence: starting 7 days before expiration, an in-app banner appears in the active session and persists until tenant either upgrades or expiration occurs. Banner is dismissable per session but reappears on next session.

**APIs**:
- `POST /api/v1/signup` — initiate signup; creates tenant in `step1_account` state
- `PUT /api/v1/signup/{tenant_id}/step{N}` — advance the wizard one step at a time
- `GET /api/v1/signup/{tenant_id}/state` — get current signup state for resumability

**Effort estimate**: Medium-Large — 5–6 days. Schema + state machine + trial expiration enforcement + APIs + Celery tasks.

### A74. Legal Acceptance Recording

**Triggered by**: Decision 3 — legal acceptance during wizard step 2.

**Scope**:
- New table `tenant_legal_acceptance`
  - `acceptance_id` UUID PK
  - `tenant_id` UUID FK
  - `user_id` UUID FK — the user who accepted (the owner during signup)
  - `document_type` TEXT (`tos | privacy | eula | marketing_email_optin`)
  - `document_version_hash` TEXT — hash of the document text version accepted
  - `accepted_at` TIMESTAMPTZ
  - `ip_address` INET
  - `user_agent` TEXT
- Per (tenant_id, user_id, document_type) — multiple rows allowed if document version changes and user re-accepts
- API: `POST /api/v1/signup/{tenant_id}/legal/accept` — record acceptance; called per checkbox check
- API: `GET /api/v1/signup/{tenant_id}/legal/required` — returns list of legal documents that need acceptance (fresh on signup; only previously-unaccepted-versions on subsequent re-acceptance flows)

**Document version hashing**: each legal document has a version hash computed from its content. Hash changes when document content changes. Tenants whose accepted hash differs from current are prompted to re-accept on next login.

**Phase 2**: re-acceptance flow when documents change. MVP: documents are versioned but re-acceptance is a separate flow not in MVP scope.

**Effort estimate**: Small — 2 days. Schema + recording API + version hashing.

### A75. Subscription Tier Infrastructure

**Triggered by**: Decision 5 — tier selection, trial-as-tier framing.

**Scope**:
- New table `subscription_tier`
  - `tier_id` UUID PK
  - `tier_name` TEXT (`trial | starter | professional | enterprise | ...`)
  - `display_label` TEXT — user-facing label
  - `monthly_price_cents` INTEGER NOT NULL — `0` for trial
  - `is_trial` BOOLEAN — true only for the trial tier
  - `trial_duration_days` INTEGER NULL — set for trial tier; system default
  - `max_users` INTEGER NOT NULL — user count limit
  - `max_sms_segments_per_month` INTEGER NULL — null = unlimited; otherwise enforced (overage billing per Tier 1.5)
  - `is_active` BOOLEAN — true if available for new signups
  - `display_order` INTEGER — order in tier picker UI
- Seed data: Trial, Starter, Professional, Enterprise per Decision 5 placeholder values
- Frontend reads from this table at render time; tier names/prices/limits flexible via DB updates

**Operator-controlled overrides**:
- New table `tenant_tier_override`
  - `tenant_id` UUID PK
  - `override_tier_id` UUID FK → subscription_tier — if set, supersedes normal tier
  - `override_trial_length_days` INTEGER NULL — if set, supersedes system default
  - `override_reason` TEXT NULL — operator note
  - `set_by_operator_user_id` UUID
- Read by tenant signup flow and trial expiration flow

**Usage tracking**:
- New table `tenant_subscription_usage`
  - `tenant_id` UUID
  - `period_start`, `period_end` TIMESTAMPTZ — aligned to subscription billing cycle
  - `current_user_count` INTEGER
  - `current_sms_segment_count` INTEGER (links to A65 from Tier 1.5)
- Updated by user-add events and SMS-send events

**APIs**:
- `GET /api/v1/subscription-tiers` — returns active tiers for tier picker
- `GET /api/v1/tenants/{tenant_id}/subscription` — returns current tier + usage stats
- `PUT /api/v1/tenants/{tenant_id}/subscription/upgrade` — initiate tier change (calls into A76 for Stripe)

**Tier limit enforcement**:
- User-add flow checks `current_user_count >= max_users`; if so, returns Er3-class error with "Upgrade tier" CTA
- SMS-send flow checks `current_sms_segment_count >= max_sms_segments_per_month`; per Tier 1.5 quota model

**Effort estimate**: Medium — 4 days. Schema + tier picker API + usage tracking + limit enforcement.

### A76. Stripe Integration for Paid Conversion

**Triggered by**: Decisions 5, 6 — Stripe payment for paid tier selection.

**Scope**:

**Stripe Elements integration**:
- Frontend uses Stripe Elements (card input + address input)
- Backend creates Stripe Customer record on tenant signup with paid tier (or first conversion)
- Backend creates Stripe Subscription with the selected tier's price ID
- On successful subscription creation, tenant tier is updated to the paid tier and trial is converted

**Stripe Webhooks**:
- New endpoint `POST /api/v1/webhooks/stripe` — receives Stripe webhook payloads with signature verification
- Handles events:
  - `customer.subscription.created` — confirm tier activation
  - `customer.subscription.updated` — handle tier changes
  - `invoice.paid` — confirm successful payment
  - `invoice.payment_failed` — trigger payment retry / paywall
  - `customer.subscription.deleted` — handle cancellation
- Stripe webhook signing secret stored in environment

**Webhook idempotency dedup** (per cross-check finding A1 / arch doc §20.6) — Stripe explicitly delivers webhooks multiple times and recommends idempotency. Without dedup, a webhook retry (e.g., `invoice.paid` received twice) could double-record a payment or double-activate a subscription tier. Dedup table:

```sql
stripe_webhook_event_processed (
    event_id      TEXT PRIMARY KEY,    -- Stripe event ID (e.g., "evt_1abc...")
    processed_at  TIMESTAMPTZ NOT NULL,
    event_type    TEXT NOT NULL
)
```

Handler flow:
1. On webhook arrival, after signature verification, check `event_id` in `stripe_webhook_event_processed`
2. If already exists → return 200 idempotently without reprocessing
3. If not → INSERT row + process event → return 200
4. Use SQL transaction to make insert + processing atomic; if processing fails, don't mark as processed

Cleanup: `cleanup_incomplete_stripe_payment_intents` Celery task per §3.2 cleans up abandoned payment intents; the dedup table itself does not require cleanup (event IDs are small text; retention is indefinite for audit purposes).

**Tier conversion APIs**:
- `POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial` — initiates conversion; expects Stripe Payment Method ID from frontend Stripe Elements
- `POST /api/v1/tenants/{tenant_id}/subscription/change-tier` — changes between paid tiers (Phase 2 surface; backend supports)

**Payment failure handling**:
- On Stripe payment failure during signup wizard step 5, return Er2 (validation error) state
- For ongoing subscription payment failures, Stripe handles retries (3 attempts over 7 days); after exhaustion, tenant moves to "payment failed" state with paywall

**Phase 2**:
- Stripe Customer Portal for self-service payment method updates
- Annual billing discount
- Coupon / promo code support

**Effort estimate**: Medium-Large — 5.5–6.5 days. Stripe Elements integration + Subscriptions API + webhooks + payment failure handling + webhook dedup table. Stripe API integration is the cost driver; +0.5 day for webhook dedup per cross-check finding A1.

### A77. Onboarding State Tracking + Checklist Resumability

**Triggered by**: Decisions 7, 11 — checklist persistence + auto-completion + wizard resumability.

**Scope**:

**Checklist state**:
- New table `tenant_onboarding_checklist`
  - `tenant_id` UUID PK
  - `account_created` BOOLEAN — auto-set on signup completion
  - `legal_accepted` BOOLEAN — auto-set on legal acceptance
  - `tier_selected` BOOLEAN — auto-set on tier selection
  - `first_customer_added` BOOLEAN — auto-set on first customer create
  - `first_customer_added_at` TIMESTAMPTZ
  - `catalog_setup` BOOLEAN — auto-set on first catalog item added
  - `catalog_setup_at` TIMESTAMPTZ
  - `quickbooks_connected` BOOLEAN — auto-set on QB OAuth complete
  - `quickbooks_skipped` BOOLEAN — set when user clicks Skip in checklist
  - `calendar_connected` BOOLEAN — auto-set on Calendar OAuth complete
  - `calendar_skipped` BOOLEAN — set when user clicks Skip in checklist
  - `team_invited` BOOLEAN — auto-set on first team invite sent
  - `team_skipped` BOOLEAN — set when user clicks Skip in checklist
  - `checklist_hidden` BOOLEAN — set when user clicks "Hide" in widget
  - `checklist_dismissed_permanently` BOOLEAN — set when user clicks "Don't show again"

**Auto-completion detection**:
- Customer create event → check tenant onboarding state; if `first_customer_added` not yet set, mark true
- Catalog item create event → similar
- QB OAuth complete event → similar
- Calendar OAuth complete event → similar
- Team invite send event → similar
- Each detection runs on the existing event/action handlers in those domains

**APIs**:
- `GET /api/v1/tenants/{tenant_id}/onboarding/checklist` — returns checklist state for widget rendering
- `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/skip/{item}` — mark an item as skipped
- `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden` — toggle widget visibility
- `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/dismissed` — permanent dismiss

**Effort estimate**: Small-Medium — 3 days. Schema + auto-completion event handlers + APIs + widget state management.

### A78. Mobile Push Permission Tracking + Degraded-Mode Fallback

**Triggered by**: Decisions 12, 13, 14, 15 — push permission flow.

**Scope**:

**Schema**:
- New table `mobile_push_permission_state`
  - `tenant_id` UUID
  - `user_id` UUID
  - `device_id` UUID — references A51 push token registry
  - `permission_state` TEXT (`not_asked | granted | denied_by_user_choice | denied_by_os | revoked_in_settings`)
  - `last_state_change_at` TIMESTAMPTZ
  - `dismissable_banner_dismissed_at` TIMESTAMPTZ NULL — for the "push is off" banner reappearance logic

**Mobile app integration**:
- Mobile app reads `permission_state` on launch
- If `permission_state = not_asked` and onboarding is complete, mobile app starts the mobile setup phase (per Decision 8) including the push permission request screen
- If `permission_state = granted`, push token registered via A51
- If `permission_state = denied_*`, dismissable banner shows on Today tab per Decision 14

**APIs**:
- `PUT /api/v1/users/me/devices/{device_id}/push-permission` — update permission state from mobile app
- `GET /api/v1/users/me/devices/{device_id}/push-permission` — get current state (used on app launch)

**Banner reappearance logic**:
- Banner shows on Today tab when `permission_state` is denied
- User can dismiss the banner; recorded in `dismissable_banner_dismissed_at`
- Banner reappears once after 7 days from dismissal
- After second dismissal, banner doesn't reappear

**Effort estimate**: Small — 2 days. Schema + APIs + mobile app state coordination.

## Additions from Pass 4 Tier 4 #12 (In-Flight Sync Indicator with Pending Count)

### A79. Unified Pending-Count Exposure for Sync Surfaces

**Triggered by**: Decisions 1, 3, 4 — pending-count visibility across all four sync surfaces.

**Scope**:

**Unified pending-count API**:
- New endpoint: `GET /api/v1/sync/{surface}/status` — returns sync state + pending count for a given surface
- Path parameter `surface`: `calendar | quickbooks | mobile_data | background`
- Response shape:
  ```json
  {
    "surface": "calendar",
    "state": "synced_pending | syncing | sync_error | sync_paused | synced_idle",
    "pending_count": 3,
    "pending_items": [
      {"type": "event_added", "label": "Johnson panel upgrade — 4:30 PM today"},
      {"type": "event_updated", "label": "Smith service call — moved to Friday"},
      {"type": "event_deleted", "label": "Davis estimate — removed externally"}
    ],
    "last_sync_at": "2026-04-27T14:32:18Z",
    "next_sync_at": "2026-04-27T14:37:18Z",
    "manual_trigger_supported": true,
    "resolve_target": null
  }
  ```
- Pending items array capped at 5 by server (matches tooltip cap from Decision 2)

**Backend reads from existing per-surface tables**:
- Calendar: aggregates from `calendar_sync_pending_change` table
- QuickBooks: aggregates from `integration_sync_pending_change` (filtered for QB)
- Mobile: aggregates from `mobile_sync_pending_operation` (filtered for the device or tenant scope)
- Background: aggregates from `mobile_sync_pending_operation` + `mobile_sync_session` last outcome

**SSE event emission**:
- Existing SSE channels emit `sync_status_changed` events when state or count changes for any surface
- Frontend subscribes to relevant channels and re-renders indicator on event

**Manual trigger endpoints**:
- Existing endpoints for triggering syncs already exist per individual flow specs:
  - `POST /api/v1/integrations/calendar/sync` — triggers immediate calendar sync
  - `POST /api/v1/integrations/quickbooks/sync` — triggers immediate QB sync
  - `POST /api/v1/mobile/sync-now` — triggers immediate mobile sync session
- A79 doesn't add new trigger endpoints; just confirms existing ones support the indicator's manual-trigger affordance

**New tenant setting**:
- `tenant_sync_indicator_pending_amber_threshold` (integer, default 5, range 1–100) per Decision 5
- Standard read/write via A52/A54 from Tier 2 #4

**Effort estimate**: Small — 2 days. The infrastructure exists; A79 is API consolidation + SSE event wiring + the threshold setting. Most of the work is in the frontend component (separate frontend effort, not in this backend addition).

## Additions from Pass 4 Tier 4 #13 (Customer-Facing Public Quote/Invoice Link Styling)

### A80. Signed URL Infrastructure for Public Quote/Invoice Links

**Triggered by**: Decisions 1, 4, 6, 11 — public access via signed URLs with 90-day expiration plus optional SMS short-link support.

**Scope**:

**Schema** (extends existing):
- `quote_public_link` and `invoice_public_link` tables already exist per arch doc
- Add columns to both: `signed_token TEXT NOT NULL` (URL-safe signed token), `expires_at TIMESTAMPTZ NOT NULL`, `revoked_at TIMESTAMPTZ NULL`, `created_by_user_id UUID NOT NULL`
- New table `public_link_short_code`:
  - `short_code TEXT PRIMARY KEY` (5–8 char base62 random)
  - `link_type TEXT` (`quote | invoice`)
  - `link_id UUID FK` — references quote_public_link or invoice_public_link
  - `created_at TIMESTAMPTZ`
  - Unique constraint enforces collision avoidance

**Token generation**:
- HMAC-signed token using a per-deployment secret
- Payload includes: link_id, link_type, expiration, customer_id (for verification)
- Tokens are URL-safe base64-encoded
- Verification at request time validates signature + expiration + revocation status

**Public access endpoints**:
- `GET /api/v1/public/quotes/{signed_token}` — returns quote payload for rendering
- `POST /api/v1/public/quotes/{signed_token}/accept` — accept quote with optional comment
- `POST /api/v1/public/quotes/{signed_token}/decline` — decline quote with reason + comment
- `GET /api/v1/public/invoices/{signed_token}` — returns invoice payload for rendering
- `POST /api/v1/public/invoices/{signed_token}/payment-intent` — initiate Stripe Payment Intent (per A81)

**Short-link redirect**:
- `GET /api/v1/short/{short_code}` — resolves short code to signed URL and 302-redirects
- Domain configuration: `pilot.tr` or similar Pilot-owned short domain (TBD; Tom owns)
- Click tracking captures user-agent and IP for Phase 2 analytics

**Revocation**:
- `POST /api/v1/quotes/{quote_id}/public-link/revoke` — manually revoke (RBAC: tenant user with quote access)
- Revocation invalidates the signed URL immediately; subsequent access shows expired page

**No customer authentication** — clicking the link IS the access. The signed URL is the credential.

**Effort estimate**: Medium — 4 days. Token generation/verification + endpoints + short-link infrastructure (if pilot.tr domain ready) + revocation.

### A81. Stripe One-Time Payment for Invoices with Amount Variance

**Triggered by**: Decisions 4, 5, 12 — Stripe payment integration for invoice payment with variance handling.

**Scope**:

**Stripe Payment Intents integration**:
- Frontend uses Stripe Elements (card input + address input) on the public invoice page
- Backend creates Stripe Payment Intent for the customer-entered amount
- Customer-entered amount can differ from invoice total; comment is required by frontend validation when amount differs
- On successful payment confirmation from Stripe webhook, Pilot records the payment

**Schema**:
- Existing `payment` table extended:
  - `stripe_payment_intent_id TEXT`
  - `customer_payment_comment TEXT NULL`
  - `amount_variance_cents INTEGER NULL` — calculated as `amount_paid - invoice_total` (negative for underpayment, positive for over)
  - `paid_via TEXT` — `stripe | check | bank_transfer | other`

**Stripe webhook handler**:
- Existing webhook endpoint from A76 extended to handle Payment Intent events:
  - `payment_intent.succeeded` — record payment, update invoice balance, trigger notification
  - `payment_intent.payment_failed` — surface failure to customer-facing UI
- Invoice balance calculation: `invoice_total - sum(payments_amount_paid)`
- For underpayment (variance < 0), invoice remains in `partial` state with remaining balance
- For overpayment (variance > 0), variance flagged for tenant review (UI shows "Customer paid $X over invoice total — review")

**APIs**:
- `POST /api/v1/public/invoices/{signed_token}/payment-intent` — creates Stripe Payment Intent for the customer-entered amount; returns Stripe client secret for frontend
- `POST /api/v1/public/invoices/{signed_token}/confirm-payment` — frontend calls after Stripe Elements confirms; backend reconciles with webhook

**Stripe Connect consideration**:
- For MVP: single Stripe account model; payments accumulate in Pilot's Stripe account; disbursement to tenant is separate financial process (TBD)
- Phase 2: evaluate Stripe Connect for direct-to-tenant payment routing
- This is an architectural decision Tom should review before MVP launch

**Effort estimate**: Medium — 4–5 days. Stripe Payment Intents + webhook integration + variance handling + accounting reconciliation.

### A82. Email Template Rendering Pipeline + Tenant Brand Customization

**Triggered by**: Decisions 7, 8 — 16 email templates with structured tenant customization.

**Scope**:

**Schema**:
- New table `email_template`
  - `template_id TEXT PRIMARY KEY` (e.g., `quote_sent`, `invoice_sent`, `payment_received`, `welcome`, etc.)
  - `display_name TEXT`
  - `category TEXT` — `customer_facing | internal`
  - `subject_template TEXT` (with variable substitution)
  - `body_html_template TEXT`
  - `body_plain_template TEXT` — text fallback
  - `variables JSONB` — list of supported variables for this template
  - `is_active BOOLEAN`

- New table `tenant_email_branding`
  - `tenant_id UUID PK`
  - `logo_s3_path TEXT NULL`
  - `brand_color_hex TEXT NULL` — defaults to Pilot brand-indigo if null
  - `email_signature TEXT NULL`
  - `custom_footer TEXT NULL`
  - `updated_at TIMESTAMPTZ`

**Template seed data**:
- 16 templates seeded at deployment with placeholder copy
- Tom updates with final copy as pre-launch hygiene work proceeds
- Templates can be edited at the platform level via direct DB updates (operator admin work)

**Rendering pipeline** (`services/email_template_renderer.py`):
- Takes template_id + context payload
- Resolves variables from context: customer name, quote total, signed URL, etc.
- For customer-facing templates: applies tenant branding (logo, color, signature, footer) from `tenant_email_branding`
- For internal templates: uses Pilot standard branding
- Renders both HTML and plain text variants
- Returns ready-to-send email payload for SendGrid

**Tenant branding endpoints**:
- `GET /api/v1/settings/email-branding` — returns current branding for tenant
- `PUT /api/v1/settings/email-branding` — update branding; logo upload uses S3 presigned URL pattern
- `POST /api/v1/settings/email-branding/test-send` — send test email to requesting user's address using current branding settings

**Logo upload** (consistent with Tier 2 #7 profile photo pattern):
- Frontend requests presigned S3 URL
- Frontend uploads to S3
- Backend processes (resize to 400x100 max with transparent background preservation)
- `tenant_email_branding.logo_s3_path` updated

**Live preview**:
- `POST /api/v1/settings/email-branding/preview` — returns sample email rendered with current branding settings (uses welcome template structure as preview content)

**Effort estimate**: Medium — 4–5 days. Template schema + 16 template seeds + rendering pipeline + tenant branding endpoints + logo upload + live preview. Template content authoring is Tom's work, not part of this estimate.

### A83. Quote/Payment Customer Comment Storage with Notifications

**Triggered by**: Decision 9 — entity-bound customer comments with notifications.

**Scope**:

**Schema** (extends existing):
- Add to `quote` table:
  - `customer_acceptance_comment TEXT NULL`
  - `customer_accepted_at TIMESTAMPTZ NULL`
  - `customer_decline_comment TEXT NULL`
  - `customer_decline_reason TEXT NULL` — enum: `pricing | scope | timing | other_contractor | other`
  - `customer_declined_at TIMESTAMPTZ NULL`
  - `customer_email_at_action TEXT NULL` — captured at action time for audit
- Add to `payment` table:
  - `customer_payment_comment TEXT NULL`
  - `amount_variance_cents INTEGER NULL` (already added per A81 schema; same column)

**Action handlers**:
- Quote accept handler (called by A80 acceptance endpoint): updates quote columns + triggers notification
- Quote decline handler: updates quote columns + triggers notification
- Payment handler (already covered by A81): notification on successful payment with comment included if present

**Notifications**:
- Per Tier 2 #5 "Customer activity" category
- Notification body templates include comment text when present
- Push + email per recipient preferences

**UI rendering** (frontend; not backend addition but flagged for completeness):
- Quote detail page shows acceptance/decline comment prominently when present
- Payment detail page shows payment comment with variance indication

**Effort estimate**: Small — 2 days. Schema additions + handlers + notification triggers.

## Additions from Pass 4 Tier 4 #14 (Help / About / Feedback Surfaces)

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

### A89. LOTO (Lock Out / Tag Out) Confirmation Table + Configurable Voice Guard

**Source finding**: FIND-063 (B20, Task 3)

**Scope**:

Create `loto_confirmation` table using `AppendOnlyMixin` (adds `created_at`, `created_by`) plus: `id UUID PK`, `tenant_id UUID FK → tenant.id NOT NULL`, `job_id UUID FK → job.id NOT NULL`, `user_id UUID FK → user.id NOT NULL`, `confirmed_at TIMESTAMPTZ NOT NULL` (canonical confirmation time), `client_capture_at TIMESTAMPTZ NULL` (device time for offline capture), `server_received_at TIMESTAMPTZ NULL` (set by sync on receipt); unique natural-key dedup index on `(user_id, job_id, confirmed_at)`; UNIQUE partial index `(job_id, user_id) WHERE is_active = true`; audit trigger `audit_loto_confirmation_changes`; `guard_created_immutable` trigger.

Add `loto_confirmation_required BOOLEAN NOT NULL DEFAULT false` to `tenant_settings` (via FIND-086/B18 platform_setting migration). Voice AI guard is conditional: when `loto_confirmation_required = true` AND `ctx_dict["safety_loto_verified"] is not True`, job-completion and clock-out voice intents return refusal. When `false`, LOTO confirmation is available as optional audit action (does not gate workflow).

**APIs**:
- `POST /api/v1/jobs/{job_id}/loto-confirmations` — create LOTO confirmation event (offline-capable, `client_capture_at` + `server_received_at` pattern)
- Voice intent: `confirm_loto_via_voice` — writes `LotoConfirmation` row and sets `context["safety_loto_verified"] = True`

**Migration**: `phase_fe_1_batch_b20_loto_confirmation_table`

**Effort estimate**: 4–5 days (table + mixin + voice guard + sync integration + tests)

---

### A90. Category-Specific Markup Management Endpoints

**Source finding**: FIND-055 (B20, Task 1)

**Scope**:

`TenantMarkupVersion` uses temporal versioning via `valid_period TSTZRANGE` with a GIST exclusion constraint preventing overlapping periods per `(tenant_id, job_expense_category_code)`. The table is append-only (identity fields `created_at`, `created_by` are immutable); `valid_period` is updated during temporal supersession — to change a markup, the current row's upper bound is closed and a new row is inserted atomically in a single transaction. GIST enforces exactly one active markup per category at any point in time.

**APIs**:
- `GET /api/v1/settings/markups` — list current active markups per expense category (filtered `valid_period @> now()`)
- `POST /api/v1/settings/markups` — temporal supersession: in one transaction, (1) UPDATE current active row's `valid_period` upper bound to `effective_from`; (2) INSERT new row with `valid_period = tstzrange(effective_from, null, '[)')`. GIST validates no overlap. If no current active row for that category, just INSERT.
- `GET /api/v1/settings/markups/{category_code}/history` — list all historical versions sorted by `valid_period` DESC (audit trail)
- **No PUT/PATCH/DELETE** on historical rows — append-only identity fields; period closures via supersession POST only

**RBAC**: `catalog.manage` (owner/accountant only)

**Effort estimate**: 2–3 days (management endpoints + temporal supersession logic + tests)

---

### A91. Labor Rate Version Management Endpoints + jobs.py Wiring

**Source finding**: FIND-056 (B20, Task 2)

**Scope**:

`LaborRateVersion` uses the same `AppendOnlyMixin` + `valid_period TSTZRANGE` + GIST exclusion pattern as A90, keyed by `(tenant_id, skill_level_code)`. Skill tiers: `apprentice`, `journeyman`, `master`, `foreman`. Each row has `hourly_rate_cents` (base) and `burden_pct NUMERIC(7,4)` (overhead multiplier). Burdened rate = `hourly_rate_cents * (1 + burden_pct)`. Currently `jobs.py` uses `settings.default_labor_rate_cents if settings else 8500` — hardcoded scalar ignoring the catalog.

**APIs** (same temporal supersession pattern as A90):
- `GET /api/v1/settings/labor-rates` — current active rates per skill level (`valid_period @> now()`)
- `POST /api/v1/settings/labor-rates` — temporal supersession: close current active row + INSERT new row
- `GET /api/v1/settings/labor-rates/{skill_level_code}/history` — full audit trail
- No PUT/PATCH/DELETE on historical rows

**Code change (ships with A91)**:
In `backend/api/routes/jobs.py`, replace flat scalar lookup with: query `LaborRateVersion WHERE tenant_id = tenant_id AND skill_level_code = technician.skill_level_code AND valid_period @> now()`; compute burdened rate = `hourly_rate_cents * (1 + burden_pct)`; fall back to `settings.default_labor_rate_cents` only if no catalog entry exists for that skill level.

**RBAC**: `catalog.manage` (owner/accountant only)

**Effort estimate**: 3 days (management endpoints + jobs.py wiring + skill_level check + tests)

---

### A92. Authenticated Invoice CRUD Endpoints + Router Cleanup

**Source finding**: FIND-076 (B20, Task 4)

**Scope**:

No authenticated invoice CRUD handlers exist in the codebase. `backend/api/routes/invoices.py` is scoped exclusively to the public payment link surface. Additionally, two separate routers are registered at `/api/v1/public` — `invoices.public_router` (old SHA-256 hash pattern) and `public_invoices.router` (new A80 HMAC `signed_token` pattern) — creating a route conflict where the older router shadows the newer A80 implementation.

**Router cleanup** (ships with A92): Remove `invoices.public_router` from `invoices.py`; migrate any routes not already in `public_invoices.py` into it; remove `invoices.public_router` registration from `main.py`; `public_invoices.py` becomes the sole owner of all `/api/v1/public/invoices/...` routes.

**APIs** (in `invoices.py` — authenticated):
- `GET /api/v1/invoices` — tenant-scoped list with `status` and `due_date` filter params; RBAC `invoices.view`
- `POST /api/v1/invoices` — create from `quote_id` (copy lines + pricing from quote version) or `job_id` (generate lines from time entries + expenses); RBAC `invoices.create`
- `GET /api/v1/invoices/{id}` — full detail with lines; RBAC `invoices.view`
- `POST /api/v1/invoices/{id}/record-payment` — owner-side payment recording (cash, check, ACH — not Stripe-only); RBAC `invoices.create`

**Pydantic schemas**: `InvoiceCreate`, `InvoiceResponse`, `InvoiceListResponse`, `PaymentRecordRequest`, `PaymentResponse` (addresses FIND-144 phantom schema gap).

**Effort estimate**: 4–5 days (CRUD implementation + router cleanup + schema creation + tests)

---

### A93. Expo Push Delivery

**Source finding**: FIND-078 (B20, Task 5)

**Scope**:

Replace the push delivery stub in `notification_worker.py–66` with real Expo Push Notifications API dispatch. Look up recipient's Expo push token from `mobile_device_push_token` table. POST to `https://exp.host/--/api/v2/push/send` with `to=expo_push_token`, `title`, `body`, `data=deep_link_target` (from `in_app_notification.deep_link_target`).

**Push provider**: Expo Push Notifications API (unified relay for FCM Android + APNs iOS). Single backend HTTP call; Expo handles per-platform routing. No Firebase credentials required on backend. No APNs certificate management. Single env var: `EXPO_ACCESS_TOKEN`. **Do NOT use `FIREBASE_SERVER_KEY`** — the Firebase Cloud Messaging HTTP Legacy API was shut down by Google in June 2024.

**Error handling per Expo error codes**:
- `DeviceNotRegistered` → delete stale token from `mobile_device_push_token`
- `MessageRateExceeded` → retry with backoff
- `InvalidCredentials` → alert operator (CloudWatch alarm)

Recipient has no Expo token → delivery skipped gracefully (no exception). Forced-minimum push categories (field issues, job assignment) delivered even when user preference is muted.

**Effort estimate**: 3–4 days (Expo API integration + error handling + retry logic + tests; reduced from FCM+APNs because Expo unifies platform routing)

---

### A94. Customer Communication Template Type Lookup Table

**Source finding**: FIND-083 (B20, Task 13)

**Reference**: `dev-docs/traceability/17-cust-comms-templates.md` — canonical template catalog with MVP/Phase 2 split, per-template metadata, and activation notes.

**Scope**:

Replace `customer_communication.template_code` CHECK constraint with a proper `customer_comm_template_type` catalog table. Enables: adding new templates without schema migrations; tracking which are automated vs manual; RBAC on who can initiate each; preferred channel; lifecycle category; Phase 2 templates pre-registered as inactive rows.

**Table design**:
- **Mixin**: `StandardAuditMixin` (rows are mutable: `is_active`, `slug`, `name`, `sort_order` updatable; full audit trail)
- **Audit trigger**: `audit_customer_comm_template_type_changes` AFTER INSERT OR UPDATE OR DELETE
- `code VARCHAR PRIMARY KEY`, `slug VARCHAR NOT NULL UNIQUE` (UI identifier, decoupled from PK for future renames), `name VARCHAR NOT NULL`, `description TEXT NULL`, `category VARCHAR NOT NULL` CHECK (`pre_appointment|quoting|during_job|post_job|relationship|exception`), `preferred_channel VARCHAR NULL` CHECK (`sms|email|both|NULL`), `initiator VARCHAR NOT NULL DEFAULT 'tech'` CHECK (`tech|owner|system`), `requires_approval BOOLEAN NOT NULL DEFAULT false`, `send_mode VARCHAR NOT NULL DEFAULT 'manual'` CHECK (`manual|automated|both`), `trigger_event VARCHAR NULL`, `is_system BOOLEAN NOT NULL DEFAULT true`, `is_active BOOLEAN NOT NULL DEFAULT true`, `sort_order INT NOT NULL DEFAULT 0`

**FK replacement**: Drop `customer_communication_template_code_chk` CHECK; add `FOREIGN KEY (template_code) REFERENCES customer_comm_template_type(code) ON DELETE RESTRICT`.

**Seed data**: 13 active MVP rows (see FIND-083 remediation plan for full table) + 14 inactive Phase 2 rows (`is_active=false`) pre-registered so Phase 2 activation only requires `is_active=true` + template body content — no schema migration needed.

**ORM model**: `CustomerCommTemplateType(StandardAuditMixin, SQLModel, table=True)` in `backend/app/models/communications.py`

**Migration**: `phase_fe_1_batch_b20_customer_comm_template_type_table`

**Effort estimate**: 2 days (table + FK migration + ORM + seed data + tests)

---

### A95. Voice Command Entity Link Table

**Triggered by**: Voice Command Intent Classification (B20) — enables tracking which entities (jobs, customers, sites, quotes, etc.) were created or mutated as a result of a voice command.

**Scope**:

**Data model** (`voice_command_entity_link` junction table):
- Junction table linking `voice_command_log` (one-to-many) to entities they created or mutated
- BigInt PK (autoincrement) — optimized for high-volume voice activity
- Columns:
  - `id` BIGINT PK (autoincrement)
  - `tenant_id` UUID FK → `tenant.id` (ON DELETE RESTRICT)
  - `voice_command_log_id` BIGINT FK → `voice_command_log.id` (ON DELETE RESTRICT)
  - `entity_type` VARCHAR — one of: `job`, `customer`, `quote`, `change_order`, `invoice`, `payment`, etc. (matches `entity_type.code`)
  - `entity_id` UUID — the ID of the entity created/mutated
  - `action` VARCHAR NULL — optional action label: `create`, `mutate`, `approve`, etc.
  - `created_at` TIMESTAMPTZ — immutable via AppendOnlyMixin trigger
  - `created_by` UUID FK → `user.id` — immutable via AppendOnlyMixin trigger
- Composite indexes:
  - `ix_vcel_entity (tenant_id, entity_type, entity_id)` — lookup all voice commands that created/mutated a specific entity
  - `ix_vcel_voice_log (voice_command_log_id)` — lookup all entities created by a specific voice command
- AppendOnlyMixin pattern — no updates or deletes after creation; deletion only via archival

**Helper function** (`backend/app/models/voice_helpers.py:_link_voice_to_entity()`):
```python
def _link_voice_to_entity(
    db: Session,
    tenant_id: uuid.UUID,
    voice_command_log_id: int,
    entity_type: str,
    entity_id: uuid.UUID,
    action: Optional[str] = None,
    created_by: Optional[uuid.UUID] = None
) -> VoiceCommandEntityLink:
    """Create and return (unsaved) link row. Caller owns transaction."""
```
- Returns unsaved ORM instance; caller commits within same transaction
- Purpose: Reusable helper for B20 voice intent handlers to link voice commands to created entities

**Usage pattern** (B20 voice intent handlers):
```python
# In voice intent handler for "create_job"
job = Job(...)
link = _link_voice_to_entity(
    db,
    tenant_id=user_context.tenant_id,
    voice_command_log_id=voice_command_log.id,
    entity_type="job",
    entity_id=job.id,
    action="create",
    created_by=user_context.user_id
)
db.add(job)
db.add(link)
db.commit()  # Both persisted in same transaction
```

**Effort estimate**: Trivial — 0.5 days. ORM model + migration + helper function + tests. No new endpoints (internal use only by B20 voice handlers).

---

### A96. Receipt OCR Pipeline (RapidOCR + Llama 3.1 8B)

**Triggered by**: FIND-062 (S2 High) — PRD-§3.4-F9 receipt auto-fill feature; B21 Task 6. **Status: APPLIED — 2026-05-19.**

**Scope**:

- Receipt expense auto-fill pipeline: S3 upload of receipt image → Celery task → RapidOCR text extraction → Llama 3.1 8B field parsing → `job_expense` patch
- Carrier-agnostic adapter pattern with `MockOcrService` for test environments

**Service module** (`backend/services/ocr_service.py`):
- `OcrService` ABC with `extract(image_path: str) → OcrResult`
- `RapidOcrService` — wraps `rapidocr-onnxruntime` for CPU inference on ECS Fargate
- `MockOcrService` — returns fixture-based `{"vendor": "Home Depot", "total_cents": 4299, "date": "2026-05-16"}` in test environments
- `get_ocr_service()` factory — selects `RapidOcrService` (production) or `MockOcrService` (default / tests)

**Celery task** (`backend/tasks/receipt_ocr.py`):
- Task name: `receipt_ocr.process_receipt_ocr`
- Registered in `backend/core/celery_app.py`
- Triggered from `api/routes/photos.py`: `process_receipt_ocr.delay()` on complete-upload when `attachment.expense_id` is set

**Schema migration**:
- `job_expense` table: `ocr_processed_at TIMESTAMPTZ NULL`, `ocr_source VARCHAR NULL`
- Migration: `phase_fe_1_batch_b21_job_expense_ocr_` (2026_05_19_1247)
- Schema diff: ZERO discrepancies

**Infrastructure**:
- `rapidocr-onnxruntime==1.4.4` added to `backend/requirements.txt`
- CPU inference in existing ECS Fargate app container — zero new infrastructure, zero cloud cost
- Llama 3.1 8B on existing `pilot_ollama` (EC2 g4dn.xlarge) for structured field parsing

**Tests**: 16 tests in `backend/tests/batch_b21/test_receipt_ocr_pipeline.py` across 3 classes (`TestFind062SchemaColumns`, `TestFind062OcrServiceAbc`, `TestFind062ReceiptOcrTask`)

**Effort estimate**: 1–2 days (completed as B21 Task 6; already APPLIED)

---

## Rough Effort Estimate (Remaining MVP Additions)

| Item | Size | Days |
| :--- | :--- | :---: |
| A2 Quote Approval | Medium | 3–5 |
| A3 Time-Limited Discounts | Small-Medium | 2–3 |
| A4 Customer Communications | Medium | 4–6 |
| A5 Reports + Dashboard Widgets | Medium-Large | 5–7 |
| A6 Voice Feedback | Medium | 3–4 |
| A7 Field Mode Backend | Small | 1–2 |
| A9 Session Number Computation | Small | 1 |
| A10 Voice Session Grammar | Small-Medium | 2–3 |
| A11 Ollama Title Generation | Small | 1–2 |
| A12 Structured Message Payload | Medium | 4–6 |
| A14 ETC Capture System | Medium-Large | 6–8 |
| A15 Chart-Threshold Setting | Trivial | 0.5 |
| A16 ETC Variance Notifications | Small-Medium | 2–3 |
| A17 Margin Bucket Configuration | Small | 1–2 |
| A18 Tech Color Assignment | Small | 1–2 |
| A19 Dispatch Board API + SSE | Medium-Large | 6–8 |
| A20 Drive-Time Caching Verification | Small | 1–2 |
| A21 Per-Message Channel Override | Small | 1–2 |
| A22 Voice Intent Grammar for Comms | Medium | 4–5 |
| A23 Communication Preview Endpoint | Small | 1–2 |
| A24 Quote Line Item Schema (Visibility + Hierarchy) | Medium | 3–4 |
| A25 Quote Template Schema with Style and Versioning | Medium-Large | 5–7 |
| A26 System Template Update Notifications | Small-Medium | 2–3 |
| A27 Save Quote as Template | Medium | 3–4 |
| A28 Multi-Line Description Editing Support | Small | 1–2 |
| A29 Pending Edit Storage During Review | Medium | 4–5 |
| A30 Approval Comment & Annotation System | Small-Medium | 3–4 |
| A31 Voice Intent Grammar for Approval | Small-Medium | 2–3 |
| A32 Calendar Conflict Diff Payload | Small-Medium | 2–3 |
| A33 Pre-Resolution Staleness Check | Small | 1 |
| A34 Auto-Expiry of Stale Conflicts (System Default + Tenant Override) | Medium | 3–4 |
| A35 Mobile Pending-Conflicts Status & Notification Rate Limiting | Small | 1 |
| A36 Voice Intent Grammar for Calendar Conflict Resolution | Medium | 4–5 |
| A37 Offline-Capable Operations API Contract | Small-Medium | 2–3 |
| A38 Sync Queue State Model (Server-Side Visibility) | Medium | 3–4 |
| A39 Idempotency UUIDs for Offline Operations | Small-Medium | 3–4 |
| A40 Conflict Severity Classification Engine | Medium-Large | 5–7 |
| A41 Resumable Photo Upload Pipeline | Medium | 4–5 |
| A42 Voice Command Offline Capture & Deferred Processing | Medium | 4–5 |
| A43 Force-Quit Recovery State Persistence | Medium | 4–5 |
| A44 Auth Expiry Offline Handling | Small-Medium | 2–3 |
| A45 Tech-Resolvable Conflict UI Endpoints | Small-Medium | 2–3 |
| A46 Owner Escalation Routing & Notification | Medium | 3–4 |
| A47 Owner-Side Mobile-Conflict Escalation Queue Endpoints | Medium | 4–6 |
| A48 Owner-Side Mobile-Conflict Resolution Write Path | Medium-Large | 5–7 |
| A49 QuickBooks Conflict Queue Endpoints + Schema Extension | Medium | 4–5 |
| A50 QuickBooks Conflict Resolution Write Path + Auto-Expiry Celery Extension | Medium | 4–5 |
| A51 Background Sync Infrastructure | Medium-Large | 6–8 |
| A52 Settings Catalog Endpoint | Small-Medium | 2–3 |
| A53 Effective-Value Resolution Endpoint (Three-Tier Extension) | Small-Medium | 2 |
| A54 Tenant Settings Write Endpoints | Medium | 3–4 |
| A55 Per-User Override Write Endpoints | Small | 1–2 |
| A56 Notification Category Registry | Medium | 4 |
| A57 Notification Preference Matrix Endpoints + In-App Banner Component | Medium | 5–6 |
| A58 Delivery Dispatcher Preference Gate | Medium | 3–4 |
| A59 Telnyx Webhook Handler + Carrier-Agnostic Adapter Layer | Small-Medium | 3 |
| A60 Customer Communication Threading Schema and Routing | Medium | 4 |
| A61 Telnyx Number Provisioning at First Use | Medium | 3 |
| A62 Free-Form Reply Composition Endpoints | Small | 2 |
| A63 Voice-to-Text Reply Integration | Small-Medium | 2–3 |
| A64 Owner Visibility Surfaces — Comm History + Dashboard Widget | Small-Medium | 2–3 |
| A65 SMS Quota Tracking and Cap Enforcement | Medium | 4 |
| A66 Mobile Inbox + Conversation Thread Screen | Medium | 3–4 |
| A67 Voice Persona Tone Renderer + Preview Audio Generation + Per-User Resolution | Medium | 4-6 |
| A68 Tenant MFA Policy + Grace Period Enforcement | Medium | 4-5 |
| A69 Multi-Method MFA Enrollment + Method Management + Recovery Codes | Large | 7-9 |
| A70 Active Sessions List + Revoke | Small-to-Medium | 3 |
| A71 Data Export Request Pipeline | Medium | 4-5 |
| A72 First-Session Detection for First-Time-User States | Small | 1-2 |
| A73 Trial State Machine + Tenant Signup | Medium-Large | 5-6 |
| A74 Legal Acceptance Recording | Small | 2 |
| A75 Subscription Tier Infrastructure | Medium | 4 |
| A76 Stripe Integration for Paid Conversion | Medium-Large | 5-6 |
| A77 Onboarding State Tracking + Checklist Resumability | Small-Medium | 3 |
| A78 Mobile Push Permission Tracking + Degraded-Mode Fallback | Small | 2 |
| A79 Unified Pending-Count Exposure for Sync Surfaces | Small | 2 |
| A80 Signed URL Infrastructure for Public Quote/Invoice Links | Medium | 4 |
| A81 Stripe One-Time Payment for Invoices with Amount Variance | Medium | 4-5 |
| A82 Email Template Rendering Pipeline + Tenant Brand Customization | Medium | 4-5 |
| A83 Quote/Payment Customer Comment Storage with Notifications | Small | 2 |
| A84 Help AI Agent + RAG + Chat Session Management | Medium-Large | 5-7 |
| A85 Markdown Corpus + Embedding Pipeline + S3 Storage | Medium | 4-5 |
| A86 Contextual Help Anchor Metadata + Opener Context Payload | Small | 2 |
| A87 Feedback Submission Endpoint with Email Intake | Small | 2 |
| A88 Anonymization Pipeline for Training Data Capture | Medium | 3-4 |
| A89 LOTO Confirmation Table + Configurable Voice Guard | Medium | 4–5 |
| A90 Category-Specific Markup Management Endpoints | Medium | 2–3 |
| A91 Labor Rate Version Management + jobs.py Wiring | Medium | 3 |
| A92 Authenticated Invoice CRUD + Router Cleanup | Medium-Large | 4–5 |
| A93 Expo Push Delivery | Medium | 3–4 |
| A94 Customer Comm Template Type Table | Medium | 2 |
| A96 Receipt OCR Pipeline (RapidOCR + Llama 3.1 8B) | Small | 1–2 ✅ APPLIED |
| **Subtotal remaining MVP (Pass 4 Tier 1 + 1.5 + 2 + 3 + 4 complete + Phase 4.2 A89–A94 + Phase 4.4 A96)** | | **278–358.5 days** |
| A13 Voice Persona (Post-MVP) | Small | 2–3 |

Plus Pass 4 close activities (i.e. update PRD, update arch, update framework, etc.).

---

*This document is the consolidated Pass 4 close ledger. v6.2 (Phase 4.2 traceability remediation) adds A89–A94 per FIND-055, FIND-056, FIND-063, FIND-076, FIND-078, FIND-083. v6.3 (Phase 4.4) adds A96 (Receipt OCR Pipeline) — FIND-062 APPLIED B21 Task 6 2026-05-19. v6 is the design-phase frozen baseline; backend implementation should treat this as authoritative. See the corresponding design spec for the UI decisions that triggered each addition. Future ledger updates will track implementation progress and any post-launch additions.*
