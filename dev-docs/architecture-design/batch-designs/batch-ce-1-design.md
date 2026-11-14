# Batch CE-1 Design — Customer-Facing Enhancements (Invoice Sign-Off + Overpayment Review)

**Batch code**: CE-1 (launch plan §2.3, Beta Execution Order 1)
**Date**: 2026-08-12
**Author**: Pilot Architect
**Status**: ✅ APPROVED 2026-08-12 — design accepted; both UI specs (§H) authored + Tom-approved; Rule 9.8 dependency approved; all three engineer prompts authored (Part A `batch-ce-1-python-engr-prompt.md`, Part B `batch-ce-1-react-native-engr-prompt.md`, Part C `batch-ce-1-react-engr-prompt.md`)
**Launch plan card**: `pilot-launch-plan.md` §2.3 CE-1
**Engineer prompts (to be authored after designer-spec approval)**:
1. `batch-ce-1-python-engr-prompt.md` — Part A (backend) — runs **first**
2. `batch-ce-1-react-native-engr-prompt.md` — Part B (mobile) — after Part A merges + voice-ui spec Tom-approved
3. `batch-ce-1-react-engr-prompt.md` — Part C (web) — after Part A merges + web-ui spec Tom-approved

---

## 0. Scope Reconciliation vs. Launch Plan Card (READ FIRST)

The CE-1 plan card (written 2026-07-29) scopes two items. A full code audit (2026-08-12) found the card **half-stale**. This design implements the true residual scope:

| Plan card item | Audit finding | Disposition |
|---|---|---|
| "Mobile signature capture on invoice sign-off (Expo canvas)" | **Greenfield.** No canvas, signature component, or sign-off table exists anywhere. `signature_url` exists only on quote `Acceptance` (`quoting.py`:702) — unrelated surface. MCP confirms zero `signoff`/`signature` tables. Mobile app has **no invoice feature** at all (`frontend/apps/mobile/features/` = jobs/customers/comms/voice/offline-sync/owner-tab). | **Part A + Part B of this batch** (backend + mobile). |
| "Partial-payment 'Pay remaining' CTA on the public invoice page" | **Already built.** `InvoicePartialPaidState.tsx` renders the "Pay remaining" CTA; `InvoiceAmountSelector` + `InvoicePaymentModal` + backend `POST /api/v1/public/invoices/{token}/payment-intent` / `confirm-payment` in `public_invoices.py` implement PRD §3.6 "Pay remaining / Pay different amount" (line 382) fully. | **No new code.** Residual = E2E verification only (folded into Part C engineer's manual verification). |
| *(not on card)* PRD §3.6 line 381 + mvp-arch §18.5 line 4115: overpayment "flagged for tenant review … tenant reviews via UI … UI shows 'Customer paid $X over invoice total — review'" | **Not built.** `payment.amount_variance_cents` is recorded (schemas.py exposes it), but no tenant-facing review surface or resolution tracking exists. | **Part B backend + Part C web** (overpayment review banner + resolution). |
| *(derived)* Display captured signature to the tenant (web invoice detail) | Required for the capture to have product value. | **Part C web.** |
| *(derived)* Display captured signature on the **public** invoice page (`/i/[token]`) | Nice-to-have customer proof; the public page already handles paid/partial states per §18.6. | **DEFERRED to CE-1-FU (post-beta fast-follow).** Owned by `pilot-marketing-ui-designer` per §1.5 surface ownership. See §G-R2. |

**Beta-gate justification**: the beta-critical deliverable is *technicians can capture a customer signature at invoice sign-off in the field* (sales-demo differentiator, roadmap lines 94–95). The overpayment review surface closes a PRD §3.6 integrity gap before real money flows.

---

## A. Input Read Summary

| Input | Sections read | What it contributed |
|---|---|---|
| `mvp-prd.md` | §3.6 lines 368–383 | Exact requirement text: variance accounting (381), public-link affordances (382 — already built), branding (383) |
| `mvp-arch.md` | §18.5 (4085–4123) payment-intent flow + variance SQL + overpayment line 4115; §18.6 (4125–4139) state-aware revisit; §16 pattern inventory; §15 offline ops contract | Overpayment UI language is specified verbatim ("Customer paid $X over invoice total — review"); offline-first field patterns |
| `pilot-operations.md` | Payment/invoice sections (338–365) | Tenant Stripe pass-through, partial payments decrement `balance_due_cents`, `partial` status semantics |
| `pilot-product-roadmap.md` | lines 94–95 | CE-1 lineage: "Mobile signature capture on invoice sign-off — Expo canvas — RN Engr" |
| Launch plan `pilot-launch-plan.md` | §2.0 row 1, §2.1 Order 1, §2.3 CE-1 card | Card scope + Rule 9.8 Expo-dependency approval note |
| `invoices.py` | Full file (list 857–894, record_payment 924–936, `_impl` pattern) | No `job_id` filter on list; house `_impl` + `/test`-twin pattern to follow; `require_permission` usage |
| `public_invoices.py` | Full route surface | Partial-pay endpoints exist; no changes needed |
| `billing.py` | Invoice (153–309), Payment (443–517), InvoicePublicLink (1005–1114) | `invoice.job_id` nullable FK (195–203) — the binding key for job-scoped sign-off; `uq_invoice_tenant_idempotency` pattern |
| `fulfillment.py` | JobAttachment (394–460), Job (197–344) | Offline field-capture pattern: `client_capture_at`, idempotency key, S3 object key |
| `schemas.py` | PaymentResponse (773–785), PublicInvoice* (502–540) | `amount_variance_cents` already exposed in PaymentResponse |
| `s3_service.py` | All 7 functions | Multipart-only today; `build_photo_object_key` (150) is the object-key-builder pattern; presigned GET/PUT precedents in `user_profile.py`:87/244, `tenant_email_branding.py`:98/300 |
| Mobile `features/offline-sync/hooks/useCreateJobNote.ts` | Full file | Offline mutation pattern: WatermelonDB local write → `localSyncStatus="pending"` + `idempotencyKey` + `clientCaptureAt` → sync engine push |
| Mobile `features/jobs/components/` | JobDetailScreen + `detail/*Section.tsx` | Section-based detail architecture — sign-off entry point is a new `detail/InvoiceSignoffSection.tsx` |
| Web `features/public-invoice/` | InvoicePartialPaidState, InvoiceAmountSelector, InvoicePaymentModal | Proof partial-pay CTA is built |
| `packages/ui/src/index.ts` | Barrel exports | Component-existence check: **no** signature/canvas component exists; `NotificationBanner`, `PendingBadge`, `MessagePreviewModal` exist and must be composed |
| MCP `postgres-local` | `invoice` (33 cols), `payment` (variance cols present), `subscription*` (prior batch), signoff-name collision check (none), FK target names (`tenant`, `user`, `invoice`, `payment`, `job` verified) | All DDL below uses only MCP-verified names |
| Designer rules (§10.7) | `.roo/rules-pilot-voice-ui-designer/` (both), `.roo/rules-pilot-web-ui-designer/` (both), `.roo/rules-pilot-marketing-ui-designer/` (both) | §H designer scoping: glove-friendly 44×44 targets; token-only web specs; `/i/[token]` is marketing-ui territory |
| `pilot-architect-methods.md` | §3 workflow, §8 sub-projects, §9 frontend standards | This doc's structure; mixed-batch prompt conventions |

---

## B. Migration Plan

One Alembic migration, two changes. **No data backfill required** — all new `payment` columns are nullable (3-part NOT NULL pattern not triggered; stated explicitly per workflow). New-table NOT NULL columns are safe by definition.

### B.1 New table `invoice_signoff`

```sql
CREATE TABLE public.invoice_signoff (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID NOT NULL REFERENCES public.tenant (id),
    invoice_id            UUID NOT NULL REFERENCES public.invoice (id),
    signed_by_name        VARCHAR(200) NOT NULL,
    signature_object_key  VARCHAR(500) NOT NULL,
    terms_acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
    signed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),   -- server receipt time
    client_capture_at     TIMESTAMPTZ NULL,                     -- device clock (offline pattern, cf. job_attachment)
    captured_by_user_id   UUID NOT NULL REFERENCES public."user" (id),
    superseded_at         TIMESTAMPTZ NULL,                     -- set when a re-capture replaces this row
    idempotency_key       VARCHAR(100) NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),   -- StandardAuditMixin (all four, per Rule §3)
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by            UUID NULL,
    updated_by            UUID NULL,
    CONSTRAINT ck_invoice_signoff_terms CHECK (terms_acknowledged = TRUE)
);

-- One active (non-superseded) sign-off per invoice — race-safe re-capture
CREATE UNIQUE INDEX uq_invoice_signoff_one_active
    ON public.invoice_signoff (invoice_id)
    WHERE superseded_at IS NULL;

-- Tenant-scoped lookups
CREATE INDEX ix_invoice_signoff_tenant_invoice
    ON public.invoice_signoff (tenant_id, invoice_id);

-- Offline replay dedup (natural-key fallback per §15.4)
CREATE UNIQUE INDEX uq_invoice_signoff_tenant_idempotency
    ON public.invoice_signoff (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
```

SQLModel class `InvoiceSignoff(StandardAuditMixin, SQLModel, table=True)` → `billing.py` (sign-off is a billing artifact bound to `invoice_id`, not a fulfillment artifact — the mobile *entry point* is job-scoped but the record is invoice-scoped).

### B.2 Alter `payment` — overpayment resolution tracking

```sql
ALTER TABLE public.payment ADD COLUMN variance_resolution VARCHAR(20) NULL;
ALTER TABLE public.payment ADD COLUMN variance_resolution_note TEXT NULL;
ALTER TABLE public.payment ADD COLUMN variance_resolved_at TIMESTAMPTZ NULL;
ALTER TABLE public.payment ADD COLUMN variance_resolved_by_user_id UUID NULL REFERENCES public."user" (id);

ALTER TABLE public.payment ADD CONSTRAINT ck_payment_variance_resolution
    CHECK (variance_resolution IS NULL OR variance_resolution IN ('credit', 'refund_offline', 'writeoff'));
```

Resolution vocabulary per PRD §3.6 line 381 ("refund, credit forward, accept"): `credit` = credit forward, `refund_offline` = tenant refunded outside Pilot (record-keeping only — **no Stripe refund execution in this batch**, see §G-R6), `writeoff` = accept/keep.

### B.3 MCP pre-verification (already run 2026-08-12)

- ✅ No table matching `%signoff%`/`%signature%` exists (greenfield, no collision).
- ✅ `payment` columns present: `stripe_payment_intent_id`, `customer_payment_comment`, `amount_variance_cents`, `paid_via`; the four B.2 columns do **not** exist.
- ✅ FK targets `tenant`, `"user"`, `invoice`, `payment` exist in `public`.
- Prompt-authoring gate (Rule §3): the Python Engineer prompt will re-run `information_schema.columns` for `payment` and `invoice` before any SQL is written into the prompt.

### B.4 Triggers / functions

No new triggers or functions. `updated_at` handling follows the exact convention of the most recent migration in `migrations/` (engineer copies the prevailing pattern; audit columns are app-managed via `StandardAuditMixin`).

### B.5 Seed Data Rollout (Rule §11.5 — mandatory)

| Layer | Change |
|---|---|
| Layer 2 — Scenario (`seed_scenario_*.py`) | ① One **overpaid payment** on a demo invoice: `amount_variance_cents = 1500` ($15 over), `variance_resolution = NULL` → populates the Part C review banner in dev. ② One **`invoice_signoff` row** on a completed-job invoice (reserved-UUID tenant), object key `signatures/{tenant}/{invoice}/{signoff}.png`; the seed writes a tiny valid PNG via `put_object` wrapped in try/except — if S3 is unavailable locally, log + skip the object but keep the row (display degrades gracefully). Value-scoped DELETE-then-INSERT per Rule §11.1 (match on `invoice_id` for the signoff row, on `id` for the payment update — never channel/class-scoped deletes). |
| Verification | `seed_core.py --mode inspect` + `pytest -m unit` |
| README | Update `README-seed-data.md` §4 Current Seed State |

---

## C. Execution Order

| # | Step | Owner | Notes |
|---|---|---|---|
| 1 | Migration B.1 + B.2 | Python Engr | Verify against MCP first |
| 2 | `InvoiceSignoff` model + `Payment` field additions | Python Engr | `StandardAuditMixin`; regenerate `db_models_map.md` + schema JSON (§7/§9 inclusions) |
| 3 | `s3_service.py` helpers (§F.1) | Python Engr | |
| 4 | Schemas (§D.3) | Python Engr | New `api/schemas/invoice_signoff.py`; extend `PaymentResponse` |
| 5 | 4 endpoints + 4 `/test` twins (§D) | Python Engr | Shared `_impl` pattern per `invoices.py` |
| 6 | Unit tests (signoff create/supersede/idempotent-replay/RBAC; resolve-variance happy/409/422/RBAC) | Python Engr | Domain folder `tests/domains/invoicing_billing/` |
| 7 | OpenAPI regen + `export_openapi_json.py` + commit → **handoff signal** | Python Engr | Rule 9.3 |
| 8 | Seed rollout B.5 | Python Engr | |
| 9 | `pnpm sync-api-types` → RN + web prompts unblocked | React/RN Engrs | After Tom approves both designer specs |
| 10 | Part B mobile build (§I) | RN Engr | **Requires Tom's Rule 9.8 dependency approval first** |
| 11 | Part C web build (§I) | React Engr | Includes manual E2E pass of the pre-built partial-pay flow |

---

## D. New API Endpoints

All tenant-scoped `select()` with explicit `WHERE tenant_id = :tid` (`db.get()` banned — methods §7.1). All errors RFC 7807. Authenticated mutations require `Idempotency-Key` header (24h TTL, §7.6).

### D.1 `GET /api/v1/jobs/{job_id}/signoff-context`

Mobile entry-point data. **Auth**: `require_permission("jobs.view")` (technicians hold this — deliberate, see §G-R3).
Returns the job's signable invoices: `invoice.job_id = :job_id`, `is_active = TRUE`, invoice status `code IN ('issued', 'partial')` (resolve `status_id` by code via `invoice_status` lookup — **never hardcode UUIDs**), ordered newest first.

**Response 200** — `SignoffContextResponse`:
```json
{
  "job_id": "uuid",
  "customer_display_name": "string",
  "invoices": [
    {
      "invoice_id": "uuid",
      "invoice_number": "INV-0042",
      "status": "issued|partial",
      "total_cents": 125000,
      "balance_due_cents": 125000,
      "currency": "USD",
      "terms_text": "string (invoice.terms_and_conditions, else platform default constant)",
      "active_signoff": null | { "signoff_id": "uuid", "signed_by_name": "string", "signed_at": "ts" }
    }
  ]
}
```
Empty `invoices` → mobile hides the section. **Errors**: 403 (no `jobs.view`), 404 (job not in tenant).

### D.2 `POST /api/v1/invoices/{invoice_id}/signoff`

Capture. **Auth**: `require_permission("jobs.update")` — technicians are excluded from all `invoices.*` permissions (design-system §8; PLAT-DEBT), so this job-field action rides the permission techs already hold (§G-R3).

**Request** — `InvoiceSignoffCreateRequest`:
```json
{
  "signed_by_name": "string, 1–200, required",
  "terms_acknowledged": true,
  "signature_png_base64": "string, required — decoded ≤ 2MB, PNG magic bytes validated",
  "client_capture_at": "ts, optional (offline device clock)"
}
```
**Server flow** (single DB transaction; S3 put *before* commit):
1. Tenant-scoped invoice fetch → 404 if absent.
2. Guard: invoice status must be `issued`/`partial` → 422 otherwise (state-aware; prevents signing void/draft).
3. Decode base64 (strict) → validate PNG magic bytes + size → 422 `validation` problem detail.
4. `signoff_id = uuid4()`; `object_key = build_signature_object_key(tenant_id, invoice_id, signoff_id)`; `put_signature_object(object_key, png_bytes)` → on S3 failure: 502 problem detail, **no row written**.
5. Supersede: `UPDATE invoice_signoff SET superseded_at = now() WHERE invoice_id = :iid AND superseded_at IS NULL`.
6. Insert row (idempotency: on `uq_invoice_signoff_tenant_idempotency` conflict → return the existing row 200, §15.4 replay semantics).

**Response 200** — `InvoiceSignoffResponse`: `{ signoff_id, invoice_id, signed_by_name, signed_at, client_capture_at, captured_by_user_id, signature_url }` where `signature_url` = presigned GET, 1h TTL.
**Errors**: 400 (missing idempotency header), 403, 404, 409 (unique-active race loser → client refreshes, §16.4), 422 (validation).

### D.3 `GET /api/v1/invoices/{invoice_id}/signoff`

Web display. **Auth**: `require_permission("invoices.view")` (owner/office/operator; techs excluded — financial surface).
**Response 200** — `InvoiceSignoffResponse | {"signoff": null}`: latest active signoff + fresh presigned GET `signature_url` (1h TTL) + `superseded_count`.
**Errors**: 403, 404.

### D.4 `POST /api/v1/payments/{payment_id}/resolve-variance`

> **As-built note (2026-08-13)**: shipped at **`POST /api/v1/invoices/{payment_id}/resolve-variance`** — payment routes live on the invoices router in this codebase (`_record_payment_impl` precedent), so the engineer mounted it there; OpenAPI is authoritative and Part C consumed the as-built path. This section's `/api/v1/payments/...` form was the design-time intent only.

Overpayment review. **Auth**: `require_permission("invoices.update")` (owner/office — techs excluded).
**Request** — `ResolveVarianceRequest`: `{ "resolution": "credit|refund_offline|writeoff", "note": "string ≤1000, optional" }`
**Guards**: payment exists in tenant (404) → `amount_variance_cents > 0` else 422 ("no overpayment to resolve") → not already resolved else **409** with current resolution in the problem detail (§16.4 409-and-refresh).
**Response 200** — extended `PaymentResponse` (adds `variance_resolution`, `variance_resolution_note`, `variance_resolved_at`, `variance_resolved_by_user_id` — additive, non-breaking).

### D.5 `/test` twins

Per house pattern (`invoices.py` `send_invoice_test` etc. and inclusions §11): all four endpoints get `/test` variants sharing the same `_impl` functions. S3 calls in tests/test-mode are mocked at `_s3_client()`.

---

## E. Pattern Reuse Decisions (§16 locked patterns — compose, never reinvent)

| Pattern | Application |
|---|---|
| §15 Offline Ops Contract + §15.4 Idempotency | Sign-off rides the WatermelonDB mutation queue (`useCreateJobNote` pattern): local row → `localSyncStatus="pending"` → sync engine POSTs with `Idempotency-Key` + `client_capture_at`. Base64 PNG travels **inline in the mutation payload** — a presigned-PUT-then-confirm design is rejected because it requires connectivity at capture time (§G-R5). |
| §16.8 Optimistic UI / `PendingBadge` | Captured sign-off shows pending badge until sync confirms; compose `packages/ui` `PendingBadge`. |
| §16.4 409-and-Refresh | Resolve-variance on an already-resolved payment → 409 + refetch. Sign-off unique-active race → 409 + refetch context. |
| §18.6 State-Aware Revisit | Public page unchanged; sign-off availability is status-gated server-side (`issued`/`partial` only). |
| §16.6 Four-Class Severity | Overpayment review banner = `warning` class (`alert` tokens), never blocks other invoice actions. |
| §16.7 Always-Preview-Before-Send | N/A — no outbound comms. (Owner "invoice signed" notification deliberately deferred, §G-R8.) |

---

## F. Shared Module Interfaces

### F.1 `s3_service.py` additions (backend)

```python
def build_signature_object_key(tenant_id: str, invoice_id: str, signoff_id: str) -> str:
    """Return 'signatures/{tenant_id}/{invoice_id}/{signoff_id}.png' (cf. build_photo_object_key)."""

def put_signature_object(object_key: str, png_bytes: bytes) -> None:
    """Server-side put_object to the same bucket constant used by create_multipart_upload();
    ContentType='image/png'. Raises on failure (caller maps to 502)."""

def generate_presigned_get_url(object_key: str, expires_in: int = 3600) -> str:
    """Presigned GET (precedent: user_profile.py). Centralizes the 3 existing ad-hoc call sites' pattern."""
```

### F.2 Mobile (new files — exact paths in §I)

```typescript
// features/offline-sync/hooks/useCreateInvoiceSignoff.ts — mirrors useCreateJobNote
export interface CreateInvoiceSignoffInput {
  invoiceId: string; signedByName: string; termsAcknowledged: true;
  signaturePngBase64: string; capturedBy: string;
}
// WatermelonDB: new table `invoice_signoffs` (local) + sync-engine push registration
// (same registration path as job_notes — engineer follows existing model registration)
```

### F.3 Schemas (backend, new file `api/schemas/invoice_signoff.py`)

`InvoiceSignoffCreateRequest`, `InvoiceSignoffResponse`, `InvoiceSignoffSummary`, `SignoffContextResponse`, `SignoffContextInvoice` (names per §D shapes). `ResolveVarianceRequest` goes in `schemas.py` beside `PaymentResponse`.

### F.4 Celery

None. No new tasks, no schedule changes.

---

## G. Open Questions Resolved

- **R1 — Partial-pay CTA**: Already built and live (public-invoice feature + endpoints). Zero new code; Part C engineer runs a manual E2E pass (issue invoice → partial pay → "Pay remaining" → full pay) as verification only.
- **R2 — Public-page signature display**: Deferred to CE-1-FU. Keeps CE-1 inside the two-spec designer gate Tom approved; `/i/[token]` is `pilot-marketing-ui-designer` surface (web-ui rules §1) and adding it would force a third spec. Public page already communicates paid/partial states per §18.6.
- **R3 — RBAC**: Capture endpoint rides `jobs.update`, context rides `jobs.view`; display rides `invoices.view`. Technicians are excluded from `invoices.*` (design-system §8). **Deliberate narrow disclosure**: the sign-off screen shows the tech the invoice number + `total_cents`/`balance_due_cents` because the amount is inside the customer-facing terms text being signed (customer-present transaction). Single-invoice, job-scoped disclosure only — no list/financial access granted.
- **R4 — Re-capture semantics**: Supersede, not 409. Offline replays are deduped by idempotency key; a *deliberate* re-capture (wrong name, customer re-signs) sets `superseded_at` on the prior row. Partial unique index keeps exactly one active row race-safe.
- **R5 — Transport**: base64 PNG inline (~20–60KB at the spec'd canvas size), not S3 multipart/presigned-PUT — fully offline-capable; server puts to S3 on sync.
- **R6 — Overpayment resolution**: record-keeping only. Stripe refund execution is **out of scope** (entangles with the open Stripe Connect decision, INT-H1 / Tom). `refund_offline` = tenant refunded outside Pilot and records it here. QB sync unchanged (QB handles partial payments natively; a `credit` resolution's QB credit memo is a Phase-1.5 item — noted, not built).
- **R7 — Expo dependency**: `react-native-signature-canvas` (WebView-based, base64 PNG output) is the recommendation; **Rule 9.8 Tom approval required before install** — the gate is restated in the RN prompt. Voice-UI designer specs the canvas interaction against this library's API.
- **R8 — Owner notification on sign-off**: deferred (would compose §3.5 Billing category; not beta-critical). One-line backlog note for the 1.5-C list.
- **R9 — ADR**: Not required. §7.1 bar not met — additive table + endpoints composing existing locked patterns, easily reversible, no new infra, no cross-master-doc contradiction.
- **R10 — Cost/infrastructure**: No new AWS services. S3 storage delta ≈ 50KB/sign-off (negligible at 100-customer scale). $0 delta vs. the $888 baseline — no Founder cost review triggered (§4 guardrails assessment recorded for completeness).

---

## H. Surface Mockup Reference (frontend batches)

| # | Surface | Designer owner (§1.5) | Spec path (designer authors) | Status |
|---|---|---|---|---|
| H1 | Mobile: `InvoiceSignoffSection` (job detail entry) + full-screen capture flow (name → terms scroll + acknowledge → canvas → save/clear) + pending-sync states | **`pilot-voice-ui-designer`** | `dev-docs/architecture-design/batch-designs/batch-ce-1-mobile-ui-design-spec.md` | ✅ spec authored + Tom-approved 2026-08-12 |
| H2 | Web: invoice detail "Customer Sign-off" card (image, signer, timestamps, tech, superseded history) + empty state | **`pilot-web-ui-designer`** | `dev-docs/architecture-design/batch-designs/batch-ce-1-web-ui-design-spec.md` | ✅ spec authored + Tom-approved 2026-08-12 (one spec covers H2+H3) |
| H3 | Web: invoice detail overpayment review banner ("Customer paid $X over invoice total — review") + resolution modal (Credit forward / Record offline refund / Write off + note) | **`pilot-web-ui-designer`** | same spec as H2 | ✅ spec authored + Tom-approved 2026-08-12 |
| H4 | Public `/i/[token]` signature display block | `pilot-marketing-ui-designer` | — | **DEFERRED (§G-R2)** |

Designer constraints to restate when commissioning: H1 = glove-friendly rules (44×44pt targets, 12pt spacing, WCAG AAA contrast, sunlight-readable); H2/H3 = token-only (`pilotPreset`, zero hex), Heroicons by exact name, WCAG 2.2 AA subsection, component-existence check against `packages/ui/src/index.ts`, four TanStack Query data states, "overdue is derived" rule, money-from-cents rule. §16 composition only — no new top-level UX.

**Handoff gate**: designers STOP after their specs; Tom approves; only then are the RN/React prompts authored (methods §3.9).

---

## I. Component Manifest

Component-existence check run against `packages/ui/src/index.ts` 2026-08-12: no signature/canvas component exists; `PendingBadge`, `NotificationBanner`, `MessagePreviewModal`, `EmptyState` exist and are composed, not recreated. **Zero new `packages/ui` components.**

### Part B — Mobile (`frontend/apps/mobile/`)

| Component / file | Destination | Change |
|---|---|---|
| `InvoiceSignoffSection.tsx` | `features/jobs/components/detail/` | NEW — job-detail entry; fetches D.1; renders CTA or active-sign-off summary; hides on empty |
| `InvoiceSignoffCaptureScreen.tsx` | `features/jobs/components/detail/` (or `app/` route per mobile nav convention) | NEW — full-screen capture: name field, terms scroll + acknowledge, `react-native-signature-canvas` canvas, Clear/Save |
| `useSignoffContext.ts` | `features/jobs/hooks/` | NEW — TanStack Query wrapper on D.1 (`retry: false`) |
| `useCreateInvoiceSignoff.ts` | `features/offline-sync/hooks/` | NEW — §F.2 offline mutation |
| WatermelonDB model + schema row | `database/models/InvoiceSignoff.ts`, `database/schema.ts` | NEW — local table `invoice_signoffs` with `localSyncStatus`, `idempotencyKey`, `clientCaptureAt`, base64 field |
| Sync-engine push registration | sync engine module (follow `job_notes` registration) | MODIFY |
| `JobDetailScreen.tsx` | `features/jobs/components/` | MODIFY — mount `InvoiceSignoffSection` |

### Part C — Web (`frontend/apps/web/`)

| Component / file | Destination | Change |
|---|---|---|
| `InvoiceSignoffCard.tsx` | `src/features/invoices/components/` | NEW — display card per H2 (presigned GET image, refresh on `signature_url` expiry) |
| `OverpaymentReviewBanner.tsx` | `src/features/invoices/components/` | NEW — warning banner per H3, renders when any payment on the invoice has `amount_variance_cents > 0` and `variance_resolution IS NULL` |
| `ResolveVarianceModal.tsx` | `src/features/invoices/components/` | NEW — 3-option resolution + note; composes modal pattern (design-system §7); 409 → refetch |
| `useInvoiceSignoff.ts` / `useResolveVariance.ts` | `src/features/invoices/hooks/` | NEW — D.3/D.4 hooks (`apiClient` only; `retry: false`) |
| Invoice detail page | `src/features/invoices/components/` (existing detail surface) | MODIFY — mount card + banner |
| Manual E2E: partial-pay flow on `/i/[token]` | — | VERIFY ONLY (§G-R1) |

### Part A — Backend

| File | Change |
|---|---|
| `migrations/versions/<new>_ce1_invoice_signoff_variance.py` | NEW — §B DDL |
| `app/models/billing.py` | NEW `InvoiceSignoff`; MODIFY `Payment` (+4 fields) |
| `services/s3_service.py` | NEW §F.1 helpers |
| `api/schemas/invoice_signoff.py` | NEW; `api/schemas/schemas.py` MODIFY (`PaymentResponse` +4, `ResolveVarianceRequest`) |
| `api/routes/invoices.py` | MODIFY — D.2/D.3 (+`/test` twins) |
| `api/routes/jobs.py` | MODIFY — D.1 (+`/test` twin) |
| `api/routes/payments.py` *(or invoices.py if payments routes live there — engineer verifies)* | MODIFY — D.4 (+`/test` twin) |
| `tests/domains/invoicing_billing/test_ce1_invoice_signoff.py`, `test_ce1_variance_resolution.py` | NEW — per §C.6 |
| `migrations/scripts/seed_scenario_*.py` | MODIFY — §B.5 |
| `backend/db_models_map.md`, schema JSON, `openapi.json` | REGENERATE |

---

## Approval Gates — Status Record (all cleared 2026-08-12)

1. ✅ **Tom approved this design doc** (including deferred public-page display / §G-R2 and the §G-R3 narrow tech disclosure) — approved via directive to proceed to specs + prompts.
2. ✅ **Tom approved the `react-native-signature-canvas` native dependency** (Rule 9.8) — explicit approval 2026-08-12.
3. ✅ **Both designer specs Tom-approved** 2026-08-12: `batch-ce-1-mobile-ui-design-spec.md` (voice-ui) + `batch-ce-1-web-ui-design-spec.md` (web-ui).
4. ✅ **Prompts authored** 2026-08-12: `batch-ce-1-python-engr-prompt.md` → `batch-ce-1-react-native-engr-prompt.md` → `batch-ce-1-react-engr-prompt.md`. Execution order: Part A first (Rule 1.3); B and C in either order after A + `pnpm sync-api-types` (Rule 9.3).
