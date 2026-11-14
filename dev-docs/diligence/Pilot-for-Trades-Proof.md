# Pilot for Trades — Measured Scale and Coverage

> Figures were measured on the private original repository on 2026-10-08 (coverage on 2026-10-13). Code, schema and test counts can be re-checked against this public snapshot, within small curation deltas. Commit and timeline figures come from the private history; see [`../../PROVENANCE.md`](../../PROVENANCE.md) for what can and cannot be reproduced here.

---

## 1. What it is

Pilot for Trades is a field-service-management SaaS built for small electrical contractors (1–10 employees): voice-controlled quoting, scheduling/dispatch, real-time job profitability, invoicing and payments, customer comms (SMS/email), QuickBooks sync, and NEC 2023 calculations. It spans a FastAPI backend, a Next.js web app, a React Native mobile app, a marketing site, infrastructure-as-code, and a local AI/voice pipeline — a full-stack platform built to production standards, never operated in production. It was never released and has no customers.

---

## 2. The method

Built in **VS Code + the Roo Code extension** (continued on its community fork **Zoo Code** after the original team archived the open-source extension in May 2026), orchestrating **a minimum of 9 AI agents across 6 LLMs** (Gemini, Claude, Grok, ChatGPT, Kimi, GLM). The multi-agent workflow is checked into the repo: a `.roomodes` config defines **12 specialized agent roles**, each with its own rules directory:

`architect` · `orchestrator` · `python-engineer` · `react-engineer` · `qa-python-engineer` · `devops-engineer` · `integrations-lead` · `voice-ai-specialist` · `voice-ui-designer` · `web-ui-designer` · `marketing-ui-designer` · `electrical-domain-expert`

See [`../../METHOD.md`](../../METHOD.md) for how the roles, gates and guardrails fit together.

---

## 3. Scale

Categories are kept separate so each number can be checked on its own.

### Application code (AI-written, human-directed)
| Layer | LOC | Files |
|---|---:|---:|
| Backend (FastAPI: api, services, app, tasks, core, lambda, utils, admin) | ~100,200 | 266 |
| Frontend (Next.js web + marketing + React Native mobile; non-test) | ~146,400 | ~1,090 |
| Infrastructure as code (Terraform) | ~5,400 | 26 |
| **Application code total** | **~252,000** | **~1,380** |

### Supporting categories
| Category | Size | Note |
|---|---:|---|
| Automated tests | ~234,000 LOC; ~4,950 backend test functions + ~3,070 frontend test cases (≈8,000) | ~142K backend + ~92K frontend — a near-1:1 test-to-code ratio |
| Database migrations / seeds | 305 Alembic migrations (~390 files incl. seed scripts; ~66,000 LOC) | Categorized seed sets (core/platform/QA + scenarios: quote-to-cash, dispatch, mobile-sync, notifications) reset and re-populate the DB by category |
| Generated API-contract types (TypeScript from OpenAPI) | ~55,000 LOC | *Generated* from the OpenAPI spec, not authored |
| Design / architecture / analysis docs | 952 markdown docs in the private original (~680 in this snapshot) | AI-generated SDLC corpus |

### Data model
- **193 PostgreSQL tables**, spanning auth/MFA, multi-tenant, customers/contacts, quotes→jobs→invoices→payments, change orders, scheduling, communications/threading, integrations sync, NEC/catalog, help/RAG, and audit. Counts from `backend/scripts/schema_dump_20260907_082031.sql`: 697 foreign keys, 460 indexes, 471 triggers.

### Surface area
- **74 API route modules** / **~700 route operations** (~370 production endpoints + ~330 env-gated `/test` twins): customers, jobs, quotes, invoices, scheduling, dispatch, stripe_connect, calendar_integration, messaging, mobile_sync, mobile_push, reports, nec, help, audit, ….
- **3 frontend apps** (web, mobile/React Native, marketing) + **5 shared packages** in a Turbo monorepo.

---

## 4. Tests and coverage

- **~4,950 backend test functions** (~441 files) + **~3,070 frontend test cases** (web ~2,350 / mobile ~690 / marketing 31) ≈ **~8,000 automated tests** (source counts).
- The suite grew under a **zero-regression gate**: run summaries in the private task logs show `835 → 896 → 899 → 951 passed`, each tagged "+N new, 0 regressions." Early batch prompts set an 80% coverage target; it was not enforced as a CI gate.

**Measured backend coverage (2026-10-13)** — `pytest --cov` against current code, DB reinitialized and seeded ([report](../testing-support/backend-coverage-report-2026-10-13.md)):
- **76% combined line+branch coverage** (79.1% statement-level) over **26,455 statements**.
- **Strong:** data models 99.9%, API schemas 97%, API routes 81.5%, services 73%, core 78%; the money paths are well covered (quotes 83%, jobs 86%, invoices 84%, Stripe 76–88%).
- **Thin:** background tasks 56% (Celery workers), plus AI/voice helpers and third-party-integration shims (`ai_service` 14%, `help_agent` 14%, `voice_preview_audio` 0%, `telnyx_sms_carrier` 29%, `ocr_service` 24%, `quickbooks_sync` task 24%).
- The run had a small number of known failing tests, left unfixed at hibernation; coverage is reported independent of pass/fail.

**Measured frontend coverage (2026-10-13)** ([report](../testing-support/frontend-coverage-report-2026-10-13.md)):
- **Web (vitest):** 70.6% lines / 75.6% branch — **2,307 tests executed, all passing**.
- **Mobile (jest):** 75.4% lines / 65.9% branch — **701 tests executed, all passing**.

Coverage sits in a consistent **~71–76% band** across the three codebases. (The 3,008 frontend tests executed that day exclude the 31 marketing tests and a few cases added or skipped since; the ~3,070 figure above is a source count.)

---

## 5. Integration surface

Wired integrations, not stubs:
- **Payments — Stripe:** Connect, payment intents, subscriptions (platform billing + contractor payments). Built and exercised end-to-end in test mode, including Connect onboarding; live mode was configured and validated (products and prices) but never took a real customer payment.
- **Accounting — QuickBooks Online:** two-way sync with conflict diffing and connection notifications.
- **Calendar — Google Calendar:** OAuth 2.0 connection with two-way sync: scheduled jobs are pushed as events, and outside events are pulled in as technician unavailability (Celery tasks, with a sync log and conflict resolution).
- **SMS — Telnyx:** number provisioning, 10DLC, SMS carrier. An initial Twilio integration was replaced with Telnyx, which fit this project's 10DLC needs and budget better; remnants remain in the code.
- **Email — SendGrid.**
- **Auth — AWS Cognito:** user pools + MFA, with a mobile + web MFA enrollment wizard.
- **AWS — boto3:** S3 (file/photo storage), Lambda.
- **Mobile push — Expo:** built and tested via Expo; never submitted to the App Store or Google Play.
- **Local AI/voice pipeline — Ollama + Whisper:** voice action router (~5,200-line module), persona rendering, session + preview audio.
- **Bot protection — Cloudflare Turnstile; maps — Google Maps.**
- **Help-article embeddings — OpenAI** (`text-embedding-3-small`): the one external AI call; it indexes Pilot's own help articles, never customer audio or job data.
- **Offline-first mobile (mid-integration, ~70%):** the on-device store, sync engine and conflict handling are built and the design is complete, but local-DB migrations, the foreground sync path, and sync-engine tests were outstanding at hibernation.

Core stack: FastAPI 0.135, SQLModel on SQLAlchemy 2.0, Alembic, Celery, Redis, Pydantic v2; Next.js + React Native/Expo + Turbo; Terraform. All AWS resources are defined in Terraform (one CloudFront distribution was recreated by hand after an accidental destroy). One long-lived AWS environment, built to production spec, served as QA and production candidate; a separate QA stack was deployed once, tested, and torn down to avoid doubling cost.

---

## 6. Timeline (from the private original's git history)

- **~6 months of full-time build:** first commit 2026-03-02 → last commit 2026-09-07 (189 calendar days).
- **782 commits across 156 active days** — a commit on roughly 5 of every 6 days.
- **100% solo.** No other contributors.
- **Before the build:** roughly 4–6 months of part-time research, market analysis and design concepts (from about October 2025), not counted in these figures.

These can't be re-derived from this public snapshot, which is a single fresh commit.
