# Batch Design: STRIPE-CONNECT-1 — Tenant Card Payments via Stripe Connect (Express)

**Version**: 1.1
**Date**: 2026-08-28 (v1.1 addendum 2026-08-29)
**Author**: Pilot Architect
**Batch**: STRIPE-CONNECT-1 (Phase 1 — launch plan §1.1 Ord 6; card §3.6; **§7 founder-gate item**)
**Owner**: Pilot Python Engineer (Part A) → Pilot React Engineer (Part B, **gated on marketing-UI designer spec + Tom approval**, Rule 1.5); Tom (Stripe Dashboard webhook registration, sandbox + prod)
**Model decision**: ✅ **Express + direct charges** — Tom, 2026-08-28 (recorded as ADR-0019); destination charges + platform fees deferred to Phase 1.5 per the card
**Prompt (Part A)**: `batch-stripe-connect-1-python-engr-prompt.md` ✅ 2026-08-28
**Prompt (Part B-2 — BE addendum A9)**: `batch-stripe-connect-1-b2-python-engr-prompt.md` *(v1.1 — authored 2026-08-29 after spec approval; executes before Part C)*
**Prompt (Part C — frontend B1–B5)**: `batch-stripe-connect-1-c-react-engr-prompt.md` *(v1.1 — authored 2026-08-29; gated on Part B-2's OpenAPI regen; §1.3 mixed-batch protocol)*
**Source plan**: `pilot-launch-plan.md` §3.6
**Estimated session**: Part A 4–5 h · Part B 2–3 h
**Cost impact**: **$0** — no new AWS resources; one new env var pair on existing ECS task defs (`STRIPE_CONNECT_PLATFORM_KEY`, `STRIPE_CONNECT_WEBHOOK_SECRET`); Stripe-side economics unchanged (connected account pays Stripe fees; no application fee in MVP)

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `pilot-launch-plan.md` | §1.1 Ord 6 (deps: Tom model decision ✅ 2026-08-28; UI-FIX-2F ✅); §3.6 full card (goal, 5 scope bullets, explicit-outs); §7 gate row "tenant card payments live (test-mode verified end-to-end)" | 2026-08-28 |
| **Tom's model decision** | **Express** chosen 2026-08-28 (this session) over Standard — lowest founder-cohort onboarding friction, Stripe-hosted KYC/payouts/1099s, Account Links pattern preserved | 2026-08-28 |
| `batch-ui-fix-2f-design.md` + `ui-fix-2-decisions.md` | The as-built Connect foundation: 3 authed + 3 `/test` endpoints; `tenant.stripe_connect_account_id` migration; `stripe_account=` routing; `PaymentNotConfiguredError` 402 guard; sandbox platform `acct_XXXXXXXXXXXX` + test connected account `acct_XXXXXXXXXXXX` | 2026-08-28 |
| `backend/api/routes/stripe_connect.py` | Full file (315 lines): `_get_status_impl` (live `Account.retrieve` each call — **no local capability persistence**), `_onboard_impl` (**`stripe.Account.create(type="standard")` — line 143; flips to `express` per ADR-0019**), `_disconnect_impl` (nulls id; non-deauthorizing); all three endpoints gated on `settings.tenant.write` (**owner + operator — card requires owner-only**); hardcoded refresh/return URLs | 2026-08-28 |
| `backend/services/stripe_payment_intents.py` | Full file (398 lines): `create_payment_intent` (mock stub when `STRIPE_SECRET_KEY` unset; `stripe_account=` direct charge; **Stripe idempotency key = `pi_invoice_{invoice_id}_{amount_cents}` — same-amount repeat partial payments would collapse**); `handle_payment_intent_succeeded` (Payment row + variance + status + notification; idempotent by `stripe_payment_intent_id`); `handle_payment_intent_failed` | 2026-08-28 |
| `backend/api/routes/webhooks_stripe.py` | 12 event branches (subscription lifecycle, `payment_intent.*`, `checkout.session.completed`, `payment_method.attached`, `invoice.*`, refunds) — **zero Connect events** (`account.updated`, `account.application.deauthorized`, `charge.dispute.*` unhandled); dedup via `stripe_webhook_event_processed` (TEXT PK `event_id`, MCP-verified present) | 2026-08-28 |
| `backend/api/routes/public_invoices.py` | `PublicInvoiceResponse` schema (line 42); GET `/invoices/{signed_token}` (line 175); POST `/payment-intent` (line 261, 402/manual-payment fallback at ~314); POST `/confirm-payment` (line 330) — **no `Idempotency-Key` header support** on either POST | 2026-08-28 |
| `backend/core/idempotency.py` + `backend/utils/idempotency.py` | Existing house idempotency stack: `idempotency_key` table (24h response cache, `MachineLogMixin`), cleanup Beat task, natural-key fallback (72h offline), `X-Idempotency-Replay` header — **adopt, do not reinvent** (precedents: `payment_schedules.py`, `invoices.py` signoff) | 2026-08-28 |
| `backend/core/config.py` | `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` declared; **`STRIPE_CONNECT_PLATFORM_KEY` and `STRIPE_CONNECT_WEBHOOK_SECRET` NOT declared** (current code uses `getattr` fallback) | 2026-08-28 |
| `stripe-pricing-config.md` | §8 registered-events table (10 events, both endpoints, confirmed 2026-07-14) — gains the Connect endpoint + 6 events; the launch-plan card's "§10" pointer is stale (doc is subscription-scoped; line 10 excludes Connect) — corrected in this batch | 2026-08-28 |
| `pilot-operations.md` | §11.2 manual-payment fallback spec (phone/email/"Contact us…check, card, or Zelle"); §11.3 sandbox testing guide (Options A/B, 4242 card); §11.4 Payment Method page 4 states (Loading / Not connected / Incomplete / Connected) — **settings FE states pre-designed; no new settings spec needed** | 2026-08-28 |
| `pilot-adr-log.md` | Decision Index through ADR-0018 — **ADR-0019** is the next number (Express + direct charges) | 2026-08-28 |
| `mvp-prd.md` | §3.6: Stripe one-time payment on public link (Elements; PCI out of scope); adjustable amount + required variance comment; `amount_variance_cents`; underpay preserves balance / overpay flagged; 90-day signed URL | 2026-08-28 |
| FE surfaces | `apps/web/src/app/i/[token]/page.tsx` (public invoice page) + `features/public-invoice/InvoicePaymentModal.tsx` (raw `fetch` — public unauthenticated context, §G Q6) + `PaymentMethodSettingsPage.tsx` + `(profile-pages)/settings/billing/payment-method/page.tsx` | 2026-08-28 |
| `postgres-local` MCP (4 queries) | ① `tenant` stripe cols: `stripe_customer_id text NULL`, `stripe_connect_account_id text NULL` — **no capability columns** ② `payment` cols (23): `idempotency_key varchar NULL`, `stripe_payment_intent_id text NULL`, `amount_variance_cents int NULL`, `paid_via text NULL`, variance-resolution set ✓ ③ `stripe_webhook_event_processed` exists (dedup) ④ alembic head `58c3ad26129f` (design-time; engineer re-verifies — QB-H1 landed two migrations since) | 2026-08-28 |
| `batch-qb-h1-design.md` | Format exemplar (mixed-status header, A–G, pre-built appendix pattern) | 2026-08-28 |

---

## B. Migration Plan

One Alembic migration (blank revision; DDL + data). No new tables; **no NOT NULL additions** (3-part pattern not required — both columns nullable).

### B.1 Pre-Migration Verification (MCP state at design time)

| Check | Result | Source |
|---|---|---|
| Dev alembic head | `58c3ad26129f` at design time; **QB-H1 landed `3c69652df5d1` + `b1f8b5f00f33` after** — engineer re-verifies head in pre-work | MCP 2026-08-28 |
| `tenant` stripe columns | `stripe_customer_id text NULL`, `stripe_connect_account_id text NULL` | MCP 2026-08-28 |
| `payment` columns | full set verified incl. `idempotency_key`, `stripe_payment_intent_id`, variance set | MCP 2026-08-28 |
| `stripe_webhook_event_processed` | exists (TEXT PK `event_id`) | MCP 2026-08-28 |

### B.2 Migration `stripe_connect_1_capability_columns`

`upgrade()`:
1. `ALTER TABLE tenant ADD COLUMN stripe_connect_charges_enabled BOOLEAN NULL;`
2. `ALTER TABLE tenant ADD COLUMN stripe_connect_payouts_enabled BOOLEAN NULL;`
3. **Data (idempotent, `SET LOCAL session_replication_role = 'replica';`)**: `INSERT` 2 `notification_type` rows — `stripe_connect_disconnected`, `stripe_dispute_opened` (`ON CONFLICT DO NOTHING`; cols byte-identical to the `seed_core.py` entries) — and 6 `notification_template` rows (2 types × `email`/`in_app`/`push`, `tenant_id NULL`, `WHERE NOT EXISTS`-guarded; copy per §F.4, byte-identical to `seed_platform.py`).
4. Backfill: `UPDATE tenant SET stripe_connect_charges_enabled = true, stripe_connect_payouts_enabled = true WHERE stripe_connect_account_id IS NOT NULL;` (safe default for existing connections — the first `account.updated` or `/status` refresh corrects any false positive; documented in §G Q3).

`downgrade()`: delete the 6 templates + 2 types (value-scoped); `DROP COLUMN` both.

### B.4 v1.1 Addendum — Billing-Contact Columns (designer followup, resolved 2026-08-29)

**Driver**: the Part B `ManualPaymentPanel` needs contractor phone/email on the 200 GET (`mkt-stripe-connect-1-design-spec.md` §12.1); Part A's A6 shipped the payment-state flags only.

**Decision (see §G Q9)**: option (a) — two nullable columns on `tenant`. MCP-verified 2026-08-29: `tenant` has no contact columns; `tenant_email_branding` has **no** contact fields (logo/color/signature/footer only), killing option (c).

Migration `stripe_connect_1_billing_contact`:
1. `ALTER TABLE tenant ADD COLUMN billing_contact_phone TEXT NULL;`
2. `ALTER TABLE tenant ADD COLUMN billing_contact_email TEXT NULL;`

Nullable — no NOT NULL, no 3-part pattern, no backfill (null = contractor hasn't entered it; the panel's both-null fallback line covers it). **Seed rollout (Rule 11.5)**: dev tenant `…0001` gains realistic values in `seed_test_tenant.py` so the panel renders locally; `schema_manager.py set` for both columns; README-seed-data §4 updated. `downgrade()`: drop both columns.

### B.3 Seed Data Rollout (Rule 11.5 — REQUIRED)

**Layer 1 — Core/Platform (Group A/B):**
- `seed_core.py`: `notification_type` dict gains `stripe_connect_disconnected` + `stripe_dispute_opened` (byte-identical to migration).
- `seed_platform.py`: 6 template-copy entries (the established `(code, channel)` upsert loop).

**Layer 2 — Scenario data:** the dev/test tenant(s) that hold a `stripe_connect_account_id` (engineer verifies via MCP — e.g., the `…0001` dev tenant if configured per pilot-operations §11.3 Option A) get `charges_enabled=true, payouts_enabled=true` in the owning seed script so local/dev surfaces render the connected state. **No new scenario entities.**

**Verification:** `seed_core.py --mode inspect`; `pytest -m unit` green; README-seed-data §4 updated. **Schema JSON sync (schema change):** `schema_manager.py set` for both `tenant` columns (path-based; read `README-schema_manager.md` first).

---

## C. Execution Order

| # | Task (Part A — Backend) | Card scope item | Gate to proceed |
|---|---|---|---|
| A1 | **Account-type alignment (ADR-0019)**: `stripe_connect.py` `Account.create(type="standard")` → `type="express"` + `capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}}`; module docstring updated (Account Links pattern unchanged); sandbox test account `acct_XXXXXXXXXXXX` stays Standard (mixed-type testing noted in ADR) | Rewire per model decision | Existing stripe_connect tests updated + green |
| A2 | **§B.2 migration + §B.3 seed rollout** (capability columns + 2 notification types + 6 templates + backfill; schema_manager JSON sync) | Webhook coverage foundation | Full cycle test; `seed_core.py --mode inspect`; unit green |
| A3 | **Connect webhook endpoint**: `POST /api/v1/webhooks/stripe-connect` in `webhooks_stripe.py` with `STRIPE_CONNECT_WEBHOOK_SECRET`; tenant resolution via `event.account` → `tenant.stripe_connect_account_id`; handlers: `account.updated` (persist both flags), `account.application.deauthorized` (null id + flags + owner notification), `charge.dispute.created`/`closed` (owner notification), `payment_intent.succeeded`/`payment_intent.payment_failed` (delegate to existing handlers — they resolve via PI metadata); all deduped via `stripe_webhook_event_processed` | Webhook coverage: `account.updated`, capability/payout, charge/dispute paths | New handler tests green (constructed-event payloads, signature verify mocked) |
| A4 | **Owner-only RBAC**: onboard + disconnect gain an inline owner guard (`role_code == "owner"` per house pattern — `roles.py`/`reports.py` precedent) returning 403 RFC 7807 for operator/accountant; status stays `settings.tenant.write` | Owner-only RBAC on Connect management | Role-matrix tests (owner 200, operator 403, accountant 403) |
| A5 | **Idempotency hardening**: (a) `POST /payment-intent` + `POST /confirm-payment` adopt the existing `Idempotency-Key` header pattern (`core/idempotency.py`; 24h cache; replay returns cached response); (b) Stripe-side key → `pi_{invoice_id}_{amount_cents}_{client_key_or_uuid4}` (same-amount partial payments no longer collapse; retries still dedupe) | Idempotency keys on all payment mutations | Replay tests (same key → one PI, cached response); two same-amount payments → two PIs |
| A6 | **Public GET payment state**: `PublicInvoiceResponse` gains `card_payments_enabled: bool` + `payment_unavailable_reason: Literal["not_connected","charges_disabled"] | None` — computed from LOCAL columns (no live Stripe call on the public hot path); 402 guard on POST stays as backstop; `GET /status` refreshes local flags from Stripe (write-through) | Graceful tenant-not-connected states (BE half) | Schema tests; no live-Stripe in unit tests |
| A7 | **Env/docs**: `config.py` declares `STRIPE_CONNECT_PLATFORM_KEY` + `STRIPE_CONNECT_WEBHOOK_SECRET`; `.env.example`; `aws-env-mgmt-ops-plan.md` §3 rows (its §10 maintenance rules); `stripe-pricing-config.md` §8 gains Connect endpoint + 6 events (and the stale "§10" pointer corrected); **Tom's Dashboard step documented** (register Connect endpoint in sandbox + prod, set the secret) | — | Docs merged; `pytest -m unit` green |
| A8 | **Part A final gate** — ruff changed-files; Phase 1 unit → Phase 2 vendor-deselected full suite **+ `requires_stripe` marker suite** (this batch touches Stripe-covered code — inclusion call explicit) | — | Zero failures |
| **A9** *(v1.1 addendum — Part B-2)* | **Billing-contact fields**: §B.4 migration + seed rollout; **new router** `api/routes/billing_payment_contact.py` — `GET` + `PATCH /api/v1/settings/billing/payment-contact` (RBAC `settings.tenant.write`, Idempotency-Key 24h per house rule, `EmailStr` validation, `model_fields_set` partial-update semantics); 200 `PublicInvoiceResponse` gains `tenant_phone` / `tenant_email` from the local columns (public-contract naming; still no live Stripe call); OpenAPI regen → `pnpm sync-api-types` re-run for Part C | Panel data source (designer followup item #1) | Schema tests; PATCH round-trip tests; GET field-presence tests (both / phone-only / both-null) |

| # | Task (Part C — Frontend; designer spec ✅ Tom-approved 2026-08-29; **gated on Part B-2**) | Card scope item |
|---|---|---|
| B1 | **Designer spec** (pilot-marketing-ui-designer): `/i/[token]` payment states — `enabled` (Pay CTA → modal), `not_connected` + `charges_disabled` (upfront manual-payment panel per pilot-operations §11.2 copy: contractor phone/email + "Contact us to arrange payment by check, card, or Zelle"); token-only, WCAG 2.2 AA. Tom approves → Architect authors the React prompt | Graceful not-connected states (FE half) |
| B2 | Public page consumes `card_payments_enabled`/`payment_unavailable_reason`; `InvoicePaymentModal` opens only when enabled; sends `Idempotency-Key` (uuid v4 per attempt) on `payment-intent` | Public `/i/[token]` pay flow E2E (test mode) |
| B3 | Settings Payment Method page: consume local-backed flags (the §11.4 four states are pre-designed — verify wiring; add `payouts_enabled=false` warning chip if absent) | Owner visibility |
| B4 | **E2E verification (test mode)**: pilot-operations §11.3 playbook — Option B full UI onboarding in sandbox + 4242 payment on a public link → Payment row + connected-account charge visible in Stripe Dashboard; results recorded in the React prompt's completion summary (pairs with §2 row 2-8's Phase 2 checkpoints) | Pay flow end-to-end in test mode |
| **B5** *(v1.1 addendum)* | **Settings billing-contact inputs**: two labeled fields (phone / email) in `ManualPaymentSection` on the Payment Method page → `PATCH /settings/billing/payment-contact`; helper copy "shown to customers on your invoice payment page when card payments are off"; empty-state nudge when both null. Composes the existing settings-form pattern — no designer spec (§G Q9 proportionality call, same as Q7's warning chip) | Panel data source (UI half) |

### C.1 Explicit exclusions (card's "Explicitly out" + design decisions)

- **No application-fee / 0.5% platform-fee model** (Phase 1.5/2.0).
- **No tenant subscription-billing changes** (C-B1–C-B14 ✅); **no dunning** (C-B6 ✅).
- **No dispute-resolution UI** — dispute handling is owner-notification only; resolution happens in Stripe (Phase 1.5 candidate).
- **No migration of the sandbox test account** to Express — it stays Standard (mixed-type coverage; ADR-0019).
- **No `apiClient` conversion of the public page's raw `fetch`** — unauthenticated public context (§G Q6).

---

## D. New API Endpoints

| Path | Method | Auth | RBAC | Request → Response | Errors |
|---|---|---|---|---|---|
| `/api/v1/webhooks/stripe-connect` | POST | Stripe signature (`STRIPE_CONNECT_WEBHOOK_SECRET`) | none (machine) | Stripe event payload → `{"status": "received"}`; dedup via `stripe_webhook_event_processed` | 400 invalid signature/payload |
| *(modified)* `/api/v1/settings/billing/stripe-connect/onboard` | POST | JWT | `settings.tenant.write` **+ owner-role guard** | → `{account_link_url, expires_at}` | 403 non-owner (RFC 7807); 502 Stripe error |
| *(modified)* `/api/v1/settings/billing/stripe-connect` | DELETE | JWT | `settings.tenant.write` **+ owner-role guard** | → `{}` | 403 non-owner |
| *(modified)* `/api/v1/settings/billing/stripe-connect/status` | GET | JWT | `settings.tenant.write` (unchanged) | → `{connected, account_id?, account_name?, charges_enabled, payouts_enabled}` — now write-through-refreshes local flags | 502 Stripe error |
| *(modified)* `/api/v1/public/invoices/{signed_token}` | GET | signed token | none | response gains `card_payments_enabled: bool`, `payment_unavailable_reason: "not_connected" \| "charges_disabled" \| null` | 401/410 token |
| *(modified)* `/api/v1/public/invoices/{signed_token}/payment-intent` | POST | signed token + **`Idempotency-Key` (optional, 24h cache)** | none | unchanged + replay-safe | 402 not-configured; 401 token |
| *(modified)* `/api/v1/public/invoices/{signed_token}/confirm-payment` | POST | signed token + **`Idempotency-Key` (optional)** | none | unchanged + replay-safe | 401 token |
| *(v1.1)* `/api/v1/settings/billing/payment-contact` | GET | JWT | `settings.tenant.write` | → `{billing_contact_phone, billing_contact_email}` (settings-form hydration) | 401 |
| *(v1.1)* `/api/v1/settings/billing/payment-contact` | PATCH | JWT | `settings.tenant.write` | `{billing_contact_phone?, billing_contact_email?}` (omitted = unchanged, explicit null = cleared) + `Idempotency-Key` → updated values | 422 invalid email |
| *(v1.1 modified)* `/api/v1/public/invoices/{signed_token}` | GET | signed token | none | response also gains `tenant_phone: string \| null`, `tenant_email: string \| null` (from `tenant.billing_contact_*`) | 401/410 token |

**OpenAPI regeneration REQUIRED** (new endpoint + modified response/request shapes) → `python export_openapi_json.py` → **`pnpm sync-api-types` is the Part B handoff signal** (§9.3).

---

## E. Pattern Reuse Decisions

| Pattern / rule | Application |
|---|---|
| **§16 four-class severity + empty-state vocabulary** | The `/i/[token]` manual-payment panel is a state variant on an existing surface (designer composes — never a new top-level pattern) |
| **Idempotency (infra-constraints §5)** | Existing `core/idempotency.py` stack adopted (24h TTL, replay header, cleanup task already running) — no new mechanism |
| **Webhook dedup** | `stripe_webhook_event_processed` shared across platform + Connect endpoints (event IDs are globally unique) |
| **Owner-notification pipeline** | New types ride the SD-2/SD-3 notification stack (type → 3 channel templates → preference matrix → outbox); recipient = tenant owner (`role_code == "owner"` — the QB-H1 `qb_connection_notification.py` precedent) |
| **Two-key Stripe posture** | Platform key (subscription billing) and Connect platform key (Connect API + PI routing) stay separate Settings fields; fallback-to-platform-key behavior preserved for dev |
| **RFC 7807 + 404-not-403** | New 403 owner-guard is the deliberate exception (the resource is known-visible to the caller's role class; enumeration N/A) |
| **Sync-by-design** | All handlers sync `def`; Stripe SDK calls are blocking-by-design (existing house posture) |
| **Cost guardrail** | $0 delta — flagged per infrastructure-constraints §1 (no review needed) |

---

## F. Shared Module Interfaces

### F.1 `api/routes/webhooks_stripe.py` (modified)

```python
@router.post("/stripe-connect")
async def stripe_connect_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Connect-account events (direct charges, account lifecycle, disputes).
    Verifies with STRIPE_CONNECT_WEBHOOK_SECRET; resolves tenant via event['account']
    → tenant.stripe_connect_account_id; dedups via stripe_webhook_event_processed."""

def handle_connect_account_updated(db: Session, payload: dict) -> None:
    """Persist charges_enabled/payouts_enabled onto tenant (idempotent)."""

def handle_connect_deauthorized(db: Session, payload: dict) -> None:
    """Null stripe_connect_account_id + flags; enqueue stripe_connect_disconnected to owner."""

def handle_connect_dispute(db: Session, payload: dict, *, closed: bool) -> None:
    """Enqueue stripe_dispute_opened (or closed-note) to owner with amount + due-by."""
```

### F.2 `api/routes/stripe_connect.py` (modified)

`_onboard_impl`: `stripe.Account.create(type="express", country="US", capabilities={"card_payments": {"requested": True}, "transfers": {"requested": True}})`; owner-guard helper `_require_owner_role(user_context)` shared by onboard/disconnect (403 RFC 7807 otherwise).

### F.3 `services/stripe_payment_intents.py` (modified)

```python
def create_payment_intent(db, invoice_id, amount_cents, customer_comment, tenant_id,
                          *, idempotency_key: str | None = None) -> dict:
    # Stripe-side key: f"pi_{invoice_id}_{amount_cents}_{idempotency_key or uuid4()}"
```

### F.4 New notification content (byte-identical: migration ↔ `seed_platform.py`)

| Type / Channel | Subject | Body summary |
|---|---|---|
| `stripe_connect_disconnected` / email | `[Payments] Stripe account disconnected` | Card payments on invoice links are paused; manual-payment instructions now shown to customers; reconnect path Settings → Payment Method |
| `stripe_connect_disconnected` / in_app + push | same | Short variant + deep link |
| `stripe_dispute_opened` / email | `[Payments] A customer disputed a payment` | Amount, invoice link, respond-by date, "respond in your Stripe dashboard" (no in-Pilot dispute UI in MVP) |
| `stripe_dispute_opened` / in_app + push | same | Short variant |

### F.5 Celery

No new tasks. Existing cleanup (`cleanup_expired_idempotency_keys`, 02:00) covers the new payment-intent keys.

---

## G. Open Questions Resolved

**Q1 — Direct vs destination charges?** **Direct charges** (`stripe_account=` — already built): funds land in the contractor's account, contractor pays Stripe fees, platform-fee layering deferred (Phase 1.5). Destination charges + `application_fee_amount` would be the fee-collection model — explicitly out per the card.

**Q2 — Standard→Express flip is honest about the as-built state.** UI-FIX-2F created `type="standard"` accounts (line 143). The Account Links hosted-onboarding pattern and `stripe_account=` routing are model-agnostic and stay; the account **type** flips + capabilities are requested explicitly (Express requires it). The sandbox test account `acct_XXXXXXXXXXXX` remains Standard — direct charges behave identically across types, so mixed-type test coverage is free. Recorded in ADR-0019.

**Q3 — Backfill true/true safe?** The only tenants with `stripe_connect_account_id` today are dev/test (prod has none — QB-H1-era prod has zero Connect usage). true/true is a cosmetic default corrected by the first `account.updated`/`/status` refresh; the public hot path reads the flags but the 402 guard remains the hard backstop.

**Q4 — Why a separate Connect webhook endpoint (not reuse the platform one)?** Stripe delivers connected-account events (direct charges, `account.*`) only to endpoints registered **for connected accounts**; the platform endpoint receives platform-account events only. Two endpoints, two signing secrets, one dedup table. Tom registers the Connect endpoint in Dashboard (sandbox + prod) — Step A7 documents it; **`payment_intent.succeeded` for customer card payments arrives at the Connect endpoint**, which is why its handler delegates to the existing logic.

**Q5 — Owner-guard mechanism?** No `require_owner` dependency exists in the codebase; the house pattern is inline `role_code == "owner"` checks (e.g., `roles.py` last-owner guard, `reports.py::_is_owner_or_manager`). Adopted as-is; inventing a new permission key (`stripe_connect.manage`) would require RBAC-catalog seeding disproportionate to the delta (revisit if a second Connect management surface appears).

**Q6 — Public page keeps raw `fetch`?** Yes — `apiClient` is the rule for authenticated app surfaces (it injects the Amplify JWT); `/i/[token]` is an unauthenticated public surface with no token to inject. The modal keeps `fetch`, gains `Idempotency-Key` + the enabled-gate. Documented here so the React Engineer doesn't "fix" it.

**Q7 — Designer-spec scope?** The settings page's four states are already designed (`pilot-operations.md §11.4`) — B3 is verification + a warning chip, no new spec. Only `/i/[token]`'s payment states need a spec → **one** marketing-UI designer spec, Tom-approved, then the React prompt (Rule 1.5). If Tom prefers, the designer scope can be a one-page state table rather than full mockups (state×copy×token spec) — flagged as his call at the spec gate.

**Q8 — `STRIPE_CONNECT_PLATFORM_KEY` currently undeclared?** `getattr` fallback works but hides config. Both Connect env vars become declared Settings fields (default `""` = mock/dev fallback preserved), `.env.example` documented, env-mgmt §3 rows added (its §10 maintenance rules). No Terraform change required in-batch — the vars ride the existing secrets pattern; prod values are Tom's post-merge secrets step (tracked in A7 docs). **⚠️ Erratum (2026-08-30, found at deploy-verification)**: "no Terraform change" was wrong — `local.common_secrets` in `modules/compute/main.tf` never injected the two vars (only `secret_key`/`publishable_key`/`webhook_secret` were mapped). Tom added the two `valueFrom` mappings (`connect_platform_key` / `connect_webhook_secret` JSON keys) + `terraform apply` as part of the webhook-registration tail. Deployed env vars were empty until then.

**Q9 — Payment-contact data source (v1.1; designer followup item #1, Tom's direction 2026-08-29)?** **Option (a): `billing_contact_phone` / `billing_contact_email` nullable TEXT on `tenant`.** Option (b) (`tenant_payment_settings` table) is a table for two fields — introduce it only if a second payment-config field group ever appears. Option (c) is dead: MCP-verified 2026-08-29 that `tenant_email_branding` holds logo/color/signature/footer only (the designer's "support_email/support_phone-adjacent" note was inaccurate), and it's email-branding-scoped regardless. **No fallback chain** — never implicitly publish the owner user's personal phone/email on a public money page; both-null renders the spec §6.4 fallback line, and the settings surface (B5) nudges the contractor to fill it in. **Response naming**: the 200 GET ships `tenant_phone` / `tenant_email` (public-contract semantics; storage keeps `billing_contact_*`). **Settings UI needs no designer spec** — two inputs on a pre-designed page (§11.4) composing the existing settings-form pattern; same proportionality call as Q7's warning chip, flagged for Tom.

---

## H. Surface Mockup Reference (Part B)

| Surface | Platform | Change | Spec source |
|---|---|---|---|
| `/i/[token]` public invoice page — payment section | web (public, unauthenticated) | 3-state payment area: `enabled` (Pay CTA → `InvoicePaymentModal`), `not_connected`, `charges_disabled` (manual-payment panel, §11.2 copy) | **New**: `mkt-stripe-connect-1-design-spec.md` (pilot-marketing-ui-designer; Tom-approved before the React prompt) |
| Settings → Billing → Payment Method | web (authed) | Consume local-backed capability flags; `payouts_enabled=false` warning chip | Pre-designed: `pilot-operations.md §11.4` (4 states) — no new spec |
| `InvoicePaymentModal` | web (public) | Enabled-gate + `Idempotency-Key` per attempt | Existing component — no new spec |

§16 pattern consumption: four-class severity (warning chip), empty-state vocabulary (manual-payment panel), always-preview-before-send (N/A — public surface), optimistic UI (N/A).

## I. Component Manifest (Part B)

| Component | Destination | Status |
|---|---|---|
| `ManualPaymentPanel` (name TBD by designer) | `apps/web/src/features/public-invoice/` | **Candidate-new** — extracted state panel if the designer calls for it; otherwise inline state variants in the existing page |
| `InvoicePaymentModal` | `apps/web/src/features/public-invoice/` | Existing — modified (enabled-gate, idempotency header) |
| `PaymentMethodSettingsPage` | `apps/web/src/features/settings/components/` | Existing — modified (flags + warning chip) |

No `packages/ui/` additions anticipated; designer confirms against `packages/ui/src/index.ts` (Rule 1.5.4).
