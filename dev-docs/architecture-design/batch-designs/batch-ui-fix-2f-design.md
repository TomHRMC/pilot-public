# Batch UI-FIX-2F Design — Payment Method Screen + Stripe Connect Flow (Design Phase)

> **Stripe Context (Updated 2026-07-20)**: The existing Stripe configuration (`stripe-pricing-config.md`) covers **Pilot's own subscription billing**. It explicitly does NOT cover tenant → customer invoice payments. The `STRIPE_SECRET_KEY` test mode key is already in `backend/.env`.
>
> **Architecture decision**: Using **Stripe Account Links** (server-side onboarding), NOT the old OAuth 2.0 redirect approach. Account Links requires NO `STRIPE_CONNECT_CLIENT_ID` and NO frontend OAuth redirect. This is the current recommended Stripe Connect pattern.
>
> **Tom's Stripe setup confirmed**: Platform = `acct_XXXXXXXXXXXX` (HotRMC sandbox — already set up as Connect platform). Test connected account = `acct_XXXXXXXXXXXX` (simulates a contractor for dev testing). The sandbox `STRIPE_SECRET_KEY` for `acct_XXXXXXXXXXXX` must be added to `backend/.env` for Connect testing.

**Batch**: UI-FIX-2F  
**Fix**: FIX-020  
**Phase**: Design first — UI Designer produces spec; Python Engineer + React Engineer implement after Tom approves  
**Type**: Design → Mixed (BE + FE)  
**Estimated effort**: ~2h UI Designer + ~3–4h Python Engineer + ~3–4h React Engineer  
**Dependencies**: None for design phase. Implementation: Python Engineer runs first, then React Engineer.  
**Source decisions**: `ui-fix-2-decisions.md § FIX-020` + `ui-fix-1-decisions.md § FIX-004`

---

## A. Input Read Summary

| Input | Key Finding |
|---|---|
| `ui-fix-2-decisions.md` FIX-020 | Payment Method page at `/settings/billing/payment-method`; Stripe Connect OAuth flow; status endpoint; disconnect |
| `ui-fix-1-decisions.md` FIX-004 | Pre-launch requirement confirmed by Tom: `stripe_connect_account_id` missing from `tenant` table; `create_payment_intent()` must use per-tenant key |
| `backend/services/stripe_payment_intents.py` | Uses Pilot's platform `STRIPE_SECRET_KEY` — must be updated to use `stripe_account=tenant.stripe_connect_account_id` |
| `tenant` table (MCP confirmed) | Has `stripe_customer_id` (Pilot billing) but no `stripe_connect_account_id` — migration required |
| `frontend/apps/web/src/app/(authed)/settings/billing/page.tsx` | Renders `BillingSettingsPage` — currently shows placeholder for payment method setup |
| FIX-019 Profile dropdown | Payment Method linked from Profile dropdown → `/settings/billing/payment-method` |

---

## B. Migration Plan

### DB Migration: Add `stripe_connect_account_id` to `tenant`

**Pre-migration verification** (verify via MCP before implementation):
```sql
-- 1. Confirm stripe_connect_account_id does NOT exist yet
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
AND column_name = 'stripe_connect_account_id';

-- 2. Confirm current tenant table structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
ORDER BY ordinal_position;

-- 3. Verify alembic head
SELECT version_num FROM public.alembic_version;
```

**Migration**: Blank migration, add nullable TEXT column (no NOT NULL — tenants start disconnected):

```python
def upgrade() -> None:
    op.add_column(
        "tenant",
        sa.Column("stripe_connect_account_id", sa.Text(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("tenant", "stripe_connect_account_id")
```

**3-part NOT NULL pattern**: Not applicable — `stripe_connect_account_id` is intentionally nullable (NULL = no Stripe connected).

---

## C. Execution Order

| # | Phase | Task | Owner |
|---|---|---|---|
| 1 | Design | Read source files, understand current billing page and Stripe service | UI Designer |
| 2 | Design | Design Payment Method settings page (connection status, connect/disconnect flow, manual payment fallback) | UI Designer |
| 3 | Design | Tom reviews and approves design spec | Tom |
| 4 | Implementation | Python Engineer: DB migration + 4 Stripe Connect endpoints + `stripe_payment_intents.py` update | Python Engineer |
| 5 | Implementation | Python Engineer: Run `export_openapi_json.py` to regenerate OpenAPI | Python Engineer |
| 6 | Implementation | React Engineer: `pnpm sync-api-types` → hook + page implementation | React Engineer |

---

## D. New API Endpoints

**Architecture: Stripe Account Links (NOT legacy OAuth)**

No `STRIPE_CONNECT_CLIENT_ID` needed. No callback endpoint needed. The flow is:
1. Backend creates a Stripe account (or uses existing connected `acct_XXX`) via `stripe.accounts.create()`
2. Backend generates an Account Link via `stripe.account_links.create()` → returns a Stripe-hosted URL
3. Frontend redirects browser to that URL — Stripe handles existing-account detection vs new-account creation
4. Stripe redirects back to Pilot's `return_url` with `?connected=true`
5. Frontend polls `/status` to confirm connection is live

Three endpoints in the billing/Stripe domain:

| Method | Path | Auth | RBAC | Description |
|---|---|---|---|---|
| `GET` | `/api/v1/settings/billing/stripe-connect/status` | JWT | `settings.tenant.write` | Returns connection status + account name |
| `POST` | `/api/v1/settings/billing/stripe-connect/onboard` | JWT | `settings.tenant.write` (owner only) | Creates/retrieves Stripe connected account, generates Account Link URL, returns URL for frontend redirect |
| `DELETE` | `/api/v1/settings/billing/stripe-connect` | JWT | `settings.tenant.write` (owner only) | Nulls `stripe_connect_account_id` on tenant |

### `GET /status` response:
```python
class StripeConnectStatusResponse(BaseModel):
    connected: bool
    account_id: str | None = None       # Stripe account ID (e.g., acct_xxx) — shown masked in UI
    account_name: str | None = None     # Display name retrieved from stripe.accounts.retrieve()
    charges_enabled: bool = False       # True once contractor completes Stripe onboarding
    payouts_enabled: bool = False       # True once bank account is added
```

### `POST /onboard` request/response:
```python
# No request body needed — tenant is identified from JWT

class StripeConnectOnboardResponse(BaseModel):
    account_link_url: str    # Stripe-hosted onboarding URL — frontend redirects browser here
    expires_at: int          # Unix timestamp — Account Links expire after ~10 minutes
```

**Backend logic for `/onboard`**:
```python
# 1. If tenant already has stripe_connect_account_id → use it (resuming incomplete onboarding)
# 2. If not → create a new connected account:
account = stripe.Account.create(
    type="standard",   # Contractor uses their own Stripe account (full control)
    country="US",
)
# Save account.id → tenant.stripe_connect_account_id

# 3. Generate Account Link (expires in ~10 min — OK, user clicks immediately):
link = stripe.AccountLink.create(
    account=account.id,
    refresh_url="https://app.pilotfortrades.com/settings/billing/payment-method?retry=true",
    return_url="https://app.pilotfortrades.com/settings/billing/payment-method?connected=true",
    type="account_onboarding",
)
return {"account_link_url": link.url, "expires_at": link.expires_at}
```

### `DELETE /disconnect` response:
```python
class StripeConnectDisconnectResponse(BaseModel):
    disconnected: bool = True
    message: str = "Stripe account disconnected. Customers will see manual payment instructions."
```

---

## E. Pattern Reuse Decisions

- **`set_audit_context_sync()`** required on the DELETE disconnect endpoint and the POST onboard endpoint
- **RFC 7807 error format** on all new endpoints
- **`require_permission("settings.tenant.write")`** RBAC on all authenticated endpoints
- **Stripe Account Links** — NO `STRIPE_CONNECT_CLIENT_ID` needed. Uses `stripe.Account.create()` + `stripe.AccountLink.create()`. The only new env variable is `STRIPE_CONNECT_PLATFORM_KEY` (the sandbox `STRIPE_SECRET_KEY` for `acct_XXXXXXXXXXXX`) for testing; production uses the existing live `STRIPE_SECRET_KEY`
- **`create_payment_intent()` update**: Add guard — `if not tenant.stripe_connect_account_id: raise PaymentNotConfiguredError(...)` before any payment intent creation; also check `charges_enabled` via `stripe.Account.retrieve()` if needed

---

## F. Shared Module Interfaces

### `stripe_payment_intents.py` update (implementation reference):

```python
# BEFORE (broken — uses Pilot platform key):
stripe_key = getattr(cfg, "STRIPE_SECRET_KEY", None)
stripe.api_key = stripe_key
pi = stripe.PaymentIntent.create(amount=amount_cents, ...)

# AFTER (correct — uses tenant's connected account):
if not tenant.stripe_connect_account_id:
    raise PaymentNotConfiguredError(
        "This tenant has not connected a Stripe account. "
        "Visit Payment Method settings to connect Stripe."
    )
stripe.api_key = getattr(cfg, "STRIPE_SECRET_KEY", None)  # Pilot's key for API auth
pi = stripe.PaymentIntent.create(
    amount=amount_cents,
    currency="usd",
    stripe_account=tenant.stripe_connect_account_id,  # route to tenant's account
    ...
)
```

### New frontend hooks (implementation reference):

| Hook | Endpoint | Purpose |
|---|---|---|
| `useStripeConnectStatus()` | `GET /stripe-connect/status` | Fetch connection status on page load; re-fetch after returning from Stripe |
| `useStripeConnectOnboard()` | `POST /stripe-connect/onboard` | Mutation — calls backend, gets Account Link URL, redirects browser to Stripe |
| `useStripeConnectDisconnect()` | `DELETE /stripe-connect` | Mutation to disconnect Stripe |

**Frontend connect flow** (no backend callback needed):
```tsx
// User clicks "Connect Stripe Account"
const { mutate: onboard } = useStripeConnectOnboard();
onboard(undefined, {
  onSuccess: (data) => {
    // Redirect browser to Stripe's hosted onboarding page
    window.location.href = data.account_link_url;
    // Stripe will redirect back to: /settings/billing/payment-method?connected=true
  }
});

// On page load, check for ?connected=true or ?retry=true in URL
// If ?connected=true → show success banner, refetch status
// If ?retry=true → show "Resume Setup" button (previous session abandoned)
```

### New route:
- `apps/web/src/app/(authed)/settings/billing/payment-method/page.tsx` (new)
- Renders `<PaymentMethodSettingsPage />`

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Where does `stripe_connect_account_id` live? | `tenant` table, TEXT nullable column |
| What Stripe credentials are needed? | **No new production credentials needed** — existing `STRIPE_SECRET_KEY` is reused. For sandbox testing only: add `STRIPE_SECRET_KEY` for `acct_XXXXXXXXXXXX` (the Connect platform sandbox account). No `STRIPE_CONNECT_CLIENT_ID` required with Account Links approach. |
| Is there a `ca_` client ID needed? | **No** — `ca_` client IDs are only needed for the old Stripe OAuth 2.0 redirect approach. Account Links are entirely server-side. |
| What if a contractor already has a Stripe account? | Stripe handles this automatically. The Account Link shows them a "connect your existing account" flow rather than a sign-up flow. Pilot's code is identical either way. |
| What if a contractor already started onboarding but didn't finish? | `stripe_connect_account_id` is stored when `POST /onboard` runs (before the redirect). If they abandon, their incomplete `acct_XXX` is already stored. Returning to the page calls `/status` → `charges_enabled=false` → show "Resume Setup" button that generates a new Account Link for the same `acct_XXX`. |
| What happens when `stripe_connect_account_id` is NULL and a customer tries to pay? | `create_payment_intent()` raises `PaymentNotConfiguredError` — public invoice page renders manual payment instructions (phone, email, "pay by check/Zelle"). |
| Is there a callback endpoint? | **No** — Account Links use a `return_url` parameter (a frontend URL, not a backend endpoint). After Stripe redirects to `return_url?connected=true`, the frontend shows a success banner and calls `GET /status` to confirm `charges_enabled`. |
| How does Pilot know the onboarding is complete? | After the contractor returns from Stripe, the frontend calls `GET /status` → backend calls `stripe.Account.retrieve(account_id)` → checks `charges_enabled` and `payouts_enabled`. |
| Tom's Stripe setup — confirmed? | ✅ Platform = `acct_XXXXXXXXXXXX` (HotRMC sandbox Connect platform, already configured). Test connected account = `acct_XXXXXXXXXXXX` (can be inserted directly into `tenant.stripe_connect_account_id` for dev testing without going through the full onboarding flow). |
