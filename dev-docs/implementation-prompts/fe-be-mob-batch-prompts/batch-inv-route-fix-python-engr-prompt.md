# Implementation Prompt: INV-ROUTE-FIX — Public Invoice Route Collision (P0)

**Mode**: Pilot Python Engineer
**Batch**: INV-ROUTE-FIX
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §1 (launch-blocking) — surfaced by the 10DLC submission fast-follow investigation, 2026-07-25
**Related record**: `dev-docs/integrations/telnyx/telnyx-10dlc-customer-comms-campaign.md` §0 "Post-Submit Fast-Follow"
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: DLC-B3 (`batch-dlc-b3-react-engr-prompt.md`) — runs AFTER this batch and after `pnpm sync-api-types`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test structure, domain markers, fixtures

Critical rules for this batch:

- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates `openapi.json` + `openapi_schema_map.md`). This is the handoff signal to the React Engineer (DLC-B3).
- **Rule 5**: Never use module-level `TestClient`. Always use the `client` fixture from `conftest.py`.
- **Rule 8 / §13**: All API error responses MUST follow RFC 7807 Problem Details format. The **canonical** handler (`public_invoices.py`) currently uses **plain-string** `detail` (e.g. `detail="Invalid link token"`) — as part of this batch, upgrade those to RFC 7807 dicts so the frontend can render friendly states (see Task 4).
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. This batch **will** break tests by design (see Task 3); migrating them is in-scope, not optional.

---

## Background / Context — What Is Broken and Why (Do Not Re-Litigate)

**A `curl` against the pre-release AWS environment proved a P0:**

```
$ curl -i https://api.pilotfortrades.com/api/v1/public/invoices/A1b2C3
HTTP/2 404
{"detail":"Invoice payment link not found"}
```

That 404 string exists **only** in the legacy handler `invoices.py` — **not** in the signed-token handler the frontend was built against.

### Root cause: duplicate route registration at the same path

Two routers are mounted at the **same** `/api/v1/public` prefix, both defining `GET /invoices/{token}`:

| | Legacy — **WINS (registered first)** | Signed-token — **shadowed, never reached** |
|---|---|---|
| Route def | `invoices.py` `public_router.get("/invoices/{token}")` | `public_invoices.py` `router.get("/invoices/{signed_token}")` |
| Mounted at | `main.py` | `main.py` |
| Impl | `_get_public_invoice_impl` (`invoices.py`) via `_resolve_token` (`invoices.py`) | `get_public_invoice` (`public_invoices.py`) via `_resolve_invoice_link_or_401` (`public_invoices.py`) |

FastAPI matches the **first** registered route, so the legacy handler shadows the canonical one.

### Why this is P0 (not just the fake-token error page)

The two handlers return **incompatible response shapes** for a **valid** token:

| | Legacy `PublicInvoiceResponse` (from `invoices.py`) | Canonical `PublicInvoiceResponse` (from `public_invoices.py`) |
|---|---|---|
| Parties | `tenant_id`, `customer_id` (UUIDs) | `tenant_name`, `customer_name` (strings) |
| Amounts | `subtotal_cents`, `balance_due_cents` | `amount_due_cents`, `amount_paid_cents` |
| Line items | ❌ none | ✅ `line_items[]` |
| Branding / status | ❌ none | ✅ `branding`, `status` |

The frontend `normalizeInvoiceData` (in `apps/web/src/features/public-invoice/types.ts`) expects the **canonical** shape. So **customer invoice views/payments would be broken for any real customer**, independent of the 10DLC sample link.

### This cleanup was already intended and silently abandoned

`test_a92_invoice_crud.py` `test_public_router_removed_from_main` was written to verify the legacy `public_router` was removed from `main.py` — but its body is a **hollow `assert True`** that passes unconditionally, and the router was never actually unregistered. **B20/A92 intended exactly this fix; it just never landed.** This batch completes it.

### Decision (approved by Tom, 2026-07-25 — do not re-litigate)

**Make `public_invoices.py` the single canonical public-invoice router. Remove the legacy `GET /invoices/{token}` and the orphaned `POST /invoices/{token}/pay` from `invoices.py`. Verify no FIND-071/072/073/148 behavior is lost — fold anything still needed into the canonical path. Add a route-uniqueness regression test.**

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. Zero pre-existing failures, or confirm with Tom before starting.

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: `postgres-local` MCP is **read-only verification only**. Never INSERT/UPDATE/DELETE. If a query errors → STOP and ask Tom.

Run all of these before writing code:

```sql
-- 1. Confirm invoice_public_link columns the canonical handler + revocation logic rely on
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice_public_link'
ORDER BY ordinal_position;

-- 2. Confirm payment columns the overpayment logic (FIND-071) relies on — verify amount_variance_cents exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'payment'
  AND column_name IN ('amount_cents','amount_variance_cents','stripe_payment_intent_id','customer_payment_comment','status_id')
ORDER BY ordinal_position;

-- 3. Are there ANY existing invoice_public_link rows (all from test tenants) using the legacy token_hash path (no signed_token, or 'legacy.'-prefixed)?
--    This determines whether legacy-token backward-compat is a live concern (see Task 3 backcompat gate).
SELECT
  count(*) AS total_links,
  count(*) FILTER (WHERE signed_token IS NULL) AS null_signed_token,
  count(*) FILTER (WHERE signed_token LIKE 'legacy.%') AS legacy_prefixed
FROM public.invoice_public_link;
```

> **Backcompat gate (load-bearing):** The canonical `_resolve_invoice_link_or_401` accepts **only signed (dotted) tokens** — it has no `token_hash` fallback. The legacy `_resolve_token` accepted **both**. If query #3 shows **any** `null_signed_token` or `legacy_prefixed` rows that are still `status='active'` and unexpired, removing the legacy path could break **live** links. If count > 0 for active links → **STOP and ask Tom** before deleting the legacy resolver. If all real links are signed (expected for beta), proceed.

## Pre-Work: Read These Source Files

```
backend/app/main.py                                  ← lines 142-143 (legacy mounts) + 331-335 (canonical mount); you will remove line 143's public_router include
backend/api/routes/invoices.py                       ← lines 108-203 (_resolve_token, _generate_token_hash), 284-414 (_get/_pay impls), 1181-1213 (the two public_router routes to remove)
backend/api/routes/public_invoices.py                ← the canonical router (keep + harden); note _resolve_invoice_link_or_401 returns 401/410 only, NO 404
backend/api/schemas/schemas.py                       ← PublicInvoicePayRequest / PublicInvoicePayResponse / legacy PublicInvoiceResponse — confirm which are still referenced after removal
backend/services/stripe_payment_intents.py           ← the PI + webhook payment path; VERIFY it records FIND-071 overpayment variance (see Task 2)
backend/api/routes/webhooks_stripe.py                ← payment_intent.succeeded handler — confirms where a real payment row is written for the canonical flow
backend/tests/batch_b20/test_a92_invoice_crud.py     ← line 676 hollow assert-True test to make real (Task 5)
backend/tests/batch_1d/test_task_1d3_invoice_public_link.py    ← legacy HTTP tests that WILL break (Task 3)
backend/tests/batch_b17/test_find148_invoice_link_tracking.py  ← read-only GET tests (Task 3)
backend/tests/batch_b17/test_find142_143_invoice_pay_schemas.py ← send→signed_token→GET/pay tests (Task 3)
backend/tests/batch_b19/test_find071_overpayment_handling.py   ← imports _pay_public_invoice_impl directly (Task 2 decision)
backend/tests/batch_b19/test_find072_stripe_payment_intent_wiring.py ← imports _pay_public_invoice_impl directly (Task 2 decision)
```

Also run:

```bash
grep -rn "public_router\|_pay_public_invoice_impl\|_get_public_invoice_impl\|_resolve_token" backend/ --include="*.py"
```

---

## Task 1 — Remove the legacy public-invoice route registration (the actual P0 fix)

1. In `main.py`, **remove** the line:
   ```python
   app.include_router(invoices.public_router, prefix="/api/v1/public", tags=["public"])
   ```
   This alone un-shadows the canonical router. Do **not** touch the canonical mount at `main.py`.

2. In `invoices.py`, remove the now-orphaned public routes and the `public_router` object:
   - Delete `public_router.get("/invoices/{token}")` (`invoices.py`) and `public_router.post("/invoices/{token}/pay")` (`invoices.py`).
   - Delete the `public_router = APIRouter()` declaration (`invoices.py`).

3. **Do NOT delete `_pay_public_invoice_impl`, `_get_public_invoice_impl`, or `_resolve_token` yet** — Task 2 decides their fate based on whether the canonical flow preserves FIND-071/072 behavior. Deleting them now would break the FIND-071/072 unit tests that import them directly.

Intermediate check:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
grep -rn "public_router" backend/ --include="*.py"   # expect: zero matches after this task
```

---

## Task 2 — Verify FIND-071/072 overpayment behavior survives, then remove dead impls

The canonical customer-payment path is **PI + webhook**: frontend calls `POST /public/invoices/{token}/payment-intent` (`public_invoices.py`) → Stripe → `webhooks_stripe` `payment_intent.succeeded` writes the `payment` row. The legacy `POST /pay` recorded the payment row directly and carried **FIND-071 overpayment variance** logic (`invoices.py`).

**Verify the canonical flow preserves overpayment recording:**

1. Read `stripe_payment_intents.py` and `webhooks_stripe.py`. Confirm whether the webhook-driven payment write sets `amount_variance_cents` for overpayment (FIND-071) and links the Stripe PI (FIND-072).
2. **If the canonical path already records variance** → the legacy `/pay` impl is fully redundant. Delete `_pay_public_invoice_impl` (`invoices.py`) and migrate the FIND-071/072 unit tests to target the canonical write path (or the service function that now owns variance). Update `test_find071_*` and `test_find072_*` accordingly.
3. **If the canonical path does NOT record variance** → this is a real behavior gap. **STOP and ask Tom** — do not silently drop FIND-071 overpayment handling. (Do not attempt to re-wire the webhook in this batch without sign-off; it may be its own follow-up.)

Also remove `_get_public_invoice_impl` (`invoices.py`) and `_resolve_token` (`invoices.py`) / `_generate_token_hash` **only if** no remaining code imports them (confirm with the grep from Pre-Work; the send-invoice path may still use `_generate_token_hash` for legacy `token_hash` — verify before deleting).

Intermediate check:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 3 — Migrate the legacy HTTP tests to the canonical contract

Removing the legacy routes will break tests that drove them over HTTP. Each must be migrated to the canonical handler's contract, **not** deleted wholesale (the behavior they assert is still required):

| Test file | What breaks | Migration |
|---|---|---|
| `test_task_1d3_invoice_public_link.py` | GET unknown-token asserts **404** (:318); POST `/pay` (:396) | Unknown/garbage token now returns **401** (invalid signature) via canonical handler — update the assertion. Replace `/pay` cases with the canonical `/payment-intent` flow (see `test_find073` for the pattern), or move them under Task 2's migrated tests. |
| `test_find148_invoice_link_tracking.py` | GET via legacy handler | Repoint to the canonical GET; FIND-148 read-only invariant (used_count stays 0 on GET) still applies — the canonical GET is already read-only, so assert it stays 0. |
| `test_find142_143_invoice_pay_schemas.py` | `/pay` HTTP cases | Send endpoint returns `signed_token`; migrate `/pay` assertions to `/payment-intent` (these tokens are already signed, so GET still returns 200). |

**Semantic change to document in your Completion Summary:** an unknown/garbage token changes from **404** (legacy "not found") to **401** (canonical "invalid token"). This is correct — the canonical handler treats an unparseable token as unauthenticated, and 404-vs-401 for public tokens prevents enumeration. The frontend companion (DLC-B3) will add a 404 branch too, but the primary path for a bad token is now 401.

Intermediate check:
```bash
python -m pytest tests/batch_1d/ tests/batch_b17/ tests/batch_b19/ --tb=short -q 2>&1 | tail -15
```

---

## Task 4 — Upgrade canonical error responses to RFC 7807 (enables the friendly frontend states)

The canonical `_resolve_invoice_link_or_401` (`public_invoices.py`) raises **plain-string** `detail` (`"Invalid link token"`, `"Link has expired"`, etc.). Per Rule 8 / §13, convert these to RFC 7807 Problem Details dicts so the frontend can drive friendly invalid/expired states:

```python
# Example — adjust type slugs/titles to match existing conventions in the file
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={
        "type": "https://errors.pilotfortrades.com/invalid-link",
        "title": "Invalid link",
        "status": 401,
        "detail": "This invoice link is invalid. Please check the link in your email.",
    },
)
```

Apply to all 401 and 410 raises in `_resolve_invoice_link_or_401` and the GET/PI handlers. Keep status codes unchanged (401 invalid, 410 expired/revoked/not-found/inactive). Do **not** change the success response shape — the frontend already parses it.

> **Frontend coordination:** DLC-B3 reads `res.status` (401/410), not the body, for its branch logic — so this change is backward-safe for the existing frontend and additive for friendlier copy. Note it in the handoff.

Intermediate check:
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

---

## Task 5 — Make the hollow regression test real + add a route-uniqueness guard

1. Replace the `assert True` body of `test_a92_invoice_crud.py` with a real assertion that the legacy public route is gone AND the path resolves to exactly one route:

```python
def test_public_invoice_route_is_unique_and_canonical(self):
    """/api/v1/public/invoices/{token} must resolve to exactly ONE route (the signed-token handler)."""
    from app.main import app

    matches = [
        r for r in app.routes
        if getattr(r, "path", "") == "/api/v1/public/invoices/{signed_token}"
    ]
    # Exactly one registration — no legacy shadow
    assert len(matches) == 1, f"Expected 1 canonical route, found {len(matches)}"

    # And the legacy path param name must NOT be present (legacy used {token})
    legacy = [
        r for r in app.routes
        if getattr(r, "path", "") == "/api/v1/public/invoices/{token}"
    ]
    assert legacy == [], "Legacy public_router invoice route is still registered"
```

> Verify the exact canonical path string (`{signed_token}` vs `{token}`) against the real route by reading `public_invoices.py` — adjust the assertion to the actual param name.

2. Add a domain test under `tests/domains/invoicing_billing/` (per the domain-folder mapping) that hits `GET /api/v1/public/invoices/{signed_token}` with a **freshly generated valid signed token** and asserts the **canonical shape** (`tenant_name`, `line_items`, `branding`, `status` present) — this is the regression guard proving the pay page gets the right data. Use `generate_signed_token` from `public_link_signer.py` and an invoice_public_link row created via the existing test helper (see `test_find073` fixtures for the pattern). Include `pytestmark = [pytest.mark.domain_invoicing_billing, pytest.mark.unit]`.

---

## Regenerate OpenAPI (handoff signal to DLC-B3)

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
grep -A 5 "public/invoices" backend/openapi_schema_map.md   # confirm only the signed-token route remains
```

---

## Final Verification

### Phase 1 — Unit only (during development)
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full suite (once, before sign-off)
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/invoicing_billing/ tests/batch_1d/ tests/batch_b17/ tests/batch_b19/ tests/batch_b20/ -v 2>&1 | tail -30
echo "=== INV-ROUTE-FIX FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before done. No "pre-existing" exception without Tom's written confirmation. If the FIND-071 variance question (Task 2) is unresolved → STOP and ask Tom.

---

## Definition of Done — INV-ROUTE-FIX

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`, `pytest -m unit`)
- [ ] MCP queries run — `invoice_public_link` + `payment` columns confirmed; legacy-token backcompat gate (query #3) resolved (0 active legacy links, or Tom sign-off)
- [ ] All mandatory source files read
- [ ] **Task 1**: `invoices.public_router` removed from `main.py`; `public_router` + its two routes removed from `invoices.py`; grep shows zero `public_router` matches
- [ ] **Task 2**: FIND-071/072 overpayment behavior confirmed preserved in the PI/webhook path (or escalated to Tom); dead legacy impls removed only after confirming no importers
- [ ] **Task 3**: legacy HTTP tests (task_1d3, find148, find142_143) migrated to canonical contract; 404→401 semantic change documented
- [ ] **Task 4**: canonical 401/410 responses upgraded to RFC 7807; status codes unchanged
- [ ] **Task 5**: `test_a92` hollow `assert True` replaced with real route-uniqueness assertion; new canonical-shape regression test added under `tests/domains/invoicing_billing/`
- [ ] `python export_openapi_json.py` run — only the signed-token public invoice route remains in `openapi_schema_map.md`
- [ ] All new/modified tests use `pytestmark` domain marker + `pytest.mark.unit`; `client` fixture; `test_tenant`/`test_user` (no hardcoded UUIDs)
- [ ] **Phase 1**: all unit tests pass (zero failures)
- [ ] **Phase 2**: full suite passes (zero failures, including integration)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B
- [ ] Handoff: notify the React Engineer that DLC-B3 can start — `pnpm sync-api-types` first (OpenAPI regenerated)
- [ ] Campaign-doc fast-follow (`telnyx-10dlc-customer-comms-campaign.md` §0) payment-path-risk item updated to ✅ once the canonical-shape regression test passes

---

## Completion Summary

Add a Completion Summary to `pilot-launch-plan.md` Appendix B:

```markdown
### INV-ROUTE-FIX — Public Invoice Route Collision (P0): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed

#### What Was Accomplished
- Root cause: duplicate GET /api/v1/public/invoices/{token} — legacy invoices.public_router (main.py) shadowed the signed-token public_invoices.router (main.py), returning an incompatible response shape that broke the customer-facing pay-invoice page. Completed the removal B20/A92 intended but never landed (hollow assert True test).
- Removed legacy public_router + orphaned /pay; made public_invoices.py canonical.
- Verified FIND-071/072 overpayment/PI behavior preserved in the PI/webhook path.
- Upgraded canonical 401/410 responses to RFC 7807.
- Replaced hollow test with a real route-uniqueness guard + canonical-shape regression test.

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/app/main.py` | Updated — removed legacy invoices.public_router include (line 143) |
| `backend/api/routes/invoices.py` | Updated — removed public_router + /invoices/{token} GET + /pay + dead impls |
| `backend/api/routes/public_invoices.py` | Updated — RFC 7807 error bodies |
| `backend/tests/batch_b20/test_a92_invoice_crud.py` | Updated — real route-uniqueness assertion |
| `backend/tests/domains/invoicing_billing/test_public_invoice_canonical.py` | Created — canonical-shape regression |
| ... migrated legacy tests ... | Updated |

#### Tests Added / Migrated
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/invoicing_billing/test_public_invoice_canonical.py` | `invoicing_billing` | N | ✅ |
```
