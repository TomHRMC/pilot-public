# Batch C-B16 Design — Pilot-Hosted Tenant Sites (SMS Compliance Pages + Compliance Kit)

**Batch code**: C-B16 (launch plan §2.3, Beta Execution Order 4)
**Date**: 2026-08-13
**Author**: Pilot Architect
**Status**: ✅ **APPROVED 2026-08-14** → ✅ **IMPLEMENTED 2026-08-14** (both parts; launch plan Appendix C ×2) (Tom — direction approved 2026-08-13; **amendment 1** (2026-08-14): §G-16/17/18 website-overwrite confirmation + 10DLC brand-registration timing per Tom's failed-registration scenario; **amendment 2** (2026-08-14): §G-19/20 one-time requirements email + always-downloadable Requirements Guide PDF replace the manual kit-email resend model, per Tom — designer specs authorized; **amendment 3** (2026-08-14, infra): `p4tsites.com` registered via **Cloudflare** — supersedes the Route 53 DNS track (§C step 0, §G-1, §G-11, §J updated; ADR-0014))
**Launch plan card**: `pilot-launch-plan.md` §2.3 C-B16 (lines 297–305)
**UI specs**: `mkt-c-b16-design-spec.md` (public templates + PDF layout) + `batch-c-b16-web-ui-design-spec.md` (Settings surface) — both ✅ Tom-approved 2026-08-14
**Engineer prompts (authored 2026-08-14, after both designer specs Tom-approved)**:
1. `batch-c-b16-python-engr-prompt.md` — Part A (backend) — runs **first** ✅ DONE 2026-08-14
2. `batch-c-b16-react-engr-prompt.md` — Part B (web) — after Part A merges + `pnpm sync-api-types` ✅ DONE 2026-08-14

---

## 0. Scope Reconciliation vs. Launch Plan Card (READ FIRST)

The plan card (written 2026-08-08) scopes a single "tenant public compliance page" auto-populating C-B9's `website` field. The **2026-08-13 alignment session with Tom** expanded this into a three-option product model and fixed all four C-SPIKE-2 open questions. This design implements the approved residual scope:

| Item | Alignment decision (Tom, 2026-08-13) | Disposition |
|---|---|---|
| Option 1 — **Compliance Kit** (tenant self-hosts) | Strong requirements warning wherever a self-managed URL is entered; **one-time auto-email** (requirements content + pre-merged Privacy/Terms kit text + guide link) on first self-host signal; **always-downloadable Requirements Guide PDF** (full TCR requirements + worked examples) — no resend/retry management (Tom simplification 2026-08-14, §G-19/20). No hosting. | **This batch (Part A + Part B)** |
| Option 2 — **Hosted Compliance Site** | We host a 3-page site: minimal landing (business identity = About/Contact evidence for TCR) + `/privacy` + `/terms`. *The card's "key pages only" concept was upgraded: a landing page is mandatory — a bare domain with only /privacy and /terms underperforms TCR vetting.* | **This batch (Part A + Part B)** |
| Option 3 — **Hosted Starter Site** | Richer single business site (services, about, hours, logo, contact form) + the compliance pages. Scope intentionally undefined until GTM pricing research completes. | **DEFERRED to C-B17** — `site_kind` CHECK constraint reserves the value (§G-14) |
| Domain choice | **New dedicated domain** (working name `p4tsites.com`, subject to availability; alternates `p4t-pages.com` / `p4t-websites.com`). Brand/security/SEO isolation from `pilotfortrades.com`. Cost **+$1.58/mo** (Route 53 registration ~$13/yr + hosted zone $0.50/mo) — flagged per Rule §4, approved. The 2026-08-08 "short-link domain dropped" note is unaffected (different purpose). | Locked |
| Subdomain vs folder | **Wildcard per-tenant subdomains** — `{slug}.p4tsites.com`. One wildcard ACM cert + one wildcard Route 53 record + one ALB host rule. Zero per-tenant DNS operations. Better TCR optics than folders; keeps future tenant custom domains possible via CNAME. | Locked |
| Generic vs white-labeled | **Tenant-branded** (their business name/content), with a small "Hosted by Pilot for Trades" footer. True white-label / custom domains deferred (C-B17+). | Locked |
| Pricing model ("for a cost") | Charter members: included (gate on `tenant.charter_eligible`). `hosted_compliance` (Option 2): **free on all paid tiers** — it is a 10DLC deliverability enabler; charging creates a vetting-failure incentive. `starter_site` (Option 3): target ~$9.99/mo add-on after GTM research. **No Stripe wiring in C-B16** — entitlement check defaults to allow. Pricing research task added to Tom's to-do doc. | Locked |
| Data/serving model | **Publish → snapshot → SSR serve.** Authenticated publish writes a rendered content snapshot; the public endpoint serves only the snapshot. | Locked |
| Website overwrite + TCR timing (amendment 2026-08-14) | Publishing over a **tenant-entered** `website` requires explicit in-UI confirmation (409 gate + `confirm_website_overwrite` flag). Publish response carries the 10DLC brand registration state so the UI sequences correctly — an in-flight vet checks the OLD URL; `brand_rejected` → re-submit from the C-B9 Messaging UI after publish; live brand → re-vetting warning. **No automatic Telnyx brand update in C-B16.** | Locked (Tom scenario) |

**External clock**: sole-proprietor tenants without a website **will fail** TCR 10DLC brand registration (C-SPIKE-2, verified across Plivo/Hustle/TCR/Twilio sources). Nothing else in Order 4 has a third-party gatekeeper; this batch is the last open Charter follow-on.

---

## A. Input Read Summary

| Input | Sections read | What it contributed |
|---|---|---|
| `pilot-launch-plan.md` | §2.3 C-B16 card (297–305), §2.1 Order 4 (146), §2.1a follow-ons (156) | Card scope, "next in order" position, the four C-SPIKE-2 questions the design must resolve |
| C-SPIKE-2 archive card — `pilot-launch-plan-archive-2026.08.08.md` | Lines 865–919 | TCR requirements verbatim: website URL; About/Contact/ToS/Privacy pages; SMS-specific privacy disclosure (message types, cadence, rate notices, opt-out, no-third-party-sharing); Terms + Privacy URLs under campaign CTA. Competitive finding: no SaaS hosts these for customers |
| `batch-c-b9-design.md` | Input summary (33–35), nullable-fields rationale (61–63, 99–100), open Q#4 + T2 (707–717) | `website` auto-populate contract: application-layer, never overwrite tenant-entered URL |
| `mvp-arch.md` | §16 pattern inventory (3412–3430) | §16.5 system-default/tenant-override (field defaults), §16.7 always-preview-before-send (publish flow) |
| `marketing.py` | Header security model (13–17), limiter usage (175, 242, 366, 517) | The 4-layer public-endpoint lockdown precedent: CORS allowlist + Turnstile + SlowAPI + honeypot/UNIQUE |
| `main.py` | CORS origins (420–459), router registrations (122–415) | Prod CORS = 3 origins only; `/api/v1/sites` already taken by job sites (137) → router naming collision avoided (§G-5); public router precedent (357–376) |
| `mixins.py` | Full file | `StandardAuditMixin` = all four audit columns (9–28) — mirrored in §B DDL per Rule §3 |
| `tenant_10dlc_profile.py` | GET (176–178), PUT (205–207) | RBAC precedent: `settings.view` / `settings.manage` for tenant settings surfaces |
| `public_charter.py`, `public_invoices.py`, `public_quotes.py` | Route surfaces | Public GET precedent (no JWT, read-only); HMAC signed-token pattern evaluated and rejected for sites (§G-6) |
| MCP `postgres-local` (this session) | `tenant_10dlc_profile` (19 cols — `website` text nullable ✅; legal/dba names, support email/phone, HQ address present); `tenant` (17 cols — `charter_eligible`, `charter_member_number` ✅); `tenant_messaging_registration` (20 cols ✅ per plan-card requirement); `pg_trigger` on `tenant_10dlc_profile` (`set_updated_at` convention confirmed); table-existence probe `tenant_site`/`%website%` → **empty (greenfield)** | All DDL below uses only MCP-verified names |
| Web app layout — `frontend/apps/web/src/app/` | Top level + `(authed)/` | `(authed)/settings/` exists (settings surface home); `i/` + `q/` public route precedent; **no `middleware.ts` exists** — Part B creates it (§G-13) |
| `python-engr-std-prompt-inclusions.md` §20 (via Rule 11.5) | Seed Data Rollout template | §B.6 below |
| Rules | `infrastructure-constraints.md` (Fargate-first, cost cap), `scaling-logic.md`, architect rules §1.3/§1.5/§3/§11.1/§11.5/§12, methods §3 | This doc's structure + guardrails |

---

## B. Migration Plan

One Alembic migration: one new table + trigger, plus **one nullable ALTER** (`tenant_10dlc_profile.requirements_emailed_at` — §B.2). `website` already exists (MCP-verified); auto-population is application-layer. **3-part NOT NULL pattern: NOT TRIGGERED** (new table + nullable add only; stated explicitly per workflow §B).

### B.0 Pre-Migration Verification (MCP, 2026-08-13)

- `tenant_10dlc_profile`: 19 columns; `website` is `text NULL`; source fields `legal_business_name`, `dba_name`, `support_email`, `support_phone`, `hq_city`, `hq_state`, `hq_address_line1`, `hq_postal_code` all present.
- `tenant`: 17 columns; `name`, `charter_eligible` (bool NOT NULL), `charter_member_number` (int NULL) present.
- `tenant_messaging_registration`: 20 columns (incl. `status`, `telnyx_brand_id`, `telnyx_campaign_id`) — referenced read-only by future campaign-CTA wiring; **no SQL in this batch touches it**.
- Trigger convention verified: `set_updated_at_<table>` BEFORE UPDATE EXECUTE `set_updated_at()` exists on `tenant_10dlc_profile` — the house trigger for mutable tenant-scoped tables.
- Greenfield probe: no table matching `tenant_site` or `%website%` in `public`/`audit`.

### B.1 New table `public.tenant_site`

```sql
CREATE TABLE public.tenant_site (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES public.tenant (id),
    slug                    VARCHAR(63) NOT NULL,               -- DNS label; validated by ck_tenant_site_slug_format + service-layer reserved list
    site_kind               VARCHAR(20) NOT NULL,               -- 'compliance_kit' | 'hosted_compliance' ('starter_site' reserved for C-B17 — §G-14)
    status                  VARCHAR(20) NOT NULL DEFAULT 'draft', -- 'draft' | 'published' | 'unpublished'
    display_name            VARCHAR(200) NOT NULL,
    tagline                 VARCHAR(300) NULL,
    public_email            VARCHAR(320) NULL,
    public_phone            VARCHAR(32) NULL,
    public_city             VARCHAR(120) NULL,
    public_state            VARCHAR(2) NULL,
    public_address_line1    VARCHAR(200) NULL,                  -- published ONLY when show_full_address = TRUE (§G-10)
    public_postal_code      VARCHAR(10) NULL,
    show_full_address       BOOLEAN NOT NULL DEFAULT FALSE,
    template_version        VARCHAR(20) NOT NULL DEFAULT 'v1',  -- pins code-resident template set (§B.5)
    published_snapshot      JSONB NULL,                         -- fully rendered page content at publish time (§F)
    published_at            TIMESTAMPTZ NULL,
    unpublished_at          TIMESTAMPTZ NULL,
    kit_sent_at             TIMESTAMPTZ NULL,                   -- one-time requirements+kit email send (§G-19); no resends by design
    website_auto_populated  BOOLEAN NOT NULL DEFAULT FALSE,     -- TRUE when we wrote tenant_10dlc_profile.website
    idempotency_key         VARCHAR(100) NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(), -- StandardAuditMixin (all four, per Rule §3)
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              UUID NULL,
    updated_by              UUID NULL,
    CONSTRAINT ck_tenant_site_kind CHECK (site_kind IN ('compliance_kit', 'hosted_compliance')),
    CONSTRAINT ck_tenant_site_status CHECK (status IN ('draft', 'published', 'unpublished')),
    CONSTRAINT ck_tenant_site_slug_format CHECK (slug ~ '^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$')
);

-- 1:1 per tenant for MVP
CREATE UNIQUE INDEX uq_tenant_site_tenant ON public.tenant_site (tenant_id);

-- Slug globally unique across the shared hosting domain
CREATE UNIQUE INDEX uq_tenant_site_slug ON public.tenant_site (slug);

-- Offline/idempotent upsert fallback per §15.4 natural-key convention
CREATE UNIQUE INDEX uq_tenant_site_tenant_idempotency
    ON public.tenant_site (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- House updated_at trigger (verified convention on tenant_10dlc_profile)
CREATE TRIGGER set_updated_at_tenant_site BEFORE UPDATE ON public.tenant_site
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

**Trigger callout (workflow §B mandatory-triggers line)**: `set_updated_at` is required and specified above. `audit_log` / `immutable_guard` triggers are **not applicable** — this is a mutable tenant-configuration table, not a ledger/immutable table (verified: `tenant_10dlc_profile` carries only `set_updated_at`). Audit coverage comes from the four `StandardAuditMixin` columns + the immutable `published_snapshot` pinning every published state + the C-B15 impersonation-audit middleware for operator mutations.

**SQLModel class**: `TenantSite(StandardAuditMixin, SQLModel, table=True)` in a **new file** `backend/app/models/tenant_site.py`. `published_snapshot` maps to a `dict` field with `sa_type=JSONB`. Python Engineer updates `backend/db_models_map.md` (Rule 12.1 — Architect verifies on batch close).

### B.2 `tenant_10dlc_profile` — one nullable column + auto-populate rules

```sql
ALTER TABLE public.tenant_10dlc_profile ADD COLUMN requirements_emailed_at TIMESTAMPTZ NULL;
```

Guards the §G-19 one-time requirements email (single source of truth; nullable add — 3-part pattern not triggered). New column name, no collision with the MCP-verified column list (§B.0).

Auto-populate is service-layer, **three-way on publish** (§G-16/17): **(1)** `website IS NULL` → set to `https://{slug}.{TENANT_SITES_BASE_DOMAIN}`; **(2)** `website_auto_populated = TRUE` (we wrote it) → refresh silently; **(3)** tenant-entered URL present → publish requires `confirm_website_overwrite=true`, else **409 `website_overwrite_requires_confirmation`** carrying current vs. new URL + brand state. The publish response always includes `website_action` + `brand_status` + `brand_guidance` so the UI sequences correctly (publish → re-submit brand). **Reconciliation hook**: if the tenant later edits `website` directly in the C-B9 profile form to a non-Pilot URL, `website_auto_populated` flips back to FALSE (Part A touchpoint in the `tenant_10dlc_profile.py` PUT — §F `on_profile_website_changed`).

### B.3 Compliance templates are code-resident — NOT a DB table

Locked Privacy/Terms language must pass code review before it changes, so templates live in the repo, versioned by directory: `backend/services/tenant_site_templates/v1/` — `landing.md`, `privacy.md`, `terms.md`. Merge via stdlib `string.Template` (`${field}` tokens) — **no new dependency**. `tenant_site.template_version` pins the set; a future language revision = new `v2/` directory + re-publish flow. The SMS clauses (message types, cadence, rates notice, STOP/HELP, no-third-party-mobile-sharing) mirror the PLATFORM-SMS-B1 approved campaign strings — single content path doctrine applies.

### B.4 Seed Data Rollout (Rule 11.5 — MANDATORY)

- **Layer 1 (core/platform)**: none — no lookup tables; `site_kind`/`status` are CHECK-constrained text (consistent with the `tenant_messaging_registration` no-lookup precedent); templates are code-resident (§B.3).
- **Layer 2 (scenario)**: extend the scenario seed set with (a) one **published** `hosted_compliance` row for the primary demo tenant (complete snapshot — enables local smoke-testing of the public pages at `{slug}.localhost:3000`), and (b) one **draft** `compliance_kit` row for a second seed tenant. `tenant_site` has `UNIQUE(tenant_id)` → `INSERT ... ON CONFLICT DO NOTHING` is sufficient; **no DELETE needed** (Rule 11.1 value-scoping not triggered).

> **As-built note (2026-08-14)**: row (b) was **not seeded** — MCP-verified only one tenant exists in the seed DB (`Pilot Dev Tenant`), so a second-tenant row was impossible without minting a new seed tenant. Deviation accepted; documented in the Part A completion summary (Appendix C). Row (a) shipped as designed (`seed_scenario_tenant_site.py`, slug `pilot-dev-tenant`, snapshot built via `build_snapshot()`).
- **Verification**: `seed_core.py --mode inspect` + `pytest -m unit`; update `README-seed-data.md` §4 (Current Seed State).

---

## C. Execution Order

| # | Step | Owner | Depends on |
|---|---|---|---|
| 0 | **Infra track (parallel; pre-prod only, does NOT block local dev)** — *amended 2026-08-14 for Cloudflare (amendment 3, ADR-0014)*: domain **`p4tsites.com` registered via Cloudflare ✅** (2026-08-14, $10.46/yr — Cloudflare is now our registrar). **Cloudflare DNS** (no Route 53 hosted zone): wildcard CNAME (`*.p4tsites.com`, DNS-only) → ALB DNS name. **Terraform (AWS side only)**: wildcard ACM cert (`*.p4tsites.com` + apex SAN, DNS validation via Cloudflare CNAMEs) + ALB host-header rule (`*.p4tsites.com` → `pilot-web` TG) (precedent: `aws_lb_listener_rule.web` line 815). **Cloudflare console (manual, documented in ops runbook)**: validation CNAMEs + wildcard CNAME + apex/www proxied placeholder + Redirect Rule (apex/www → 301 `https://pilotfortrades.com`) + deny-all SPF/DMARC (no mail on this domain) | DevOps + Tom | Domain registered ✅ |
| 1 | Alembic migration: §B.1 DDL (table + 3 indexes + trigger) | Python Engr | — |
| 2 | `TenantSite` SQLModel + schemas (`api/schemas/tenant_site.py`) | Python Engr | 1 |
| 3 | Template renderer + `v1/` template set (§B.3) + `tenant_site_service.py` (§F) | Python Engr | 2 |
| 4 | Authenticated router `api/routes/tenant_site.py` (5 endpoints + /test twins) + `main.py` registration + `on_profile_website_changed` hook in the C-B9 profile PUT (§B.2) | Python Engr | 3 |
| 5 | Public router `api/routes/public_tenant_sites.py` + SlowAPI limit + Redis cache | Python Engr | 3 |
| 6 | Celery task `tasks/tenant_site_emails.py::send_website_requirements_email` (SendGrid; one-time guard §G-19) + Requirements Guide PDF artifact (§G-20 — content authored by Architect, committed static asset) | Python Engr + Architect | 3 |
| 7 | Seed rollout (§B.4) + README §4 update + `db_models_map.md` update | Python Engr | 4 |
| 8 | Unit tests → `export_openapi_json.py` → commit → **handoff: notify React Engr to run `pnpm sync-api-types`** (Rule 9.3) | Python Engr | 4–7 |
| 9 | Part B web: middleware, public route group, settings surface (after both UI specs Tom-approved) | React Engr | 8 + specs |
| 10 | Prod cutover: apply Terraform (step 0), set prod env vars, Tom smoke-tests one seeded slug over HTTPS | Tom + DevOps | 0, 9 |

---

## D. New API Endpoints

House patterns honored: `_impl` shared logic + `/test` twins (per `quotes.py`/`invoices.py` precedent), `require_permission`, `Idempotency-Key` on all mutations (24h TTL), tenant-scoped `select()` (no `db.get()`), SlowAPI on public surface.

| # | Method & Path | Auth / RBAC | Purpose | Key errors |
|---|---|---|---|---|
| 1 | `GET /api/v1/tenant-site` | JWT · `settings.view` | Current config + status + computed URL + **effective defaults** merged from profile (for form pre-fill). Returns `{configured: false, defaults: {...}}` when no row — never 404 | — |
| 2 | `PUT /api/v1/tenant-site` | JWT · `settings.manage` · Idempotency-Key | Upsert draft: `site_kind`, `slug`, display/contact overrides, `show_full_address`. Slug editable only while never-published | 409 `slug_taken` · 422 `slug_invalid` / `slug_reserved` |
| 3 | `GET /api/v1/tenant-site/slug-availability?slug=` | JWT · `settings.view` | `{available: bool, reason?: 'taken'\|'invalid'\|'reserved', suggestion?}` for live form UX | 422 missing param |
| 4 | `POST /api/v1/tenant-site/publish` | JWT · `settings.manage` · Idempotency-Key | Builds snapshot (§F), `status=published`, `published_at`, auto-populates `website` per the §B.2 three-way rule. Body: `{confirm_website_overwrite?: bool}`. Re-publish regenerates snapshot from current draft (idempotent). Response includes `website_action` (`set`\|`kept`\|`overwritten`), `brand_status`, `brand_guidance` | 422 `missing_required_fields` (display_name, public_phone **or** public_email, public_city, public_state) · 409 `no_draft` · 409 `website_overwrite_requires_confirmation` (payload: current/new URL + `brand_status`) |
| 5 | `POST /api/v1/tenant-site/unpublish` | JWT · `settings.manage` · Idempotency-Key | `status=unpublished`, `unpublished_at`. **Does NOT clear `website`** (§G-8) — response includes `warning` string for the UI | 409 `not_published` |
| 6 | `/test` twins of 2, 4, 5 | `get_test_context()` | House test pattern | 403 when test context disabled |
| 7 | `GET /api/v1/public/tenant-sites/{slug}` | **Public (no JWT)** · SlowAPI `60/minute` per IP · Redis cache 300s keyed `tenant_site:pub:{slug}` | Returns the **published snapshot only** — whitelisted fields: `slug`, `display_name`, `tagline`, `public_email`, `public_phone`, `public_city`, `public_state`, address fields **only when `show_full_address`**, `template_version`, `published_at`, `pages: {landing, privacy, terms}` | 404 `site_not_found` for unknown slug **and** for non-published (no existence leak) |

**No kit-email endpoint (amendment 2, §G-19)**: the Option-1 requirements email is sent automatically exactly once — there is no resend affordance to rate-limit. The Requirements Guide PDF is a static-asset download (§G-20), not an API call.

**Public response payload sketch**:

```json
{
  "slug": "lang-electric",
  "display_name": "Lang Electric",
  "tagline": "Residential & commercial electrical — Richmond, VA",
  "public_email": "tom@langelectric.example.com",
  "public_phone": "+15551234567",
  "public_city": "Richmond",
  "public_state": "VA",
  "template_version": "v1",
  "published_at": "2026-08-14T01:23:45Z",
  "pages": {
    "landing": { "heading": "...", "body_paragraphs": ["..."], "contact_lines": ["..."] },
    "privacy": { "title": "Privacy Policy", "body_paragraphs": ["..."] },
    "terms":   { "title": "Terms of Service", "body_paragraphs": ["..."] }
  }
}
```

`body_paragraphs` are pre-escaped plain text (paragraph-split) — the frontend renders without a markdown parser and without HTML injection risk (§G-6).

**Router registration** (`main.py`): `tenant_site.router` at `/api/v1/tenant-site` (adjacent to `tenant_10dlc_profile`, line 278); `public_tenant_sites.router` at `/api/v1/public/tenant-sites` (adjacent to `public_charter`, line 367).

---

## E. Pattern Reuse Decisions (mvp-arch §16)

| Pattern | Application in C-B16 |
|---|---|
| **§16.5 System-default + tenant-override** | Form fields default from `tenant_10dlc_profile` / `tenant`; overrides stored on `tenant_site`; effective values resolved server-side in `get_effective_defaults()` |
| **§16.7 Always-preview-before-send** | Publish is a public one-way-door action → settings UI renders a full preview of the exact snapshot + confirm step before `publish`. (The Option-1 email is an automatic one-time send — §G-19 — so no per-send preview applies; the always-visible requirements warning panel at URL entry carries the disclosure weight instead) |
| **Idempotency (§15.4)** | `Idempotency-Key` on PUT/publish/unpublish; natural-key fallback via `UNIQUE(tenant_id)` upsert + partial unique index on `(tenant_id, idempotency_key)`. The one-time requirements email needs no key — guarded by `requirements_emailed_at` (§G-19) |
| **409-and-refresh (§16.4)** | **N/A — justified**: single-writer tenant settings surface (owner/admin role); no multi-actor contention like dispatch/QB. Documented to prevent Engineer confusion |
| **SSE vs WebSocket (Rule §8)** | N/A — no real-time surface in this batch |
| **HMAC signed public tokens** (`public_link_signer`) | **Deliberately NOT used** (§G-6): tenant sites must be discoverable/indexable by TCR vets; slugs are public by design; payload contains only tenant-published fields |
| **4-layer public lockdown** (marketing precedent) | Rate limit ✅ (SlowAPI on §D-7) · CORS **untouched** (SSR is server-to-server — §G-12) · Turnstile **N/A for read-only GET** (precedent: `public_charter`); reserved for C-B17 contact form · payload whitelist ✅ |

---

## F. Shared Module Interfaces & Celery Tasks

**`backend/services/tenant_site_service.py`** (new):

```python
SLUG_RE: re.Pattern                      # mirrors ck_tenant_site_slug_format
RESERVED_SLUGS: frozenset                # www, api, app, mail, smtp, support, help, admin,
                                         # pilot, p4t, pilotfortrades, staging, dev, qa, test,
                                         # status, billing, login, signup, marketing, cdn, assets

def get_site(db, tenant_id) -> TenantSite | None
def get_effective_defaults(db, tenant_id) -> TenantSiteDefaults
    # display_name ← dba_name or legal_business_name; email ← support_email;
    # phone ← support_phone; city/state ← hq_city/hq_state (street NEVER defaulted)
def check_slug_availability(db, slug) -> SlugAvailability
def upsert_draft(db, tenant_id, payload, idempotency_key) -> TenantSite
def build_snapshot(db, site) -> dict      # renders template_version set → pages payload (§D)
def publish(db, site, confirm_website_overwrite: bool = False) -> PublishResult
    # snapshot + status + published_at + §B.2 three-way website rule + brand-state guidance
def classify_website_action(db, site) -> WebsiteAction
    # current value / ours-vs-theirs / tenant_messaging_registration.status → guidance_key
def on_profile_website_changed(db, tenant_id, new_value: str | None) -> None
    # reconciliation: clears website_auto_populated when tenant saves a non-Pilot URL (C-B9 PUT hook)
def unpublish(db, site) -> TenantSite
def auto_populate_website(db, site) -> None  # §B.2 write-rules; sets website_auto_populated
def get_published_snapshot(db, slug) -> dict | None   # public path; status='published' only
```

**`backend/services/tenant_site_templates/`** (new): `__init__.py::render_template(page: str, version: str, context: dict) -> str` + `v1/landing.md`, `v1/privacy.md`, `v1/terms.md`. Privacy/Terms contain the locked 10DLC SMS clauses (message types, cadence, msg&data-rates notice, STOP/HELP instructions, "no mobile information shared with third parties for marketing/promotional purposes").

**`backend/tasks/tenant_site_emails.py`** (new): `send_website_requirements_email(tenant_id: str)` — Celery task, SendGrid send (dedicated-task precedent from `tasks/marketing_notifications.py`; no `notification_outbox` — tenant-optional FK pattern). Body = the website-requirements content + PDF guide link + (when profile data exists) the pre-merged Privacy/Terms kit text. **One-time guard**: enqueued only when `tenant_10dlc_profile.requirements_emailed_at IS NULL`; the flag is stamped on successful enqueue. **Triggers**: (a) C-B9 profile PUT saving a self-managed (non-Pilot) `website`; (b) Settings > Website Option-1 selection when a profile row exists. No Beat schedule, no resend endpoint (§G-19).

**Frontend (Part B)**: `src/middleware.ts` (new — host-based rewrite, §G-13); `src/lib/tenant-sites.ts` — server-side fetcher: `fetch(apiUrl, { next: { revalidate: 300 } })`.

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| 1 | Domain | **`p4tsites.com` — registered via Cloudflare 2026-08-14** ($10.46/yr; Cloudflare is now our registrar — GoDaddy $22 / Route 53 $16 declined; ADR-0014). DNS lives in Cloudflare (wildcard DNS-only posture; apex/www proxied only to power the edge redirect); **no Route 53 hosted zone**. All code reads it from env: backend `TENANT_SITES_BASE_DOMAIN`, web `NEXT_PUBLIC_TENANT_SITES_DOMAIN` — never hardcoded. +$0.87/mo approved (amended from +$1.58 — §J) |
| 2 | Subdomain vs folder | Wildcard subdomains; one-time Terraform DNS/cert; zero per-tenant Route 53 calls |
| 3 | Generic vs white-labeled | Tenant-branded content + "Hosted by Pilot for Trades" footer; custom domains deferred |
| 4 | Pricing gate | Charter included (`tenant.charter_eligible`); `hosted_compliance` free on all paid tiers; entitlement = service-layer `site_kind` check defaulting to allow; **no Stripe objects this batch**; `starter_site` pricing after GTM research (task added to `pilot-to-do-tasks-for-tom.md`) |
| 5 | Router name collision | `/api/v1/sites` is job-sites (`main.py`) → ours is `tenant-site` / `public/tenant-sites` |
| 6 | Snapshot vs render-at-request | **Snapshot at publish**: pins exactly what TCR vetted (dispute audit trail); drafts never leak; O(1) reads. No signed tokens (sites are public by design); body content stored as pre-escaped paragraphs (no HTML/markdown injection surface) |
| 7 | Slug mutability | Editable while never-published; **immutable after first publish** (MVP) — changes via support ticket |
| 8 | Unpublish side effects | Does NOT clear `tenant_10dlc_profile.website` — retracting the URL could silently break an in-flight TCR registration; UI surfaces a warning instead. Warning **escalates** when the brand is live and points at our hosted URL (unpublishing breaks the vetted site → carrier re-vet risk) |
| 9 | Turnstile on public GET | No — read-only precedent (`public/charter-availability`); Turnstile arrives with the C-B17 contact form POST |
| 10 | Address privacy | Street never defaulted (sole props register home addresses); snapshot includes `public_address_line1`/`public_postal_code` only when `show_full_address=TRUE`; city/state always shown |
| 11 | Apex/www behavior | 301 redirect to `https://pilotfortrades.com` (marketing) via a **Cloudflare Redirect Rule at the edge** (proxied apex/www placeholder record + rule) — amended 2026-08-14 from an ALB rule: zero ALB rules burned, no origin hop. Only the wildcard host rule (`*.p4tsites.com` → `pilot-web` TG) lives on the ALB |
| 12 | CORS | Untouched — tenant pages are fully SSR (server-to-server); browsers never call the API from tenant pages. If C-B17 adds a client-side POST, the allowlist is revisited then (wildcard origins don't compose with `allow_credentials`) |
| 13 | Local dev | `{slug}.localhost:3000` resolves on macOS → middleware treats any `*.localhost` host as a sites host; `?__slug=` query override for tests; dev env default `TENANT_SITES_BASE_DOMAIN=localhost:3000` |
| 14 | Forward path to Option 3 | C-B17: `ALTER TABLE ... DROP CONSTRAINT ck_tenant_site_kind` + re-ADD with `'starter_site'`; new template pages; contact form (Turnstile + new POST endpoint); Stripe add-on wiring per `stripe-pricing-config.md` §4 |
| 15 | 10DLC wiring | Publish auto-populates `website` (§B.2). Campaign CTA Terms/Privacy URLs (`{url}/terms`, `{url}/privacy`) are **read by the C-B9 provisioning UI** when present — display-only hint this batch; Telnyx campaign-submission wiring rides with PLATFORM-SMS-B2 |
| 16 | Overwriting a tenant-entered `website` (Tom scenario 2026-08-14) | **Explicit confirmation required**: publish over a tenant-entered URL returns 409 `website_overwrite_requires_confirmation` (current vs. new URL + brand state) until re-called with `confirm_website_overwrite=true`. Silent only when the field is empty or already ours. §16.7 one-way-door discipline applied to a compliance artifact |
| 17 | Brand-registration timing matrix | TCR vets the URL **as pushed to Telnyx at brand submission** — a local field change never updates an in-flight or approved brand. Guidance keys off `tenant_messaging_registration.status`: **none/draft** → new URL used on first submission. **in-flight** → vet checks the OLD URL; advise waiting for the outcome, then re-submit. **`brand_rejected`** (Tom's failed-registration scenario) → publish + overwrite-confirm, then re-submit from the existing C-B9 Messaging UI — the intended recovery path for website-content failures. **active/approved** → live brand still references the old URL; updating Telnyx may trigger TCR re-vetting — prominent warning. **No automatic Telnyx brand update in C-B16** — re-submission is tenant-initiated; auto-update evaluated with PLATFORM-SMS-B2 |
| 18 | Profile-edit reconciliation | If the tenant edits `website` directly in the C-B9 profile form to a non-Pilot URL, `website_auto_populated` flips FALSE (`on_profile_website_changed`, §F) — keeps the three-way rule's invariant intact |
| 19 | Requirements email model (Tom 2026-08-14) | **One-time automatic email, no resends**: sent on the first self-host signal (own URL saved in the C-B9 profile form, or Option-1 selection in Settings), guarded by `tenant_10dlc_profile.requirements_emailed_at`. Replaces the original manual `kit-email` endpoint + 429 rate-cap design — simpler, nothing to abuse, nothing to retry. UI shows "Guide emailed on {date}" + the download link thereafter |
| 20 | Requirements Guide PDF | Full TCR website requirements + worked examples as a **static committed asset** (`apps/web/public/resources/tenant-website-requirements-v1.pdf`, versioned filename; markdown source committed alongside for regeneration). Downloadable anytime from the C-B9 profile-form warning panel and Settings > Website. Content authored by Architect (from C-SPIKE-2 verified requirements); visual layout per the marketing-ui designer spec (§H). Linked (not attached) in the one-time email. **As-built 2026-08-16**: ✅ PDF committed — produced via the Google Docs manual-layout process (mkt spec §8.8 as-built; print-stylesheet HTML pipeline abandoned); `.md` + `.docx` + `.pdf` triple committed |

---

## H. Surface Mockup Reference (Frontend — two designer specs, Tom-gated)

Per Rule §1.5 / methods §3.9, **two specs must exist and be Tom-approved before the React Engineer prompt is authored**. The Architect does not author pixel specs.

| Spec | Owner mode | Output path | Surfaces |
|---|---|---|---|
| Public tenant-site templates | `pilot-marketing-ui-designer` (public unauthenticated surface) | `dev-docs/marketing-analysis/design-specs/mkt-c-b16-design-spec.md` | Landing, Privacy, Terms templates + 404/unknown-slug state + "Hosted by" footer. SSR, zero required client JS, token-locked, WCAG 2.2 AA + **Requirements Guide PDF layout** (§G-20 — tenant-facing downloadable compliance document; content authored by Architect) |
| Settings surface | `pilot-web-ui-designer` (authenticated `apps/web` surface) | `dev-docs/architecture-design/batch-designs/batch-c-b16-web-ui-design-spec.md` | `Settings > Website` page: 3-option cards, defaults-from-profile form, slug input w/ availability feedback, **preview-before-publish** (§16.7), publish/unpublish states, **website-overwrite confirmation dialog + brand-state guidance banner** (§G-16/17 — state-keyed copy: draft / in-flight / rejected / live), **strong requirements warning panel + PDF download + one-time-email state** (§G-19/20 — panel reused in the C-B9 10DLC profile form wherever a self-managed URL is entered) |

**Platform scope**: web-only. Mobile N/A (owner settings task; no field-tech surface). **§16 consumption**: §16.5 (defaults/override) + §16.7 (preview-before-publish) on the settings surface; the public templates consume no interactive §16 patterns (read-only) but must use the shared token vocabulary. Both specs must pass the §3.9 verification checklist (locked-pattern composition, token-only, Accessibility Notes subsection, component-existence check against `packages/ui/src/index.ts`).

---

## I. Component Manifest

**Backend (Part A — all new unless noted)**:

| File | Purpose |
|---|---|
| `backend/app/models/tenant_site.py` | `TenantSite` SQLModel |
| `backend/api/schemas/tenant_site.py` | Request/response schemas (§D) |
| `backend/api/routes/tenant_site.py` | Authenticated router (5 endpoints + /test twins) |
| `backend/api/routes/public_tenant_sites.py` | Public router (§D-8) |
| `backend/services/tenant_site_service.py` | §F service |
| `backend/services/tenant_site_templates/__init__.py` + `v1/{landing,privacy,terms}.md` | §B.3 template set |
| `backend/tasks/tenant_site_emails.py` | §F Celery task |
| `backend/app/main.py` | **EDIT** — 2 `include_router` lines |
| `backend/db_models_map.md` · `backend/README-seed-data.md` §4 | **EDIT** — Rule 12.1 / Rule 11.5 |
| `backend/tests/unit/...` tenant-site domain tests | Slug validation, publish/snapshot, auto-populate write-rules incl. overwrite-confirm 409 (§G-16), public 404/whitelist, one-time email guard (§G-19), seed idempotency |

**Web (Part B — all new unless noted)**:

| File | Purpose |
|---|---|
| `apps/web/src/middleware.ts` | Host rewrite; matcher scoped to sites domains only — must NOT intercept existing auth/api paths |
| `apps/web/src/app/(tenant-site)/sites/[slug]/{layout,page,not-found}.tsx` + `privacy/page.tsx` + `terms/page.tsx` | Public SSR route group |
| `apps/web/src/lib/tenant-sites.ts` | Server fetcher (`revalidate: 300`) |
| `apps/web/src/app/(authed)/settings/website/page.tsx` | Settings surface (+ settings nav registration) |
| `apps/web/src/features/tenant-site/` | `TenantSiteSettingsForm`, `SiteOptionCard`, `SlugAvailabilityInput`, `SitePreviewPanel`, `PublishConfirmDialog` (incl. the §G-16 overwrite-confirm branch on 409), `BrandStateNotice` (§G-17 state-keyed guidance), `WebsiteRequirementsPanel` (§G-19 strong warning + PDF download — reused in the C-B9 profile form), `SelfHostEmailNotice` ("Guide emailed on {date}" state) + hooks (`useTenantSite`, `useUpsertTenantSite`, `usePublishTenantSite`, `useUnpublishTenantSite`) — TanStack Query `retry: false`, `apiClient` only |
| `apps/web/src/mocks/handlers/tenant-site.ts` + `index.ts` barrel | MSW handlers (registered in barrel) |
| `apps/web/public/resources/tenant-website-requirements-v1.pdf` (+ `.md` source + `.docx` working file) | Requirements Guide static asset (§G-20) — Architect authors content; committed, versioned filename. As-built 2026-08-16: ✅ all three committed (Google Docs layout process, mkt spec §8.8 as-built) |
| `packages/ui/` | **No new shared components expected** — designer spec confirms against the barrel (§3.9) |

---

## J. Infrastructure, Cost & Master-Document Stewardship

**Cost delta (Rule §4 flag — approved 2026-08-13; amended 2026-08-14 for Cloudflare, ADR-0014)**: **+$0.87/mo** (domain registration $10.46/yr amortized; Cloudflare DNS on the free plan; **no Route 53 hosted zone** — saves the $0.50/mo from the original +$1.58 estimate). ACM cert free; ALB rule zero marginal; compute rides the existing `pilot-web` Fargate service. Baseline ~$888 → **~$888.87/mo**. No new AWS service.

**New env vars** (added to `aws-env-mgmt-ops-plan.md` per Rule 10.8 in this same change set): `TENANT_SITES_BASE_DOMAIN` (backend), `NEXT_PUBLIC_TENANT_SITES_DOMAIN` (web). Dev: `localhost:3000`; QA/prod: the registered domain. No new secrets (SendGrid key exists).

**Master-doc updates (Rule 12.3 — same change set)**:

| Document | Update | Owner |
|---|---|---|
| `pilot-docs-list.md` | Add this design doc; later the 2 specs + 2 prompts | Architect (this session) |
| `pilot-launch-plan.md` | C-B16 card: design link + status; §1 add GTM pricing-research task | Architect (this session) |
| `mvp-prd.md` | New compact section: tenant website hosting options (product truth) | Architect (this session) |
| `aws-env-mgmt-ops-plan.md` | Env vars + new domain registration posture | Architect (this session) |
| `pilot-to-do-tasks-for-tom.md` | GTM pricing research task (Option 3 ~$9.99 validation) | Architect (this session) |
| `backend/db_models_map.md` · `backend/README-seed-data.md` §4 | New model + seed state | Python Engineer (batch close; Architect verifies) |
| `aws-infrastructure-as-built.md` | Domain/cert/ALB rules as-built | DevOps (step 0/10; Architect verifies) |

**OpenAPI handoff (Rule 9.3)**: Part A closes with `python export_openapi_json.py` + commit; Part B opens with `pnpm sync-api-types`.
