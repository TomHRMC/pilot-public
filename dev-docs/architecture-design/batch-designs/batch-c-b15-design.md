# C-B15 — Platform Shell + Tenant Impersonation

**Batch**: C-B15
**Mode**: Pilot Python Engineer (Part A) → Pilot Web UI Designer → Pilot React Engineer (Part B)
**Prerequisite**: C-B11 ✅ (platform auth `get_platform_user()`, cohort dashboard, `GET /api/v1/operator/auth/me`)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §8 (Operator Tooling); launch plan row 14v
**Status**: Complete
**Date**: August 8, 2026

> **Scope decision (Tom, 2026-08-06)**: C-B11 shipped Path A (standalone `/operator/cohort` page, no shell). C-B15 adds the full platform shell + tenant impersonation: operator navigation shell, tenant selector, `X-Impersonate-Tenant` header injection by `apiClient`, impersonation banner, and the `get_current_user()` impersonation path (platform user with `impersonate_tenant` permission → `AuthenticatedUser` with the selected tenant context).

---

## Overview

C-B15 gives Pilot operators (Tom, initially) the ability to (a) navigate a dedicated operator area with room to grow beyond the cohort dashboard, and (b) **impersonate any tenant** to see the app exactly as that tenant's owner sees it — for support, onboarding assistance, and Charter cohort management.

This is a **mixed batch**:

- **Part A (Python Engineer)** — impersonation path in `get_current_user()`, 3 new operator endpoints (tenant list, impersonation start/end), audit logging of impersonation sessions and impersonated mutations, OpenAPI regen.
- **Part B (React Engineer)** — operator layout shell (sidebar + header), tenant selector dropdown, impersonation context + `apiClient` header injection, impersonation banner in both the operator shell and the `(authed)` tenant shell. **Requires a Tom-approved UI design spec from `pilot-web-ui-designer` before the prompt is issued** (Architect Rule §1.5).

### Key Design Decision: Impersonation rides the existing tenant auth path

The impersonated session reuses `get_current_user()` (`core/auth.py`) rather than adding a parallel dependency. When the JWT belongs to a platform user (no `tenant_user` row) AND the request carries an `X-Impersonate-Tenant: <uuid>` header AND the user's `platform_role.permissions.impersonate_tenant == true`, the dependency builds an `AuthenticatedUser` for the **target tenant** with the tenant `owner` role's permission set. Every existing tenant-scoped endpoint, RBAC decorator, audit trigger, and tenant-isolation rule then works unchanged — the impersonator *is* a tenant owner for the duration of the session, and every state-changing request is audit-logged with the impersonator's identity.

This is the lowest-risk design: no endpoint changes, no new RBAC vocabulary, no tenant-context leaks (the `tenant_id` used everywhere is the impersonated tenant's, never the platform user's — platform users have no tenant).

---

## A. Input Read Summary

| Input | Source | Key findings |
|---|---|---|
| Launch plan row 14v (C-B15) | `pilot-launch-plan.md` | Full scope: login flow (done in C-B11), operator nav shell, tenant selector, `X-Impersonate-Tenant` header injection, banner, `get_current_user()` impersonation path. Dependency C-B11 ✅. |
| Spec §8 — Operator Tooling | `pilot-tech-impl-spec-v1.md` §8 | "Hidden Pilot operator routes, RBAC-gated to the operator role, audit-logged." Impersonation audit logging is a spec-level requirement. |
| C-B11 design + shipped code | `batch-c-b11-design.md`; `backend/core/auth.py` | `PlatformUser` model + `get_platform_user()` at lines 295–403. Cohort router at `backend/api/routes/cohort_dashboard.py` with prefix `/api/v1/operator`. `GET /operator/auth/me` returns `user_type` + `redirect_to`. |
| Live DB — `platform_role` | MCP (this session) | 3 active rows. `owner` + `support` have `impersonate_tenant: true`; `accountant` has `false`. Permission JSON keys: `read_all`, `write[]`, `impersonate_tenant`, `manage_jwks`. |
| Live DB — `audit.event` | MCP (this session) | Columns: `tenant_id` (nullable), `user_id`, `actor_type` CHECK (`system`/`user`/`platform`/`external_webhook`), `user_role`, `entity_name`, `entity_id`, `action`, `old_values`/`new_values` jsonb, `contextdata` jsonb, `occurred_at`. Impersonation rows use `actor_type='platform'`, `entity_name='impersonation'`, `entity_id=<tenant uuid>`. No migration needed. |
| Existing code — `get_current_user()` | `core/auth.py` | Raises 403 at line 245 when no `tenant_user` row. The impersonation branch hooks in exactly there: platform user + header → build tenant context instead of raising. |
| Existing code — `AuthenticatedUser` | `core/auth.py` | Fields: `user`, `tenant_id`, `role_code`, `permissions`. C-B15 adds optional `impersonator_user_id: uuid \| None = None` (default keeps all existing constructors valid). |
| Existing code — `apiClient` | `frontend/packages/shared-api/src/client.ts` | Axios instance with JWT request interceptor (lines 38–67). C-B15 adds `X-Impersonate-Tenant` injection in the same interceptor, reading from a new module-level impersonation store. |
| Existing code — `AuthProvider` | `frontend/packages/ui/src/auth/AuthProvider.tsx` | `fetchUserFromBackend()` calls `GET /api/v1/users/me/permissions` via raw `fetch()` (pre-dates the apiClient mandate). That endpoint uses `get_current_user()` — so it inherits the impersonation path automatically once the header is attached. C-B15 adds the header to this fetch + triggers a full reload on impersonation start/exit so the provider re-runs. |
| Existing code — `/users/me/permissions` | `backend/api/routes/roles.py` | Uses `get_current_user()`. No route change needed. |
| CORS | `backend/app/main.py` | `allow_headers=["*"]` — `X-Impersonate-Tenant` passes with no CORS change. |
| Operator route group (web) | `frontend/apps/web/src/app/operator/` | Only `cohort/page.tsx`; **no `layout.tsx` yet**. C-B15 adds the operator layout shell here. |
| Tenant shell | `frontend/apps/web/src/app/(authed)/layout.tsx` | Header + `AppSidebar` + collapsible state. Impersonation banner mounts here (above header) when impersonation is active. |
| ADR log | `pilot-adr-log.md` | ADR-0005 (tenant-scoped select, `db.get()` banned), ADR-0007 (OpenAPI contract), ADR-0010 (RBAC vocabulary) all apply. No existing ADR governs impersonation — see §G Q4 (ADR candidate noted, not required). |
| mvp-arch §16 | `mvp-arch.md` §16 | No new top-level UX patterns; shell composes existing sidebar/banner conventions. Optimistic UI (§16.6) applies to selector interaction; impersonation start/exit is a deliberate full reload (not optimistic) for auth-context correctness. |

---

## B. Migration Plan

### B.1 — DB Changes

**No migration needed.** No new tables, no new columns:

- Impersonation permission already exists: `platform_role.permissions.impersonate_tenant` (JSON key, live-verified).
- Audit trail reuses `audit.event` (append-only ledger; `actor_type='platform'` is already an allowed CHECK value).
- Tenant list reuses `tenant` + `subscription_tier` + `subscription` + `subscription_status`.

### B.2 — MCP Verification Queries (pre-implementation)

```sql
-- 1. Impersonation permission flags
SELECT code, permissions -> 'impersonate_tenant' AS can_impersonate, is_active
FROM public.platform_role ORDER BY code;

-- 2. tenant columns needed by the selector endpoint
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('id', 'name', 'is_active', 'current_subscription_tier_id', 'created_at')
ORDER BY ordinal_position;

-- 3. audit.event actor_type CHECK allows 'platform'
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'audit_event_actor_type_chk';

-- 4. subscription + status join columns for tenant list
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('tenant_id', 'status_id', 'is_active')
ORDER BY ordinal_position;

-- 5. tenant_user_role owner permission payload shape
SELECT code, permissions FROM public.tenant_user_role WHERE code = 'owner';
```

### B.3 — Pre-Implementation State

- `get_current_user()` 403s for all platform users (no impersonation path).
- `platform_role`: owner/support `impersonate_tenant=true`, accountant `false`.
- No `X-Impersonate-Tenant` handling anywhere (verified by grep — zero matches in backend).
- Web `operator/` route group has no layout.

### B.4 — 3-Part NOT NULL Pattern

Not applicable — no new columns.

### B.5 — Audit Columns

Not applicable — no new table.

### B.6 — Seed Data Rollout

Not applicable — no new lookup rows or seed data. `platform_role` rows already carry `impersonate_tenant`. (Rule §11.5 verified: this batch adds/modifies **no** DB data.)

---

## C. Execution Order

### Part A — Backend (Python Engineer)

| # | Task | Files | Description |
|---|---|---|---|
| 1 | Impersonation path in `get_current_user()` | `backend/core/auth.py` | At the no-`tenant_user` branch (line ~245): if user is platform user, `X-Impersonate-Tenant` header present, and `impersonate_tenant` permission true → load target tenant (must exist, `is_active=true`), load `tenant_user_role` `owner` permissions, return `AuthenticatedUser(tenant_id=target, role_code='owner', impersonator_user_id=platform_user.id)`. Otherwise keep the existing 403. Sets `request.state.impersonator_user_id`. |
| 2 | `AuthenticatedUser.impersonator_user_id` | `backend/core/auth.py` | New optional field `impersonator_user_id: uuid.UUID \| None = None` + `is_impersonated` computed property. |
| 3 | Impersonation audit helper | `backend/services/impersonation_service.py` (NEW) | `log_impersonation_event(db, *, tenant_id, impersonator_user_id, action, context=None)` — inserts `audit.event` row (`actor_type='platform'`, `entity_name='impersonation'`, `entity_id=str(tenant_id)`, `action` in `start`/`end`/`request`, `contextdata` JSON). Also `list_operator_tenants(db)` aggregation for the selector. |
| 4 | Operator endpoints | `backend/api/routes/operator_tenants.py` (NEW) | 3 endpoints (see §D). Router prefix `/api/v1/operator`, all `get_platform_user()`. Start/end call the audit helper. |
| 5 | Impersonated-mutation audit middleware | `backend/app/main.py` | Lightweight pure-ASGI/HTTP middleware registered after auth: if `request.state.impersonator_user_id` is set AND method not in `{GET, HEAD, OPTIONS}` → write one `audit.event` row (`action='request'`, `contextdata={method, path}`). Failure to write must not break the request (log + continue). |
| 6 | Router registration | `backend/app/main.py` | Register `operator_tenants` router. |
| 7 | Schemas | `backend/api/schemas/operator.py` (NEW) | `OperatorTenantSummary`, `OperatorTenantListResponse`, `ImpersonationStartRequest`, `ImpersonationSessionResponse`. |
| 8 | OpenAPI regen | — | `python export_openapi_json.py` — 3 new endpoints. |
| 9 | Tests | `backend/tests/domains/platform_infrastructure/test_cb15_impersonation.py` (NEW) | Unit + endpoint tests (see Part A test matrix in the prompt). |

### Part B — Frontend (React Engineer, web only)

| # | Task | Files | Description |
|---|---|---|---|
| 1 | Impersonation store + header injection | `frontend/packages/shared-api/src/impersonation.ts` (NEW), `client.ts` | Module-level store persisted to `sessionStorage` (`pilot.impersonation` = `{tenantId, tenantName}`). `apiClient` request interceptor adds `X-Impersonate-Tenant` when set. Exports `getImpersonation/setImpersonation/clearImpersonation` + `useImpersonation()` React hook (sync via `storage`/custom event). |
| 2 | Operator layout shell | `apps/web/src/app/operator/layout.tsx` (NEW) | Client layout: platform-user guard (`useAuthMe` → `user_type==='platform'` else redirect `/dashboard`), `OperatorSidebar` + header with `TenantSelector`. Cohort page inherits it automatically. |
| 3 | Operator sidebar | `apps/web/src/components/operator/OperatorSidebar.tsx` (NEW) | Nav: Cohort Dashboard (active), disabled "More operator tools coming" group for future pages. Mirrors `AppSidebar` collapse conventions. |
| 4 | Tenant selector | `apps/web/src/components/operator/TenantSelector.tsx` (NEW) | Searchable dropdown (existing `packages/ui` primitives), source `useOperatorTenants()`. Selecting a tenant → confirm modal (§16.7 always-preview) → `useImpersonationStart` → `setImpersonation()` → `window.location.assign('/dashboard')`. |
| 5 | Impersonation banner | `apps/web/src/components/operator/ImpersonationBanner.tsx` (NEW) | Fixed banner: "Viewing as: {tenantName} — Exit". Mounted in `operator/layout.tsx` AND `(authed)/layout.tsx` when `useImpersonation()` is non-null. Exit → `useImpersonationEnd` → `clearImpersonation()` → `window.location.assign('/operator/cohort')`. |
| 6 | AuthProvider header | `packages/ui/src/auth/AuthProvider.tsx` | `fetchUserFromBackend()` attaches `X-Impersonate-Tenant` from the store when present. Full reload on start/exit re-runs the provider; no incremental state patching. |
| 7 | Hooks | `apps/web/src/features/operator/hooks/` | `useOperatorTenants.ts`, `useImpersonationStart.ts`, `useImpersonationEnd.ts` — TanStack Query, `retry: false`, apiClient only. |
| 8 | MSW handlers | `apps/web/src/mocks/handlers/operatorTenantsHandlers.ts` (NEW) + `index.ts` barrel | Handlers for the 3 new endpoints. Register in barrel. |
| 9 | Tests | Component + integration tests under `apps/web/src/__tests__/batch_c_b15/` | Selector flow, banner render/exit, header injection, platform guard redirect. |

---

## D. New API Endpoints

### D.1 — `GET /api/v1/operator/tenants`

**Auth**: `get_platform_user()` · **Permission**: `permissions.read_all == true`
**Purpose**: Tenant selector source. All tenants (not just Charter), active first, alphabetical.

**Response**: `OperatorTenantListResponse`

```json
{
  "tenants": [
    {
      "tenant_id": "uuid",
      "name": "Acme Electric",
      "is_active": true,
      "tier_name": "Charter",
      "subscription_status": "trialing",
      "created_at": "2026-08-01T00:00:00Z"
    }
  ]
}
```

`tier_name`/`subscription_status` are nullable (tenant may have no subscription row). No pagination at MVP scale (< 200 tenants); add `limit/offset` only when the selector measurably slows.

### D.2 — `POST /api/v1/operator/impersonation/start`

**Auth**: `get_platform_user()` · **Permission**: `permissions.impersonate_tenant == true`
**Request**: `ImpersonationStartRequest` — `{ "tenant_id": "uuid" }`
**Behavior**: validates tenant exists + `is_active=true`; writes `audit.event(action='start')`; returns session summary. Idempotent by nature — starting an already-active session for the same tenant returns 200 with the same payload (no duplicate-semantics risk; the client stores only one active impersonation).

**Response**: `ImpersonationSessionResponse`

```json
{
  "tenant_id": "uuid",
  "tenant_name": "Acme Electric",
  "impersonator_user_id": "uuid",
  "role_code": "owner",
  "started_at": "2026-08-08T16:00:00Z"
}
```

**Errors**: `403` role lacks `impersonate_tenant` (accountant) · `404` tenant not found · `409` tenant inactive/suspended.

### D.3 — `POST /api/v1/operator/impersonation/end`

**Auth**: `get_platform_user()` · **Permission**: `impersonate_tenant == true`
**Request**: `{ "tenant_id": "uuid" }` (the session being ended — keeps the audit pair symmetric)
**Behavior**: writes `audit.event(action='end')`. Always 200 even if no matching `start` row (defensive — client state may have been cleared). Response: `{ "ended": true }`.

### D.4 — Changed behavior: `get_current_user()` (no new route)

Every existing tenant endpoint now additionally accepts the impersonation path described in §C-A1. Security invariants:

1. Header is **ignored** (not an error) for tenant users — a tenant user sending `X-Impersonate-Tenant` gets their normal context. Only platform users can activate it.
2. Platform user **without** the header still gets the existing 403 (operator endpoints remain `get_platform_user()`-gated).
3. Platform user with header but `impersonate_tenant=false` (accountant) → 403 RFC 7807.
4. Target tenant must be active → `404`/`409` as above.
5. Impersonated context is always `role_code='owner'` with the owner role's permission list from `tenant_user_role` — no synthetic super-permissions.

---

## E. Pattern Reuse Decisions

| Pattern | Source | How it applies |
|---|---|---|
| `get_platform_user()` | C-B11 `core/auth.py` | Auth for all 3 new endpoints; permission checks via `can_read_all()` / `permissions.get('impersonate_tenant')`. |
| `audit.event` append-only ledger | `app/models/system.py` | Impersonation start/end/request rows; `actor_type='platform'` (already allowed by CHECK). Direct ORM insert, not the trigger path (no table row is being mutated by these events). |
| Tenant-scoped `select()` (ADR-0005) | mvp-arch §7 | `list_operator_tenants` is deliberately **cross-tenant** (platform read) — the only sanctioned exception, same class as `cohort_dashboard.get_cohort_overview()`. |
| RFC 7807 errors | Standard | All 403/404/409 responses use Problem Details. |
| §16.7 always-preview-before-send | mvp-arch §16 | Tenant selector confirm modal: "You are about to view Pilot as **Acme Electric** (owner). All changes you make are real and audit-logged." |
| §16.6 optimistic UI | mvp-arch §16 | Selector dropdown filters client-side; start/exit are **not** optimistic (full reload after success only). |
| `retry: false` + MSW barrel | react-engr inclusions | All 3 new hooks. |
| Existing `AuditEvent` archive task | `tasks/archive_audit_logs.py` | Impersonation rows inherit the existing 90-day archive/export pipeline — no new ops surface. |

---

## F. Shared Module Interfaces

### F.1 — `core/auth.py` changes

```python
class AuthenticatedUser(BaseModel):
    user: User
    tenant_id: uuid.UUID
    role_code: str
    permissions: list[str]
    impersonator_user_id: uuid.UUID | None = None  # NEW — set when this context
                                                    # was built via impersonation

    @property
    def is_impersonated(self) -> bool:
        return self.impersonator_user_id is not None
```

`get_current_user()` — new branch replacing the bare 403 at the no-`tenant_user` path:

```python
IMPERSONATE_TENANT_HEADER = "x-impersonate-tenant"

def _try_impersonation(request, db, user) -> AuthenticatedUser | None:
    """Return an impersonated owner context, or None to fall through to 403."""
    tenant_header = request.headers.get(IMPERSONATE_TENANT_HEADER)
    if not tenant_header or not user.is_platform_user or not user.platform_role_code:
        return None
    # ... load platform_role, check impersonate_tenant, parse uuid,
    #     load active tenant, load owner TenantUserRole permissions,
    #     request.state.impersonator_user_id = user.id
    #     return AuthenticatedUser(user=user, tenant_id=tenant.id,
    #         role_code="owner", permissions=owner_permissions,
    #         impersonator_user_id=user.id)
```

### F.2 — `services/impersonation_service.py` (NEW)

```python
def list_operator_tenants(db: Session) -> list[OperatorTenantSummary]: ...
def log_impersonation_event(
    db: Session, *, tenant_id: uuid.UUID, impersonator_user_id: uuid.UUID,
    action: Literal["start", "end", "request"],
    context: dict[str, Any] | None = None,
) -> None: ...
def start_impersonation(db, *, tenant_id, platform_user: PlatformUser) -> ImpersonationSessionResponse: ...
def end_impersonation(db, *, tenant_id, platform_user: PlatformUser) -> dict: ...
```

### F.3 — `packages/shared-api/src/impersonation.ts` (NEW)

```ts
export interface ImpersonationSession { tenantId: string; tenantName: string; }
export function getImpersonation(): ImpersonationSession | null
export function setImpersonation(s: ImpersonationSession): void
export function clearImpersonation(): void
export function useImpersonation(): ImpersonationSession | null  // React hook
```

`client.ts` interceptor addition (after JWT attach): `const imp = getImpersonation(); if (imp) config.headers["X-Impersonate-Tenant"] = imp.tenantId;`

---

## G. Open Questions Resolved

1. **Read-only vs read-write impersonation?** → **Read-write, as tenant owner.** The support use case (fix a tenant's misconfigured setting, walk a Charter member through setup) requires writes. Mitigations: permission gate (`accountant` cannot impersonate), mandatory confirm modal, persistent banner, and audit rows for every mutation. Flagged for Tom confirmation at design approval.
2. **How does the client persist the session?** → `sessionStorage` (tab-scoped, cleared on tab close — a safety feature, not a bug). Full page reload on start/exit re-runs `AuthProvider` so all TanStack caches are rebuilt under the new tenant context — no cross-tenant cache leakage.
3. **Cache leakage between impersonation sessions?** → Solved by full reload (`window.location.assign`), never in-place React state swap. Documented as a hard rule in the React prompt.
4. **New ADR?** → Not logged. Impersonation is operator tooling internal to the auth layer; it reuses ADR-0005's tenant-scoping model (one sanctioned cross-tenant read, same as cohort dashboard) and introduces no new quality-attribute tradeoffs beyond what C-B11's platform auth already established. If Tom later wants read-only impersonation or time-boxed sessions, that change would cross the ADR bar.
5. **SSE while impersonating?** → Out of scope. SSE endpoints use `?token=JWT`; the impersonation header is not part of that flow. Dispatch-board SSE under impersonation will connect as the platform user and fail tenant auth — acceptable (operator views, doesn't monitor live boards). Documented limitation; revisit only if Tom hits it.
6. **Impersonate another platform user or the Pilot dev tenant?** → No special-casing. Any active tenant is impersonable, including the internal dev tenant.
7. **Mobile app?** → No change. The store lives in `shared-api` but mobile never sets it; the header is simply never attached. `AuthProvider` change is a no-op on mobile (no session in storage).

---

## H. Surface Mockup Reference (frontend half)

- **Design spec**: `dev-docs/architecture-design/batch-designs/batch-c-b15-ui-design-spec.md` — to be authored by `pilot-web-ui-designer` and **Tom-approved before the React prompt is issued** (Rule §1.5 handoff gate).
- **Platform scope**: `apps/web` only. No mobile, no marketing.
- **§16 pattern consumption**: §16.6 (optimistic UI — selector filtering), §16.7 (always-preview — impersonation confirm modal). No new top-level UX patterns.
- **Surfaces**: (1) operator shell layout (sidebar + header) for `/operator/*`; (2) tenant selector dropdown in the operator header; (3) impersonation confirm modal; (4) impersonation banner in both shells.
- **Designer constraints to restate in the designer prompt**: token-only (`pilotPreset`, zero hex), WCAG 2.2 AA, component-existence check against `frontend/packages/ui/src/index.ts`, banner must be color-independent (icon + text, not color alone).

## I. Component Manifest (frontend half)

| Component | Destination | New/Reuse |
|---|---|---|
| `impersonation.ts` store + `useImpersonation` | `frontend/packages/shared-api/src/impersonation.ts` | New |
| `OperatorLayout` (route layout) | `apps/web/src/app/operator/layout.tsx` | New |
| `OperatorSidebar` | `apps/web/src/components/operator/OperatorSidebar.tsx` | New |
| `TenantSelector` | `apps/web/src/components/operator/TenantSelector.tsx` | New |
| `ImpersonationConfirmModal` | `apps/web/src/components/operator/ImpersonationConfirmModal.tsx` | New (compose existing `packages/ui` modal primitive — existence check required) |
| `ImpersonationBanner` | `apps/web/src/components/operator/ImpersonationBanner.tsx` | New |
| `useOperatorTenants` / `useImpersonationStart` / `useImpersonationEnd` | `apps/web/src/features/operator/hooks/` | New ×3 |
| `operatorTenantsHandlers` | `apps/web/src/mocks/handlers/operatorTenantsHandlers.ts` + barrel | New |
| `(authed)/layout.tsx` | banner mount only | Modified |
| `AuthProvider.tsx` | header attach only | Modified |
| `client.ts` | header injection only | Modified |

No orphan components permitted — the designer spec's manifest must reconcile with this table (Rule §1.5.4).

---

## Handoff

1. **Tom approves this design** (incl. §G Q1 read-write decision).
2. Architect issues the **web UI designer prompt** → designer authors `batch-c-b15-ui-design-spec.md` → **Tom approves spec**.
3. **Part A**: Python Engineer prompt issued → implements, runs `python export_openapi_json.py`, commits, handoff note.
4. `pnpm sync-api-types` (React Engineer Pre-Work step 1).
5. **Part B**: React Engineer prompt issued (references the approved UI spec).
6. On completion: launch plan row 14v → ✅ with completion summary; this doc's status → Complete.
