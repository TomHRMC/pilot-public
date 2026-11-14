# Security and Tenant Isolation — how a request is trusted

*How the API decides who is calling, which tenant they belong to, and what they may touch. Drawn from `backend/core/` and `backend/api/routes/`. Solid = built. Dashed orange = enterprise path (designed for, not built). See the [diagram index](README.md) for the legend and sources.*

## 1. One authenticated write, end to end

A technician updating a quote from the mobile app. Every step below is code that runs on every authenticated write.

```mermaid
sequenceDiagram
  autonumber
  participant C as Web / mobile app
  participant MW as API middleware<br/>request ID · idempotency
  participant A as Auth dependency<br/>get_current_user
  participant R as Route handler
  participant PG as PostgreSQL

  C->>MW: HTTPS PATCH /api/v1/quotes/{id}<br/>Bearer JWT (Cognito) · Idempotency-Key
  MW->>PG: look up Idempotency-Key
  alt key already succeeded with the same body
    MW-->>C: cached response · X-Idempotency-Replay: true
  else same key, different body
    MW-->>C: 409 Conflict
  end
  MW->>A: continue (key locked: in progress)
  A->>A: verify RS256 signature + expiry<br/>against Cognito JWKS (cached 1 h)
  A->>PG: active user → active tenant membership → active role
  Note over A,PG: no membership or no role → 403 (fails closed)
  A->>R: AuthenticatedUser {tenant_id, role, permissions}
  R->>R: require_permission("quotes.update")<br/>(RBAC — denied → 403 with hint)
  R->>PG: SET LOCAL app.user_id (audit context)
  R->>PG: SELECT … WHERE id = :id AND tenant_id = :tenant_id
  Note over R,PG: ADR-0005 — db.get() banned on tenant tables.<br/>Another tenant's row → 404, never 403 (no enumeration)
  R->>PG: UPDATE quote
  Note over PG: audit.log_changes() trigger writes<br/>old values · new values · user · tenant
  R-->>MW: 200
  MW->>PG: cache response against the key (24 h)
  MW-->>C: 200
```

## 2. Every way in, and what guards it

The API has five kinds of caller. Each gets its own check before it reaches tenant data.

```mermaid
flowchart LR
  subgraph callers["Callers"]
    direction TB
    users(["Owners, office staff,<br/>technicians"])
    ops(["Pilot platform operator"])
    cust(["Contractor's customer"])
    hooks(["Stripe · QuickBooks · Telnyx"])
    anon(["Anonymous visitor"])
  end

  subgraph gates["Check at the door"]
    direction TB
    jwt["<b>Cognito JWT</b><br/>RS256 signature + expiry<br/>MFA: TOTP or SMS"]
    imp["<b>Platform role</b><br/>must hold impersonate_tenant<br/>target tenant must be active"]
    link["<b>Signed link token</b><br/>HMAC-SHA256 · expiry<br/>revocation checked (410)"]
    sig["<b>Webhook signature</b><br/>Stripe · QuickBooks HMAC<br/>Telnyx Ed25519"]
    bot["<b>Bot and abuse checks</b><br/>Cloudflare Turnstile · honeypot<br/>per-IP rate limits on some routes"]
  end

  subgraph scope["Scoped to one tenant"]
    direction TB
    rbac["<b>Membership + role → permissions</b><br/>owner · office staff · technician<br/>require_permission() on routes"]
    asowner["<b>Acts as that tenant's owner</b><br/>real owner permissions,<br/>never super-permissions"]
    one["<b>One quote or invoice</b><br/>view · accept · decline"]
    evt["<b>Event for one tenant</b><br/>payment · sync change · inbound SMS"]
    pub["<b>Public endpoints only</b><br/>waitlist · microsites · invites"]
  end

  q["<b>Tenant-scoped queries</b><br/>tenant-scoped fetches filter tenant_id<br/>27 cross-tenant isolation tests"]
  pg[("<b>PostgreSQL</b><br/>tenant_id on tenant tables<br/>audit trigger on writes")]
  audit["<b>audit.event</b><br/>row changes with user + tenant<br/>every impersonated write<br/>tagged actor: platform"]

  users --> jwt --> rbac --> q
  ops --> imp --> asowner --> q
  cust --> link --> one --> q
  hooks --> sig --> evt --> q
  anon --> bot --> pub
  q --> pg --> audit

  aud["Strict token claim checks<br/>iss · aud · token_use"]:::path
  sso["Enterprise SSO<br/>SAML / OIDC federation"]:::path
  quota["Per-tenant API quotas by plan<br/><i>limiter keyed by tenant<br/>already in core/rate_limit.py</i>"]:::path
  rls["Postgres row-level security<br/><i>second wall under the<br/>tenant-scoped queries</i>"]:::path
  idem["Idempotency replay<br/>scoped to the caller's tenant"]:::path

  jwt -.-> aud
  jwt -.-> sso
  rbac -.-> quota
  pg -.-> rls
  q -.-> idem

  classDef path stroke:#c77700,stroke-width:2px,stroke-dasharray:6 4;
  linkStyle 16,17,18,19,20 stroke:#c77700,stroke-width:2px;
```

## What this shows

- **Isolation is enforced in the query, not after it.** [ADR-0005](../pilot-adr-log.md) bans `db.get()` on any tenant-owned table. Every tenant-scoped fetch filters on `tenant_id` in SQL (a few route groups miss the caller check — Known Limitations #27), and a miss returns 404 so one tenant can't learn that another's record exists. A dedicated suite (`backend/tests/test_multi_tenancy_isolation.py`, 27 tests) tries cross-tenant reads and writes across customers, sites, jobs, quotes, catalog and voice sessions.
- **Fails closed.** A valid token is not enough. The caller must have an active user record, an active tenant membership and an active role, or the request stops with 403.
- **Every write is attributable.** The route sets `app.user_id` for the transaction, and a database trigger (`audit.log_changes()`) records old and new values, the user and the tenant. Operator impersonation gets its own audit event on every mutating request.
- **Retries are safe.** The mobile app is designed to queue work offline for up to 72 hours (the sync layer was ~70% integrated at hibernation), so duplicate submissions on reconnect are expected. Writes carry an `Idempotency-Key`, and a replay returns the original response instead of creating a second record ([ADR-0006](../pilot-adr-log.md)).
- **No unsigned callers.** Customer-facing links are HMAC-signed with an expiry and can be revoked. Webhooks are rejected without a valid provider signature.

## Enterprise path shown here

| Upgrade | Why it's next | Starting point already in place |
|---|---|---|
| Postgres row-level security | A second, database-enforced wall under the application's tenant filter | `tenant_id` already on tenant tables; queries already filter on it; isolation test suite to prove it |
| Enterprise SSO (SAML / OIDC) | Customers sign in with their own identity provider | `sso_provider` and `user_sso_identity` tables in the schema; Cognito supports federation |
| Strict token claim checks (`iss`, `aud`, `token_use`) | Accept only tokens issued to Pilot's own app clients | Signature, expiry and key rotation (JWKS cache with TTL) already verified |
| Per-tenant API quotas by plan | Fair use across tenants; plan-based limits | Limiter keyed by tenant with per-tier limits defined (`core/rate_limit.py`); applied today to public, abuse-prone endpoints |
| Tenant-scoped idempotency replay | Bind a cached replay to the tenant that created it | Keys already store `tenant_id` and `user_id` |

## Sources

`backend/core/auth.py` · `backend/core/permissions.py` · `backend/core/idempotency.py` · `backend/core/rate_limit.py` · `backend/core/db.py` · `backend/app/main.py` · `backend/services/public_link_signer.py` · `backend/api/routes/webhooks.py`, `webhooks_stripe.py`, `webhooks_sms.py`, `marketing.py` · `backend/migrations/versions/` (audit trigger) · `backend/tests/test_multi_tenancy_isolation.py` · [ADR log](../pilot-adr-log.md) · [Known Limitations](../../diligence/Pilot-Known-Limitations.md)
