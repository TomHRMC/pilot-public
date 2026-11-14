# Implementation Prompt: C-B16 (Part A — Backend) — Pilot-Hosted Tenant Sites (SMS Compliance Pages + Compliance Kit)

**Mode**: Pilot Python Engineer
**Batch**: C-B16 — Part A (backend) — runs **FIRST**
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 C-B16 card (Beta Execution Order 4)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b16-design.md` ✅ APPROVED 2026-08-14 (incl. amendments 1 + 2)
**Estimated session**: 5–7 hours (natural checkpoint after Task 5 if two sessions are needed)
**Platform**: Backend only (`backend/`)
**Frontend companion**: C-B16 Part B — `batch-c-b16-react-engr-prompt.md` (web; starts only after this part merges + `pnpm sync-api-types`)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **The design doc** — `batch-c-b16-design.md` §B (migration), §D (endpoints), §F (service interfaces), §G (resolved questions). The DDL and signatures in this prompt come from there; the design doc is the authority if anything here drifts.

Critical rules for this batch:

- **Rule 1 / Rule 16 (verify, don't assume)**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. 186 tables exist. If MCP returns an error → **STOP and ask Tom**. The Architect pre-verified `tenant_10dlc_profile` (19 cols), `tenant_messaging_registration` (20 cols), `tenant` (17 cols), and the `tenant_site` greenfield probe on 2026-08-14 — you still run the Pre-Work queries yourself (engineer safety net, inclusions §3).
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). This batch's migration is **DDL-only** (no data changes) — the `SET LOCAL session_replication_role = 'replica';` line is therefore NOT required (it is for seed/data migrations only).
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause. This batch is a tenant-scoped settings entity — every query goes through `tenant_id`.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 8 (RFC 7807)**: All API error responses MUST follow RFC 7807 Problem Details format (`{"type": "https://...", "title": "...", "status": N, "detail": "..."}`) — including the public endpoint's 404. Plain-string `detail` is banned.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=current_user.id)` before the first `db.add()` / `db.commit()`.
- **Rule 10**: `require_permission()` `feature_code` — **deliberately NOT used in this batch**. Design §G-4: `hosted_compliance` is free on all paid tiers, entitlement check defaults to allow, no Stripe wiring. Do not invent a feature gate.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. No "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def`. **Never convert a handler that touches the sync `Session` to `async def`.** See the Sync-by-Design callout below.
- **Rule 13 (Pydantic v2 — rules §22)**: v2 idioms only — `model_config = ConfigDict(...)`, `@field_validator` / `@model_validator`, `.model_dump()`, `.model_validate()`. Every route needs `response_model`. Banned: `class Config`, `@validator`, `.dict()`, `.parse_obj()`.
- **Rule 14 (Ruff — rules §23)**: Run ruff **only against the files you changed** (`git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`). Fix ALL errors in those files, including pre-existing ones. Do not hand-order imports.
- **Rule 15 (audit mixins — rules §24)**: The new `tenant_site` table inherits `StandardAuditMixin` (all four audit columns) — never hand-declare `created_at`/`updated_at`. Add `tenant_id` explicitly. All timestamps are TIMESTAMPTZ (UTC-aware datetimes non-negotiable). The migration DDL includes all four audit columns + the `set_updated_at` trigger (design §B.1).

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either (a) confirm with Tom that this is a known, accepted failure with a documented reason, or (b) fix the failure before touching any batch files. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.
>
> **Two read-only MCP servers exist** (global rule `.roo/rules/02-database-mcp-access.md`): **`postgres-local`** is the default for all verification. **`postgres-prod`** reads production but **requires an SSH tunnel that only Tom controls** — this batch needs `postgres-local` only.

```sql
-- 1. Confirm tenant_10dlc_profile columns: website is text NULL, requirements_emailed_at does NOT exist yet
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_10dlc_profile'
ORDER BY ordinal_position;

-- 2. Greenfield probe: tenant_site must NOT exist yet
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE '%tenant_site%';

-- 3. Confirm the house trigger convention: set_updated_at() function + trigger on tenant_10dlc_profile
SELECT proname FROM pg_proc WHERE proname = 'set_updated_at';
SELECT trigger_name FROM information_schema.triggers
WHERE event_object_table = 'tenant_10dlc_profile';

-- 4. Brand-state classification input: actual registration status values present (read-only data check)
SELECT DISTINCT status FROM public.tenant_messaging_registration;

-- 5. Current alembic head (record it — your new migration's down_revision)
SELECT version_num FROM public.alembic_version;

-- 6. Confirm tenant.name / charter_eligible (defaults + entitlement context)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
ORDER BY ordinal_position;
```

**Engineer safety net (MANDATORY)**: Before writing ANY SQL statement, Alembic migration code, or SQLModel field reference, confirm the columns you use against query 1/6 results above. If any column name in this prompt does not match what MCP returns → use the MCP-returned name, not the prompt's name, and note the discrepancy in your Completion Summary. Do NOT ask the Architect to re-do the prompt — correct it inline and proceed.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
dev-docs/architecture-design/batch-designs/batch-c-b16-design.md   ← the spec: §B DDL, §D endpoints, §F service signatures, §G resolved questions (esp. G-16/17/18/19/20)
backend/app/models/mixins.py                                        ← StandardAuditMixin (all four audit columns) — TenantSite inherits it
backend/db_models_map.md                                            ← locate the Tenant10dlcProfile / TenantMessagingRegistration model files
backend/api/routes/tenant_10dlc_profile.py                          ← RBAC precedent (settings.view / settings.manage) + the PUT _impl you will hook (Task 4)
backend/api/schemas/  (ls + read the 10dlc profile schema file)     ← existing Pydantic shapes before adding the new schema file
backend/api/routes/marketing.py                                     ← SlowAPI limiter pattern (header security model ~13–17; limiter usage ~175, 242, 366, 517)
backend/api/routes/public_charter.py                                ← public read-only GET precedent (no JWT)
backend/app/main.py                                                 ← router registration zones: authenticated (~line 278 tenant_10dlc_profile) and public (~line 367 public_charter); CORS (~420–459) — DO NOT TOUCH CORS
backend/tasks/marketing_notifications.py                            ← Celery + SendGrid dedicated-task precedent (two-layer _impl + task)
backend/services/platform_sms_templates.py                          ← single-content-path doctrine reference (approved SMS language now lives in DB templates)
backend/core/test_context.py                                        ← TestUserContext / get_test_context (verify path via grep if different)
backend/migrations/versions/  (ls -t | head -3, read the newest)    ← current migration style + head revision
backend/tests/conftest.py                                           ← fixtures (client, db_session, test_tenant, second_tenant, tenant_a/tenant_b, mock_cognito_jwt…)
backend/README-seed-data.md  §3 (Group A–D), §6 (run order), §7 (DELETE safety)  ← seed system rules before Task 7
dev-docs/architecture-design/batch-designs/batch-c-b9-design.md     ← the 13-state 10DLC registration state machine (brand_status classification, Task 3)
dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md  §6/§8  ← approved SMS disclosure clause language the templates mirror
```

Also run these grep commands to find related files:

```bash
grep -rn "Idempotency-Key\|idempotency_key" backend/api/routes/ --include="*.py" -l | head -5   # house idempotency pattern
grep -rln "tenant_10dlc" backend/tests/domains/ | head -5                                       # where profile/messaging tests live (domain-folder precedent)
grep -rn "SENDGRID" backend/core/ backend/tasks/ --include="*.py" | head -5                     # settings module + SendGrid client location
grep -rn "import redis\|from redis\|Redis(" backend/core/ backend/services/ --include="*.py" | head -10  # existing Redis client / cache pattern (maps cache)
grep -rn "set_updated_at" backend/migrations/versions/*.py | tail -3                            # trigger DDL precedent in migrations
```

---

## Background / Context

**Why this batch exists**: sole-proprietor tenants without a website **will fail** TCR 10DLC brand registration (C-SPIKE-2, verified across Plivo/Hustle/TCR/Twilio). C-B16 ships two tenant options: **Option 1 — Compliance Kit** (strong requirements warning + one-time requirements email + downloadable Requirements Guide PDF; tenant self-hosts) and **Option 2 — Hosted Compliance Site** (Pilot hosts a 3-page site — landing + privacy + terms — at `{slug}.{TENANT_SITES_BASE_DOMAIN}`). Option 3 (Hosted Starter Site) is deferred to C-B17 — do not build for it.

**Key design decisions (do not re-litigate — all Tom-approved in the design doc)**:

1. **Publish → snapshot → SSR serve** (§G-6): publish renders locked code-resident templates + tenant data into an immutable `published_snapshot` JSONB; the public endpoint serves only the snapshot. Pins exactly what TCR vetted; drafts never leak; O(1) reads.
2. **Three-way website auto-populate on publish** (§B.2 / §G-16): `website IS NULL` → set; `website_auto_populated = TRUE` → silent refresh; tenant-entered URL → **409 `website_overwrite_requires_confirmation`** until re-called with `confirm_website_overwrite=true`. Never silently overwrite a tenant-entered URL.
3. **Brand-registration timing matrix** (§G-17): TCR vets the URL as pushed to Telnyx at brand submission — a local field change never updates an in-flight or approved brand. Publish response carries `brand_status` + `brand_guidance` so the UI sequences correctly. **No automatic Telnyx brand update in C-B16.**
4. **Profile-edit reconciliation** (§G-18): tenant edits `website` directly in the C-B9 profile form to a non-Pilot URL → `website_auto_populated` flips FALSE (`on_profile_website_changed` hook in the profile PUT).
5. **One-time requirements email** (§G-19): automatic, exactly once, guarded by `tenant_10dlc_profile.requirements_emailed_at`. No resend endpoint, no retries. Triggers: (a) profile PUT saving a self-managed URL; (b) Option-1 (`compliance_kit`) selection when a profile row exists.
6. **Unpublish never clears `website`** (§G-8) — retracting the URL could silently break an in-flight TCR registration; the response carries a `warning` string instead.
7. **Address privacy** (§G-10): street address is never defaulted into the form (sole props register home addresses); the snapshot includes `public_address_line1` / `public_postal_code` only when `show_full_address = TRUE`.
8. **Public endpoint lockdown** (§E): SlowAPI `60/minute` per IP + payload whitelist via `response_model` + 404 `site_not_found` for unknown AND non-published slugs (no existence leak). No Turnstile (read-only GET precedent: `public_charter`). CORS untouched (SSR is server-to-server).
9. **Templates are code-resident** (§B.3): `backend/services/tenant_site_templates/v1/{landing,privacy,terms}.md`, stdlib `string.Template` (`${field}` tokens) — **no new dependency**. Locked 10DLC language changes via code review only.
10. **Router naming** (§G-5): `/api/v1/sites` is already job-sites — ours are `/api/v1/tenant-site` and `/api/v1/public/tenant-sites`.

---

## Task 1 — Alembic Migration (design §B.1 + §B.2)

**One blank migration** containing exactly the design-doc DDL:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "c_b16_tenant_site_and_requirements_emailed_at"
```

`upgrade()` — copy verbatim from design §B.1/§B.2:

```sql
CREATE TABLE public.tenant_site (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES public.tenant (id),
    slug                    VARCHAR(63) NOT NULL,
    site_kind               VARCHAR(20) NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'draft',
    display_name            VARCHAR(200) NOT NULL,
    tagline                 VARCHAR(300) NULL,
    public_email            VARCHAR(320) NULL,
    public_phone            VARCHAR(32) NULL,
    public_city             VARCHAR(120) NULL,
    public_state            VARCHAR(2) NULL,
    public_address_line1    VARCHAR(200) NULL,
    public_postal_code      VARCHAR(10) NULL,
    show_full_address       BOOLEAN NOT NULL DEFAULT FALSE,
    template_version        VARCHAR(20) NOT NULL DEFAULT 'v1',
    published_snapshot      JSONB NULL,
    published_at            TIMESTAMPTZ NULL,
    unpublished_at          TIMESTAMPTZ NULL,
    kit_sent_at             TIMESTAMPTZ NULL,
    website_auto_populated  BOOLEAN NOT NULL DEFAULT FALSE,
    idempotency_key         VARCHAR(100) NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              UUID NULL,
    updated_by              UUID NULL,
    CONSTRAINT ck_tenant_site_kind CHECK (site_kind IN ('compliance_kit', 'hosted_compliance')),
    CONSTRAINT ck_tenant_site_status CHECK (status IN ('draft', 'published', 'unpublished')),
    CONSTRAINT ck_tenant_site_slug_format CHECK (slug ~ '^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$')
);
CREATE UNIQUE INDEX uq_tenant_site_tenant ON public.tenant_site (tenant_id);
CREATE UNIQUE INDEX uq_tenant_site_slug ON public.tenant_site (slug);
CREATE UNIQUE INDEX uq_tenant_site_tenant_idempotency
    ON public.tenant_site (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE TRIGGER set_updated_at_tenant_site BEFORE UPDATE ON public.tenant_site
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE public.tenant_10dlc_profile ADD COLUMN requirements_emailed_at TIMESTAMPTZ NULL;
```

`downgrade()` — exact reverse (never leave it empty): drop trigger, drop table (indexes drop with it), drop the added column.

Test the full cycle:

```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

Then MCP-verify the post-migration state: `tenant_site` exists with 25 columns (incl. all four audit columns), `requirements_emailed_at` present on `tenant_10dlc_profile`, trigger `set_updated_at_tenant_site` present.

**3-Part NOT NULL pattern: NOT TRIGGERED** (new table + nullable add only).

Intermediate test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` — must match baseline.

---

## Task 2 — `TenantSite` SQLModel + Pydantic Schemas

**New file `backend/app/models/tenant_site.py`**:

```python
class TenantSite(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "tenant_site"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", index=True)
    slug: str = Field(max_length=63)
    site_kind: str = Field(max_length=20)
    status: str = Field(default="draft", max_length=20)
    display_name: str = Field(max_length=200)
    tagline: str | None = Field(default=None, max_length=300)
    public_email: str | None = Field(default=None, max_length=320)
    public_phone: str | None = Field(default=None, max_length=32)
    public_city: str | None = Field(default=None, max_length=120)
    public_state: str | None = Field(default=None, max_length=2)
    public_address_line1: str | None = Field(default=None, max_length=200)
    public_postal_code: str | None = Field(default=None, max_length=10)
    show_full_address: bool = Field(default=False)
    template_version: str = Field(default="v1", max_length=20)
    published_snapshot: dict | None = Field(default=None, sa_column=Column(JSONB))
    published_at: AwareDatetime | None = None
    unpublished_at: AwareDatetime | None = None
    kit_sent_at: AwareDatetime | None = None
    website_auto_populated: bool = Field(default=False)
    idempotency_key: str | None = Field(default=None, max_length=100)
```

Match the mixin file's exact `AwareDatetime` import/usage (read `mixins.py` first). Do NOT hand-declare the four audit columns. Register the model in `backend/app/models/__init__.py` (barrel — the F401 on your line is expected and already suppressed by `pyproject.toml` per-file-ignores; do not add `# noqa`).

**New file `backend/api/schemas/tenant_site.py`** (Pydantic v2, `response_model` shapes — separate from the ORM layer):

- `TenantSiteUpsertRequest` — `site_kind`, `slug`, optional display/contact overrides, `show_full_address`. Validate `site_kind ∈ {compliance_kit, hosted_compliance}`.
- `TenantSiteDefaults` — the §16.5 effective-defaults payload (`display_name`, `public_email`, `public_phone`, `public_city`, `public_state`; each with a `source` indicator of `tenant_override` vs `system_default` if you follow the §16.5 vocabulary — the web UI annotates defaults from this).
- `TenantSiteResponse` — full config + `status` + computed `site_url` (`https://{slug}.{TENANT_SITES_BASE_DOMAIN}` when published) + `requirements_emailed_at` (read from the profile row, nullable — the UI renders "Guide emailed on {date}" from it, §G-19) + `defaults`.
- `TenantSiteGetResponse` — `{configured: bool, site?: TenantSiteResponse, defaults: TenantSiteDefaults}` — **never 404 when no row** (§D-1).
- `SlugAvailabilityResponse` — `{available: bool, reason?: 'taken'|'invalid'|'reserved', suggestion?: str}`.
- `PublishRequest` — `{confirm_website_overwrite: bool = False}`.
- `PublishResponse` — the site payload **plus** `website_action: 'set'|'kept'|'overwritten'`, `brand_status: str` (raw `tenant_messaging_registration.status`, or `"none"` when no registration row), `brand_guidance: 'none_or_draft'|'in_flight'|'brand_rejected'|'live'` (the classification bucket the web UI's `BrandStateNotice` switches on).
- `UnpublishResponse` — the site payload **plus** `warning: str` (§G-8 copy hook; escalated wording when the brand is live and points at our hosted URL).
- `PublicTenantSiteResponse` — **whitelisted only**: `slug`, `display_name`, `tagline`, `public_email`, `public_phone`, `public_city`, `public_state`, `public_address_line1`/`public_postal_code` (only present in the snapshot when `show_full_address`), `template_version`, `published_at`, `pages: {landing, privacy, terms}` where each page is `{heading|title, body_paragraphs: list[str], contact_lines?: list[str]}` per design §D payload sketch. This `response_model` IS the public payload whitelist — the route never returns the ORM row.

Intermediate test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`.

---

## Task 3 — Template Set + `tenant_site_service.py`

**New package `backend/services/tenant_site_templates/`**:

- `__init__.py` — `render_template(page: str, version: str, context: dict) -> str` using stdlib `string.Template` (`${field}` tokens). Unknown page/version → raise a clear `ValueError`. Escape/normalize merged values so `body_paragraphs` are pre-escaped plain text (paragraph-split) — the frontend renders without a markdown parser and with zero HTML injection surface (§G-6).
- `v1/landing.md`, `v1/privacy.md`, `v1/terms.md` — the locked template set.

**Locked 10DLC SMS clause content** (privacy + terms must contain all of these — mirror the approved campaign language style from the Telnyx playbook §6/§8; canonical base wording per the marketing-ui spec):

> "We may send you text messages regarding appointment confirmations, service updates, and account alerts. Message frequency varies but is typically no more than 5 messages per month. Message and data rates may apply. To opt out, reply STOP to any message. For help, reply HELP. We do not share mobile information with third parties for marketing or promotional purposes."

Required clause categories (all six, in both privacy and terms): **message types · frequency/cadence · msg&data-rates notice · STOP opt-out · HELP instructions · no-third-party-mobile-sharing**. The landing template needs: business name (H1-equivalent heading), tagline (omitted when null), contact lines (phone/email — at least one required at publish), city/state, about paragraph, and Privacy/Terms link lines (`/privacy`, `/terms` paths on the same host).

**New file `backend/services/tenant_site_service.py`** — implement exactly the design §F interface:

```python
SLUG_RE: re.Pattern        # mirrors ck_tenant_site_slug_format: ^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$
RESERVED_SLUGS: frozenset  # www, api, app, mail, smtp, support, help, admin,
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
def classify_website_action(db, site) -> WebsiteAction
def on_profile_website_changed(db, tenant_id, new_value: str | None) -> None
def unpublish(db, site) -> TenantSite
def auto_populate_website(db, site) -> None  # §B.2 write-rules; sets website_auto_populated
def get_published_snapshot(db, slug) -> dict | None   # public path; status='published' only
```

Implementation requirements:

- **All functions are sync `def`** and take an injected `Session` (testable without a request).
- Every query is tenant-scoped (`select()` + `WHERE tenant_id = :tid`) except `get_published_snapshot` / `check_slug_availability`, which are intentionally keyed by the globally-unique `slug`.
- **Slug rules**: invalid format → 422 `slug_invalid`; reserved → 422 `slug_reserved`; taken → 409 `slug_taken` (with a `suggestion` derived from the base, e.g. `lang-electric-2`). Slug editable only while never-published; after first publish → **409 `slug_immutable`** (Architect-specified error derived from §G-7).
- **`publish()` three-way website rule** (§B.2/§G-16): (1) profile `website IS NULL` → set to `https://{slug}.{TENANT_SITES_BASE_DOMAIN}`, `website_action='set'`; (2) `website_auto_populated = TRUE` → refresh silently, `website_action='kept'`; (3) tenant-entered URL present and `confirm_website_overwrite=False` → raise 409 `website_overwrite_requires_confirmation` with an RFC 7807 detail payload carrying `current_url`, `new_url`, and `brand_status`; with `=True` → overwrite, set `website_auto_populated=TRUE`, `website_action='overwritten'`.
- **Publish validation** (§D-4): no site row/draft → 409 `no_draft`; missing any of `display_name`, (`public_phone` OR `public_email`), `public_city`, `public_state` → 422 `missing_required_fields` listing the missing fields. Re-publish regenerates the snapshot from the current draft (idempotent).
- **Brand classification** (`classify_website_action`): read the tenant's latest `tenant_messaging_registration` row (read-only). Buckets per §G-17: no row / `draft`-family → `none_or_draft`; submitted/vetting/pending-family → `in_flight`; `brand_rejected` → `brand_rejected`; active/approved/campaign-live-family → `live`. **Verify the actual status literals** against the C-B9 state machine (design doc + registration service code + your MCP query #4) — do not invent status strings.
- **Unpublish** (§G-8): sets `status='unpublished'` + `unpublished_at`; **never clears `website`**; returns a `warning` string — escalated when the brand classification is `live` and `website` currently points at our hosted URL.
- **Entitlement** (§G-4): service-layer `site_kind` check defaulting to allow; `starter_site` is not in the CHECK constraint yet — if a payload requests it, reject with 422 `slug_invalid`-style RFC 7807 error (`site_kind_unsupported`). No Stripe, no feature_code.
- **Env var**: read the base domain from settings — add `TENANT_SITES_BASE_DOMAIN: str = "localhost:3000"` to the settings module (find it via the SENDGRID grep) and add a line to the repo-root `.env.example`. Never hardcode the domain.

Intermediate test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`.

---

## Task 4 — Authenticated Router + `main.py` + Profile-PUT Hook

**New file `backend/api/routes/tenant_site.py`** — 5 endpoints + 3 `/test` twins (house `_impl` + twin pattern per `quotes.py` precedent; read `tenant_10dlc_profile.py` for RBAC):

| # | Method & Path | RBAC | Notes |
|---|---|---|---|
| 1 | `GET /api/v1/tenant-site` | `require_permission("settings.view")` | `{configured: false, defaults}` when no row — never 404 |
| 2 | `PUT /api/v1/tenant-site` | `require_permission("settings.manage")` + Idempotency-Key | Upsert draft via `upsert_draft`; honors `Idempotency-Key` header (24h TTL) via the house pattern you found in Pre-Work grep; natural-key fallback = `UNIQUE(tenant_id)` upsert + partial unique index |
| 3 | `GET /api/v1/tenant-site/slug-availability?slug=` | `require_permission("settings.view")` | 422 when `slug` param missing |
| 4 | `POST /api/v1/tenant-site/publish` | `require_permission("settings.manage")` + Idempotency-Key | Body `PublishRequest`; returns `PublishResponse` |
| 5 | `POST /api/v1/tenant-site/unpublish` | `require_permission("settings.manage")` + Idempotency-Key | Returns `UnpublishResponse`; 409 `not_published` |
| 6 | `/test` twins of 2, 4, 5 | `get_test_context()` | Unauthenticated house test pattern; 403 when test context disabled |

- Every mutation: `set_audit_context_sync(db, user_id=current_user.id)` first; sync `def`; `response_model`; RFC 7807 errors.
- **Option-1 email trigger (b)** (§G-19): in the PUT `_impl`, when the saved `site_kind` is `compliance_kit`, a `tenant_10dlc_profile` row exists, and `requirements_emailed_at IS NULL` → enqueue `send_website_requirements_email.delay(str(tenant_id))` and, on successful enqueue, stamp `requirements_emailed_at = now()` on the profile AND `kit_sent_at = now()` on the site row.

**`backend/app/main.py`** — two `include_router` lines only: `tenant_site.router` at `/api/v1/tenant-site` (adjacent to `tenant_10dlc_profile`, ~line 278) and `public_tenant_sites.router` at `/api/v1/public/tenant-sites` (adjacent to `public_charter`, ~line 367). **Do not touch CORS** (§G-12).

**Profile-PUT hook** (`backend/api/routes/tenant_10dlc_profile.py` — EDIT, surgical): in the PUT `_impl`, after a successful update where `website` changed:

1. Call `tenant_site_service.on_profile_website_changed(db, tenant_id, new_value)` — when the new value is non-empty and NOT a Pilot-hosted URL (`*.TENANT_SITES_BASE_DOMAIN`), flip `website_auto_populated = FALSE` on the tenant's site row if one exists (§G-18 reconciliation).
2. **Email trigger (a)** (§G-19): when the new value is non-empty and non-Pilot and `requirements_emailed_at IS NULL` → enqueue the requirements email and stamp `requirements_emailed_at` on successful enqueue.

Do not break any C-B9 behavior — the profile endpoint's existing tests must stay green.

Intermediate test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`.

---

## Task 5 — Public Router (design §D-7)

**New file `backend/api/routes/public_tenant_sites.py`**:

```python
@router.get("/{slug}", response_model=PublicTenantSiteResponse)
@limiter.limit("60/minute")
def get_public_tenant_site(request: Request, slug: str, db: Session = Depends(get_db)):
    ...
```

- **No JWT, no `get_current_user`.** Follow the `public_charter.py` precedent + the `marketing.py` SlowAPI limiter pattern (note the `request: Request` param SlowAPI requires).
- Serve from `get_published_snapshot(db, slug)` — returns the snapshot only when `status='published'`.
- **404 `site_not_found` (RFC 7807) for unknown slug AND for draft/unpublished** — no existence leak (§D-7).
- **Redis cache, 300s TTL**, key `tenant_site:pub:{slug}`: reuse the existing Redis client/cache pattern you found in Pre-Work (maps caching). If a general cache pattern exists, follow it; otherwise use a module-level `redis.Redis` client built from the existing Redis URL setting, **DB 0** (the ephemeral/rate-limit DB — do not create a new DB partition without Architect review), with the exact key prefix above. **Cache must be fail-open**: on any Redis error, serve from Postgres and continue — the public endpoint must never 5xx because Redis is down. Cache only published snapshots; never cache 404s longer than the 300s TTL.
- **Cache invalidation**: on publish/unpublish (Task 4 routes), best-effort `DELETE tenant_site:pub:{slug}` so republishes propagate immediately.

Intermediate test run: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`. **This is the natural two-session checkpoint if needed** (all routes live after this task).

---

## Task 6 — Celery Email Task (design §F / §G-19)

**New file `backend/tasks/tenant_site_emails.py`** — two-layer pattern (business logic testable without a worker):

```python
def _send_website_requirements_email_impl(tenant_id: str, db: Session) -> dict:
    """Pure logic — injected Session. Sends via SendGrid. Returns {"sent": bool, "reason": str}."""

@celery_app.task
def send_website_requirements_email(tenant_id: str) -> dict:
    """Celery entry point — creates its own session, calls _impl. No business logic here."""
    with next(get_db()) as db:
        return _send_website_requirements_email_impl(tenant_id, db)
```

- **SendGrid** send following the `tasks/marketing_notifications.py` dedicated-task precedent (client location from your SENDGRID grep). **No `notification_outbox`** — tenant-optional FK pattern per design §F.
- Body: the website-requirements summary content + the Requirements Guide PDF link (`https://app.pilotfortrades.com/resources/tenant-website-requirements-v1.pdf`) +, when profile data exists, the pre-merged Privacy/Terms kit text (rendered from the same `v1/` templates with the tenant's effective defaults — single content path).
- **One-time guard lives at the enqueue sites** (Task 4) — the task itself re-checks `requirements_emailed_at IS NULL` defensively and returns `{"sent": False, "reason": "already_emailed"}` when stamped (race safety).
- No Beat schedule. No resend endpoint.

---

## Task 7 — Seed Data Rollout (Rule 11.5 — MANDATORY)

Per `backend/README-seed-data.md` — you read §3, §6, §7 in Pre-Work.

### Layer 1 — Core / Platform values (Group A / B)

**None** — no lookup tables; `site_kind`/`status` are CHECK-constrained text (consistent with the `tenant_messaging_registration` no-lookup precedent); templates are code-resident.

### Layer 2 — Scenario data (Group D)

Extend the scenario seed set (find where the primary demo tenant's 10DLC profile is seeded — your `tenant_10dlc` test-domain grep and the seed scripts; prefer extending that script, otherwise create `seed_scenario_tenant_site.py` and register it in the run order per README §6):

- **(a)** one **published** `hosted_compliance` row for the primary demo tenant — complete `published_snapshot` (build it by calling `build_snapshot()` from the service with the seeded draft data, so the snapshot shape can never drift from the renderer) — enables local smoke-testing of the public pages at `{slug}.localhost:3000`;
- **(b)** one **draft** `compliance_kit` row for a second seed tenant.

`tenant_site` has `UNIQUE(tenant_id)` → `INSERT ... ON CONFLICT DO NOTHING` is sufficient; **no DELETE** (Rule 11.1 value-scoping not triggered). Look up FK values by business key at runtime — never hardcode a `gen_random_uuid()`-generated scenario UUID. `StandardAuditMixin` tables need explicit `created_at, updated_at = NOW(), NOW()` in raw-SQL inserts.

### Verification

- After seeding: `python migrations/scripts/seed_core.py --mode inspect` (core rows present) + run the affected scenario seed twice → idempotent (no dupes).
- Run `pytest -m unit` after the seed change — a seed row a test doesn't expect will break tests (README §7 shared-DB rule). Fix any seed-resilience failures (assert-by-ID, never by count).

### README update

- Update `backend/README-seed-data.md` §4 (Current Seed State) with the new `tenant_site` rows/fields.

---

## Task 8 — Tests

Write the full test suite per the Test Requirements section below. Minimum coverage (from design §I):

1. **Slug validation**: bad format → 422 `slug_invalid`; reserved (`www`, `admin`, `pilot`, …) → 422 `slug_reserved`; taken → 409 `slug_taken` (+`suggestion`); availability endpoint happy path.
2. **GET**: no row → `{configured: false, defaults}` (never 404); defaults merged from profile (`dba_name`→display_name, `support_email`→public_email, `hq_city`/`hq_state`; street never defaulted); row present → full config + computed `site_url`.
3. **PUT upsert**: creates draft; Idempotency-Key replay returns the same row (no dup); slug change after publish → 409 `slug_immutable`.
4. **Publish**: missing required fields → 422 `missing_required_fields`; no draft → 409 `no_draft`; website NULL → set + `website_action='set'` + `website_auto_populated=TRUE`; ours → silent refresh (`kept`); tenant-entered → 409 `website_overwrite_requires_confirmation` carrying `current_url`/`new_url`/`brand_status`, then `confirm_website_overwrite=true` → `overwritten`; re-publish regenerates snapshot.
5. **Brand classification**: insert registration rows in each status family → correct `brand_status`/`brand_guidance` bucket (use `second_tenant`/explicit inserts — never mutate shared seed rows).
6. **Unpublish**: 409 `not_published` when draft; success sets `unpublished_at`, leaves `website` intact, returns `warning`.
7. **Public endpoint**: unknown slug → 404 `site_not_found`; draft/unpublished → 404 (no existence leak); published → whitelisted payload with `pages`; address fields present only when `show_full_address=TRUE`; no auth header needed.
8. **One-time email guard**: profile PUT with self-managed URL enqueues once (patch the task's `.delay`), stamps `requirements_emailed_at`; second PUT does not re-enqueue; Option-1 selection trigger enqueues + stamps `kit_sent_at`; `on_profile_website_changed` flips `website_auto_populated` FALSE on non-Pilot URL.
9. **Cross-tenant isolation** (`tenant_a`/`tenant_b`): GET/PUT/publish never see or modify the other tenant's site.
10. **RBAC**: `settings.view` required for GET (403 without), `settings.manage` for PUT/publish/unpublish — follow the existing settings-route test pattern.
11. **Celery `_impl`**: call `_send_website_requirements_email_impl` directly with `db_session` (never `.delay()`/`.apply()` in unit tests); mock the SendGrid client per the marketing-notifications precedent; assert the already-emailed defensive guard.
12. **Seed idempotency**: run the scenario seed twice → no duplicate `tenant_site` rows for the seeded tenants.

Intermediate test run after each group: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`.

---

## Regeneration + Schema Steps

Run all four (order matters):

```bash
cd <repo>/backend
source .venv/bin/activate

# 1. DB model map (Rule 2) — stdout redirect + explicit dir arg
python generate_db_model_map.py app > db_models_map.md
grep "TenantSite" db_models_map.md        # must appear under DB Tables

# 2. App model import map (new test files added)
python generate_app_import_map.py tests > app_model_imports.md

# 3. OpenAPI (Rule 3)
python export_openapi_json.py
grep -A 5 "tenant-site" openapi_schema_map.md
grep -A 5 "public/tenant-sites" openapi_schema_map.md
```

**Schema JSON sync** — update `dev-docs/db-design/pilot-db-schema-v2.6h.json` via `backend/schema_manager.py` (read `backend/README-schema_manager.md` first). Dot-notation `--path` traversal only — verbs `get`/`set`/`delete`/`array-append`/`array-remove`/`array-update`; complex values via `--payload <file.json>` (temp file, then `rm`). Add the full `tables.tenant_site` definition (columns, check constraints, indexes, trigger) and `tables.tenant_10dlc_profile.columns.requirements_emailed_at`. **NEVER edit the JSON with `sed`/`awk`/inline Python.** If `schema_manager.py` errors → STOP, quote the exact command + error, ask Tom.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/<your-domain-folder>/ -v 2>&1 | tail -20
grep -A 5 "tenant-site" openapi_schema_map.md

echo "=== C-B16 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` reports zero remaining issues **in your changed files** (no unjustified `# noqa`), and the pytest run is free of `DeprecationWarning` noise. **Do not run `ruff check .` against the entire codebase.** Any failure in either phase must be fixed before the batch is declared done — there is no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`. **Domain folder**: co-locate with the existing `tenant_10dlc` / messaging tests if your Pre-Work grep found them (likely `notifications_comms/`); otherwise use `platform_infrastructure/` (platform settings). Confirm the exact marker name (`pytest.mark.domain_<domain>`) against `README-adding-tests.md` / `pyproject.toml` before writing.
- Use the `client` fixture (never module-level `TestClient`).
- Use `test_tenant` / `test_user` / `second_tenant` / `tenant_a` / `tenant_b` fixtures — never hardcoded UUIDs.
- Scope assertions by inserted IDs — never `assert len(all_rows) == N` (seed data makes total counts unpredictable).
- **Test Resilience Rule**: never UPDATE/DELETE rows you did not INSERT; never assert total row counts; never assume a table is empty (use `second_tenant` for empty-state); the `db_session` fixture's transaction rollback is the cleanup mechanism.
- **Autouse fixtures** already handle Cognito JWKS, AI services, and entitlement bypass. This batch's entitlement check defaults to allow (§G-4) — no `skip_mock_entitlement_allowed` needed unless you explicitly test a denial path.
- **Sync-by-Design (rules §21)**: every route/`_impl()`/service touching the `Session` is `def` (sync). The public route is sync too (SlowAPI works with sync handlers — see `marketing.py`). `async def` only for handlers that exclusively await non-blocking I/O and never touch the `Session` — none in this batch.

---

## Definition of Done — C-B16 Part A

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 6 MCP pre-work queries run — `website` text NULL confirmed; `tenant_site` absent pre-migration / present post-migration with 25 columns; `requirements_emailed_at` added; `set_updated_at` function + both triggers confirmed; alembic head recorded; every touched table verified via `information_schema.columns` (rules §25)
- [ ] All mandatory source files read before writing any code (including `api/schemas/` 10dlc file)
- [ ] Task 1: blank migration (DDL-only), full upgrade/downgrade/upgrade cycle passes
- [ ] Task 2: `TenantSite` model (StandardAuditMixin, explicit `tenant_id`, JSONB snapshot) + barrel export + all schemas in `api/schemas/tenant_site.py`
- [ ] Task 3: `v1/` template set (all six SMS clauses in privacy + terms) + renderer + `tenant_site_service.py` with the full §F interface
- [ ] Task 4: 5 authed endpoints + 3 `/test` twins + `main.py` registration (2 lines) + profile-PUT hook (reconciliation + email trigger a) + Option-1 trigger (b)
- [ ] Task 5: public endpoint — SlowAPI 60/min, fail-open Redis cache (300s, `tenant_site:pub:{slug}`, DB 0), 404 `site_not_found` for unknown AND non-published
- [ ] Task 6: `tasks/tenant_site_emails.py` two-layer task, SendGrid send, defensive already-emailed guard
- [ ] Task 7: seed rollout (published hosted_compliance + draft compliance_kit, idempotent) + README-seed-data.md §4 updated
- [ ] Task 8: all 12 test groups written and green
- [ ] All DB-touching routes/`_impl()` are sync `def` — no `async def` on the blocking `Session` (rules §21)
- [ ] Only Pydantic v2 idioms; every new route has `response_model`; money N/A (no money fields in this batch)
- [ ] `set_audit_context_sync()` called at the start of every mutation endpoint
- [ ] All new API errors follow RFC 7807 Problem Details format (incl. public 404)
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`; no module-level `TestClient`; fixtures only (no hardcoded UUIDs)
- [ ] `TENANT_SITES_BASE_DOMAIN` added to settings + `.env.example` (dev default `localhost:3000`); domain never hardcoded
- [ ] `python generate_db_model_map.py app > db_models_map.md` + `python generate_app_import_map.py tests > app_model_imports.md` run
- [ ] `schema_manager.py` used (path-based `--path`/`--payload`) for `tables.tenant_site` + `requirements_emailed_at` — JSON never edited directly
- [ ] `python export_openapi_json.py` run — both `openapi.json` and `openapi_schema_map.md` updated; new endpoints visible in the map
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues, no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration tests, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix C
- [ ] Source spec task headers updated (README-seed-data.md §10 if it tracks a C-B16 item)

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C** using the exact format below.
2. If this batch closes tasks tracked in another source spec (e.g., `README-seed-data.md` §10), update those task headers to ✅ Complete BEFORE declaring the batch done.

```markdown
### C-B16 (Part A) — Pilot-Hosted Tenant Sites (Backend): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [tenant_site table + migration; model/schemas; template set + service; 5 authed endpoints + /test twins; public endpoint; Celery email; seed rollout]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated — [what changed] |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/<domain>/test_tenant_site_*.py` | `<domain>` | N | ✅ |
```

---

## After This Task — Next Step (Handoff to Part B — Rule 9.3, MANDATORY)

This is a **mixed batch** (Rule 1.3). Part A runs first; Part B cannot start until the API contract is regenerated:

1. Ensure `python export_openapi_json.py` has been run and **`backend/openapi.json` + `backend/openapi_schema_map.md` are committed**.
2. Commit all Part A work.
3. **Notify the React Engineer (Tom) that Part A is merged** — Part B (`batch-c-b16-react-engr-prompt.md`) opens with `cd frontend && pnpm sync-api-types` to regenerate `packages/shared-types/src/api-schema.d.ts` from your new endpoints. Both UI specs are already Tom-approved (2026-08-14), so no design gate remains.
4. The Architect-owned Requirements Guide markdown/PDF (design §G-20) is delivered separately — the email task links to `https://app.pilotfortrades.com/resources/tenant-website-requirements-v1.pdf` regardless; if the asset is not yet committed when you finish Task 6, note it in your Completion Summary (the link target is Part B's static-asset step).
