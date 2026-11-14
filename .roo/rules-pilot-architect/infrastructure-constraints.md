# 🏗️ Infrastructure Constraints: Architectural Guardrails

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. Fiscal Hard Cap: $1,000/Month
The primary constraint is a total monthly infrastructure spend of **<$1,000** for the first 100 customers.
* **Target MVP Cost**: Maintain **~$888/month** to protect high gross margins (94.0% at $149/mo pricing).
* **Per-Customer Target**: Base infrastructure cost should not exceed **$8.88/customer/month** at the 100-user mark.
* **Cost Review**: You are operating with only an ~$112 buffer. ANY architectural change, new AWS service, or third-party API that increases the monthly baseline must be explicitly flagged for Founder review with a cost-benefit analysis.

## 2. "Fargate-First" Compute Policy
* **ECS Fargate**: Use for the FastAPI application, Celery workers (concurrency: 2), **and the Next.js web dashboard (`pilot-web`)** to save ~$73/month by avoiding EKS control plane costs. The web dashboard runs as a 4th ECS service on the existing `pilot-production` cluster (0.5 vCPU / 1024MB, port 3000); the existing ALB is shared via a listener rule routing `Host: app.pilotfortrades.com` — zero marginal ALB cost.
* **App Runner**: ~~Deprecated~~ **AWS App Runner was sunset April 30, 2026 — no new services can be created on any AWS account.** All container workloads (including Next.js SSR) use ECS Fargate. Do not design any new workload for App Runner.
* **Lambda**: Restrict to lightweight, event-driven, or scheduled background tasks (under 15 minutes).

## 3. Specialized AI Compute & External APIs
* **Owned GPU (Voice AI)**: **EC2 g4dn.xlarge** (NVIDIA T4) is mandatory. It must handle unlimited Whisper transcriptions and Ollama intent parsing to avoid variable cloud GPU costs. Optimized to handle up to **500 customers** before scaling.
* **OpenAI (Help System)**: Restricted *only* to `text-embedding-3-small` for pgvector document embeddings (~$7/mo). Do not use OpenAI for generative chat intents; route generative chat to the local Llama model.
* **Map Provider**: Utilize Google Maps API but enforce server-side caching. Be aware this is a major variable cost (~$77/mo at 100 users).
* **SMS (Telnyx)**: Assume ~$1.50/mo per active tenant. Ensure carrier interactions go through the `SmsCarrier` adapter layer to prevent vendor lock-in.

## 4. Database & Storage Constraints
* **PostgreSQL 17+**: Use **RDS Multi-AZ (db.t4g.micro)**. Must use `pgvector` with HNSW indexes for the AI Help system and conversation context.
* **ElastiCache Redis 7**: Mandatory. Use **cache.t4g.micro**. Strictly partition usage: DB 0 (Rate Limiting), DB 1 (Celery Broker), DB 2 (Celery Results).
* **S3 Storage**: Use for resumable multipart photo uploads, audio files, and markdown help corpus. Rely on signed URLs to offload upload/download bandwidth from the API.

## 5. Deployment & Security Guardrails
* **Terraform**: All infrastructure must be defined in Terraform.
* **Blue-Green Deployment**: Zero-downtime shifts via ALB traffic weighting.
* **Idempotency**: All POST/PATCH endpoints must support `Idempotency-Key` headers (24-hour TTL) with natural-key fallback for 72-hour offline mobile sync resolution.