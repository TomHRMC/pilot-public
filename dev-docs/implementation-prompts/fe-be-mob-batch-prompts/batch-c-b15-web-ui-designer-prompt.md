# UI Design Spec Prompt: C-B15 — Platform Shell + Tenant Impersonation

**Mode**: Pilot Web UI Designer
**Batch**: C-B15 (Part B prerequisite — UI design spec)
**Design doc**: `batch-c-b15-design.md` §H (Surface Mockup Reference), §I (Component Manifest)
**Output**: `dev-docs/architecture-design/batch-designs/batch-c-b15-ui-design-spec.md`
**Platform**: Web only (`apps/web`)
**Tom gate**: The React Engineer prompt for C-B15 Part B will NOT be authored until this spec is Tom-approved. STOP after producing the spec — implementation begins only on Tom's approval.

---

## Task

Author a UI design spec for the **Platform Shell + Tenant Impersonation** — the operator-only navigation shell that wraps `/operator/*` pages, a tenant selector, an impersonation confirm modal, and the impersonation banner shown while an operator is viewing the app as a tenant.

### Context

C-B11 shipped the first operator page (`/operator/cohort`) as a standalone route with its own minimal layout (Path A, Tom decision 2026-08-06). C-B15 builds the full platform shell around it and adds tenant impersonation: an operator picks any tenant from a selector, confirms, and is dropped into the normal tenant app (`/dashboard`) as that tenant's owner — with a persistent banner ("Viewing as: Acme Electric — Exit") until they exit.

This is a **platform-level operator tool** (not tenant-scoped). The shell is visually distinct from the tenant shell so an operator always knows which context they are in.

### Surfaces to spec

1. **Operator layout shell** (`/operator/*` route group layout) — sidebar (nav: "Cohort Dashboard" active; a disabled/placeholder group for future operator tools) + header. The header carries the tenant selector. Platform-user guard behavior: non-platform users are redirected to `/dashboard` (note the loading/redirect state in the spec).
2. **Tenant selector** — dropdown in the operator header. Source: `GET /api/v1/operator/tenants`. Searchable/filterable list showing tenant name, tier, subscription status. Include empty, loading, and error states.
3. **Impersonation confirm modal** (§16.7 always-preview-before-send) — triggered by selecting a tenant. Copy direction: "You are about to view Pilot as **{tenant name}** (owner). All changes you make are real and audit-logged." Buttons: Cancel (default, safe) / "View as {tenant name}" (primary). On confirm → full page navigation to `/dashboard` (deliberate full reload — not an in-place state swap).
4. **Impersonation banner** — fixed banner rendered at the top of BOTH shells (operator layout AND the tenant `(authed)` layout) whenever an impersonation session is active. Text: "Viewing as: {tenant name}" + an "Exit" action (≥24×24px target). Exit → full page navigation to `/operator/cohort`. The banner must be **color-independent** (icon + text, never color alone) and must not overlap or displace the existing `(authed)` header/sidebar in a way that breaks layout at 1280px and 1440px viewports.

### API endpoints

- `GET /api/v1/operator/tenants` → `OperatorTenantListResponse` (C-B15 Part A; if not yet in `openapi_schema_map.md` at authoring time, spec against the design doc §D.1 contract)
- `POST /api/v1/operator/impersonation/start` → `ImpersonationSessionResponse` (design §D.2)
- `POST /api/v1/operator/impersonation/end` → `{ "ended": true }` (design §D.3)

### Design constraints

- **Token-only**: `pilotPreset` design tokens — zero hex codes
- **WCAG 2.2 AA**: color-independent status, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallbacks. Include the **Accessibility Notes** subsection.
- **Locked §16 patterns — compose, never invent**: always-preview-before-send (confirm modal) and optimistic UI (client-side selector filtering) are implemented in `packages/ui/`. Impersonation start/exit is a deliberate **full reload** — do not spec an optimistic or in-place context swap (design §G Q2/Q3).
- **Component-existence check**: confirm against `frontend/packages/ui/src/index.ts` that no existing component already covers the banner/modal/sidebar primitives before proposing new ones. Your manifest must reconcile with the Architect's Component Manifest (design §I) — no orphan components.
- **Existing shells as reference**: the tenant shell is `apps/web/src/app/(authed)/layout.tsx` with `AppSidebar`; the C-B11 standalone operator page is `apps/web/src/app/operator/cohort/page.tsx`. The operator sidebar should mirror `AppSidebar` collapse conventions so the two shells feel like one product.

### §16 pattern consumption

| Pattern | Where |
|---|---|
| §16.7 always-preview-before-send | Impersonation confirm modal |
| §16.6 optimistic UI | Selector client-side filtering only |
| Four-class severity | Tenant subscription-status pill in the selector list |

### Component manifest (from design doc §I — must reconcile)

| Component | Destination | New/Reuse |
|---|---|---|
| `OperatorLayout` | `apps/web/src/app/operator/layout.tsx` | New |
| `OperatorSidebar` | `apps/web/src/components/operator/OperatorSidebar.tsx` | New |
| `TenantSelector` | `apps/web/src/components/operator/TenantSelector.tsx` | New |
| `ImpersonationConfirmModal` | `apps/web/src/components/operator/ImpersonationConfirmModal.tsx` | New (compose existing modal primitive) |
| `ImpersonationBanner` | `apps/web/src/components/operator/ImpersonationBanner.tsx` | New |

### Read before designing

- `batch-c-b15-design.md` — full design doc (§D API contracts, §G resolved questions, §H surfaces, §I manifest)
- `mvp-arch.md` §16 — locked platform patterns
- `.roo/rules-pilot-web-ui-designer/` — your operating rules (tokens, WCAG 2.2 AA, design-spec output format)
- `frontend/packages/ui/src/index.ts` — component-existence check
- `batch-c-b11-ui-design-spec.md` — sibling operator-surface spec for conventions

### Output format

Write the spec to `dev-docs/architecture-design/batch-designs/batch-c-b15-ui-design-spec.md` following your standard output format. Include: per-surface mockup descriptions, token references, the Accessibility Notes subsection, states (loading/empty/error) for the selector, the component manifest reconciled against design §I, and a note on how the banner coexists with both shells.

**STOP after producing the spec. Tom reviews and approves before any implementation begins.**
