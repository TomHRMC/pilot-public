# The Method — How This Was Built

This repository is a **curated public snapshot** of *Pilot for Trades*, a full-stack field-service platform I architected and built **solo, AI-augmented**, in about six months of full-time build. It is a personal R&D build — a lab to prove a delivery method on myself. It was never released and has no customers, and its technical design follows the **SOC 2 security criteria** (built to the controls, not audited; no organizational controls).

The point of this repo isn't the code volume. It's the **method**: what it looks like when one experienced technologist runs an engineering organization whose team is AI — and the system of judgment and guardrails that makes the output correct rather than fast, confident debt.

## The operating model

One human acts as architect, reviewer, and accountable owner. The "team" is a set of **specialized AI agents**, each with a defined role, backed by multiple frontier models routed to what each does best. The human sets the architecture, assigns the work, reviews every output, and owns the decisions that are expensive to reverse. The agents draft and implement against those decisions.

**Twelve specialized agent roles** are checked into this repo (`.roomodes` + `.roo/rules-pilot-*`):

`architect` · `orchestrator` · `python-engineer` · `react-engineer` · `qa-python-engineer` · `devops-engineer` · `integrations-lead` · `voice-ai-specialist` · `voice-ui-designer` · `web-ui-designer` · `marketing-ui-designer` · `electrical-domain-expert`

Each role has its own rules directory the agent must read before acting — so standards travel with the role, not with the operator's memory.

## The guardrail system

The core discovery of the build: AI agents will repeatedly drift from the directions given in a chat, or from the project's established standards and procedures. Re-correcting the same drift by hand doesn't scale. The answer is to **harden the workflow** so the agents have no latitude to act outside the defined rules. The standing guardrails:

- **Environment discipline.** Every Python command runs through a fixed, mandatory prefix — activate the project virtual environment first, from the right directory — codified in the python-engineer methods ([`dev-docs/architecture-design/pilot-python-engineer-methods.md`](dev-docs/architecture-design/pilot-python-engineer-methods.md) §2, "Environment Setup"). No agent runs Python outside it.
- **Schema integrity.** A single **Golden Master JSON** schema file is the source of truth for the data model. It is mutated **only** through a dedicated tool (`backend/schema_manager.py`, documented in `README-schema_manager.md`) — never hand-edited — and every batch passes a **schema-diff gate** (physical DB vs. master JSON must reconcile) before work proceeds. Sync first.
- **Test discipline.** A **regression baseline** (fast unit tests, integration excluded) is captured *before any file is touched*; every unit of work reports `baseline → new, zero regressions, +N tests`. "Done" is never asserted without the suite run.
- **Documentation & closeout.** "Done" is defined as code **plus** migration **plus** master-JSON update **plus** the paired docs and trackers — enforced by a rigid finding/batch closeout template, so bookkeeping can't be silently skipped.
- **Dual-endpoint API pattern.** Secured routes ship with a `/test` variant (about 330 twins for about 340 secured operations at hibernation) that bypasses authentication in DEV/QA (env-gated) and is blocked in staging/production, enabling local testing without a live authenticated cloud connection — with the OpenAPI spec suppressed in production.
- **Verify, don't trust.** Live database state is verified (via MCP) before any DB query is composed — no hand-tracing, no assumed column names.
- **Human-in-the-loop gating.** A **propose → human-gate → verify** loop: the agent proposes and drafts; the human runs the migrations, schema diffs, and tests and confirms at defined gates; work advances **one unit at a time**; and agent context is recycled before it degrades (with a standardized re-entry prompt). A human owns every output.

## The stack

FastAPI, SQLModel on SQLAlchemy 2.0, Alembic, Celery, Redis, Pydantic v2 on the backend; Next.js (web + marketing) and React Native / Expo (mobile) in a Turbo monorepo; PostgreSQL; infrastructure as code in Terraform. Integrations: Stripe (Connect / payments / subscriptions), QuickBooks / Intuit, Google Calendar, Telnyx (telephony/SMS; replaced Twilio), AWS Cognito (auth + MFA), AWS (S3, Lambda), Expo push, OpenAI embeddings (help articles only), plus a local voice-AI pipeline.

## Not everything was a fight

Where the patterns were well-defined up front, the AI delivered smoothly. The Terraform infrastructure and the **AWS cost-profile scripts** (`infrastructure/scripts/profile-*.sh` — profile-switched environments to control cloud spend on an R&D budget) came together cleanly and generated almost no correction. That's part of the honest picture: a good method produces calm results where the rules are clear, and concentrates the human's attention where judgment is actually required.

## The takeaway

The leverage is real — one person produced what a much larger team would take far longer to build. But the leverage didn't remove the need for senior judgment; it **concentrated its value**. The scarce, decisive input was knowing what to build, which of the AI's plausible options fit this system, what was quietly broken, and which decisions were expensive to get wrong. That is the product. See `AI-PITFALLS.md` for the specific failure modes this method was built to contain.
