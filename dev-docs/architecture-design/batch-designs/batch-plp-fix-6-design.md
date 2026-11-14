# Batch Design: PLP-FIX-6 — Stripe Connect v15 `.get()` Repair + `StripeClient` v1 Migration + Checklist-Flag Wiring (Issues 9, 7a)

**Batch code**: PLP-FIX-6 (backend-only, Python Engineer)
**Date**: 2026-09-02
**Author**: Pilot Architect
**Status**: Tom-approved 2026-09-02 — runs **BEFORE** PLP-FIX-4 (Ord 24) despite higher Ord number; it is ~2h and unblocks the payments surface.
**Bug intake doc**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` (Issue 9 investigation chain, Issue 7a)
**Companion frontend batch**: none — contract-preserving; `pnpm sync-api-types` NOT required after this batch.

---

## Scope Statement

Three production defects, one batch:

1. **Issue 9 (P0-adjacent, payments surface blocked)** — `GET /api/v1/stripe-connect/status` returns **502** on prod for every tenant with a connected Stripe account. Root cause (proven via Tom's three probe runs on prod, recorded in the bug intake doc): `stripe-python` v12+ removed `dict` inheritance from `StripeObject`; dict-style `.get()` now raises `AttributeError: get` (re-raised as `KeyError: 'get'` via `StripeObject.__getattr__`, `_stripe_object.py`). The 09-01 stale-image rebuild installed the pinned `stripe==15.1.0`; the endpoint previously worked on the old image. The four `.get()` calls at `backend/api/routes/stripe_connect.py` blow up inside the broad `except Exception` → 502 with the useless detail string `"Could not retrieve Stripe account status: get"`.
2. **Issue 7a (design-time finding from PLP-FIX-4)** — `mark_first_customer()` in `backend/services/onboarding_service.py` has **zero production callers** (grep-verified), so the onboarding checklist "Add your first customer" item never advances. PLP-FIX-4 (frontend) deep-links that checklist item; without this wiring the item stays forever incomplete. Same audit found `mark_catalog_setup()` (`onboarding_service.py`) also has zero production callers — same gap class, same one-line fix.
3. **Fixture-fidelity gap (test-suite blind spot)** — every Stripe Connect test mocks `stripe.Account.retrieve` with **plain dicts** (`tests/domains/platform_infrastructure/test_stripe_connect.py`, `tests/domains/invoicing_billing/test_sc1_capability_columns.py`). Plain dicts support `.get()`, so the suite stayed green while prod broke. This is the fourth instance of the fixture-blindness class this cycle (quote_version fixtures, MSW dev-seed UUIDs, dict-mocked Stripe responses).

**Explicitly out of scope**: billing/webhook Stripe code paths (audited — they consume dict webhook payloads, not `StripeObject` attribute access; safe), cross-account customer lookups (probe B's `InvalidRequestError: No such customer` is the expected consequence of the multi-account key structure — Connect sandbox key vs billing test key; not a bug), any frontend change.

**Blast radius confirmation** (from the code audit recorded in the bug intake doc): the `.get()`-on-`StripeObject` pattern exists **only** in `_get_status_impl`. `_onboard_impl` uses attribute access only (`account.id`, `link.url`, `link.expires_at`) and `_disconnect_impl` makes no Stripe call. Billing, webhooks, and the bootstrap script are unaffected; `stripe_bootstrap.py` already documents the house pattern ("StripeObject does not support dict-style .get()").

---

## A. Input Read Summary

| Input | What was read / verified | Date |
|---|---|---|
| `PLP-testing-bugs-2026-09-02.md` | Issue 9 full investigation chain: 502 body, three Tom probe runs (A: legacy `Account.retrieve` OK; B: `Customer.retrieve` cross-account `InvalidRequestError` — expected; C: `StripeClient.v1.accounts.retrieve` OK + `client.accounts` `DeprecationWarning`), corrected final root cause, blast-radius audit | 2026-09-02 |
| `backend/api/routes/stripe_connect.py` | **Full file 1–391**: `_get_stripe_connect_client` (84–94, mutates module `stripe.api_key`), `_get_status_impl` (97–166 — the four `.get()` offenders at 120–124, `PermissionError` → degraded card, broad `except` → 502 at 158–166), `_onboard_impl` (169–239 — `stripe.Account.create(type="express", capabilities=…)` + `stripe.AccountLink.create(…)`, attribute access only), `_disconnect_impl` (242–274 — no Stripe call), endpoint layer + `/test` twins (282–391) | 2026-09-02 |
| `backend/scripts/stripe_bootstrap.py` | House pattern at 356–380: `_meta()` / `_metadata_to_dict()` — `getattr(obj, "metadata", None)` + `.to_dict().get(...)`; docstrings explicitly state "StripeObject does not support dict-style .get()" and "dict(StripeObject) does not work as expected; use .to_dict() instead" | 2026-09-02 |
| `backend/api/routes/customers.py` | `_create_customer_impl` (31–138): two commit paths — DLC-1 attestation path (customer commit at 102–104, audit commit at 122–123, `return customer` at 133) and plain path (commit at 135–137, `return` at 138) | 2026-09-02 |
| `backend/api/routes/catalog.py` | `_create_pricebook_item_impl` (438–498): item flush + raw-SQL version insert, single `db.commit()` at 475, `db.refresh` at 476, return at 477, rollback handlers at 479–498 | 2026-09-02 |
| `backend/services/onboarding_service.py` | `mark_first_customer` (73–85) and `mark_catalog_setup` (88–96): idempotent, self-committing, `_get_or_create_checklist` guarded | 2026-09-02 |
| Codebase grep — `StripeClient` | **Zero existing usage** anywhere in `backend/` — this batch establishes the house `StripeClient` pattern | 2026-09-02 |
| Codebase grep — `mark_catalog_setup` / `mark_first_customer` | Zero production callers for both; only the definitions and `tests/batch_b14/test_a77_onboarding_checklist.py` unit tests | 2026-09-02 |
| Connect test inventory | `tests/domains/platform_infrastructure/test_stripe_connect.py` (`TestStripeConnectStatus`/`Onboard`/`Disconnect` — patches `stripe.Account.retrieve` returning plain dicts), `tests/domains/invoicing_billing/test_sc1_capability_columns.py` (`TestStatusWriteThrough`, dict mock at line 393), plus `test_sc1_connect_webhook.py`, `test_sc1_payment_idempotency.py`, `test_sc1_connect_rbac.py` (webhook/idempotency/RBAC paths — dict payloads, not affected) | 2026-09-02 |
| `backend/python-engr-std-prompt-inclusions.md` | Full re-read (945 lines) before prompt authoring — per architect rule §9.1 | 2026-09-02 |

**Live DB (MCP) state**: no schema change in this batch; the prompt's Pre-Work MCP queries verify the `tenant.stripe_connect_*` write-through columns and `tenant_onboarding_checklist` flag/timestamp columns against `information_schema` before any SQL is written into tests.

---

## B. Migration Plan

**None.** This batch makes zero schema changes and zero data changes. It modifies application code and test fixtures only.

- No Alembic migration.
- No seed-data changes (checklist flags are runtime writes by existing service functions, not new lookup/reference values). The prompt carries an explicit "Seed Data Rollout — N/A" statement per architect rule §11.5 so the consideration is on record.
- Pre-Work MCP verification queries (read-only) confirm the columns the code writes through to: `tenant.stripe_connect_account_id`, `tenant.stripe_connect_charges_enabled`, `tenant.stripe_connect_payouts_enabled` (names to be confirmed verbatim by the engineer's MCP query — do not hand-write SQL from memory), and `tenant_onboarding_checklist.first_customer_added` / `first_customer_added_at` / `catalog_setup` / `catalog_setup_at`.

---

## C. Execution Order

| # | Step | File(s) | Notes |
|---|---|---|---|
| 1 | Regression baseline: `pytest -m unit --tb=no -q \| tail -5` + MCP verification queries + mandatory file reads | — | Pre-Work gate; record baseline counts |
| 2 | Refactor `_get_stripe_connect_client()` → returns `stripe.StripeClient` (no module `stripe.api_key` mutation) | `backend/api/routes/stripe_connect.py` (84–94) | Establishes the house `StripeClient` pattern; missing-key behavior preserved exactly |
| 3 | Fix `_get_status_impl`: `client.v1.accounts.retrieve(...)` + single `account.to_dict()` conversion + `logger.exception` + `type(e).__name__` in the 502 detail | `backend/api/routes/stripe_connect.py` (97–166) | The Issue 9 repair; `PermissionError` degraded-card branch and tenant capability write-through preserved byte-for-byte in behavior |
| 4 | Migrate `_onboard_impl`: `client.v1.accounts.create(...)` + `client.v1.account_links.create(...)` | `backend/api/routes/stripe_connect.py` (169–239) | Params dict mirrored from current kwargs; engineer verifies installed `stripe==15.1.0` v1-service signature before writing |
| 5 | Fixture fidelity: convert Connect test mocks to `stripe.Account.construct_from(...)`; repoint patches from `stripe.Account.retrieve` to `_get_stripe_connect_client` | `tests/domains/platform_infrastructure/test_stripe_connect.py`, `tests/domains/invoicing_billing/test_sc1_capability_columns.py` | Real `StripeObject` fixtures make any future `.get()` regression go red |
| 6 | New regression tests: status happy path via v15-faithful fixture; status with absent optional nested keys (`business_profile` missing → degraded name, no crash); 502 detail contains exception class name | `tests/domains/platform_infrastructure/test_stripe_connect.py` | The anti-blindness tests |
| 7 | FIX4-BE-01a: wire `mark_first_customer` into `_create_customer_impl` (both commit paths, non-fatal wrapper) | `backend/api/routes/customers.py` (before `return` at 133 and 138) | Issue 7a |
| 8 | FIX4-BE-01b: wire `mark_catalog_setup` into `_create_pricebook_item_impl` (after commit, non-fatal wrapper) | `backend/api/routes/catalog.py` (after 476) | Audit-completing rider |
| 9 | Rider wiring tests: endpoint → flag advances; idempotent on second create; mark-failure does not fail the create | `tests/domains/customers/…`, `tests/domains/catalog/…` (per `_FOLDER_TO_DOMAIN_MARKER` in `conftest.py`) | Endpoint-level, not service-level — `tests/batch_b14/test_a77_onboarding_checklist.py` already covers the service functions directly |
| 10 | Phase 2 verification: ruff on changed files + full suite vendor-deselected; spot checks | — | DoD gate |

Steps 2→4 must land together (the client factory change is breaking to call sites by design). Steps 5–6 follow immediately so the suite proves the fix. Steps 7–9 are independent of 2–6 and may interleave.

---

## D. New API Endpoints

**None.** All changes are internal to existing endpoint implementations. Request/response contracts are unchanged:

- `GET /api/v1/stripe-connect/status` → `StripeConnectStatusResponse` — same shape; only the 502 `detail` string gains the exception class name prefix (an error-path diagnostic string, not a schema field).
- `POST /api/v1/stripe-connect/onboard`, `DELETE /api/v1/stripe-connect` — unchanged.
- `POST /api/v1/customers/`, `POST /api/v1/catalog/pricebook-items` — unchanged responses; new internal side effect (checklist flag write).

**No OpenAPI regeneration, no `pnpm sync-api-types`, no FE handoff.** This is stated explicitly in the prompt so the engineer does not run the regeneration machinery needlessly.

---

## E. Pattern Reuse Decisions

| `mvp-arch.md` §16 pattern / house standard | Applies? | How |
|---|---|---|
| RFC 7807 error format | Preserved | The 502 handler keeps the existing error envelope; only the human-readable `detail` string changes. No new error shapes. |
| Sync-by-design (rules §21) | Preserved | All routes remain sync `def`; the `StripeClient` calls are blocking SDK calls in the FastAPI threadpool — same posture as today's legacy calls. |
| Tenant-scoped `select()` (no `db.get()`) | Preserved | `_get_status_impl`'s tenant lookup is untouched. |
| `/test` endpoint twins | Preserved | `/test` variants (350–391) delegate to the same `_impl` functions; they inherit the fix automatically. |
| Idempotency-Key | N/A | No new POST/PATCH contract. |
| House Stripe pattern (from `stripe_bootstrap.py`) | **Adopted** | `.to_dict()` conversion for dict-style reads; `getattr` for scalar attribute reads; never `.get()` on a `StripeObject`. The bootstrap script's docstrings are quoted in the prompt as the canonical reference. |
| `StripeClient` v1 namespace | **Established** (new house pattern) | First `StripeClient` usage in the codebase. All future Stripe service migrations copy this pattern: construct a client via a factory, call `client.v1.<resource>.<method>`, patch the factory in tests. Recorded as a candidate ADR only if a second Stripe surface migrates — a single endpoint group does not clear the §7.1 bar on its own. |

---

## F. Shared Module Interfaces

### F.1 — `backend/api/routes/stripe_connect.py`

```python
def _get_stripe_connect_client() -> "stripe.StripeClient":
    """Return a StripeClient configured with the Connect platform key.

    Key precedence UNCHANGED: STRIPE_CONNECT_PLATFORM_KEY → STRIPE_SECRET_KEY.
    Missing-key behavior UNCHANGED (whatever the current code raises/returns
    when neither env var is set — preserve it exactly).
    No longer mutates module-level stripe.api_key.
    """
```

Status-impl access pattern (the Issue 9 fix):

```python
client = _get_stripe_connect_client()
account = client.v1.accounts.retrieve(tenant.stripe_connect_account_id)
account_dict = account.to_dict()  # StripeObject → plain dict ONCE (bootstrap house pattern)

account_name = (account_dict.get("business_profile") or {}).get("name") or (
    account_dict.get("settings") or {}
).get("dashboard", {}).get("display_name")
charges_enabled = account_dict.get("charges_enabled", False)
payouts_enabled = account_dict.get("payouts_enabled", False)
```

502 handler (diagnosability fix):

```python
except Exception as e:
    logger.exception("Stripe Connect status retrieval failed for tenant %s", tenant_id)
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Could not retrieve Stripe account status: {type(e).__name__}: {e!s}",
    )
```

Onboard-impl call migration (params content unchanged, transport updated):

```python
account = client.v1.accounts.create(params={...same dict as today's kwargs...})
link = client.v1.account_links.create(params={...same dict as today's kwargs...})
# attribute access unchanged: account.id, link.url, link.expires_at
```

### F.2 — Test fixture factory (new, lives in `test_stripe_connect.py`; copied to `test_sc1_capability_columns.py` or factored into a shared `tests/` helper if both files need it)

```python
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

Patch pattern (replaces `patch("stripe.Account.retrieve", ...)` everywhere in Connect tests):

```python
with patch("api.routes.stripe_connect._get_stripe_connect_client") as factory:
    client = MagicMock()
    client.v1.accounts.retrieve.return_value = _make_connect_account()
    factory.return_value = client
    ...
```

### F.3 — FIX4-BE-01 wiring (non-fatal wrapper — see §G.5)

`customers.py`, immediately before each `return customer` (lines 133 and 138):

```python
    # FIX4-BE-01 (PLP-FIX-6): advance onboarding checklist — never fail the create
    try:
        mark_first_customer(db, user_context.tenant_id)
    except Exception:
        logger.warning("mark_first_customer failed for tenant %s", user_context.tenant_id, exc_info=True)
```

`catalog.py`, in `_create_pricebook_item_impl` after `db.refresh(item)` (line 476), before `return`:

```python
        # FIX4-BE-01 (PLP-FIX-6): advance onboarding checklist — never fail the create
        try:
            mark_catalog_setup(db, user_context.tenant_id)
        except Exception:
            logger.warning("mark_catalog_setup failed for tenant %s", user_context.tenant_id, exc_info=True)
```

Module-level imports (`from services.onboarding_service import mark_first_customer` / `mark_catalog_setup`) — `onboarding_service` imports only models + stdlib, so there is no circular-import risk with the route modules. Add `logger = logging.getLogger(__name__)` to either route module if absent.

---

## G. Open Questions Resolved

1. **Convert-once (`to_dict()`) vs `getattr`-per-field?** → Convert once. The impl reads five fields including two-level-nested ones; a single `account.to_dict()` keeps the existing `.get()` chains working verbatim on a real dict, which is exactly the `stripe_bootstrap.py` `_metadata_to_dict` precedent ("dict(StripeObject) does not work as expected; use .to_dict() instead"). Minimal diff, minimal re-review surface.
2. **`StripeClient` v1 namespace vs repairing the legacy module API?** → v1 namespace. Tom's probe C proved `client.v1.accounts.retrieve` works on prod's pinned `stripe==15.1.0` and that `client.accounts` emits a `DeprecationWarning`. Migrating now (while the file is open) avoids a second forced migration when the legacy shims are removed. `_disconnect_impl` makes no Stripe call and stays untouched.
3. **Where do tests patch after the client migration?** → At the factory, `_get_stripe_connect_client`, returning a `MagicMock` client whose `.v1.accounts.*` methods return `construct_from`-built real `StripeObject`s. This (a) decouples tests from SDK internals, (b) keeps fixtures v15-faithful so the dict-mock blind spot cannot recur, (c) leaves one obvious patch point for future Connect work.
4. **`mark_catalog_setup` audit result?** → Also zero production callers (grep-verified). Wired into `_create_pricebook_item_impl` — creating a pricebook item is the "catalog setup" action the checklist item describes. Both flags now advance from real user flows.
5. **Should a checklist-mark failure fail the primary create?** → No. The mark functions self-commit to a different table; a failure there must never 500 a successfully created customer/pricebook item. Both call sites wrap in `try/except Exception` + `logger.warning(..., exc_info=True)`. This is recorded here so the engineer does not "simplify" the wrapper away.
6. **Probe B's `InvalidRequestError: No such customer 'cus_…'`?** → Not a bug; not in scope. The Connect platform key (sandbox) and the billing key (test) point at different Stripe accounts, so a billing-side customer ID is invisible to the Connect key. Recorded so nobody re-opens it during this batch.
7. **Does the 502 detail-string change break the FE?** → No. `PaymentMethodSettingsPage.tsx` renders the error state generically (it does not parse the detail string); the contract shape is unchanged.
8. **v1 `create` signatures (kwargs vs `params=` dict)?** → Engineer verifies against the installed `stripe==15.1.0` service signatures (`backend/.venv` — `inspect.signature(stripe.StripeClient().v1.accounts.create)` or the generated `account_service.py` docstring) before writing, and passes the same field set the current code passes (`type="express"`, `capabilities` card_payments/transfers, account-link `account`/`refresh_url`/`return_url`/`type`). The design pins the field set; the SDK-exact call form is an implementation detail verified locally.

---

## Verification (post-implementation, Tom on prod)

1. **Payments surface unblocked**: Settings → Payment Methods loads the status card for Lang Electric — "Connected", charges/payouts enabled, account name shown (no 502 banner).
2. **Disconnect/reconnect round-trip**: onboard link generation still redirects to Stripe-hosted onboarding (v1 `create` path exercised end-to-end).
3. **Checklist advances**: dashboard onboarding checklist "Add your first customer" completes after creating a customer (HotRDA tenant has none); "Set up your catalog" completes after creating a pricebook item.
4. **Suite health**: full vendor-deselected suite green with the new v15-faithful fixtures; deliberately reverting one `.to_dict()` line locally makes the new status tests go red (the anti-blindness proof — engineer demonstrates this during development, does not commit the sabotage).
