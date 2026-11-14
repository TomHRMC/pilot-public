# How I Deliver — The Pilot for Trades Build Story

> **What this is:** the end-to-end story of a real platform, built to production standards, that I architected and built **solo, AI-augmented, in about six months of full-time build** — told as evidence of *how I run engineering with AI*. Honest by design: an R&D build that proves a **method**, not a shipped product — built to production standards, never operated in production. Figures and how they were measured: [`Pilot-for-Trades-Proof.md`](Pilot-for-Trades-Proof.md).

---

## 0. The thesis

**A senior technical leader directing a team of AI agents delivered what I estimate a conventional team of 20–30 engineers would take about a year to build — one person, in about six months of full-time build — and the leader is *why it's correct*, not just why it's fast.**

The leverage from AI is real. But AI multiplies whatever you point it at, including mistakes, at machine speed. The scarce, decisive input is senior judgment: knowing *what* to build, which of the AI's plausible options fit the system, what's quietly broken, and which decisions are expensive to reverse. **That judgment is the transferable asset.** Pilot for Trades is the proof.

## 1. The business need (why this product)

Small electrical/trades contractors (1–10 employees) drown in administrative work — quoting, scheduling, invoicing, chasing payment, bookkeeping — usually on a phone, in a truck, between jobs. In my assessment the small end of the market is underserved; established platforms largely serve larger or multi-trade operations.

I chose a **hard, regulated, integration-heavy domain on purpose**: voice-controlled quoting, real-time job profitability, QuickBooks sync, NEC 2023 compliance math, payments, and telephony. If the method can deliver *this* end-to-end, it can deliver anything a growth-stage company needs. The product was the proving ground; the method is the point.

## 2. From requirements to a real product (what got built)

A full-stack, multi-tenant SaaS — **web app + React Native/Expo mobile app + marketing site + per-tenant compliance microsites** — delivered as 100+ named, gated work batches, June–September 2026, following a March–May foundation phase. Delivered capabilities:

- **Core operations:** customers, versioned quotes, jobs with real-time profitability, invoices + AR aging, dispatch board (week/month), recurring jobs, catalog/pricebook, dashboards.
- **Payments:** Stripe Connect (Express, tenant direct charges) plus metered platform billing — **built and exercised end-to-end in test mode**, including Connect onboarding; live mode was configured and validated (products and prices) but never took a real customer payment.
- **Accounting:** QuickBooks Online two-way sync (OAuth, dedup/conflict handling), coverage-audited and hardened.
- **Go-to-market engine:** a full **Charter program** — self-serve signup, trial + usage-metered subscriptions, cohort cap, upgrade flow, operator/platform shell with tenant impersonation (**build sequence complete, Aug 2026**).
- **Communications:** Telnyx telephony/SMS with a **proven 10DLC carrier loop** (campaign approved under the brand; real texts delivered to my own phone), STOP/START/HELP automation, and per-tenant SMS-compliance microsites.
- **Voice AI:** a local Whisper (speech-to-text) + Llama (intent parsing) pipeline for hands-free quoting in the field.
- **Trust & safety:** multi-tenant isolation, MFA, server-authoritative RBAC, audit logging, rate limiting on selected public routes, idempotency.

## 3. The engineering stack (modern, mainstream, defensible)

| Layer | Choice |
|---|---|
| **Backend** | FastAPI (Python), SQLAlchemy 2.0 / SQLModel, Pydantic v2, Celery + Redis, Alembic |
| **Data** | PostgreSQL 17 + pgvector (HNSW); **193-table** multi-tenant schema |
| **Web** | Next.js (web app + marketing), TanStack Query, in a Turbo monorepo |
| **Mobile** | React Native / Expo; offline-first layer (on-device SQLite + background sync) — designed, mid-integration (see status) |
| **AI / voice** | Local Ollama (Llama 3.1) + Whisper large-v3 — no per-request inference cost (fixed-cost GPU); no third-party AI on customer audio or job data (OpenAI embeddings index Pilot's own help articles) |
| **Auth** | AWS Cognito (user pools + MFA), JWT, server-authoritative RBAC |
| **Infra** | AWS (ECS Fargate, RDS Multi-AZ PG17, Redis/ElastiCache, g4dn GPU, ALB, S3), **Terraform IaC** |
| **CI/CD** | GitHub Actions with **OIDC** (no long-lived keys), Trivy secret scanning, Playwright E2E workflow (nightly schedule paused at hibernation) |
| **Integrations (12)** | Stripe (incl. Connect), QuickBooks Online, Google Calendar, Telnyx, SendGrid, AWS Cognito, S3/Lambda, Expo push, local Whisper + Llama, Cloudflare Turnstile, Google Maps, OpenAI (help-article embeddings) |

Every backend dependency pinned with `==` and frontend versions locked via `pnpm-lock.yaml`; no exotic bets; the stack a competent team would pick.

## 4. The delivery method (the differentiator)

**One human acts as architect, reviewer, and accountable owner. The "team" is specialized AI agents, routed across the models that each do best.**

- **The team:** 9+ AI agents across **6 LLMs** (Gemini, Claude, Grok, ChatGPT, Kimi, GLM), configured as **12 specialized roles** (architect · orchestrator · python-engineer · react-engineer · qa-engineer · devops · integrations-lead · voice-AI · 3 UI designers · electrical-domain-expert) — the role definitions are checked into the repo (`.roomodes` + `.roo/rules-*`). Tooling: VS Code + Roo Code, continued on its community fork Zoo Code.
- **The core discovery:** AI agents reliably *drift* from instructions and standards. Re-correcting by hand doesn't scale. So the workflow is **hardened with guardrails that remove the agents' latitude to decide outside the rules** (full detail in [`AI-PITFALLS.md`](../../AI-PITFALLS.md)):
  - **Environment discipline** — a fixed, mandatory command prefix; no agent runs outside the project venv.
  - **Schema integrity** — one **Golden-Master JSON** schema, mutated only through a dedicated tool (never by hand), behind a schema-diff gate that must reconcile live DB vs. master before work proceeds.
  - **Test discipline** — a regression baseline captured *before any file is touched*; every unit of work reports `baseline → new, 0 regressions, +N tests`.
  - **Dual-endpoint API pattern** — secured routes are paired with a `/test` twin (about 330 at hibernation), env-gated to dev/qa and blocked in prod.
  - **Verify, don't trust** — live DB state verified before any query is written; no assumed columns.
  - **Human-in-the-loop** — a **propose → gate → verify** loop: the agent proposes and drafts; I run the migrations, diffs, and tests and confirm at defined gates; work advances one unit at a time.

**The takeaway:** the leverage didn't remove the need for senior judgment — it *concentrated its value*. A good method produces calm results where the rules are clear and concentrates the human's attention where judgment actually matters.

## 5. How the work was governed (project management that holds up)

This wasn't vibes — it was governed delivery with a paper trail:

- **Batches & phases** — every unit of work a named batch with a full-scope card (inclusions, explicit exclusions, exit criteria), sequenced into phases (Pre-Founder Core → Full UI → Fix Sprint → Founder Gate → Post-Founder).
- **A formal launch gate** — a 16-row **Founder Launch Gate** ("all rows green before founder #1"), owner-assigned, with explicit on-the-record *non-gates*.
- **A close protocol** — status-flip-only: engineer appends a completion summary to the batch's own prompt doc; architect flips status with a date and a one-line registry entry. Append-only, stable IDs.
- **A decision log** — an ADR log (through ADR-0021) as the single source of architectural truth; decisions cited inline as authority.
- **Cadence** — weekly review of open items; completed work swept into **dated archives** at each phase exit (five archives, July→Aug) — a visible record of sustained, disciplined output.

## 6. Testing & quality (built in, not bolted on)

- **~8,000 automated tests** — ~4,950 backend + ~3,070 across web/mobile/marketing (on the last recorded run, 2026-10-13, both frontend suites were fully green and the backend had a small number of known failures, left unfixed at hibernation) — grown under a **zero-regression ratchet** that blocks any new uncovered error path.
- A dedicated **integration suite** (not just units), plus an **MSW fixture-fidelity** harness that keeps mocks contract-faithful.
- **Measured coverage** (fresh runs, 2026-10-13): **76%** backend (line+branch), **~71%** web and **~75%** mobile lines — a consistent full-stack band. Early batch prompts set an 80% target; it was not enforced as a CI gate.
- Every batch reports an exact passing/failing delta — "done" is a measured result, never a claim.

## 7. From build to test to prod (the pipeline)

- **Containerized dev from day one** — locally, Docker Compose ran Postgres, Redis, the Celery worker and beat, Ollama and Whisper, with the API under `uvicorn`; in AWS the API, worker and beat ran from the same backend image, with managed services (RDS, ElastiCache, a GPU instance) in place of the local containers. Deploys went to one long-lived AWS environment, built to production spec, that served as QA and production candidate (a separate QA stack was deployed once, tested, and torn down to avoid doubling cost).
- **Infrastructure as code** — all AWS resources defined in Terraform; one CloudFront distribution was recreated by hand after an accidental destroy, and other manual console changes were limited to testing/verification.
- **CI/CD** — GitHub Actions with OIDC role assumption (no stored keys), container builds to ECR, Trivy secret scanning (image and dependency scanning not yet in the pipeline), a Playwright E2E workflow (nightly schedule paused at hibernation).
- **Deploy discipline** — ECS rolling deploys with circuit-breaker rollback, run off-hours with a hardened runbook and post-deploy smoke checks; **I personally ran a verification plan against the AWS environment after each batch**, and residual findings spawned the next fix batch (an 11-batch September hardening series came straight from that testing). The environment never carried customer traffic.

## 8. The receipts (proof metrics)

- **~252,000 lines** of application code (AI-written, human-directed) across ~1,380 files · **~8,000 automated tests** (~234K test LOC) · **193 database tables** · **74 API route modules / ~700 operations** (incl. ~330 env-gated `/test` twins) · **952 design/architecture docs** (~680 in this snapshot) · **12 integrations**.
- **Timeline (private history):** first commit 2026-03-02 → last 2026-09-07 — **~6 months of full-time build, 782 commits across 156 active days (a commit ~5 of every 6 days), 100% solo**, after ~4–6 months of part-time research and design.
- **Cost-efficient by design:** ~$888/mo modelled infrastructure cost at 100 customers (design target, under a $1,000 cap) — ~$8.88/customer; ~94% infrastructure margin at the $149 Teams-annual price (~82–85% at the $49–$59 tiers), before payment and SMS fees; one fixed-cost GPU sized on paper for up to ~500 customers (not load-tested), so no per-request inference cost for voice AI.

## 9. Where it landed (the honest status)

Carried to a **Charter / founder-ready state**, then **deliberately hibernated** (Sept 2026). The Charter program (signup, metered billing, upgrade, platform shell) is fully built; the Founder Launch Gate was reached but intentionally not fully cleared (remaining items were mostly go-to-market ops — app-store submission, live-mode payment audit, recruiting the first founders). Three engineering items were open: the **mobile offline-sync layer** (~70%, mid-integration — its design is complete, but local-DB migrations, foreground wiring, and real sync-engine tests are outstanding), an owner-MFA-reset escape hatch, and a mobile UX up-design. It **never onboarded a paying customer, by design** — founders were to be the beta. The AWS stack was torn down to near-zero cost; restarting is about one day of runbook work (allow about a week of calendar time). The technical design follows the **SOC 2 security criteria — built to the controls, not audited.** Restartable, not abandoned.

## 10. What this means for you

You're not buying this product. You're seeing **how I'd run your engineering**: set the architecture and own the expensive-to-reverse decisions; stand up an AI-augmented team that ships *correct* work under hard guardrails instead of fast, confident debt; govern it with gates, tests, and a decision log; and deploy it with real DevOps discipline. That's what a fractional or interim CTO from HotRMC puts in place — senior leadership and a proven delivery method, at a fraction of the cost and risk of a full-time hire.
