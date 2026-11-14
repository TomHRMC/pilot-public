# Implementation Prompt: PLP-FIX-6 — Stripe Connect v15 `.get()` Repair + `StripeClient` v1 Migration + Checklist-Flag Wiring (Issues 9, 7a)

**Mode**: `pilot-python-engineer`
**Batch**: PLP-FIX-6 (backend-only)
**Launch plan**: `dev-docs/analysis/pilot-launch-plan.md` §1 / §3.25 (Ord 25)
**Design doc (read first)**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-6-design.md`
**Bug intake / root-cause record**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` (Issue 9 investigation chain, Issue 7a)
**Estimate**: ~2 hours (Tom-approved scope)
**Platform**: Backend (FastAPI + SQLModel + pytest)
**Frontend companion**: **None.** Contract-preserving batch — do **NOT** run `export_openapi_json.py`, do **NOT** ask anyone to run `pnpm sync-api-types`.
**Sequencing**: Runs **before** PLP-FIX-4 (React) — it unblocks the payments surface Tom is testing.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing any code, read these documents **in full**:

1. `backend/pilot-python-engineer-methods.md` — house engineering method (sync routes, session handling, RFC 7807, testing posture)
2. `backend/tests/README-adding-tests.md` — test placement, domain markers, autouse fixtures
3. The design doc linked above — all section letters (A–G). §G decisions are settled; do not re-litigate.

Do not start Task 1 until all three are read.

---

## Batch-Specific Critical Rules

1. **Never call `.get()` on a `StripeObject`.** In `stripe-python` v12+, `StripeObject` no longer subclasses `dict`; `.get()` raises `AttributeError: get` (re-raised as `KeyError: 'get'` via `StripeObject.__getattr__`). This exact line is what broke prod. The house pattern (`backend/scripts/stripe_bootstrap.py`) is: convert once via `.to_dict()`, then dict-read; use `getattr(obj, "attr", default)` for scalar attribute reads. Quote from the bootstrap source: *"StripeObject does not support dict-style .get()"* and *"dict(StripeObject) does not work as expected; use .to_dict() instead."*
2. **Tenant-scoped `select()` only.** `db.get()` is permanently banned on tenant-scoped models. The existing code complies — keep it that way.
3. **Never guess column names.** The Architect ran the MCP verification queries below against the live local DB and recorded the results. You re-run them in Pre-Work and use only returned column names in any SQL you write.
4. **Sync-by-design.** All routes stay sync `def`. `StripeClient` calls are blocking SDK calls in the FastAPI threadpool — same posture as the legacy calls they replace.
5. **No contract changes.** Do not add, remove, or rename any endpoint, request field, or response field. The only externally visible delta is the 502 error-path `detail` **string** (gains the exception class name).
6. **Test fidelity is part of the fix.** Plain-dict Stripe mocks are the reason the suite stayed green while the endpoint was failing on the pre-release AWS environment. Every Stripe fixture you touch becomes a real `stripe.*.construct_from(...)` object.
7. **Checklist-mark calls are non-fatal by design.** The `try/except` + `logger.warning` wrapper around `mark_first_customer` / `mark_catalog_setup` is a settled design decision (design §G.5) — do not "simplify" it away.

---

## Pre-Work: Establish Regression Baseline

```bash
cd backend && pytest -m unit --tb=no -q | tail -5
```

Record the passed/failed counts in your Completion Summary as the baseline. (Reference point: PLP-FIX-3 closed at **4755 passed**.)

---

## Pre-Work: Run MCP Verification Queries

Run these via the `postgres-local` MCP server (read-only). The Architect has already run them; the expected results are recorded — confirm your results match. If any query returns different columns, **STOP and report back** — do not improvise.

**Query 1 — tenant Stripe Connect write-through columns:**
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant' AND column_name LIKE 'stripe%'
ORDER BY ordinal_position;
```
Expected: `stripe_customer_id` (text), `stripe_connect_account_id` (text), `stripe_connect_charges_enabled` (boolean), `stripe_connect_payouts_enabled` (boolean).

**Query 2 — tenant audit column used by the write-through block:**
```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('updated_at', 'stripe_connect_account_id',
                      'stripe_connect_charges_enabled', 'stripe_connect_payouts_enabled');
```
Expected: all 4 rows present.

**Query 3 — onboarding checklist flag columns (FIX4-BE-01 targets):**
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_onboarding_checklist'
ORDER BY ordinal_position;
```
Expected: includes `first_customer_added` (boolean NOT NULL), `first_customer_added_at` (timestamptz nullable), `catalog_setup` (boolean NOT NULL), `catalog_setup_at` (timestamptz nullable), plus all four audit columns (`created_at`, `updated_at`, `created_by`, `updated_by`).

---

## Pre-Work: Read These Source Files

Read before editing anything:

1. `backend/api/routes/stripe_connect.py` — **full file, lines 1–391**. The fix zones: `_get_stripe_connect_client` (84–94), `_get_status_impl` (97–166 — `.get()` offenders at 120–124, write-through at 126–138, `PermissionError` degraded card at 150–157, 502 handler at 158–166), `_onboard_impl` (169–239), endpoint + `/test` layer (282–391).
2. `backend/scripts/stripe_bootstrap.py` lines 346–380 — the `_meta` / `_metadata_to_dict` house pattern you are adopting.
3. `backend/api/routes/customers.py` lines 1–140 — `_create_customer_impl`, both commit paths (attestation path returns at 133; plain path at 135–138).
4. `backend/api/routes/catalog.py` lines 438–498 — `_create_pricebook_item_impl` (commit at 475, refresh at 476, return at 477, rollback handlers 479–498).
5. `backend/services/onboarding_service.py` lines 40–130 — `mark_first_customer` (73–85), `mark_catalog_setup` (88–96): idempotent, self-committing.
6. `backend/api/schemas/schemas.py` — the `StripeConnectStatusResponse` / `StripeConnectOnboardResponse` / `StripeConnectDisconnectResponse` definitions (grep for them; confirm the response fields your impl code sets).
7. `backend/tests/domains/platform_infrastructure/test_stripe_connect.py` — full file. Note every `patch("stripe.Account...")` call site and every plain-dict mock.
8. `backend/tests/domains/invoicing_billing/test_sc1_capability_columns.py` — `TestStatusWriteThrough` (dict mock at ~line 393).
9. `backend/tests/conftest.py` lines 68–145 — `_FOLDER_TO_DOMAIN_MARKER` mapping (test placement rule).
10. `backend/tests/batch_b14/test_a77_onboarding_checklist.py` — existing service-level coverage of the mark functions (your rider tests are endpoint-level wiring tests, not duplicates of these).

---

## Background / Context

**Issue 9** — On prod, `GET /api/v1/stripe-connect/status` returns **502** for every tenant with a connected account, breaking the Settings → Payment Methods page. Tom's probe runs on prod (full chain in the bug intake doc) proved:

- Legacy `stripe.Account.retrieve(acct_id)` **works** (probe A: OK).
- The failure is the **next line**: `account.get("business_profile")` raises `AttributeError: get` because `stripe-python` v12+ removed `dict` inheritance from `StripeObject`. The 09-01 image rebuild installed the pinned `stripe==15.1.0`; the endpoint worked on the previous image.
- `client.v1.accounts.retrieve(acct_id)` **works** (probe C); `client.accounts` emits a `DeprecationWarning` → use the **v1 namespace**.
- The broad `except Exception` swallowed the real error class, emitting the useless 502 detail `"Could not retrieve Stripe account status: get"` — that string **is** the `str()` of `AttributeError("get")`.

**Blast radius (already audited — do not expand scope)**: only `_get_status_impl` uses `.get()` on a `StripeObject`. `_onboard_impl` uses attribute access only; `_disconnect_impl` makes no Stripe call; billing/webhooks consume dict payloads and are unaffected.

**Issue 7a (FIX4-BE-01 rider)** — `mark_first_customer()` and `mark_catalog_setup()` have **zero production callers** (grep-verified). The onboarding checklist items they advance can never complete. PLP-FIX-4 (frontend) deep-links the "Add customer" checklist item — without this wiring, Tom's verification of that batch fails.

**Fixture-fidelity gap** — all Connect tests mock `stripe.Account.retrieve` with plain dicts, which support `.get()`. The suite was green while the endpoint was failing on the pre-release AWS environment. This is the fourth fixture-blindness instance this cycle; this batch closes the Stripe instance permanently.

---

## Design Decisions (Do Not Re-Litigate)

From design §G — settled:

1. **Convert once via `.to_dict()`** in `_get_status_impl` (not `getattr`-per-field) — keeps the existing `.get()` chains working verbatim on a real dict; bootstrap precedent.
2. **`stripe.StripeClient` with the v1 namespace** replaces the module-`stripe.api_key` mutation + legacy classmethods. This is the first `StripeClient` in the codebase — it establishes the house pattern.
3. **Tests patch the factory** (`_get_stripe_connect_client`), not SDK internals, and fixtures are `construct_from`-built real `StripeObject`s.
4. **`mark_catalog_setup` is wired too** (audit found zero callers; same gap class as `mark_first_customer`).
5. **Checklist-mark failures are non-fatal** (`try/except` + `logger.warning`) — a checklist write must never 500 a successful create.
6. **Probe B's `No such customer` is expected** (multi-account key structure) — not a bug, not in scope.
7. **The 502 `detail` string change is safe** — the FE renders the error state generically; no FE change.

---

## Task 1 — `_get_stripe_connect_client()` returns a `StripeClient`

**File**: `backend/api/routes/stripe_connect.py` (lines 84–94)

Replace the function body so it returns a `stripe.StripeClient` instance instead of mutating module state:

```python
def _get_stripe_connect_client():
    """Return a StripeClient configured with the Connect platform key.

    PLP-FIX-6: establishes the house StripeClient pattern (v1 namespace).
    Key precedence UNCHANGED: STRIPE_CONNECT_PLATFORM_KEY → STRIPE_SECRET_KEY.
    No missing-key guard existed before; none is added — the SDK raises on
    use, exactly as the module-level mutation did.
    """
    import stripe

    from core.config import settings as cfg

    stripe_key = getattr(cfg, "STRIPE_CONNECT_PLATFORM_KEY", None) or getattr(
        cfg, "STRIPE_SECRET_KEY", None
    )
    return stripe.StripeClient(api_key=stripe_key)
```

Keep the function-local `import stripe` (matches current style). Behavior note: previously callers did `stripe = _get_stripe_connect_client(); stripe.Account.retrieve(...)`; now they do `client = _get_stripe_connect_client(); client.v1.accounts.retrieve(...)`. Update the local variable name at each call site accordingly.

---

## Task 2 — `_get_status_impl`: the Issue 9 repair

**File**: `backend/api/routes/stripe_connect.py` (lines 117–166)

**2a.** Replace the retrieve + four `.get()` calls (current lines 118–124) with:

```python
    try:
        client = _get_stripe_connect_client()
        account = client.v1.accounts.retrieve(tenant.stripe_connect_account_id)
        # PLP-FIX-6: StripeObject is not a dict in stripe-python v12+.
        # Convert ONCE via .to_dict() (stripe_bootstrap.py house pattern),
        # then all dict-style reads are safe.
        account_dict = account.to_dict()
        account_name = (account_dict.get("business_profile") or {}).get("name") or (
            account_dict.get("settings") or {}
        ).get("dashboard", {}).get("display_name")
        charges_enabled = account_dict.get("charges_enabled", False)
        payouts_enabled = account_dict.get("payouts_enabled", False)
```

**2b.** Leave the write-through block (current lines 126–138) and the `return StripeConnectStatusResponse(...)` (140–146) **behavior-identical**. `account.id` attribute access in the return is fine on a `StripeObject`.

**2c.** Leave the `PermissionError` degraded-card branch (150–157) untouched.

**2d.** Replace the 502 raise (158–166) so the real exception is logged and named:

```python
        logger.exception(
            "Stripe Connect status retrieval failed for tenant %s", tenant_id
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "type": "https://errors.pilotfortrades.com/stripe-error",
                "title": "Stripe API error",
                "status": 502,
                "detail": f"Could not retrieve Stripe account status: {type(e).__name__}: {e!s}",
            },
        )
```

**2e.** Module logger: check the file header (lines 1–58). If `logger = logging.getLogger(__name__)` is absent, add `import logging` + the module-level logger.

---

## Task 3 — `_onboard_impl`: migrate to the v1 namespace

**File**: `backend/api/routes/stripe_connect.py` (lines 169–239)

**3a.** Read the current impl. It calls `stripe.Account.create(type="express", capabilities={...})` and `stripe.AccountLink.create(...)` via the legacy module and reads `account.id`, `link.url`, `link.expires_at` (attribute access — safe).

**3b.** Before writing, verify the installed SDK's v1 create signature:

```bash
cd backend && .venv/bin/python -c "import stripe, inspect; c = stripe.StripeClient(api_key='sk_test_x'); print(inspect.signature(c.v1.accounts.create)); print(inspect.signature(c.v1.account_links.create))"
```

**3c.** Migrate both calls to the v1 namespace, passing **the same field set** the current code passes (Express account type, card_payments + transfers capabilities, and the account-link `account` / `refresh_url` / `return_url` / `type` fields). Use the call form the installed signature supports (a `params={...}` dict, or kwargs if the service accepts them). Attribute access on the returns stays as-is. Record which call form you used in the Completion Summary.

**3d.** `_disconnect_impl` (242–274) makes no Stripe call — do not touch it.

---

## Task 4 — Fixture fidelity: real `StripeObject` mocks

**Files**:
- `backend/tests/domains/platform_infrastructure/test_stripe_connect.py`
- `backend/tests/domains/invoicing_billing/test_sc1_capability_columns.py` (`TestStatusWriteThrough`)

**4a.** Add a fixture factory (top of `test_stripe_connect.py`; if `test_sc1_capability_columns.py` needs the same shape, duplicate the tiny helper or factor it into a shared `tests/` helper module — your call, keep it simple):

```python
import stripe


def _make_connect_account(**overrides) -> "stripe.Account":
    """v15-faithful fixture: a REAL StripeObject (attribute access, NO .get()).

    Any regression to dict-style access in the impl fails here, not in prod.
    """
    values = {
        "id": "acct_test_123",
        "charges_enabled": True,
        "payouts_enabled": True,
        "business_profile": {"name": "Test Electric"},
        "settings": {"dashboard": {"display_name": "Test Electric"}},
    }
    values.update(overrides)
    return stripe.Account.construct_from(values, key="sk_test_fake")
```

**4b.** Repoint every patch from SDK classmethods to the factory, and every dict mock to the factory-built object:

```python
with patch("api.routes.stripe_connect._get_stripe_connect_client") as factory:
    client = MagicMock()
    client.v1.accounts.retrieve.return_value = _make_connect_account()
    factory.return_value = client
    ...
```

Onboard tests: `client.v1.accounts.create.return_value = _make_connect_account()` and `client.v1.account_links.create.return_value = stripe.AccountLink.construct_from({"url": "https://connect.stripe.com/setup/s/test", "expires_at": 1893456000}, key="sk_test_fake")` (adjust the field set to what the impl actually reads — `url`, `expires_at`).

**4c.** Preserve every existing assertion's intent (status codes, response fields, write-through column assertions, RBAC cases). You are changing fixture fidelity and patch points, not test coverage.

---

## Task 5 — New regression tests (the anti-blindness tests)

**File**: `backend/tests/domains/platform_infrastructure/test_stripe_connect.py`

Add a test class (e.g. `TestStatusV15Fidelity`) covering:

1. **Happy path via real StripeObject**: factory returns `client.v1.accounts.retrieve` → `_make_connect_account()`; call the `/test` status endpoint; assert `connected is True`, `charges_enabled is True`, `payouts_enabled is True`, `account_name == "Test Electric"`.
2. **Absent optional nested keys degrade gracefully**: `_make_connect_account()` with `business_profile` and `settings` **removed from the values dict entirely** → response still 200, `account_name is None`, no 502. (This pins the `(… or {})` fallback semantics.)
3. **Unexpected error names its class**: `client.v1.accounts.retrieve.side_effect = ValueError("boom")` → 502; assert the RFC 7807 `detail.detail` string contains `"ValueError"`.
4. **Sabotage check (development-only, NOT committed)**: while developing, temporarily revert one line in `_get_status_impl` from `account_dict.get(...)` to `account.get(...)` and confirm tests 1–2 go **red**. Restore immediately. State in the Completion Summary that you performed this check.

Test-hygiene rules: use the existing client/tenant fixtures in the file; scope assertions to the response body and the specific tenant row you control — never count global rows.

---

## Task 6 — FIX4-BE-01a: wire `mark_first_customer` into customer create

**File**: `backend/api/routes/customers.py` (`_create_customer_impl`, lines 31–138)

**6a.** Module header: add `import logging` + `logger = logging.getLogger(__name__)` (neither exists today) and `from services.onboarding_service import mark_first_customer`. (`onboarding_service` imports only models + stdlib — no circular-import risk; module-level import is the house style, e.g. `quotes.py` imports `services.quote_service`.)

**6b.** Two insertion points (the impl has two exit paths — attestation path returns at line 133, plain path at line 138). Immediately **before each `return customer`**, insert:

```python
    # FIX4-BE-01 (PLP-FIX-6): advance onboarding checklist — never fail the create
    try:
        mark_first_customer(db, user_context.tenant_id)
    except Exception:
        logger.warning(
            "mark_first_customer failed for tenant %s",
            user_context.tenant_id,
            exc_info=True,
        )
```

The mark function is idempotent and self-committing (it commits its own checklist row); both insertion points run **after** the customer commit on their path. Both authenticated and `/test` endpoints flow through `_create_customer_impl`, so both get the behavior.

---

## Task 7 — FIX4-BE-01b: wire `mark_catalog_setup` into pricebook-item create

**File**: `backend/api/routes/catalog.py` (`_create_pricebook_item_impl`, lines 438–498)

**7a.** Module header: add `import logging` + `logger = logging.getLogger(__name__)` if absent, and `from services.onboarding_service import mark_catalog_setup`.

**7b.** After `db.refresh(item)` (line 476), before `return _build_pricebook_item_response(item, db)` (line 477), insert:

```python
        # FIX4-BE-01 (PLP-FIX-6): advance onboarding checklist — never fail the create
        try:
            mark_catalog_setup(db, user_context.tenant_id)
        except Exception:
            logger.warning(
                "mark_catalog_setup failed for tenant %s",
                user_context.tenant_id,
                exc_info=True,
            )
```

The inner `try/except` swallows mark failures, so the outer rollback handlers (479–498) are never triggered by a checklist write — that is intentional (design §G.5).

---

## Task 8 — Rider wiring tests (endpoint-level)

Placement per `_FOLDER_TO_DOMAIN_MARKER` in `conftest.py` (lines 68–145):

**8a.** `tests/domains/crm/` — find the existing customer-create test file and add a class covering:
- Creating a customer via the authenticated endpoint advances the checklist: query `tenant_onboarding_checklist` for the fixture tenant and assert `first_customer_added is True` and `first_customer_added_at is not None`.
- Idempotency: create a second customer; assert the flag stays `True` and the timestamp is unchanged (capture it after the first create).
- Failure isolation: `patch("api.routes.customers.mark_first_customer", side_effect=RuntimeError("x"))` → the create still returns 201 and the customer row exists.

**8b.** `tests/domains/catalog_pricing/` — find the existing pricebook-item-create test file and add the same trio for `catalog_setup` / `catalog_setup_at`, patching `api.routes.catalog.mark_catalog_setup` for the failure-isolation case.

Both: scope every DB assertion to the fixture tenant's row (`WHERE tenant_id = <fixture tenant id>`) — never assert on global counts. Note: `tests/batch_b14/test_a77_onboarding_checklist.py` already covers the service functions directly; your tests prove the **wiring** from the endpoint.

---

## Conditional Sections — Explicit Dispositions

- **Alembic Migration Standards** — **N/A.** No migration in this batch.
- **Schema JSON Sync (`schema_manager.py`)** — **N/A.** No schema change.
- **DB Model Map Regeneration** — **N/A.** No model change.
- **OpenAPI Regeneration** — **N/A. Do not run `export_openapi_json.py`.** No endpoint or contract change; there is no FE handoff and no `pnpm sync-api-types` signal.
- **Mutation Endpoint Audit Context** — **N/A.** No new mutation endpoints; existing endpoints' audit posture unchanged.
- **`/test` Endpoint Pattern** — **N/A (already satisfied).** All touched endpoints already have `/test` twins that delegate to the same `_impl` functions; they inherit the fix.
- **Celery Task Structure** — **N/A.**
- **Seed Data Rollout (rule §11.5 consideration)** — **N/A, recorded for the audit trail.** This batch adds/changes **no** DB data: no new columns, tables, lookup rows, or seed values. The checklist flags are runtime writes by pre-existing service functions. No `seed_*.py` change; no `README-seed-data.md` update.

## RFC 7807 Error Format (awareness)

The 502 handler you edit already uses the RFC 7807 dict envelope — keep that shape. You are only changing the inner human-readable `detail` string to include `type(e).__name__`. Do not introduce any plain-string `detail` anywhere.

## Sync-by-Design (rules §21)

This batch modifies routes. All endpoints stay sync `def`; blocking SDK calls (`client.v1.*`) run in the FastAPI threadpool exactly as the legacy calls did. Do not introduce `async def` into any touched function.

## Lint, Format & Modern-Python Idioms (rules §22–§23)

Ruff runs from inside `backend/` with backend-relative paths:

```bash
cd backend && ruff check api/routes/stripe_connect.py api/routes/customers.py api/routes/catalog.py \
  tests/domains/platform_infrastructure/test_stripe_connect.py \
  tests/domains/invoicing_billing/test_sc1_capability_columns.py \
  tests/domains/crm/ tests/domains/catalog_pricing/
```

Fix **all** reported errors on files you touched (E501 line length included — the long f-string in the 502 detail and the `logger.warning` calls may need wrapping).

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd backend && pytest -m unit --tb=no -q | tail -5
```

Fast feedback loop. After Task 4/5 you may also run the targeted files directly, e.g. `pytest tests/domains/platform_infrastructure/test_stripe_connect.py -q`.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end, before DoD sign-off)

```bash
# 1. Ruff — command from the Lint section above (fix ALL errors)

# 2. Full suite minus live-vendor markers (requires_stripe is deselected by default per pytest.ini)
cd backend && pytest --tb=no -q | tail -5
```

**Batch-specific spot checks:**

```bash
# Zero dict-style access on Stripe objects remains in the Connect route:
cd backend && grep -n "account\.get(" api/routes/stripe_connect.py   # expect: no output

# Zero legacy Stripe classmethod calls remain in the Connect route:
cd backend && grep -n "stripe\.Account\.\|stripe\.AccountLink\." api/routes/stripe_connect.py   # expect: no output (comments/docstrings excepted)

# Module no longer mutates global stripe.api_key:
cd backend && grep -n "stripe\.api_key" api/routes/stripe_connect.py   # expect: no output

# Wiring is present:
cd backend && grep -n "mark_first_customer" api/routes/customers.py && grep -n "mark_catalog_setup" api/routes/catalog.py
```

Baseline vs final counts go in the Completion Summary (baseline was recorded in Pre-Work; suite must end at baseline + your new tests, zero regressions).

---

## Definition of Done — PLP-FIX-6

- [ ] All three Pre-Work sections complete (baseline recorded; MCP queries re-run and match expected results; all 10 files read)
- [ ] Task 1: `_get_stripe_connect_client()` returns `stripe.StripeClient`; no module `stripe.api_key` mutation remains
- [ ] Task 2: `_get_status_impl` uses `client.v1.accounts.retrieve` + single `.to_dict()` conversion; write-through + `PermissionError` branch behavior-identical; 502 logs via `logger.exception` and names the exception class
- [ ] Task 3: `_onboard_impl` on v1 namespace with identical field set; installed-SDK signature verified first; call form recorded
- [ ] Task 4: all Connect test mocks are `construct_from`-built real `StripeObject`s; patches point at `_get_stripe_connect_client`
- [ ] Task 5: three new regression tests pass; sabotage check performed (and reverted)
- [ ] Task 6: `mark_first_customer` wired on both `_create_customer_impl` exit paths with the non-fatal wrapper
- [ ] Task 7: `mark_catalog_setup` wired into `_create_pricebook_item_impl` with the non-fatal wrapper
- [ ] Task 8: six rider wiring tests (3 crm + 3 catalog_pricing) pass, tenant-scoped assertions
- [ ] Phase 1 run after each task group — recorded
- [ ] Phase 2 run once at the end: ruff clean on touched files + full suite green (zero regressions vs baseline)
- [ ] All four spot checks produce the expected output
- [ ] Explicitly NOT done (correctly): no Alembic migration, no `export_openapi_json.py`, no `schema_manager.py`, no seed-script change
- [ ] Completion Summary filled in below (append to this file's appendix)

---

## Completion Summary

When finished, append your summary to `## Appendix — Completion Summary` at the bottom of this file using **exactly** this structure:

### PLP-FIX-6 — Stripe Connect v15 Repair + Checklist Wiring: Completion Summary

#### What Was Accomplished
(5–8 bullets: the Issue 9 repair, the client migration, the fixture-fidelity conversion, the new regression tests incl. the sabotage-check confirmation, both checklist wirings, suite delta)

#### Files Changed / Created
(Grouped by Production code / Tests, with one-line purpose each)

#### Tests Added
(Count + names; baseline → final suite counts; Phase 1 / Phase 2 evidence)

#### SDK Verification
(The `inspect.signature` output for `v1.accounts.create` / `v1.account_links.create`, and which call form — `params=` dict or kwargs — you used)

#### Regeneration Status
(State: "N/A — no migration, no OpenAPI regen, no schema sync, no seed change" with one-line reasons)

#### Spot-Check Output
(The four grep commands' actual output)

---

## After This Task — Next Step

1. Commit on the batch branch per `dev-docs/sdlc/repo-sdlc.md` and notify Tom: **PLP-FIX-6 ready for deploy**.
2. There is **no FE handoff** — do not trigger the `pnpm sync-api-types` flow.
3. Tom's post-deploy verification list lives in the design doc's final section (payments surface loads; onboard round-trip; checklist advances after adding a customer and a pricebook item).
4. After deploy verification, the queue is: **PLP-FIX-4** (React — already authored, checklist deep-link + email/phone validation + unit-price input), then **PLP-FIX-5** (mixed).

---

## Appendix — Completion Summary

### PLP-FIX-6 — Stripe Connect v15 Repair + Checklist Wiring: Completion Summary

#### What Was Accomplished

- **Issue 9 repair**: `_get_status_impl` now calls `client.v1.accounts.retrieve()` and converts the returned `StripeObject` to a plain dict via a single `.to_dict()` call (the `stripe_bootstrap.py` house pattern). All four `.get()` chains now operate on a real dict, eliminating the `AttributeError: get` that 502'd every connected test tenant on the pre-release AWS environment. The 502 handler now logs via `logger.exception` and names the exception class (`type(e).__name__`) in the RFC 7807 `detail` string.
- **`StripeClient` v1 migration**: `_get_stripe_connect_client()` returns a `stripe.StripeClient` instance instead of mutating module-level `stripe.api_key`. Both `_get_status_impl` and `_onboard_impl` use the v1 namespace (`client.v1.accounts.retrieve/create`, `client.v1.account_links.create`). This is the first `StripeClient` in the codebase — establishes the house pattern.
- **Fixture-fidelity conversion**: all Stripe Connect test mocks converted from plain-dict `MagicMock` objects to real `stripe.Account.construct_from(...)` / `stripe.AccountLink.construct_from(...)` `StripeObject` instances. Patches repointed from `stripe.Account.retrieve` to `_get_stripe_connect_client` factory. The dict-mock blind spot that kept the suite green while the endpoint was failing is now permanently closed.
- **Three new anti-blindness regression tests** (`TestStatusV15Fidelity`): happy path via real StripeObject, absent-nested-keys graceful degradation, and unexpected-error class-name assertion. Sabotage check performed (reverted one `.to_dict()` line → tests 1–2 went red with `AttributeError: get`; restored immediately).
- **Checklist wiring**: `mark_first_customer` wired into both exit paths of `_create_customer_impl` (attestation + plain); `mark_catalog_setup` wired into `_create_pricebook_item_impl`. Both use the non-fatal `try/except` + `logger.warning` wrapper per design §G.5.
- **Suite delta**: baseline 4755 passed → final 4764 passed (+9 new tests, 0 regressions). 1 pre-existing skip unchanged.

#### Files Changed / Created

**Production code:**
- `backend/api/routes/stripe_connect.py` — Issue 9 repair: `StripeClient` factory, v1 namespace migration, `.to_dict()` conversion, named 502 handler
- `backend/api/routes/customers.py` — `mark_first_customer` wiring on both create exit paths + `logging`/`logger` setup
- `backend/api/routes/catalog.py` — `mark_catalog_setup` wiring after pricebook item commit + `logging`/`logger` setup

**Tests:**
- `backend/tests/domains/platform_infrastructure/test_stripe_connect.py` — full rewrite: `construct_from` fixtures, factory-patch pattern, 3 new `TestStatusV15Fidelity` regression tests
- `backend/tests/domains/invoicing_billing/test_sc1_capability_columns.py` — `TestStatusWriteThrough` mock converted to real `StripeObject`, patch repointed to factory
- `backend/tests/domains/crm/test_onboarding_wiring_customer.py` — new: 3 rider wiring tests for `mark_first_customer`
- `backend/tests/domains/catalog_pricing/test_onboarding_wiring_catalog.py` — new: 3 rider wiring tests for `mark_catalog_setup`

**Baseline:**
- `backend/tests/baselines/error_path_coverage.json` — pruned 2 stale entries (stripe-connect onboard + disconnect now have error-path coverage)

#### Tests Added

9 new tests total:
- `TestStatusV15Fidelity::test_happy_path_via_real_stripe_object`
- `TestStatusV15Fidelity::test_absent_optional_nested_keys_degrade_gracefully`
- `TestStatusV15Fidelity::test_unexpected_error_names_its_class`
- `TestMarkFirstCustomerWiring::test_create_customer_advances_checklist`
- `TestMarkFirstCustomerWiring::test_create_customer_is_idempotent_on_checklist`
- `TestMarkFirstCustomerWiring::test_mark_failure_does_not_fail_create`
- `TestMarkCatalogSetupWiring::test_create_pricebook_item_advances_checklist`
- `TestMarkCatalogSetupWiring::test_create_pricebook_item_is_idempotent_on_checklist`
- `TestMarkCatalogSetupWiring::test_mark_failure_does_not_fail_create`

Baseline: 4755 passed, 1 skipped → Final: 4764 passed, 1 skipped (+9, 0 regressions).
Phase 1: targeted Stripe Connect tests green after each task group.
Phase 2: full vendor-deselected suite green in one run (56.47s).

#### SDK Verification

`inspect.signature` output for `stripe.StripeClient(api_key='sk_test_x')`:
- `v1.accounts.create`: `(params: AccountCreateParams | None = None, options: RequestOptions | None = None) -> Account`
- `v1.account_links.create`: `(params: AccountLinkCreateParams, options: RequestOptions | None = None) -> AccountLink`
- `v1.accounts.retrieve`: `(account: str, params: AccountRetrieveParams | None = None, options: RequestOptions | None = None) -> Account`

**Call form used**: `params={...}` dict (the v1 service signature requires a single `params` positional argument, not kwargs).

#### Regeneration Status

N/A — no migration, no OpenAPI regen, no schema sync, no seed change. No model files modified, no endpoints added/removed/renamed, no contract changes. The only externally visible delta is the 502 error-path `detail` string (gains the exception class name) — an error-path diagnostic, not a schema field.

#### Spot-Check Output

```
=== SPOT CHECK 1: account.get( ===
(empty — no output)

=== SPOT CHECK 2: stripe.Account. / stripe.AccountLink. ===
9:    ``stripe.Account.create(type="express", ...)`` with explicit capability
(only a docstring reference; no live classmethod calls)

=== SPOT CHECK 3: stripe.api_key ===
(empty — no output)

=== SPOT CHECK 4a: mark_first_customer ===
25:from services.onboarding_service import mark_first_customer
139:            mark_first_customer(db, user_context.tenant_id)
142:                "mark_first_customer failed for tenant %s",
155:        mark_first_customer(db, user_context.tenant_id)
158:            "mark_first_customer failed for tenant %s",

=== SPOT CHECK 4b: mark_catalog_setup ===
25:from services.onboarding_service import mark_catalog_setup
484:            mark_catalog_setup(db, user_context.tenant_id)
487:                "mark_catalog_setup failed for tenant %s",
```
