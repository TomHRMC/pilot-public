# How I Stress-Tested My Own Build

*An adversarial self-review of this repo — run as a skeptical mid/senior engineer would when asked "is this real / scalable / solid?" — with findings drawn from the code, Terraform and docs (2026-10-12, coverage figures 2026-10-13; counts re-taken on this snapshot 2026-11-14). I publish it because a build you can't critique honestly isn't one you understand. Pairs with [`Pilot-for-Trades-Proof.md`](Pilot-for-Trades-Proof.md).*

---

## Bottom line

The repo **holds up under technical scrutiny** — the tests are deep, auth and multi-tenancy are real and enforced (with the route-level gaps in Known Limitations #27), backend dependencies are fully pinned, and there's genuine IaC + OIDC CI. The honest exposures are a short, specific list, and they're the expected shape of a solo R&D build: no production traffic, bus factor 1, not audited, and a few known cleanup targets.

**The frame that makes those fair, not damning:** this is an R&D build that proves a *delivery method* — built to production standards, never operated in production. The point isn't that it's flawless; it's that I look for the weaknesses and publish the ones I find.

---

## What the self-review found (evidence)

| Area | Verdict | Evidence from the repo |
|---|---|---|
| **Is it real?** | **Yes, clearly** | ~4,950 backend test functions / **~11,000 assertions** (~2.2 per test — not status-only theater); a dedicated `tests/integration/` suite; 305 Alembic migrations; wired Stripe/QBO/Telnyx/Cognito; a 5,189-line voice action router. Git (private history): 782 commits / 156 active days. |
| **Test depth** | **Strong** | ~11,000 asserts; status-200/201-only checks ~1,030 (≈21%, a minority); ~1,330 mock/patch call sites in `backend/tests` (`Mock(`, `MagicMock`, `AsyncMock`, `patch(`, `mocker.`). Measured coverage: **76% backend** (line+branch), **~71% web / ~75% mobile** lines (2026-10-13). |
| **`/test` endpoint safety** | **Properly gated** | `TEST_ENDPOINT_ENABLED=False` by default **and** only honored when `ENVIRONMENT in ["dev","qa"]` — double-blocked in prod. Defuses the obvious "the test endpoints bypass auth" critique. |
| **Auth + RBAC** | **Really enforced** | ~250 auth/permission route dependencies in `backend/api/` (`Depends(get_current_user`/`require_permission`/`get_platform_user`), **~350 RBAC permission-check call-sites** (`require_permission(`/`has_permission(`) — not just a role data model. |
| **Multi-tenancy** | **Solid** | over 10,000 `tenant_id` references across the backend tree; isolation is **application/query-layer enforced** (Postgres RLS not enabled); dedicated `test_multi_tenancy_isolation.py` suite + 16 tenant/isolation test files. |
| **Security hardening** | **Real and wired** | Rate limiting (`core/rate_limit.py`, applied to three public route groups; not global — Known Limitations #28), **audit logging** wired into ~40 route files plus DB audit triggers, global idempotency middleware on POST/PATCH/PUT/DELETE (`core/idempotency.py`), Fernet token encryption. |
| **Code health** | **Clean** | ~21 TODO/FIXME/HACK markers across backend, frontend and infrastructure code (5 in backend app code); 41 `# type: ignore` across the backend tree (37 in app code); **no bare `except:`** in backend app code (347 explicit `except Exception` across the backend tree, 259 in app code); `print()` is absent from the route and model code (`api`/`app`); outside the tooling scripts, a handful remain in `services`/`core`/`tasks` (item 5 below). |
| **Dependencies** | **Disciplined** | 104 backend deps, **100% pinned (`==`)**; frontend versions locked via `pnpm-lock.yaml`. |
| **DevOps / IaC** | **Real** | 26 Terraform files; 2 GitHub Actions workflows; OIDC role-assumption (no long-lived keys in CI); Trivy secret scanning. |
| **Observability** | **Gap** | ~620 logger calls across the backend (575 in app code) plus a CloudWatch dashboard and 12 infrastructure alarms, but **no application-level metrics/tracing/error-monitoring** (no OpenTelemetry / Prometheus / Sentry). |

*Counts re-taken on this snapshot on 2026-11-14. "Backend tree" includes tests and migrations; "app code" means `api`, `app`, `core`, `services` and `tasks`.*

---

## What the review surfaced — and how I think about it

**1. The most useful catch was in my own docs.** An earlier README status label lagged the code — it still read as if the security-hardening phase hadn't started, when RBAC enforcement, audit logging, and rate limiting were all in the codebase. I reconciled it. That's the self-review doing exactly its job: catching my own drift before a reader did.

**2. No application-level metrics / tracing / error-monitoring.** Structured logging, a CloudWatch dashboard and 12 infrastructure alarms are in; APM, application metrics and error monitoring are not. A legitimate production-readiness gap — standard next-phase ops work I didn't add in a lab build.

**3. A 5,189-line module (`voice_action_router.py`).** A real maintainability flag and the single densest file; it's table-driven (verbose, not tangled), and it's the first thing I'd decompose handing this to a team.

**4. The inherent R&D-build facts.** Never ran production traffic / no load test; bus factor 1; no human peer review (AI review ≠ code review); built to the SOC 2 security criteria, not audited; JWT `iss`, `aud` and `token_use` claim checks not yet enabled; container-image and dependency-vulnerability scanning not yet in CI. All expected for a lab build — owned, not hidden.

**5. Minor cleanup.** A handful of `print()` calls in `services`/`core`/`tasks` that belong in logging — trivial.

---

## The hard questions, answered honestly

1. **"Did you actually build this, or did AI?"** — I architected and directed it; AI agents authored code against my decisions, and I reviewed and owned every one. The judgment — what to build, what to reject, what's expensive to reverse — is mine. That's the point.
2. **"Is it real or a demo?"** — Real: a 193-table schema, 305 migrations, ~8,000 tests with ~11k assertions, wired payment/accounting/telephony/auth integrations. The private original ran end-to-end; this public snapshot is a curated subset and isn't intended to run as-is. Never put in front of customers — it's a lab.
3. **"Are those tests meaningful or just a count?"** — ~2.2 assertions per test, a dedicated integration suite, a zero-regression gate on every batch, and measured coverage of 76% backend / ~71% web / ~75% mobile.
4. **"The `/test` endpoints bypass auth — isn't that a hole?"** — Double-gated: disabled by default and only ever active in dev/qa, blocked in prod. A dev-velocity tool, disabled in production, though the routes are still registered (Known Limitations #19).
5. **"Will it scale?"** — Architected for it — multi-tenant with application-enforced isolation, async workers, stateless API on Fargate, RDS Multi-AZ. Not yet proven under real load; proving it is next-phase work.
6. **"Is it SOC 2 ready?"** — The technical design follows the SOC 2 security criteria — encryption at rest/in transit (Redis excepted, Known Limitations #24), tenant isolation, RBAC, OIDC CI. It is *not* audited, and SOC 2 is largely organizational process. I know the difference because I've helped two client organizations through SOC 2 Type II audits.
7. **"Who maintains this — what if you're hit by a bus?"** — Today, me; it's a solo R&D build. It's documented (METHOD, AI-PITFALLS, 952 design docs in the private original) specifically so a team could pick it up — that handoff is unproven, and I'd treat team onboarding as real work.
8. **"Isn't 193 tables over-engineered for no customers?"** — It reflects the full product vision the method was proving against. For a real MVP I'd right-size — and knowing what to cut is exactly the judgment that matters.
9. **"Did it ever run in production?"** — Not with customers. One long-lived AWS environment, built to production spec, served as QA and production candidate and was tested after every batch (a separate QA stack was deployed once, tested, and torn down to avoid doubling cost). It never carried customer traffic or real user data. R&D, by design.
10. **"Any security review?"** — Trivy secret scanning in CI and fully pinned backend deps; container-image and dependency-vulnerability scanning are not yet in the pipeline, and there's no third-party human pen-test — appropriate for a lab, and a day-one item for anything going live.

---

## What this demonstrates

This isn't a product I'm selling — it's evidence of how I work: a senior technical leader directing an AI team to produce correct, disciplined engineering built to production standards at a fraction of the usual time and cost, with me as the judgment layer that keeps it correct rather than fast debt. The fact that the sharpest critic of this build is its author is the whole point.
