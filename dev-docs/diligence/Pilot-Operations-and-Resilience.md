# Operations & Resilience — as architected

*How the platform was built to be deployed, recovered, and observed. Capability evidence that I build operable, reproducible systems — not a claim of production operations, which the platform never had. Implemented vs. aspirational is marked.*

---

## Infrastructure as code (implemented)
- **All AWS resources defined in Terraform** — 26 `.tf` files; environments split (e.g. `environments/production/`). One CloudFront distribution was recreated by hand after an accidental destroy; otherwise the stack is reproducible from code, and manual console changes were limited to testing and setup verification, to keep drift minimal.
- **RDS** PostgreSQL 17 with **storage encryption + KMS and Multi-AZ** declared in Terraform; Redis/ElastiCache; ECS Fargate; ALB; S3; a g4dn GPU node for local inference.

## Environments & deployment (implemented)
- **Same backend code locally and in AWS** — locally, Docker Compose ran Postgres, Redis, the Celery worker and beat, Ollama and Whisper, with the API under `uvicorn`; in AWS the API, worker and beat ran from the same backend image, with managed services (RDS, ElastiCache, a GPU instance) in place of the local containers.
- **One long-lived AWS environment**, built to production spec, served as QA and production candidate. A separate QA stack was deployed once, tested, and torn down to avoid doubling cost. The environment never carried customer traffic.
- **Gated pipeline** — GitHub Actions with **OIDC** (no stored keys), image build to ECR, **Trivy secret scan** (container-image and dependency-vulnerability scanning not yet in the pipeline), and a Playwright E2E workflow (nightly schedule paused at hibernation).
- **Safe releases** — **ECS rolling deploys with circuit-breaker auto-rollback** and post-deploy health checks, run off-hours with a hardened runbook. Blue/green target groups are provisioned for a later CodeDeploy traffic-shift phase that was not enabled. A **human-run verification plan followed each batch** (the September fix series came straight from those runs).

## Backup & recovery (implemented + documented)
- A **timestamped `pg_dump` backup/restore workflow** is documented in the AWS ops runbook (`dev-docs/devops/aws-ops-runbook.md`) and was used in development (the backup dumps themselves are excluded from the public snapshot).
- **RDS backups (production-spec environment), two layers:** daily automated backups with **28-day retention and point-in-time restore** (`backup_retention_period = 28` in `infrastructure/terraform/modules/database/main.tf`), plus **weekly manual snapshots** kept indefinitely (procedure in the AWS ops runbook). Automating the weekly copy with an AWS Backup plan, including cross-region copies, is the next step.

## Disaster recovery / continuity (implemented)
- Because the stack is Terraform-defined, it is **rebuildable from code** (the hand-recreated CloudFront distribution aside); Multi-AZ RDS covers single-AZ failover.
- The platform was **intentionally hibernated** (AWS torn down toward near-zero cost) with a **documented restart runbook — about one day of runbook work; allow about a week of calendar time** (GPU capacity, DNS, carrier and Stripe re-verification) — paused, not abandoned. The restart runbook's fidelity is the main continuity dependency, and it's called out as such.

## Observability (partial — the honest gap)
- **Implemented:** structured application logging across the API/app layer; **CloudWatch alarms → SNS → email** (e.g. an `Errors ≥ 1 / 5 min` alarm on the Cognito custom-email Lambda).
- **Implemented (infrastructure level):** CloudWatch logs for every service, a CloudWatch dashboard, 12 alarms (p95 latency, error rate, CPU/memory across RDS, Redis, GPU and Lambda) and RDS Performance Insights.
- **Aspirational / next-phase:** no application-level APM, metrics, distributed tracing, or error-monitoring (OpenTelemetry / Prometheus / Sentry). This is the clearest production-readiness gap and standard early-ops work — named, not hidden.

## Incident response (partial)
- **Implemented:** alarm-to-email notification; a hardened deploy/rollback runbook (trigger-detach fallbacks documented for the Cognito path).
- **Aspirational:** formal on-call, SLOs/error budgets, and a paging rotation — operating-business maturity a lab build doesn't carry.

## What this demonstrates
The reproducible-from-code foundation, the gated rolling-deploy pipeline, the backup/restore workflow, and the honest observability gap together show an architect who builds for operations from the start and **knows exactly where a lab build's ops maturity stops and a staffed service's begins.** Standing up that operational layer — the monitoring, the on-call, the SLOs — is precisely the work a fractional or interim CTO leads.
