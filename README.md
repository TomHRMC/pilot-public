# Pilot for Trades

**AI-Powered Field Service Management for Electrical Contractors**

Pilot for Trades was built as a SaaS platform for small electrical contractors (1-10 employees), featuring voice-controlled quoting, real-time job profitability, QuickBooks two-way sync, and Stripe payments. This monorepo contains the complete software stack — the FastAPI backend, Next.js web and Expo/React Native mobile apps, the local AI pipeline, and the Terraform-provisioned AWS infrastructure.

---

> ## 📌 Public snapshot — read this first
> This repository is a **capability demonstration** — the launching pad for **HotRMC**, Tom Lang's fractional-CTO practice. It is a **curated, public snapshot** of *Pilot for Trades*, a personal **R&D build** he architected **solo, AI-augmented, in ~6 months of full-time build** to prove a delivery method on a real, hard problem. The product is the **vehicle, not the offer**: it was **never released and has no customers** (hibernated on purpose at a founder-ready gate), its technical design follows the **SOC 2 security criteria — built to the controls, not audited** (never certified or compliant), and it is **not a product for sale** — source-available, view-only ([`LICENSE`](LICENSE)). What it *is* is proof that one experienced architect, wielding AI with real guardrails, delivers engineering built to production standards at a fraction of the usual time and cost.
>
> **Start here:** [`WHY-THIS-EXISTS.md`](WHY-THIS-EXISTS.md) · [`PROVENANCE.md`](PROVENANCE.md) · [`METHOD.md`](METHOD.md) · [`AI-PITFALLS.md`](AI-PITFALLS.md)

## Project Vision

Pilot for Trades eliminates the administrative burden for electricians by providing:
- **Voice AI Quoting** - Create quotes hands-free while on-site
- **Real-Time Profitability** - Track job costs vs. revenue in real-time
- **QuickBooks Sync** - Bidirectional customer/invoice synchronization
- **NEC Calculations** - Voltage drop, conduit fill, and ampacity from NEC 2023 tables — mobile calculator screens, a REST endpoint, and voice commands (design in [`mvp-arch.md`](dev-docs/architecture-design/mvp-arch.md) §6.8.1)
- **Mobile-First UX** - Designed for field technicians, not office staff

**Target Market:** 1-10 employee electrical contractors generating $500K-$2M annually

---

## Repository Structure

```
pilot-public/
├── backend/                  # FastAPI API + Celery workers (Python 3.14)
│   ├── api/                  # Routes & request/response schemas
│   ├── app/                  # SQLModel DB models + main.py (FastAPI entrypoint)
│   ├── core/                 # Auth, config, db, encryption, permissions, middleware
│   ├── lambda/               # Cognito trigger Lambdas (post-confirmation, post-auth, custom email sender)
│   ├── migrations/           # Alembic versions + environment-aware seed scripts
│   ├── scripts/              # Ops scripts (Stripe bootstrap, maintenance broadcast, etc.)
│   ├── services/             # Business logic (AI, email, QuickBooks, SMS, Stripe, voice actions)
│   ├── tasks/                # Celery background tasks
│   ├── tests/                # Pytest suite (~4,950 test functions)
│   └── README.md             # Backend development workflow
│
├── frontend/                 # pnpm + Turborepo monorepo
│   ├── apps/web/             # Next.js (App Router) office/admin web app
│   ├── apps/mobile/          # Expo / React Native field app (iOS/Android)
│   ├── apps/marketing/       # Next.js static-export marketing site
│   ├── packages/             # Shared UI, API client, OpenAPI-generated types, lint/TS configs
│   └── README.md             # Frontend setup & monorepo guide
│
├── infrastructure/           # Terraform IaC — networking, compute, database, security, storage, monitoring
│   └── scripts/              # Ops / cost-profile scripts (incl. hibernation + restart)
│
├── admin-tools/              # Schema backup & diff automation
│
├── dev-docs/                 # Design, decisions, prompts, runbooks — see Documentation Index below
│   ├── analysis/             # Delivery & governance synthesis
│   ├── architecture-design/  # MVP architecture, ADR log, batch designs, UI prototypes
│   ├── db-design/            # PostgreSQL schema v2.6h + schema-sync/audit toolchain
│   ├── devops/               # AWS as-built, ops runbook, environment management
│   ├── diligence/            # Due-diligence pack (proof, security, quality, limitations)
│   ├── implementation-prompts/ # The AI engineers' batch prompts (~340)
│   ├── integrations/         # Stripe, QuickBooks/Intuit, Telnyx
│   ├── product-requirements/ # PRD + historical roadmap
│   ├── sdlc/                 # Git workflow, repo SDLC, LLM model strategy
│   ├── seed-data/            # Seed-data analysis & decisions
│   ├── testing-support/      # Test plans, QA results, alpha-testing findings
│   ├── visuals/              # Proof infographics (self-contained HTML)
│   └── wikis/                # LLM-wiki methodology
│
├── .github/workflows/        # CI/CD: production deploy (incl. the marketing site), Playwright E2E (OIDC; nightly schedule paused)
├── .roo/  ·  .roomodes       # Roo Code agent modes & rules — the AI "team"
├── WHY-THIS-EXISTS.md · PROVENANCE.md · METHOD.md · AI-PITFALLS.md
├── pilot-docs-list.md        # Full documentation index
├── docker-compose.yml        # Local stack (Postgres, Redis, Celery, Ollama, Whisper)
├── docker-compose.e2e.yml    # Isolated E2E stack
├── LICENSE
└── README.md                 # This file
```

---

## Running it

This public snapshot is a **curated subset** of the private original and has not been tested to run from a clean clone. The private original ran as a Docker Compose stack (PostgreSQL 17 + pgvector, Redis, Celery worker + beat, Ollama with Llama 3.1 8B, and Faster-Whisper large-v3-turbo) alongside the FastAPI backend and the pnpm/Turborepo frontend. Setup notes are kept for reference in [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md).

Toolchain at hibernation: Python 3.14 in the application image (CI test jobs ran on 3.12), Node.js 20 with pnpm (Next.js 16 requires Node 20+), Docker Desktop.

---

## Documentation Index

### Start here
- **[Why This Exists](WHY-THIS-EXISTS.md)** · **[Provenance](PROVENANCE.md)** · **[Method](METHOD.md)** · **[AI Pitfalls](AI-PITFALLS.md)**
- **[How the Work Was Planned, Governed, and Verified](dev-docs/analysis/Pilot-Delivery-and-Governance.md)**
- **[Proof Infographics](dev-docs/visuals/)** - Delivery method, unit economics, governed delivery, guardrails *(self-contained HTML — download and open in a browser)*

### Due-Diligence Pack
- **[Diligence README](dev-docs/diligence/README.md)** - Index of the pack
- **[Measured Scale and Coverage](dev-docs/diligence/Pilot-for-Trades-Proof.md)** - Measured scale, tests and coverage
- **[Security Architecture](dev-docs/diligence/Pilot-Security-Architecture.md)** · **[Compliance by Design](dev-docs/diligence/Pilot-Compliance-by-Design.md)**
- **[Code Quality Assessment](dev-docs/diligence/Pilot-Code-Quality-Assessment.md)** · **[Database Assessment](dev-docs/diligence/Pilot-Database-Assessment.md)**
- **[Operations & Resilience](dev-docs/diligence/Pilot-Operations-and-Resilience.md)** · **[Known Limitations](dev-docs/diligence/Pilot-Known-Limitations.md)**

### Architecture & Decisions
- **[Architecture Diagrams](dev-docs/architecture-design/diagrams/README.md)** - Six views of the as-built system and its enterprise path; start with the one-page [maturity map](dev-docs/architecture-design/diagrams/06-enterprise-maturity-map.md)
- **[MVP Architecture](dev-docs/architecture-design/mvp-arch.md)** - Complete system architecture (AWS, services, data flow)
- **[ADR Log](dev-docs/architecture-design/pilot-adr-log.md)** - 21 architecture decision records
- **[Architect Methods](dev-docs/architecture-design/pilot-architect-methods.md)** - How the AI architect role operated
- **[Batch Designs](dev-docs/architecture-design/batch-designs/)** - Per-batch design docs with scope, exclusions, exit criteria
- **[Test Endpoints Architecture](dev-docs/architecture-design/archived/test-endpoints-architecture.md)** *(archived)* - The `/test` endpoint pattern

### Data
- **[Database Schema v2.6h](dev-docs/db-design/pilot-db-process-v2.6h.md)** - PostgreSQL 17 multi-tenant schema ([JSON blueprint](dev-docs/db-design/pilot-db-schema-v2.6h.json))
- **[Schema Sync & Audit Toolchain](dev-docs/db-design/db-schema-sync-archive/README.md)** - Tenant-isolation, FK-index, and deletion-pathway audits

### Product
- **[MVP PRD](dev-docs/product-requirements/mvp-prd.md)** - Product requirements document
- **[Product Roadmap](dev-docs/product-requirements/pilot-product-roadmap.md)** *(historical snapshot, June 2026 — the roadmap was last revised then; later work was tracked in the private launch plan)*

### DevOps & Integrations
- **[AWS Infrastructure As-Built](dev-docs/devops/aws-infrastructure-as-built.md)** · **[AWS Ops Runbook](dev-docs/devops/aws-ops-runbook.md)** (incl. restart from hibernation)
- **[Stripe Ops Runbook](dev-docs/integrations/stripe/stripe-ops-runbook.md)** · **[QuickBooks Coverage Matrix](dev-docs/integrations/quickbooks/qb-coverage-matrix.md)** · **[Telnyx 10DLC Platform Campaign](dev-docs/integrations/telnyx/telnyx-10dlc-p4t-tenant-comms-campaign.md)**

### AI-Augmented Delivery
- **[Implementation Prompts](dev-docs/implementation-prompts/)** - The batch prompts the AI engineers executed
- **[Architect Session Startup Prompt](dev-docs/implementation-prompts/README-architect-session-startup.md)** - How each architect session was kicked off
- **[LLM Wiki Methodology](dev-docs/wikis/pilot-wikis-plan.md)** - Token-efficient knowledge bases for the AI agents
- **[Repo SDLC](dev-docs/sdlc/repo-sdlc.md)** - Branching, git workflow, and release discipline

### Testing
- **[Beta Test Plan](dev-docs/testing-support/beta-test-plan.md)** - Manual test protocol from owner self-test to external beta

For the complete list of documents, see **[`pilot-docs-list.md`](pilot-docs-list.md)**.

---

## Testing

### Run Backend Test Suite
```bash
cd backend
source .venv/bin/activate

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_quotes.py -v

# Run with coverage (measures api, app, core, services, tasks per .coveragerc)
pytest --cov --cov-report=html
```

**Test status:** ~8,000 automated tests in total — ~4,950 backend test functions + ~3,070 frontend test cases — grown under a zero-regression ratchet. On the last recorded full run (2026-10-13) both frontend suites were fully green (2,307 web + 701 mobile tests executed; the source counts above are approximate and count `it`/`test` calls, so parametrized and skipped cases make the two differ) and the backend had a small number of known failures, left unfixed at hibernation.

**Measured coverage (2026-10-13):** backend 76% line+branch, web ~71% lines, mobile ~75% lines — see the [backend](dev-docs/testing-support/backend-coverage-report-2026-10-13.md) and [frontend](dev-docs/testing-support/frontend-coverage-report-2026-10-13.md) coverage reports.

### Test Categories
- **Backend:** ~4,950 test functions (API routes, models, business logic) plus a dedicated integration suite.
- **Frontend:** ~3,070 test cases across web, mobile, and marketing (Vitest / Jest + MSW).

---

## Technology Stack

### Backend
- **Framework:** FastAPI 0.135 (Python 3.14)
- **Database:** PostgreSQL 17 with pgvector + HNSW indexes
- **ORM:** SQLModel on SQLAlchemy 2.0 (Pydantic models)
- **Background Jobs:** Celery + Redis broker
- **Authentication:** AWS Cognito (RS256 JWTs verified via JWKS) + MFA; server-authoritative RBAC
- **Migrations:** Alembic
- **Testing:** Pytest + httpx.AsyncClient

### AI Pipeline (Local)
- **Speech-to-Text:** Whisper large-v3 on the AWS GPU; large-v3-turbo in local dev (Faster-Whisper server)
- **Intent Parsing:** Llama 3.1 8B (via Ollama)
- **Vector Search:** pgvector (conversation context windows)
- **Cost:** no per-request inference fees; fixed cost of one EC2 g4dn.xlarge GPU instance
- **External AI:** none on customer audio or job data; the one external AI call is OpenAI embeddings for indexing Pilot's own help articles (`tasks/help_corpus.py`); voice previews use gTTS (a Google service) on fixed sample text, with an optional OpenAI TTS path

### Frontend
- **Monorepo:** pnpm workspaces + Turborepo
- **Web:** Next.js (App Router) + Tailwind CSS + shadcn/ui
- **Mobile:** Expo / React Native + gluestack-ui (iOS/Android)
- **Marketing:** Next.js static export
- **Data:** TanStack Query + shared API client; types generated from the backend's OpenAPI schema
- **Forms:** mostly hand-rolled React state; React Hook Form + Zod installed, migration pending
- **Testing:** Vitest / Jest + MSW; Playwright E2E

### Infrastructure (AWS)
- **Cloud:** AWS (ECS Fargate, RDS Multi-AZ, ElastiCache)
- **GPU Compute:** EC2 g4dn.xlarge (NVIDIA T4) for Voice AI
- **IaC:** Terraform (networking, compute, database, security, storage, monitoring modules)
- **CI/CD:** GitHub Actions with OIDC — production deploy (ECS rolling with circuit-breaker rollback; Trivy secret scan; it also deploys the marketing site), Playwright E2E workflow (nightly schedule paused at hibernation)
- **Cost target:** ~$888/month modelled infrastructure cost at 100 customers (design target, under a $1,000 cap) — ~$8.88/customer; ~94% infrastructure margin at the $149 Teams-annual price (~82–85% at the $49–$59 tiers), before payment and SMS fees

### Integrations
- **Accounting:** QuickBooks Online two-way sync (OAuth 2.0 + webhooks, conflict handling)
- **Email:** SendGrid (transactional + Cognito custom-email-sender Lambda)
- **SMS:** Telnyx (10DLC campaign approved under the brand; real texts delivered to the author's own phone); MFA OTP via AWS SNS toll-free
- **Payments:** Stripe Connect (Express, direct charges) + Stripe Billing (trial + usage-metered) — test mode end-to-end; live mode configured but never took a real customer payment
- **Calendar:** Google Calendar two-way sync (OAuth 2.0; scheduled jobs pushed as events, outside events pulled in as technician unavailability)
- **Other:** Cloudflare Turnstile (bot protection), Google Maps, Expo push, AWS Cognito, OpenAI embeddings (help articles only)

---

## Project Status

This is a **personal R&D build, deliberately hibernated pre-launch** (Sept 2026). It was carried to a **Charter / founder-ready state** and then paused — it never onboarded a paying customer, by design (founders were to be the beta). The summary below is where the build actually landed.

**Built, gated, and closed:**
- **Multi-tenant core** — AWS Cognito auth + MFA, server-authoritative **RBAC**, tenant-scoped data isolation (application-enforced), **audit event logging**, **rate limiting** on selected public routes, idempotency middleware.
- **Application suite** (web + React Native/Expo mobile) — customers, versioned quotes, jobs + real-time profitability, invoices + AR aging, dispatch board, recurring jobs, catalog/pricebook, dashboards.
- **Payments — Stripe Connect** (Express, tenant direct charges) + metered platform billing — built and exercised end-to-end in test mode, including Connect onboarding; live mode was configured and validated (products and prices) but never took a real customer payment.
- **QuickBooks Online** two-way sync (OAuth, dedup/conflict handling) — coverage-audited and hardened.
- **Charter program** — self-serve signup, trial + usage-metered subscriptions, cohort cap, upgrade flow, operator/platform shell — **build sequence complete (Aug 2026)**.
- **Telephony/SMS** — Telnyx with a proven 10DLC carrier loop (campaign approved under the brand; real texts delivered to the author's own phone); per-tenant SMS-compliance microsites.
- **Voice-AI pipeline** — local Whisper + Llama intent parsing.
- **Infra/DevOps** — Terraform-provisioned AWS (ECS Fargate, RDS PG17, Redis, GPU, ALB, Cognito); locally, Docker Compose for the supporting services, with the API run under `uvicorn`; on AWS, the same backend image in one long-lived environment built to production spec, which served as QA and production candidate (a separate QA stack was deployed once, tested, and torn down to avoid doubling cost); GitHub Actions CI with OIDC; Playwright E2E workflow.
- **Tests** — grew to **~8,000 automated tests** (~4,950 backend + ~3,070 frontend) under a zero-regression ratchet; measured coverage 76% backend / ~71% web / ~75% mobile (2026-10-13).

**Carried to a founder-ready state, then deliberately hibernated.** A formal Founder Launch Gate governs first-founder onboarding. Engineering was complete except three open items (below); the gate's remaining rows were go-to-market ops — live-mode Stripe bootstrap audit, App Store / Play store binaries, a full prod E2E pass, recruiting the first 3–5 Charter founders — deferred on purpose, not left undone. The open engineering items: the **mobile offline-sync layer (~70%, mid-integration)** — its design is complete and the on-device store and sync engine are built, but finishing the local-DB migrations, wiring the foreground sync path, and adding real sync-engine tests remain outstanding (more code and more tests to write); plus an owner-MFA-reset escape hatch and a mobile UX up-design.

**Then: intentional hibernation (Sept 2026).** The AWS stack was torn down to a near-zero-cost static hold page. Restarting is about one day of runbook work; allow about a week of calendar time for a demo-ready environment. The project is restartable — paused, not abandoned.

> **Honest framing:** this is a lab that proves a delivery *method*, not a shipped product — built to production standards, never operated in production. Built to the SOC 2 security criteria, never audited; it never carried production traffic or real customer data.

---

## Security posture

### Data Protection
- **Encryption at Rest:** AWS RDS encryption (AES-256)
- **Encryption in Transit:** TLS 1.2+ (TLS 1.3 preferred) at the ALB
- **Token Encryption:** Fernet (symmetric encryption for OAuth tokens)
- **Passwords:** handled by AWS Cognito; legacy pre-Cognito auth tables remain in the schema, unused

### Multi-Tenancy Isolation
- **Tenant Scoping:** Tenant-owned tables carry a `tenant_id` column; isolation is enforced in the application/query layer (Postgres RLS is not enabled)
- **Query Filtering:** tenant-scoped routes filter on the caller's `tenant_id` (a final code read found a few route groups that don't — Known Limitations #27); public, webhook and signed-link routes are scoped by their own token or signature
- **Test Coverage:** Dedicated multi-tenancy isolation suite (`test_multi_tenancy_isolation.py`) plus tenant-scoping assertions across 16 tenant/isolation test files

### Timezone Handling ("Double-Lock" Standard)
- **Python:** All datetime fields use `AwareDatetime` (Pydantic)
- **Database:** All datetime columns use `TIMESTAMPTZ` (PostgreSQL)
- **Validation:** Naive datetime objects rejected at API boundary
- **Storage:** All times stored in UTC, converted to tenant timezone for display

### Compliance
- **GDPR:** a data-export engine is built (`services/data_export_compiler.py`); self-serve export/deletion endpoints and a DSAR workflow are not (hibernated pre-launch)
- **SOC 2 (design reference only):** technical design informed by the SOC 2 security criteria (audit event logging, encryption at rest and in transit, least-privilege access); no organizational controls — **not audited or certified**
- **PCI DSS:** Stripe handles all payment processing (no card storage); intended scope SAQ A or A-EP, no SAQ completed

---

## Development Principles

### 1. Cost-Optimized MVP (~$888/month design target, under a $1,000 cap)
- **Fargate-First:** ECS Fargate for every container workload — API, Celery, and the Next.js web app; no EKS control-plane tax ([ADR-0001](dev-docs/architecture-design/pilot-adr-log.md))
- **Shared GPU:** one g4dn.xlarge, sized on paper for up to ~500 customers (not load-tested)
- **Sub-Linear Scaling:** Fixed costs amortized across growing customer base
- **No third-party AI on customer data:** speech and intent run locally (Whisper + Llama) with no per-request inference fees; the one external AI call is OpenAI embeddings for indexing Pilot's own help articles

### 2. "Double-Lock" Timezone Standard
- **Never** store naive datetime objects
- **Always** use `AwareDatetime` (Pydantic) + `TIMESTAMPTZ` (PostgreSQL)
- **Test** timezone handling in every datetime-related test

### 3. Test Endpoints for Rapid Development
- Secured routes are paired with an env-gated `/test` variant (about 330 twins for about 340 secured operations at hibernation)
- **No JWT** required in development (TEST_ENDPOINT_ENABLED=true)
- **Faster** test iteration (~10-15s → <5s per test)
- **Blocked** in production (403 Forbidden)

### 4. Idempotency by Default
- **All** mutation endpoints (POST/PATCH/DELETE) support `Idempotency-Key` header
- **24-hour** response caching (prevents duplicate quotes, invoices)
- **Conflict detection** (409 Conflict if key reused with different payload)

### 5. Real-Time Profitability
- **Background workers** recalculate job costs on every time entry/expense
- **Database triggers** update quote/change order totals automatically
- **Designed to stay current** - dashboard totals are recalculated as entries change

---

## Contributing

This is a solo-built personal **R&D project** by Tom Lang, published as a read-only **proof / portfolio snapshot**. It is not accepting external contributions and is not a product in active development.

---

## License

**Source-available for evaluation and portfolio review only — all rights reserved.** See [`LICENSE`](LICENSE). This is **not** open-source software: no commercial use, redistribution, or derivative works without written permission.

---

## Contact

**Built by:** Tom Lang — HotRMC (fractional CTO)  
**Status:** Personal R&D build — hibernated (never released, not in active development)  
**Contact:** tom@hotrmc.com

---

## Additional Resources

- **Backend README:** [`backend/README.md`](backend/README.md) - Detailed development workflow
- **Database Schema:** [`dev-docs/db-design/pilot-db-schema-v2.6h.json`](dev-docs/db-design/pilot-db-schema-v2.6h.json) - Complete schema definition
- **API Documentation:** http://localhost:8000/docs (when FastAPI server is running)
- **Frontend README:** [`frontend/README.md`](frontend/README.md) - Monorepo setup and shared packages
- **Full Documentation Index:** [`pilot-docs-list.md`](pilot-docs-list.md)
