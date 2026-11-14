# Pilot for Trades - Technical Architecture Document

> **Snapshot note:** historical working document, published as last edited during the build and not maintained. Statuses and figures below reflect that date; for current, checked figures see [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../diligence/README.md). The product was never released and never carried customer traffic. "Prod" here means the one pre-release AWS environment, used for the author's own tests.

**Version**: 5.4 (July 9, 2026 pricing evolution — §20 subscription architecture updated to Founders/Trial/Starter/Teams; Schedule Lanes replace Dispatch Slots; Enterprise removed)
**Last Updated:** July 9, 2026
**Author:** Tom (Founder)
**Status:** ACTIVE — Reflects all Pass 1–4 design completion; design phase frozen; backend implementation source of truth

---

## Table of Contents

- [Pilot for Trades - Technical Architecture Document](#pilot-for-trades---technical-architecture-document)
  - [Table of Contents](#table-of-contents)
  - [Executive Summary](#executive-summary)
    - [Product Overview](#product-overview)
    - [Technical Stack](#technical-stack)
    - [Architecture Principles](#architecture-principles)
    - [Key Metrics](#key-metrics)
  - [1. Infrastructure Architecture](#1-infrastructure-architecture)
    - [1.1 AWS Services Overview](#11-aws-services-overview)
    - [1.2 Infrastructure Diagram](#12-infrastructure-diagram)
    - [1.3 Cost Optimization Strategy](#13-cost-optimization-strategy)
    - [1.4 Infrastructure Costs (100 Customers)](#14-infrastructure-costs-100-customers)
    - [1.5 Scaling Strategy](#15-scaling-strategy)
    - [1.6 Terraform Configuration](#16-terraform-configuration)
  - [2. Database Architecture](#2-database-architecture)
    - [2.1 PostgreSQL Schema Design](#21-postgresql-schema-design)
    - [2.2 Domain-to-Schema Mapping](#22-domain-to-schema-mapping)
    - [2.3 pgvector Configuration](#23-pgvector-configuration)
    - [2.4 Database Performance Configuration](#24-database-performance-configuration)
    - [2.5 Database Backup Strategy](#25-database-backup-strategy)
  - [3. Background Processing](#3-background-processing)
    - [3.1 Architecture Overview](#31-architecture-overview)
    - [3.2 Celery Beat Schedule (All Registered Tasks)](#32-celery-beat-schedule-all-registered-tasks)
    - [3.3 Task Modules](#33-task-modules)
    - [3.4 Profitability Rollup Worker](#34-profitability-rollup-worker)
    - [3.5 Notification Preference Center Architecture](#35-notification-preference-center-architecture)
  - [4. Authentication \& Authorization](#4-authentication--authorization)
    - [4.1 AWS Cognito Configuration](#41-aws-cognito-configuration)
    - [4.2 JWT Authentication Flow](#42-jwt-authentication-flow)
    - [4.3 Role-Based Access Control (RBAC)](#43-role-based-access-control-rbac)
    - [4.4 Post-Signup Lambda](#44-post-signup-lambda)
    - [4.5 Multi-Factor Authentication](#45-multi-factor-authentication)
    - [4.6 Refresh Token TTL \& Offline Scenario](#46-refresh-token-ttl--offline-scenario)
    - [4.7 Onboarding State Machine](#47-onboarding-state-machine)
    - [4.8 Account Settings — Active Sessions and Data Export](#48-account-settings--active-sessions-and-data-export)
  - [5. QuickBooks Integration](#5-quickbooks-integration)
    - [5.1 OAuth 2.0 Connection Flow](#51-oauth-20-connection-flow)
    - [5.2 Token Encryption \& Refresh](#52-token-encryption--refresh)
    - [5.3 Bi-Directional Sync Strategy](#53-bi-directional-sync-strategy)
    - [5.4 Conflict Detection \& Resolution](#54-conflict-detection--resolution)
    - [5.4 Conflict Detection \& Resolution](#54-conflict-detection--resolution-1)
    - [5.5 Webhook Handler](#55-webhook-handler)
  - [6. Voice AI Pipeline](#6-voice-ai-pipeline)
    - [6.1 End-to-End Architecture](#61-end-to-end-architecture)
    - [6.2 Voice Intent Handlers (Registered in INTENT\_HANDLERS)](#62-voice-intent-handlers-registered-in-intent_handlers)
    - [6.3 Multi-Turn Context Management](#63-multi-turn-context-management)
    - [6.4 Conversation Sessions \& Structured Message Payload](#64-conversation-sessions--structured-message-payload)
    - [6.5 GPU Instance Configuration](#65-gpu-instance-configuration)
    - [6.6 Confirm-as-Turn for Destructive Actions](#66-confirm-as-turn-for-destructive-actions)
    - [6.7 Deferred Voice Processing Pipeline (Offline-Captured Audio)](#67-deferred-voice-processing-pipeline-offline-captured-audio)
    - [6.8 NEC Code Assistance](#68-nec-code-assistance)
  - [7. API Design](#7-api-design)
    - [7.1 Application Entry Point \& Middleware Stack](#71-application-entry-point--middleware-stack)
    - [7.2 RESTful Conventions](#72-restful-conventions)
    - [7.3 Versioning Strategy](#73-versioning-strategy)
    - [7.4 Error Response Format (RFC 7807)](#74-error-response-format-rfc-7807)
    - [7.5 Rate Limiting](#75-rate-limiting)
    - [7.6 Idempotency Keys](#76-idempotency-keys)
    - [7.7 Request ID Tracing](#77-request-id-tracing)
    - [7.8 Cursor-Based Pagination](#78-cursor-based-pagination)
    - [7.9 Pre-Commit Staleness Check Pattern (409-and-Refresh)](#79-pre-commit-staleness-check-pattern-409-and-refresh)
  - [8. Monitoring \& Observability](#8-monitoring--observability)
    - [8.1 Structured Logging](#81-structured-logging)
    - [8.2 OpenTelemetry Metrics](#82-opentelemetry-metrics)
    - [8.3 Distributed Tracing (X-Ray + ADOT)](#83-distributed-tracing-x-ray--adot)
    - [8.4 CloudWatch Dashboards — Key Metrics](#84-cloudwatch-dashboards--key-metrics)
    - [8.5 Alerting](#85-alerting)
    - [8.6 Service Level Objectives (SLOs)](#86-service-level-objectives-slos)
    - [8.7 Monitoring Costs](#87-monitoring-costs)
  - [9. Security Architecture](#9-security-architecture)
    - [9.1 Secrets Management](#91-secrets-management)
    - [9.2 Encryption](#92-encryption)
    - [9.3 Network Security](#93-network-security)
    - [9.4 Application Security](#94-application-security)
    - [9.5 IAM Least Privilege](#95-iam-least-privilege)
    - [9.6 Security Monitoring](#96-security-monitoring)
    - [9.7 GDPR Compliance](#97-gdpr-compliance)
  - [10. Deployment \& CI/CD](#10-deployment--cicd)
    - [10.1 Docker Containerization](#101-docker-containerization)
    - [10.2 GitHub Actions CI/CD Pipeline](#102-github-actions-cicd-pipeline)
    - [10.3 Blue-Green Deployment](#103-blue-green-deployment)
    - [10.4 Database Migrations (Alembic)](#104-database-migrations-alembic)
    - [10.5 Rollback Procedures](#105-rollback-procedures)
    - [10.6 Disaster Recovery](#106-disaster-recovery)
  - [11. Front-End Architecture](#11-front-end-architecture)
    - [11.1 Strategic Direction](#111-strategic-direction)
    - [11.2 Monorepo Architecture (Turborepo + pnpm)](#112-monorepo-architecture-turborepo--pnpm)
    - [11.3 Front-End Tech Stack](#113-front-end-tech-stack)
    - [11.4 Type Generation from FastAPI](#114-type-generation-from-fastapi)
  - [12. Local Development Environment](#12-local-development-environment)
    - [12.1 Docker Stack (6 Containers)](#121-docker-stack-6-containers)
    - [12.2 Development Terminal Setup (3 Terminals)](#122-development-terminal-setup-3-terminals)
    - [12.3 Key Environment Variables (`backend/.env`)](#123-key-environment-variables-backendenv)
    - [12.4 One-Time Local Setup](#124-one-time-local-setup)
    - [12.5 Database Backup (Local)](#125-database-backup-local)
  - [13. Scheduling \& Dispatch](#13-scheduling--dispatch)
    - [13.1 Architecture Overview](#131-architecture-overview)
    - [13.2 Data Model](#132-data-model)
    - [13.3 Provider-Abstract Interfaces](#133-provider-abstract-interfaces)
    - [13.4 Conflict Detection (Four-Class Severity)](#134-conflict-detection-four-class-severity)
    - [13.5 Bi-Directional Calendar Sync](#135-bi-directional-calendar-sync)
    - [13.6 Celery Task Registry](#136-celery-task-registry)
    - [13.7 API Design](#137-api-design)
    - [13.8 Cost Considerations](#138-cost-considerations)
    - [13.9 Failure Modes \& Recovery](#139-failure-modes--recovery)
    - [13.10 Monitoring](#1310-monitoring)
    - [13.11 Dispatch Board Live Updates (Server-Sent Events)](#1311-dispatch-board-live-updates-server-sent-events)
  - [14. Quote Approval \& Templates Architecture](#14-quote-approval--templates-architecture)
    - [14.1 Quote Line Item Visibility \& Hierarchy](#141-quote-line-item-visibility--hierarchy)
    - [14.2 Three Quote Presentation Styles](#142-three-quote-presentation-styles)
    - [14.3 ETC (Estimate-to-Complete) Capture System](#143-etc-estimate-to-complete-capture-system)
    - [14.4 Quote Approval Workflow](#144-quote-approval-workflow)
    - [14.5 Quote Template System with Style and Versioning](#145-quote-template-system-with-style-and-versioning)
    - [14.6 Time-Limited Discounts with Margin Cap](#146-time-limited-discounts-with-margin-cap)
  - [15. Mobile Offline Operations Architecture](#15-mobile-offline-operations-architecture)
    - [15.1 Strategic Direction](#151-strategic-direction)
    - [15.2 Offline-Capable Operations Contract](#152-offline-capable-operations-contract)
    - [15.3 Sync Queue State Model](#153-sync-queue-state-model)
    - [15.4 Idempotency UUIDs with Natural-Key Fallback](#154-idempotency-uuids-with-natural-key-fallback)
    - [15.5 Resumable Photo Upload Pipeline (S3 Multipart)](#155-resumable-photo-upload-pipeline-s3-multipart)
    - [15.6 Conflict Severity Classification Engine](#156-conflict-severity-classification-engine)
    - [15.7 Voice Capture Offline, Process Online](#157-voice-capture-offline-process-online)
    - [15.8 Force-Quit Recovery via Persistent Local Queue](#158-force-quit-recovery-via-persistent-local-queue)
    - [15.9 Tech-Resolvable Conflict Resolution Endpoints](#159-tech-resolvable-conflict-resolution-endpoints)
    - [15.10 Owner Escalation Routing](#1510-owner-escalation-routing)
    - [15.11 Time-Bounded Offline Operation](#1511-time-bounded-offline-operation)
    - [15.12 Auth Expiry Handling with Disabled-Account Export](#1512-auth-expiry-handling-with-disabled-account-export)
    - [15.13 Sync Triggers (Updated: Background Sync Now in MVP — see §16.12)](#1513-sync-triggers-updated-background-sync-now-in-mvp--see-1612)
    - [15.14 Customer Comms Stay Online-Only](#1514-customer-comms-stay-online-only)
  - [16. Cross-Cutting Platform Patterns](#16-cross-cutting-platform-patterns)
    - [16.1 Pattern Inventory](#161-pattern-inventory)
    - [16.2 Track-Changes Diff Vocabulary](#162-track-changes-diff-vocabulary)
    - [16.3 Confirm-as-Turn for Destructive Voice Actions](#163-confirm-as-turn-for-destructive-voice-actions)
    - [16.4 Pre-Commit Staleness Check (409-and-Refresh)](#164-pre-commit-staleness-check-409-and-refresh)
    - [16.5 System Default + Tenant Override Two-Tier Configuration](#165-system-default--tenant-override-two-tier-configuration)
    - [16.6 Four-Class Severity Pattern](#166-four-class-severity-pattern)
    - [16.7 Always-Preview-Before-Send for One-Way-Door Actions](#167-always-preview-before-send-for-one-way-door-actions)
    - [16.8 Optimistic UI with Pending Badges](#168-optimistic-ui-with-pending-badges)
    - [16.9 Mobile Owner Status Row + Deep-Link](#169-mobile-owner-status-row--deep-link)
    - [16.10 Bilateral Integration Conflict Resolution Pattern](#1610-bilateral-integration-conflict-resolution-pattern)
    - [16.11 Mobile-to-Web Escalation Pattern](#1611-mobile-to-web-escalation-pattern)
    - [16.12 Background Sync Execution Pattern](#1612-background-sync-execution-pattern)
    - [16.13 In-Flight Sync Indicator with Pending Count](#1613-in-flight-sync-indicator-with-pending-count)
  - [17. SMS Infrastructure](#17-sms-infrastructure)
    - [17.1 Carrier Choice and Adapter Layer](#171-carrier-choice-and-adapter-layer)
    - [17.2 A2P 10DLC Compliance](#172-a2p-10dlc-compliance)
    - [17.3 Number Provisioning Strategy](#173-number-provisioning-strategy)
    - [17.4 Inbound Message Routing](#174-inbound-message-routing)
    - [17.5 Threading Schema](#175-threading-schema)
    - [17.6 Subscription Quota and Cap Enforcement](#176-subscription-quota-and-cap-enforcement)
    - [17.7 Voice Intent Integration](#177-voice-intent-integration)
    - [17.8 Notification Integration](#178-notification-integration)
    - [17.9 Audit and Compliance](#179-audit-and-compliance)
    - [17.10 Backend Module Structure](#1710-backend-module-structure)
    - [17.11 Cost Implications](#1711-cost-implications)
    - [17.12 Phase 2 Roadmap](#1712-phase-2-roadmap)
  - [18. Customer-Facing Public Surfaces Architecture](#18-customer-facing-public-surfaces-architecture)
    - [18.1 Strategic Direction](#181-strategic-direction)
    - [18.2 Signed URL Infrastructure](#182-signed-url-infrastructure)
    - [18.3 Short-Link Redirect Infrastructure](#183-short-link-redirect-infrastructure)
    - [18.4 Public Page Routing](#184-public-page-routing)
    - [18.5 Stripe One-Time Payment for Invoices with Amount Variance](#185-stripe-one-time-payment-for-invoices-with-amount-variance)
    - [18.6 State-Aware Revisit Handling](#186-state-aware-revisit-handling)
    - [18.7 Customer Comment Storage (Entity-Bound)](#187-customer-comment-storage-entity-bound)
    - [18.8 Email Template Rendering Pipeline](#188-email-template-rendering-pipeline)
    - [18.9 Backend Module Structure](#189-backend-module-structure)
    - [18.10 Audit Logging](#1810-audit-logging)
    - [18.11 Phase 2 Considerations](#1811-phase-2-considerations)
  - [19. Help System Architecture](#19-help-system-architecture)
    - [19.1 Strategic Direction](#191-strategic-direction)
    - [19.2 Markdown Corpus Storage and Structure](#192-markdown-corpus-storage-and-structure)
    - [19.3 Embedding Pipeline](#193-embedding-pipeline)
    - [19.4 Help AI Agent](#194-help-ai-agent)
    - [19.5 RAG Retrieval](#195-rag-retrieval)
    - [19.6 Chat Session Management](#196-chat-session-management)
    - [19.7 AI Knowledge Boundaries and Escalation](#197-ai-knowledge-boundaries-and-escalation)
    - [19.8 Voice Integration](#198-voice-integration)
    - [19.9 Anonymization Pipeline (Training Data Capture)](#199-anonymization-pipeline-training-data-capture)
    - [19.10 Backend Module Structure](#1910-backend-module-structure)
    - [19.11 Selective Contextual Help Anchors](#1911-selective-contextual-help-anchors)
    - [19.12 Phase 2 Considerations](#1912-phase-2-considerations)
  - [20. Subscription Tier + Stripe Integration Architecture](#20-subscription-tier--stripe-integration-architecture)
    - [20.1 Strategic Direction](#201-strategic-direction)
    - [20.2 Subscription Tier Schema](#202-subscription-tier-schema)
    - [20.3 Subscription Usage Tracking](#203-subscription-usage-tracking)
    - [20.4 Stripe Subscriptions Integration](#204-stripe-subscriptions-integration)
    - [20.5 Stripe Payment Intents Integration (One-Time Invoice Payments)](#205-stripe-payment-intents-integration-one-time-invoice-payments)
    - [20.6 Stripe Webhook Handler](#206-stripe-webhook-handler)
    - [20.7 Tier Limit Enforcement](#207-tier-limit-enforcement)
    - [20.8 Trial Expiration Read-Only State](#208-trial-expiration-read-only-state)
    - [20.9 Operator Overrides](#209-operator-overrides)
    - [20.10 Backend Module Structure](#2010-backend-module-structure)
    - [20.11 Phase 2 Considerations](#2011-phase-2-considerations)
  - [Cost Analysis](#cost-analysis)
    - [Total Infrastructure Cost (100 Customers — MVP)](#total-infrastructure-cost-100-customers--mvp)
    - [Scaling Economics](#scaling-economics)
  - [Appendices](#appendices)
    - [A. Glossary](#a-glossary)
    - [B. Key Technical Decisions](#b-key-technical-decisions)
    - [C. Security Checklist](#c-security-checklist)
    - [D. Useful Commands Reference](#d-useful-commands-reference)
    - [E. External Resources](#e-external-resources)
  - [Document End](#document-end)

---

## Executive Summary

### Product Overview

**Pilot for Trades** is an AI-powered SaaS platform for small electrical contractors (1–10 employees) featuring voice-controlled quoting with conversational continuity, real-time job profitability tracking with mid-job ETC capture, QuickBooks Online bi-directional sync, dispatch board with four-class conflict detection, bi-directional Google Calendar sync with field-level conflict resolution, customer communication templates with always-preview-before-send safety, mobile offline-to-online sync as a first-class capability, and NEC 2023 code assistance — all accessible via a voice-first interface from the job site or anywhere else.

**Key Differentiators:**
- Voice-first interface (hands-free operation on job sites via Whisper + Ollama; multi-turn conversation continuity; confirm-as-turn for destructive actions; offline voice capture with deferred processing)
- Real-time profit tracking per job (Celery-driven actuals vs. estimates; mid-job ETC capture surfaces course-correction opportunities before completion)
- Seamless QuickBooks Online bi-directional integration with field-level conflict resolution UI inheriting calendar conflict resolution vocabulary
- Bi-directional Google Calendar sync with full field-level conflict resolution surface (web for touch, voice from anywhere)
- Templated customer communications with always-preview-before-send safety rule
- Mobile offline-to-online sync with four-class conflict severity and optimistic UI
- NEC 2023 code calculation engine (voltage drop, conduit fill, ampacity)
- Premium positioning at $149/month (planned price point)

**Target Market:**
- Small electrical contractors (1–10 employees) at MVP; expanding to plumbing and HVAC trades in Phase 2
- Revenue range: $500K–$2M annually
- Primary users: Owner-operators and field technicians; secondary: bookkeepers and office managers

### Technical Stack

**Core Technologies:**

| Layer | Technology | Notes |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI 0.115+ (Python 3.14+) | Async, OpenAPI auto-docs |
| **Database** | PostgreSQL 17+ with pgvector | HNSW indexes for vector similarity |
| **ORM / Migrations** | SQLModel + Alembic | Pydantic-native type safety |
| **Web Frontend** | Next.js 16 (App Router) + Tailwind v4 + React 19 | Owner/bookkeeper dashboard |
| **Mobile Frontend** | Expo SDK 54 + React Native 0.81 + Expo Router | Field technician app (iOS/Android) |
| **Frontend Monorepo** | Turborepo 2.x + pnpm 9.x workspaces | Shared types, API hooks, UI primitives |
| **AI: Speech-to-Text** | Whisper Large-v3 (faster-whisper-server) | Local GPU, no per-use cost |
| **AI: Intent Parsing** | Llama 3.1 8B via Ollama | Local GPU, no per-use cost |
| **Task Queue** | Celery + Redis (broker) | Workers in Docker containers |
| **Cloud** | AWS (cost-optimized) | ECS Fargate, RDS, ElastiCache |
| **Auth** | AWS Cognito + RS256 JWT | JWKS validation, RBAC permissions |
| **Secrets** | AWS Secrets Manager + Fernet | OAuth tokens encrypted at rest |
| **IaC** | Terraform | Multi-environment (dev/staging/prod) |
| **CI/CD** | GitHub Actions + OIDC + ECS | Blue-green, zero-downtime deploy (design goal; as built: rolling deploys — Known Limitations #18) |

### Architecture Principles

1. **Cost-Optimized MVP**: Target $600–1,000/month infrastructure for 100 customers
2. **Voice-First**: All core field functions accessible via natural language voice commands
3. **Local AI Processing**: Whisper + Ollama on owned/leased GPU instance — unlimited usage, zero per-request cost
4. **QuickBooks Native**: Bi-directional sync with conflict detection; contractors keep their existing accounting workflow
5. **Fast Deployment**: Zero-downtime blue-green deployments via ALB traffic weighting *(design goal; as built: ECS rolling deploys with circuit-breaker rollback — the green target group is provisioned but not yet used)*
6. **Security First**: Encryption at rest/transit, OWASP Top-10, tenant isolation, RBAC with wildcard permissions
7. **Idempotency by Default**: All POST/PATCH endpoints support `Idempotency-Key` header (24-hour deduplication)

### Key Metrics

| Metric | Target |
| :--- | :--- |
| **Infrastructure Cost** | $600–1,000/month (100 customers) |
| **API Latency (p95)** | < 500ms |
| **Voice AI Latency (p95)** | < 2 seconds end-to-end |
| **Availability SLO** | 99.9% (43 min downtime/month) |
| **Time to Deploy** | < 10 minutes (blue-green design goal; as built: rolling) |
| **Rollback Time** | < 2 minutes |
| **Test Suite** | 283 tests, 100% passing |

---

## 1. Infrastructure Architecture

### 1.1 AWS Services Overview

**Compute:**
- **ECS Fargate** — FastAPI application (2 tasks @ 0.25 vCPU/1024MB), Celery workers (2 tasks @ 0.25 vCPU/512MB), Celery Beat (1 task), and Next.js web dashboard `pilot-web` (1 task @ 0.5 vCPU/1024MB, port 3000) — 4 services on the `pilot-production` cluster
- **EC2 g4dn.xlarge** — Persistent GPU instance (NVIDIA T4) for Whisper + Ollama
- **Lambda** — Lightweight event-driven and scheduled background tasks (<15 min)

> **Note**: AWS App Runner was sunset April 30, 2026 — no new services can be created. The Next.js web dashboard (`pilot-web`) runs on ECS Fargate as the 4th service on the existing cluster. The existing ALB is shared via a `Host: app.pilotfortrades.com` listener rule — zero marginal ALB cost.

> **Note**: API Gateway is deferred to post-MVP. Direct ALB routing saves ~$18/month per million requests.

**Database & Storage:**
- **RDS PostgreSQL 17+** — Primary database, Multi-AZ, `db.t4g.micro` with pgvector
- **ElastiCache Redis 7** — `cache.t4g.micro`; three logical databases:
  - DB 0: Rate limiting (SlowAPI token buckets)
  - DB 1: Celery task broker
  - DB 2: Celery result backend
- **S3** — Audio file uploads, receipt images, PDF exports, Terraform state

**Networking:**
- **VPC** — Isolated network, public subnets (ALB) + private subnets (ECS/RDS/Redis/GPU)
- **Application Load Balancer** — HTTPS termination (ACM), blue-green traffic weighting (design goal; as built: rolling deploys)
- **NAT Gateway** — Single AZ, outbound internet for private subnet services
- **Route 53** — DNS management
- **CloudFront** — CDN for static assets (optional for MVP)
- **AWS Shield / WAF** — DDoS and Layer-7 attack protection (design goal; as built: Shield Standard only, no WAF)

**Security & Management:**
- **Cognito** — User authentication, MFA, Google/Apple SSO, JWKS endpoint for JWT validation
- **Secrets Manager** — Secure credential storage (DB password, QB OAuth keys, SendGrid, Telnyx)
- **KMS** — Encryption key management for RDS, S3, Secrets Manager
- **ACM** — TLS certificate management for ALB
- **IAM** — ECS task roles scoped to minimum required permissions

**Monitoring:**
- **CloudWatch** — Logs, metrics, dashboards, alarms
- **X-Ray** — Distributed tracing (ADOT collector)
- **GuardDuty** — Automated threat detection
- **Security Hub** — CIS benchmark compliance monitoring

### 1.2 Infrastructure Diagram

```
Internet
   ↓
┌──────────────────────────────────────────────┐
│  Route 53 (DNS)                              │
│  pilotfortrades.com → CloudFront (CDN, optional)   │
└──────────────────────────────────────────────┘
   ↓
┌──────────────────────────────────────────────┐
│  Application Load Balancer (ALB)             │
│  - HTTPS termination (ACM certificates)      │
│  - Public subnets (us-east-1a, us-east-1b)   │
│  - Rolling deploys (blue/green = goal)       │
└──────────────────────────────────────────────┘
   ↓
┌──────────────────────────────────────────────┐
│  VPC: 10.0.0.0/16                            │
│  ┌────────────────────────────────────────┐  │
│  │  Private Subnets                       │  │
│  │  ┌──────────────────┐  ┌────────────┐ │  │
│  │  │ ECS Fargate      │  │ RDS        │ │  │
│  │  │ - FastAPI (x2)   │  │ PostgreSQL │ │  │
│  │  │ - Celery workers │  │ + pgvector │ │  │
│  │  └──────────────────┘  └────────────┘ │  │
│  │  ┌──────────────────┐  ┌────────────┐ │  │
│  │  │ EC2 (GPU)        │  │ Redis      │ │  │
│  │  │ g4dn.xlarge      │  │ ElastiCache│ │  │
│  │  │ - Whisper :8080  │  │ DB 0,1,2   │ │  │
│  │  │ - Ollama :11434  │  └────────────┘ │  │
│  │  └──────────────────┘                  │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │  NAT Gateway (for outbound internet)   │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
   ↓ (outbound via NAT Gateway)
External APIs:
- QuickBooks Online (OAuth 2.0 + Webhooks)
- SendGrid (transactional email)
- Telnyx (SMS notifications)
- Supplier price feeds (planned; not built)
```

### 1.3 Cost Optimization Strategy

**Key Decisions:**

| Decision | Savings |
| :--- | :--- |
| ECS Fargate over EKS (all 4 services including web dashboard) | ~$73/month (no control plane cost) |
| Single Multi-AZ RDS `db.t4g.micro` | ~$43/month vs $2,000+/month managed cluster |
| Owned GPU Instance (g4dn.xlarge) | ~$384/month for unlimited AI vs $1,000+/month cloud GPU APIs |
| Local Ollama (Llama 3.1 8B) | $0 inference vs $30–100/month OpenAI/Anthropic |
| Direct ALB routing (no API Gateway) | ~$18/month per million requests saved |
| Single NAT Gateway | ~$32/month vs ~$64/month for Multi-AZ NAT |
| Shared ALB for web dashboard (ECS listener rule vs. separate load balancer) | ~$18/month (no second ALB needed) |

### 1.4 Infrastructure Costs (100 Customers)

| Service | Instance Type | Monthly Cost |
| :--- | :--- | :--- |
| **ECS Fargate — API** | 2 tasks (0.25 vCPU / 1024MB) — bumped from 512MB 2026-07-06 (two uvicorn workers × ~200MB baseline left only ~110MB headroom) | ~$22 |
| **ECS Fargate — Celery Worker** | 2 tasks (0.25 vCPU / 512MB) | ~$18 |
| **ECS Fargate — Celery Beat** | 1 task (0.25 vCPU / 256MB) | ~$8 |
| **ECS Fargate — Web Dashboard** | 1 task (0.5 vCPU / 1024MB, port 3000) | ~$18 |
| **RDS PostgreSQL** | db.t4g.micro (Multi-AZ) | ~$28 |
| **ElastiCache Redis** | cache.t4g.micro | ~$13 |
| **EC2 GPU** | g4dn.xlarge (NVIDIA T4) | ~$390 |
| **S3** | 100GB storage + transfer | ~$5 |
| **Application Load Balancer** | Standard (shared: API + web dashboard) | ~$18 |
| **NAT Gateway** | Single AZ | ~$35 |
| **CloudWatch** | Logs + metrics + alarms | ~$28 |
| **Secrets Manager** | ~11 secrets | ~$4 |
| **Data Transfer** | ~500GB out | ~$45 |
| **Lambda** | Background/event jobs | ~$0 |
| **VPC Endpoints** | S3, Secrets Manager | ~$7 |
| **Security** | GuardDuty + Security Hub | ~$17 |
| **TOTAL** | | **~$682/month** |

> **Version history**: Original estimate was ~$643/month based on 2 ECS tasks and App Runner for the web dashboard. Corrected to ~$682/month reflecting: (1) separate ECS services for Celery Worker + Beat + Web Dashboard as billable tasks, (2) App Runner replaced by ECS Fargate for `pilot-web` after App Runner sunset April 30 2026, (3) mid-2026 verified pricing. Budget target remains $888/month — **$206/month buffer remains.**

**Per-customer cost:** $6.82/month
**Gross margin at $149/month:** 95.4% (excluding support costs)

### 1.5 Scaling Strategy

| Component | MVP (100 Users) | Growth (500 Users) | Scale (1,000 Users) |
| :--- | :--- | :--- | :--- |
| **ECS Fargate** | 2 Tasks (0.25 vCPU) | 4 Tasks | 8 Tasks |
| **RDS PostgreSQL** | db.t4g.micro | db.t4g.small | db.t4g.medium |
| **ElastiCache** | cache.t4g.micro | cache.t4g.small | cache.t4g.medium |
| **EC2 GPU** | 1 × g4dn.xlarge | 1 × g4dn.xlarge | 2 × g4dn.xlarge |
| **Monthly Cost** | **~$682** | **~$1,100** | **~$1,900** |
| **Cost Per User** | **$6.82** | **$2.20** | **$1.90** |

**Scaling Triggers (from `scaling-logic.md`):**
- **ECS**: CPU > 70% or Memory > 80% for 3 consecutive 5-min periods → add 2 tasks
- **RDS**: Storage at 80% → enable autoscaling first; upgrade class only if connections exhausted
- **GPU**: Voice AI p95 latency > 2.5 seconds due to queue depth → provision second g4dn.xlarge

### 1.6 Terraform Configuration

```
infrastructure/
└── terraform/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── backend.tf              # S3 + DynamoDB remote state
    ├── versions.tf
    ├── modules/
    │   ├── networking/         # VPC, subnets, security groups, NAT
    │   ├── compute/            # ECS cluster (4 services: api, worker, beat, web), EC2 GPU, Lambda
    │   ├── database/           # RDS, ElastiCache
    │   ├── storage/            # S3 buckets
    │   ├── security/           # IAM roles, KMS, Secrets Manager
    │   └── monitoring/         # CloudWatch, alarms, X-Ray
    └── environments/
        ├── dev/
        ├── staging/
        └── production/
```

**Remote state backend:**
```hcl
terraform {
  backend "s3" {
    bucket         = "pilot-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "pilot-terraform-locks"
  }
}
```

---

## 2. Database Architecture

### 2.1 PostgreSQL Schema Design

The authoritative schema reference is `dev-docs/db-design/pilot-db-schema-v2.6h.json` and the process document at `dev-docs/db-design/pilot-db-process-v2.6h.md`.

**Schema Summary:**
- **17 PostgreSQL schemas** organizing 130+ tables into bounded domains
- **Multi-tenancy**: Every tenant-owned table carries `tenant_id UUID NOT NULL`; immutability triggers block reassignment
- **UTC enforcement ("Triple-Lock")**: All timestamp columns use `TIMESTAMPTZ`; Pydantic uses `AwareDatetime`; Python uses `datetime.now(UTC)`
- **Soft deletes**: `is_active BOOLEAN NOT NULL DEFAULT TRUE` on all entities; soft-delete cascade triggers propagate deactivation
- **Audit triggers**: `audit.log_changes()` fires on all 130+ tables, capturing JSONB `OLD`/`NEW` snapshots (FIND-053 — Phase 4.2 correction)
- **pgvector**: HNSW indexes on `conversation_messages.embedding` and `conversation_sessions.context_embedding` for vector similarity search

### 2.2 Domain-to-Schema Mapping

| Domain | Key Tables |
| :--- | :--- |
| **Auth / Identity** | `user`, `tenant`, `tenant_user`, `tenant_user_role`, `user_endpoint` |
| **CRM** | `customer`, `site`, `entity_contact`, `entity_address`, `payment_method` |
| **Catalog & Pricing** | `supplier`, `supplier_item`, `supplier_item_price`, `pricing_cache`, `pricebook_item_version`, `tenant_markup_version` |
| **Quoting / Sales** | `quote`, `quote_version`, `quote_line`, `quote_public_link`, `quote_acceptance`, `quote_public_link_contact_action` |
| **Field Ops / Jobs** | `job`, `job_assignment`, `job_time_entry`, `job_expense`, `job_attachment`, `change_order`, `change_order_line` |
| **Invoicing & Billing** | `invoice`, `invoice_line`, `payment`, `payment_type`, `invoice_public_link` |
| **Tax Calculation** | `tax_jurisdiction`, `tax_rate_version`, `quote_line_tax_component`, `invoice_line_tax_component` |
| **Notifications** | `notification_outbox`, `notification_channel`, `notification_delivery_attempt` |
| **QuickBooks Integration** | `app_service`, `integration_credential`, `integration_sync_mapping`, `integration_sync_log`, `integration_sync_conflict` |
| **Subscriptions** | `product_plan`, `product_feature`, `product_plan_version`, `subscription`, `usage_ledger`, `subscription_usage`, `tenant_product_feature_override` |
| **Platform / System** | `idempotency_key`, `tenant_rate_limit`, `audit_log` |
| **Voice AI** | `conversation_session`, `conversation_message` |

### 2.3 pgvector Configuration

```sql
-- Enable extension (required on RDS after provisioning)
CREATE EXTENSION IF NOT EXISTS vector;

-- HNSW index for fast conversation context similarity search
CREATE INDEX idx_conversation_embeddings ON conversation_messages
USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_session_embeddings ON conversation_sessions
USING hnsw (context_embedding vector_cosine_ops);
```

```sql
-- Example: Find similar conversation messages for context resolution
SELECT * FROM conversation_messages
WHERE session_id = :session_id
ORDER BY embedding <=> :query_embedding
LIMIT 5;
```

### 2.4 Database Performance Configuration

**PostgreSQL RDS Parameter Group:**
```ini
# Connection management
max_connections = 100
shared_buffers = 256MB

# Query optimization
effective_cache_size = 1GB
random_page_cost = 1.1        # SSD-optimized
work_mem = 4MB

# Autovacuum
autovacuum = on
autovacuum_max_workers = 3

# Slow query logging
log_min_duration_statement = 1000   # Log queries >1s
log_connections = on
log_disconnections = on

# Replication (Multi-AZ standby)
wal_level = replica
max_wal_senders = 5
```

**Connection pooling:** ECS tasks use SQLAlchemy connection pooling (`pool_size=5`, `max_overflow=10`) to stay within the 100-connection micro-tier limit.

### 2.5 Database Backup Strategy

| Backup Type | Retention | Window |
| :--- | :--- | :--- |
| **Automated daily backups** | 28 days | 03:00–04:00 US-Eastern |
| **Weekly manual snapshots** | Indefinite | Sunday 04:00–05:00 US-Eastern |

**Recovery Objectives:**
- **RTO** (Recovery Time Objective): 4 hours
- **RPO** (Recovery Point Objective): 1 hour

---

## 3. Background Processing

### 3.1 Architecture Overview

**Three-Tier Processing Model:**

| Tier | Technology | Use Case |
| :--- | :--- | :--- |
| **Tier 1** | Celery Beat (cron) | Periodic scheduled tasks (cleanup, sync, billing) |
| **Tier 2** | Celery Workers | Long-running tasks (QB sync, profitability rollups, email delivery) |
| **Tier 3** | Lambda | Lightweight event-driven tasks (<15 min, low frequency) |

**Celery Infrastructure:**
- **Broker**: Redis DB 1 (`redis://redis:6379/1`)
- **Result Backend**: Redis DB 2 (`redis://redis:6379/2`)
- **Worker Concurrency**: 2 threads (CPU-bound tasks)
- **Both worker and beat scheduler** run as Docker containers in all environments

### 3.2 Celery Beat Schedule (All Registered Tasks)

| Schedule Name | Task | Cadence | Purpose |
| :--- | :--- | :--- | :--- |
| `cleanup-expired-idempotency-keys` | `cleanup_expired_idempotency_keys` | Daily at 2:00 AM | Remove 24-hour-old idempotency keys |
| `cleanup-old-failed-keys` | `cleanup_old_failed_keys` | Daily at 2:30 AM | Remove 7-day-old failed keys |
| `poll-pending-notifications` | `poll_pending_notifications` | Every 30 seconds | Process email/SMS notification outbox |
| `expire-old-sessions` | `expire_old_sessions` | Daily at 3:00 AM | Mark sessions > 24 hours as expired |
| `archive-old-sessions` | `archive_old_sessions` | Daily at 3:30 AM | Archive sessions > 30 days |
| `cleanup-orphaned-messages` | `cleanup_orphaned_messages` | Daily at 4:00 AM | Delete orphaned conversation messages |
| `refresh-quickbooks-tokens` | `refresh_quickbooks_tokens` | Every 30 minutes | Proactively refresh QB OAuth tokens before expiry |
| `sync-quickbooks-customers` | `sync_all_tenants_customers` | Every 15 minutes | Incremental bi-directional QB customer sync |
| `archive-audit-logs` | `archive_audit_logs` | Daily at 1:00 AM | Purge audit records older than 90 days |
| `expire-stale-calendar-conflicts` | `expire_stale_calendar_conflicts` | Daily at 5:00 AM | Auto-resolve unresolved calendar sync conflicts past tenant/system threshold (default 30 days); send pre-warning notifications at threshold (default 7 days before) — see §13.5 |
| `notify-etc-variance-owners` | `notify_etc_variance_owners` | Every 15 minutes | Owner notification when projected job cost (actuals + ETC) exceeds quote by `etc_variance_owner_notify_pct` (default 50%) — see §14.3 |
| `cleanup-incomplete-photo-uploads` | `cleanup_incomplete_photo_uploads` | Weekly | Validate and remove orphaned `photo` records whose S3 multipart upload session expired without completion — see §15.5 |
| `process-deferred-voice-audio` | `process_voice_audio_async` | Event-driven (offline audio uploaded) | Whisper transcription + Llama intent parsing for offline-captured voice; route to deferred-confirmation flow if intent is destructive — see §15.7 |
| `expire-deferred-voice-confirmations` | `expire_deferred_voice_confirmations` | Hourly | Cancel deferred voice intents pending confirmation > 24 hours; emit cancellation notification — see §15.7 |
| `cleanup-mobile-sync-events` | `cleanup_mobile_sync_events` | Daily at 5:30 AM | Archive `mobile_sync_event` rows > 30 days consistent with audit retention policy |
| `notify-system-template-updates` | `notify_system_template_updates` | Daily at 6:00 AM | Notify tenants whose recent quotes used a system template that has been updated — see §14.5 |
| `auto-expire-qb-conflicts` | `auto_expire_qb_conflicts_per_tenant` | Hourly | Per-tenant QB conflict auto-expiry per `qb_auto_expire_{entity}_enabled` + `qb_auto_expire_{entity}_direction`; sends pre-warnings — see §5.4 |
| `monitor-sms-quota-thresholds` | `monitor_sms_quota_thresholds` | Hourly | Detect 80% and 100% SMS quota thresholds; dispatch notifications per Tier 2 #5 Billing category — see §17.6 |
| `rollover-sms-quota-periods` | `rollover_sms_quota_periods` | Daily | Create new `sms_quota_period` row at subscription billing cycle boundaries — see §17.6 |
| `enforce-trial-expirations` | `enforce_trial_expirations` | Hourly | Transition expired trials to `trial_expired` state; dispatch paywall notifications — see §20 (Subscription Tier Architecture) |
| `notify-mfa-grace-period-reminders` | `notify_mfa_grace_period_reminders` | Daily at 9 AM tenant local time | Per-tenant MFA enrollment reminders during grace period; daily-escalating copy from gentle (days 0–3) to urgent (days 4–6) to critical (day 7) — see §4.5 |
| `process-help-article-embeddings` | `process_help_article` | Event-driven (S3 upload) + weekly fallback | Re-embed help corpus chunks into pgvector when markdown content changes — see §19 (Help System Architecture) |
| `anonymize-help-sessions` | `anonymize_help_sessions` | Daily | Anonymize help chat sessions older than 90 days; PII detection + tenant-data scrubbing; roll into training corpus — see §19 |
| `cleanup-incomplete-stripe-payment-intents` | `cleanup_incomplete_stripe_payment_intents` | Daily | Clean up abandoned Stripe Payment Intents older than 24 hours that didn't complete |

### 3.3 Task Modules

| File | Tasks |
| :--- | :--- |
| `tasks/cleanup_idempotency_keys.py` | `cleanup_expired_idempotency_keys`, `cleanup_old_failed_keys` |
| `tasks/notification_worker.py` | `poll_pending_notifications` — processes `notification_outbox` via SendGrid |
| `tasks/cleanup_sessions.py` | `expire_old_sessions`, `archive_old_sessions`, `cleanup_orphaned_messages` |
| `tasks/quickbooks_token_refresh.py` | `refresh_quickbooks_tokens` |
| `tasks/quickbooks_sync.py` | `sync_all_tenants_customers` |
| `tasks/archive_audit_logs.py` | `archive_audit_logs` |
| `tasks/profitability_rollup.py` | `calculate_job_profitability` — recalculates `actual_labor_cost_cents`, `actual_material_cost_cents`, `actual_profit_cents` on `job` |
| `tasks/calendar_conflict_expiry.py` | `expire_stale_calendar_conflicts` — auto-resolves stale calendar conflicts per system+tenant tier configuration (§13.5) |
| `tasks/etc_variance_notifier.py` | `notify_etc_variance_owners` — owner notifications when projected (actuals + ETC) exceeds quote threshold (§14.3) |
| `tasks/photo_upload_cleanup.py` | `cleanup_incomplete_photo_uploads` — orphaned S3 multipart sessions cleanup (§15.5) |
| `tasks/voice_deferred_processor.py` | `process_voice_audio_async`, `expire_deferred_voice_confirmations` — deferred voice processing pipeline (§15.7) |
| `tasks/mobile_sync_cleanup.py` | `cleanup_mobile_sync_events` — `mobile_sync_event` retention archival |
| `tasks/system_template_notifier.py` | `notify_system_template_updates` — tenant notification of system template updates (§14.5) |
| `tasks/qb_conflict_expiry.py` | `auto_expire_qb_conflicts_per_tenant` — auto-resolves stale QB conflicts per per-entity tenant configuration (§5.4) |
| `tasks/sms_quota.py` | `monitor_sms_quota_thresholds`, `rollover_sms_quota_periods` — SMS quota tracking + threshold notifications + period boundaries (§17.6) |
| `tasks/trial_management.py` | `enforce_trial_expirations` — transitions expired trials and dispatches paywall (§20) |
| `tasks/mfa_reminders.py` | `notify_mfa_grace_period_reminders` — daily escalating MFA enrollment reminders (§4.5) |
| `tasks/help_corpus.py` | `process_help_article` (event-driven), `anonymize_help_sessions` — help corpus embedding + chat session anonymization (§19) |
| `tasks/stripe_cleanup.py` | `cleanup_incomplete_stripe_payment_intents` — abandoned Stripe payment intent cleanup |

### 3.4 Profitability Rollup Worker

The `profitability_rollup` task is triggered asynchronously whenever a `job_time_entry` or `job_expense` is created or modified. It recalculates:

```
actual_labor_cost_cents  = Σ (time_entry.hours × hourly_rate_cents)
actual_material_cost_cents = Σ (job_expense.cost_cents × (1 + markup_pct))
actual_profit_cents      = quoted_total_cents - actual_labor_cost_cents - actual_material_cost_cents
```

The results are written back to the `job` table, making the contractor's dashboard always current without requiring real-time synchronous computation on the API.

### 3.5 Notification Preference Center Architecture

Pass 4 Tier 2 #5 introduced per-user notification preferences with category × channel granularity. The existing `notification_outbox` infrastructure (per §3.7 PRD; existing `poll_pending_notifications` Celery task per §3.2) is extended with a preference gate that consults user preferences before dispatching.

#### 3.5.1 Notification Category Registry

Every backend firing site classifies notifications into one of eight categories. Sub-trigger metadata drives the user-context-asymmetric forced-minimum semantics.

**Schema** (per A56):

```sql
notification_category (
    category_id              TEXT PRIMARY KEY,
        -- 'quote_approvals' | 'field_issues' | 'sync_conflicts' | 'job_activity'
        -- | 'customer_activity' | 'billing' | 'background_sync_alerts'
        -- | 'system_announcements'
    display_label            TEXT NOT NULL,
    description              TEXT NOT NULL,
    category_group_id        TEXT NULL,        -- Phase 2 forward-compatibility for grouping
    display_order            INTEGER NOT NULL
)

notification_category_sub_trigger (
    sub_trigger_id                       TEXT PRIMARY KEY,
        -- e.g., 'customer_activity.inbound_sms_reply',
        -- 'job_activity.assignment', 'system_announcements.critical'
    category_id                          TEXT NOT NULL REFERENCES notification_category,
    display_label                        TEXT,
    forced_minimum_push_uniform          BOOLEAN NOT NULL DEFAULT FALSE,
    forced_minimum_push_recipient_only   BOOLEAN NOT NULL DEFAULT FALSE
)
```

**Schema extension to `notification_outbox`**:

```sql
ALTER TABLE notification_outbox ADD COLUMN category_id TEXT NOT NULL
    REFERENCES notification_category(category_id);
ALTER TABLE notification_outbox ADD COLUMN sub_trigger_id TEXT NULL
    REFERENCES notification_category_sub_trigger(sub_trigger_id);
ALTER TABLE notification_outbox ADD COLUMN recipient_user_id_originating UUID NULL;
    -- The user the notification "belongs to" for forced-minimum-recipient-only semantics
    -- (e.g., the tech in a customer SMS conversation).
```

**Audit pass requirement**: every existing `notification_outbox.create()` call site (estimated 8 sites across the codebase) needs a category assignment. This is foundational work for A56 — without consistent classification, preferences can't be respected. Audit pass runs as part of A56 implementation.

#### 3.5.2 Default Policy and Preference Schema

Pilot ships system-default policies per category × channel; tenants can override; users can override within tenant policy.

**Schema**:

```sql
notification_default_policy (
    tenant_id        UUID NULL,                -- NULL = Pilot system default
    category_id      TEXT NOT NULL REFERENCES notification_category,
    channel          TEXT NOT NULL,            -- 'push' | 'email' | 'in_app'
    enabled          BOOLEAN NOT NULL,
    UNIQUE (tenant_id, category_id, channel)   -- with NULL handling for system defaults
)

notification_preference (
    tenant_id        UUID NOT NULL,
    user_id          UUID NULL,
        -- NULL = tenant-level override of system default
        -- Non-NULL = user-level override
    category_id      TEXT NOT NULL REFERENCES notification_category,
    channel          TEXT NOT NULL,
    enabled          BOOLEAN NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, user_id, category_id, channel)   -- with NULL handling
)
```

**Pilot system defaults** (seeded at deployment):

| Category | Push | Email | In-app |
| :--- | :---: | :---: | :---: |
| Quote approvals | ON | ON | ON |
| Field issues | ON | ON | ON |
| Sync conflicts | OFF | ON | ON |
| Job activity | ON | OFF | ON |
| Customer activity | ON | OFF | ON |
| Billing | OFF | ON | ON |
| Background sync alerts | ON | OFF | ON |
| System announcements | OFF | ON | ON |

#### 3.5.3 Forced-Minimum Categories

Four categories cannot be muted by user override (push channel only; email and in-app remain user-configurable):

| Category × Sub-trigger | Forced minimum scope |
| :--- | :--- |
| Field issues (all sub-triggers) | All users (uniform forced-minimum) |
| Job activity → `assignment` sub-trigger | The tech being assigned (recipient-only) |
| System announcements → `critical` sub-trigger | All users (uniform forced-minimum) |
| Customer activity → `inbound_sms_reply` sub-trigger | The tech in the conversation (recipient-only) |

**The user-context-asymmetric forced-minimum** for Customer activity is new vocabulary for Pilot. Same category, different semantics depending on who's receiving:

- *Tech in the conversation*: push is forced minimum (cannot mute)
- *Owner receiving ambient awareness about another tech's conversation*: push is fully mutable
- *Other techs not in the conversation*: not in recipient list at all

The dispatcher implements this via per-recipient evaluation against the sub-trigger's `forced_minimum_push_recipient_only` flag plus comparison of `recipient_user_id_originating` to the candidate recipient.

#### 3.5.4 Three-Tier Resolution

Resolution chain for any user × category × channel:

1. If a row exists in `notification_preference` with `tenant_id`, `user_id`, `category_id`, `channel` → use that
2. Else if a row exists with `tenant_id`, `user_id IS NULL`, `category_id`, `channel` (tenant override) → use that
3. Else look up `notification_default_policy` with `tenant_id IS NULL` (Pilot system default) → use that
4. Else fallback constant (default OFF)

Implementation in `services/notification_resolver.py::get_effective_preference(tenant_id, user_id, category_id, channel)`.

**Forced-minimum override logic** (applies after resolution):

```python
effective_value = get_effective_preference(...)
sub_trigger = notification_outbox.sub_trigger_id

# Uniform forced-minimum push
if sub_trigger.forced_minimum_push_uniform AND channel == 'push':
    return True  # Override regardless of user preference

# Recipient-only forced-minimum push
if (sub_trigger.forced_minimum_push_recipient_only
    AND channel == 'push'
    AND recipient_user_id == notification_outbox.recipient_user_id_originating):
    return True

return effective_value
```

#### 3.5.5 Delivery Dispatcher Preference Gate

The existing `poll_pending_notifications` Celery task (§3.2) is extended with the preference gate. For each pending `notification_outbox` entry, for each potential recipient (one notification may have multiple recipients):

1. Look up effective preference for `(category_id, channel)` via the three-tier chain
2. Apply forced-minimum override logic
3. If channel still disabled: skip the channel; log the suppression for support/debugging
4. If all channels for a recipient are skipped: skip the recipient
5. If all recipients are skipped: mark the outbox row as `suppressed_by_preferences`

**Performance**: cache effective preferences per (user, category, channel) for the duration of a single dispatcher poll cycle. Cache invalidated on settings change (write triggers cache eviction in `notification_resolver.py`).

**Composes with rate limiting** (existing per A35): a notification must clear both the rate limit AND the user's preferences to be delivered. Rate limit is system-level (no more than X per category per hour); preferences are user-level (subscription); they compose without conflict.

#### 3.5.6 In-App Banner Channel

The third notification channel is partially new infrastructure. Push and email use existing infrastructure; in-app banner needs new components.

**Schema**:

```sql
in_app_notification (
    notification_id      UUID PRIMARY KEY,
    tenant_id            UUID NOT NULL,
    user_id              UUID NOT NULL,
    category_id          TEXT NOT NULL REFERENCES notification_category,
    body                 TEXT NOT NULL,
    deep_link_target     TEXT NOT NULL,
        -- per-category deep-link mapping; see §3.5.7
    priority             TEXT NOT NULL,            -- 'standard' | 'critical'
    created_at           TIMESTAMPTZ NOT NULL,
    read_at              TIMESTAMPTZ NULL
)
```

**SSE delivery channel** (extends existing SSE infrastructure per §13.11):

- `/sse/notifications` — streams in-app notifications to active sessions for the authenticated user
- Connection authenticated via Cognito JWT (per §4.2)
- One persistent connection per active web session; mobile uses SSE when foregrounded, falls back to push when backgrounded

**Frontend components** (shared web/mobile):

- `<NotificationBanner />` — slide-down from top of active page; auto-dismiss 6s standard / 12s critical; click-to-navigate; ARIA `role="alert"`
- Notification center bell icon in app shell — badge count of unread from last 24 hours; opens panel with last 50 notifications

**APIs**:

- `POST /api/v1/notifications/in-app/mark-read` — mark notification(s) as read
- `GET /api/v1/notifications/in-app/recent?limit=50` — returns last 50 for the bell panel

#### 3.5.7 Push Deep-Link Mapping

Every notification category has a defined deep-link target so tapping a push opens the relevant entity:

| Category | Deep-link target |
| :--- | :--- |
| Quote approvals | `/quotes/approvals/{quote_id}` |
| Field issues | `/dashboard/approvals/field-issues/{escalation_id}` |
| Sync conflicts | `/settings/integrations/{integration}/conflicts/{id}` |
| Job activity | `/jobs/{job_id}` |
| Customer activity | `/customers/{customer_id}/comm-history#thread-{thread_id}` |
| Billing | `/settings/subscription/invoices` |
| Background sync alerts | mobile sync queue surface |
| System announcements | `/settings/announcements/{id}` (Phase 2 surface route reserved) |

Implementation: each `notification_outbox` entry stores its deep-link target alongside the body. Dispatcher includes deep-link in push payload. Frontend handles deep-link routing on tap.

#### 3.5.8 Tenant Defaults Sub-Surface

Owners edit tenant-level defaults at `Settings > Notifications > Tenant defaults` (separate sub-page from `Settings > Notifications > Preferences` to keep scope clear). Same matrix structure; edits affect tenant defaults, not the owner's user override.

RBAC: `notification_preference.tenant_default.edit` — owner only.

#### 3.5.9 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── notification_categories.py    # GET /api/v1/notifications/categories
│   │   ├── notification_preferences.py   # GET/PUT/DELETE preference matrix
│   │   ├── notification_in_app.py        # in-app banner endpoints
│   │   └── ...
│   └── ...
├── services/
│   ├── notification_resolver.py          # three-tier resolution + forced-minimum logic
│   ├── notification_dispatcher.py        # extended with preference gate
│   └── ...
└── tasks/
    └── notification_worker.py            # poll_pending_notifications (extended; existing per §3.2)
```

---

## 4. Authentication & Authorization

### 4.1 AWS Cognito Configuration

| Setting | Value |
| :--- | :--- |
| **Sign-in method** | Email (CITEXT, case-insensitive) |
| **Password policy** | Min 12 chars; requires lowercase, uppercase, numbers, symbols |
| **Temporary password validity** | 7 days |
| **MFA** | Authenticator app, email OTP, or SMS |
| **Account recovery** | Verified email or verified phone |
| **OAuth flows** | Authorization code + PKCE |
| **Scopes** | `email`, `openid`, `profile` |
| **Token expiration** | Access: 1 hour; ID: 1 hour; Refresh: 30 days |
| **Social providers** | Google, Apple |
| **Enterprise** | Custom SAML identity providers (post-MVP) |

### 4.2 JWT Authentication Flow

```
Client → POST /api/v1/auth/login
   ↓
Cognito returns RS256-signed JWT
   ↓
Client sends: Authorization: Bearer <JWT>
   ↓
FastAPI dependency: get_current_user()
   1. Extract unverified header to get key ID (kid)
   2. Fetch JWKS from Cognito:
      https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json
      (JWKS cached in-process to avoid repeated network calls)
   3. Construct RSA public key from matching JWKS entry
   4. Verify JWT signature (RS256) + expiration
   5. Extract email claim from payload
   6. Query DB: User → TenantUser → TenantUserRole
   7. Cache permissions in AuthenticatedUser object
   8. Set request.state.tenant_id + request.state.user_id
   ↓
Returns: AuthenticatedUser(user, tenant_id, role_code, permissions)
```

**Security-Fail-Safe**: If the user's role is not found or is inactive, the system returns `403 Forbidden` — denying access rather than defaulting to permissive behavior.

### 4.3 Role-Based Access Control (RBAC)

**Implementation**: `core/permissions.py`

**Permission Format**: `resource.action`  
**Wildcard Support**:
- `"*"` — Full access (owner role)
- `"quotes.*"` — All actions on quotes
- `"*.view"` — View action on all resources
- `"quotes.create"` — Specific action on specific resource

**Pre-Seeded Roles:**

| Role | Permissions | Description |
| :--- | :--- | :--- |
| `owner` | `["*"]` | Full access to all resources |
| `technician` | `["jobs.*", "time_entries.*", "expenses.*", "voice.use", "nec.calculate", "voice.manage_own_sessions", "schedule.view_own", "quote.submit_for_approval"]` | Field operations only; no financial or integration access |
| `office_staff` | `["customers.*", "quotes.*", "sites.*", "jobs.view", "invoices.*", "voice.manage_own_sessions"]` | Office management; no user or integration admin |
| `accountant` | `["invoices.view", "payments.view", "audit.view", "financials.view", "voice.manage_own_sessions", "voice.provide_feedback", "quote.approve", "quote.apply_discount", "quote_template.create", "quote_template.edit", "quote_template.fork_system"]` | Read-only financial access plus quote review and template management |

**Pass 3 RBAC Additions** (also reflected in role assignments above):

| Permission | Roles | Purpose | Source Flow |
| :--- | :--- | :--- | :--- |
| `quote.submit_for_approval` | technician | Submit tech-created quote for owner review | Flow 5 |
| `quote.approve` | owner, accountant | Approve, reject, or edit-and-approve pending quotes | Flow 5 |
| `quote.apply_discount` | owner, accountant | Apply time-limited discounts within margin cap | Flow 5 |
| `voice.provide_feedback` | owner, accountant | Flag voice misrecognitions; corrections feed model fine-tuning corpus | Flow 1 |
| `voice.manage_own_sessions` | all authenticated roles | Rename, delete, open own conversation sessions | Flow 1 |
| `quote_template.create` | owner, accountant | Save quote as template; create new tenant templates from scratch | Flow 5 |
| `quote_template.edit` | owner, accountant | Edit existing tenant templates | Flow 5 |
| `quote_template.fork_system` | owner, accountant | Fork system templates to tenant ownership for customization | Flow 5 |
| `schedule.manage` | owner, office_staff | Dispatch, assignments (already implemented in Pass 2 — confirmed in role mappings) | Flow 3 |
| `schedule.view_own` | technician | View own assigned schedule (already implemented in Pass 2) | Flow 3 |

**Route-Level Enforcement:**
```python
from core.permissions import require_permission

@router.post("/quotes")
def create_quote(
    current_user: AuthenticatedUser = Depends(require_permission("quotes.create"))
):
    # Only users with quotes.create permission reach this handler
    ...
```

**Error Response (RFC 7807, HTTP 403):**
```json
{
    "type": "https://pilotfortrades.com/errors/forbidden",
    "title": "Insufficient Permissions",
    "status": 403,
    "detail": "You do not have permission to perform this action",
    "required_permission": "invoices.view",
    "user_role": "technician",
    "hint": "Contact your administrator to request the 'accountant' or 'owner' role"
}
```

#### 4.3.1 Operator Role and Hidden Pilot Routes

Pass 4 introduced the **operator role** — a special platform-level role outside tenant RBAC, exclusively for the Pilot operator (Tom). The operator role manages cross-tenant settings via hidden Pilot routes that bypass standard tenant scoping.

**Why a special role**: operator-controlled values (per-tenant trial length override, per-tenant subscription tier override without payment, tenant suspension/restoration, tenant deletion with data purge, system default settings) cannot reasonably be managed through the standard RBAC model. Tenants shouldn't see these settings at all (security boundary), and the operator needs cross-tenant access (data scoping boundary).

**Operator-role permissions**:

| Permission | Purpose |
| :--- | :--- |
| `operator.tenant.override_trial_length` | Set per-tenant trial length override |
| `operator.tenant.override_subscription_tier` | Force a tenant onto a specific subscription tier without payment |
| `operator.tenant.suspend` | Suspend tenant access (e.g., for non-payment, ToS violation) |
| `operator.tenant.delete` | Permanently delete a tenant and all associated data |
| `operator.help_content.edit` | (Phase 2) Admin UI for editing help corpus directly |
| `operator.email_template.edit` | (Phase 2) Admin UI for editing email templates directly |
| `operator.subscription_tier.create_or_edit` | Manage available subscription tiers |
| `operator.feature_flag.toggle` | Operator-level feature flag management |

**Hidden Pilot routes**:

- Path prefix: `/admin/*` (or equivalent — final path TBD)
- Routes are accessible only to users with the `operator` role
- Standard Cognito authentication still applies; operator role is a Cognito user pool group attribute
- Routes bypass tenant scoping (no `require_tenant_isolation()` dependency)
- Routes have stricter rate limiting and audit logging

**MVP implementation strategy**: for MVP, operator-admin functions are managed via direct DB updates (Tom acts as the operator). Hidden Pilot routes are deferred operator infrastructure work. The data model includes operator-controlled fields (`tenant_tier_override.override_trial_length_days`, `tenant_tier_override.override_subscription_tier_id`, etc.); the UI for setting them is genuinely separate operator infrastructure outside Pass 4 design framework.

**Tenant tier override schema**:

```sql
tenant_tier_override (
    tenant_id                       UUID PRIMARY KEY REFERENCES tenant,
    override_tier_id                UUID NULL REFERENCES subscription_tier,
        -- if set, supersedes tenant.current_subscription_tier_id
    override_trial_length_days      INTEGER NULL,
        -- if set, supersedes system_default_trial_length_days
    override_reason                 TEXT NULL,
        -- operator note
    set_by_operator_user_id         UUID NOT NULL REFERENCES user,
    set_at                          TIMESTAMPTZ NOT NULL
)
```

Read by tenant signup flow and trial expiration flow (per §4.7.1).

**Why deferred**: as a solo operator, building admin UI for content editing, tier creation, etc. is real work that doesn't directly enable shipping MVP. Direct DB management is acceptable for the early-customer phase. Phase 2 introduces hidden Pilot routes when operator workload justifies it.

### 4.4 Post-Signup Lambda

The Cognito Post-Confirmation Lambda trigger is the **single account-birth bridge** from a confirmed Cognito identity to RDS. It fires on **every** confirmation in the pool, so it is a **3-path user-provisioning router** (not a blind "create a tenant" step). The join key between Cognito and RDS is **`email`** — the `user` table has **no `cognito_sub` column** (MCP-verified 2026-07-29); Cognito identity resolves to a `user` row by the token's `email` claim. Adding a `cognito_sub` linkage is a separate, larger decision (not taken).

The router branches on `email`:

1. **Path 1 — existing/platform user → no-op.** A `user` row already exists for the email (a platform user — `is_platform_user=true` — or a re-fired confirmation). Do nothing; never create a tenant. Idempotent.
2. **Path 2 — pending-invite attach.** A pending `tenant_user_invite` (`accepted_at IS NULL`, `is_active`, not expired) exists for the email (an invited tenant employee). Create the `user`, attach a `tenant_user` to the invite's `tenant_id` (`joined_at=now`), and set `invite.accepted_at`. Do **not** create a tenant.
3. **Path 3 — new-owner create (self-serve GA).** Neither a `user` nor a pending invite exists (a self-serve tenant owner). Create the `tenant` (with a display-only placeholder name `"{email-local-part}'s Company"`), the owner `user`, the `tenant_user(owner, joined_at=now)`, and the owner role assignment.

The Lambda **must never raise to Cognito** — an unhandled exception fails the confirmation and can strand the user. Because `tenant.name` is **display-only and no longer unique** (the `tenant_name_key` UNIQUE constraint was dropped — see ADR-0012), Path 3 inserts the placeholder name **unconditionally**, with no collision check that could throw. The self-serve wizard (`services/tenant_signup.py`) then **resolves-or-attaches by email** and overwrites the placeholder `tenant.name` with the real business name; it never forks a second tenant. See ADR-0011.

> **Concierge (Beta) vs self-serve (GA)**: in the concierge path Tom runs `AdminCreateUser`, the Lambda's Path 3 (or Path 1, if Tom pre-creates the tenant) provisions RDS, and the wizard is a setup/collection flow. In self-serve GA the client calls Cognito `SignUp` (email+password) via Amplify; on email confirmation the same Lambda router fires. This preserves "the signup path is the single account-birth path" — self-registration does **not** bypass it.

### 4.5 Multi-Factor Authentication

MFA is available for all tenant users (owners, staff, technicians); tenant policy controls whether it's required. Optional for end-customers. Pass 4 Tier 2 #7 introduced full multi-method MFA infrastructure with self-service enrollment and tenant-required policy.

> **Architecture boundary — MFA per-method lockout (FIND-170, Phase 4.2)**: The 5-wrong-attempts → 15-minute method lock behavior documented in this section is enforced entirely by **AWS Cognito** at the identity-provider layer. Pilot's `user_mfa_method` table stores enrollment data only (which methods are configured) — it does NOT replicate lockout state from Cognito. Adding lockout columns to `user_mfa_method` would create a conflicting second source of truth with Cognito's enforcement. This is the correct and intentional architecture. Do not add lockout enforcement to the Pilot schema.

**Supported methods** (Cognito-backed):

- **TOTP** (authenticator apps — Google Authenticator, Authy, 1Password, Apple Passwords) — most secure
- **SMS OTP** — convenient but less secure; vulnerable to SIM swap attacks (surfaced honestly in user UI)
- **Email OTP** — convenient but vulnerable if email account itself is compromised

Users enroll any combination of the three methods at first MFA enrollment. Multi-method enrollment is encouraged via the wizard pattern ("Enroll all three for the strongest lockout protection") to prevent the "lost my phone, locked out" support scenario.

**Recovery codes**: 10 single-use codes generated at first enrollment, displayed once. Hashed via bcrypt before storage in `user_mfa_recovery_code` table. Regenerable on demand (invalidates prior unused codes). Used as ultimate lockout fallback when all enrolled methods are inaccessible.

**Schema** (per A69):

```sql
user_mfa_method (
    mfa_method_id          UUID PRIMARY KEY,
    tenant_id              UUID NOT NULL,
    user_id                UUID NOT NULL,
    method_type            TEXT NOT NULL,  -- 'totp' | 'sms' | 'email'
    enrolled_at            TIMESTAMPTZ NOT NULL,
    last_used_at           TIMESTAMPTZ NULL,
    cognito_method_id      TEXT NOT NULL,
    verification_status    TEXT NOT NULL,  -- 'verified' | 'needs_reverification'
    metadata               JSONB,          -- last 4 digits of phone, etc.
    UNIQUE (tenant_id, user_id, method_type)
)

user_mfa_recovery_code (
    code_id                UUID PRIMARY KEY,
    tenant_id              UUID NOT NULL,
    user_id                UUID NOT NULL,
    code_hash              TEXT NOT NULL,  -- bcrypt-hashed
    generated_at           TIMESTAMPTZ NOT NULL,
    used_at                TIMESTAMPTZ NULL,
    set_id                 UUID NOT NULL   -- groups codes generated together
)
```

**Login challenge flow**:

1. User submits username + password to existing Cognito flow
2. Server checks if MFA is required (per tenant policy or user enrollment) and if user has any methods
3. If multiple methods enrolled: server returns method-selection challenge; user picks one
4. If single method: server initiates challenge with that method directly
5. User enters 6-digit code from chosen method (or 10-character recovery code as escape)
6. Server verifies via Cognito; on success, login completes

**Wrong-code handling**: 5 wrong attempts on a single method locks that method for 15 minutes; user can try a different enrolled method or wait. Per-method lockout is intentional (vs. account lockout) — allows legitimate users with one bad TOTP guess to switch to SMS rather than being fully locked out. After 3 lockouts in 24 hours, account flagged for owner review (Phase 2 enforcement).

> **ARCH-DECISION (FIND-170)**: MFA per-method lockout enforcement is delegated entirely to AWS Cognito (§4.1). Cognito handles attempt counting, per-method lock state, and the 15-minute lockout window at the identity-provider layer. Pilot's `user_mfa_method` table stores enrollment data only — it does NOT replicate lockout state from Cognito. Adding lockout columns to `user_mfa_method` would create a conflicting second source of truth. This is the correct and intentional architecture. Do not add lockout enforcement to the Pilot schema.

**Tenant-required MFA policy** (per A68):

- Tenant setting `tenant_mfa_required` (default FALSE; owner-only edit at `Settings > Users & Roles > Security policy`)
- Tenant setting `tenant_mfa_required_grace_period_starts_at` — populated when policy enabled; drives 7-day grace window
- Tenant setting `tenant_mfa_grace_period_days` (default 7)

**Grace period behavior**:

- Day 0: policy enabled; all tenant users have 7 days to enroll at least one MFA method
- Daily reminder push + email at 9 AM tenant local time during grace period
- During grace, warning banner persistent in app; user with valid session continues working
- Login-trigger enforcement: any login during grace activates immediate enrollment for that session
- After grace: every login by an unenrolled user forces enrollment before any other action

**Existing authenticated sessions**: continue working through grace period until next login. Preserves in-flight tech work; eventual enforcement is guaranteed because tokens eventually expire (refresh token TTL per §4.6).

**Owner reset of user MFA** (support escape hatch, per A69): owner can remove all MFA methods + recovery codes for any user via `Settings > Users & Roles > [user detail] > Reset MFA`. User re-enrolls on next login. Notifies user via email + push. Audit log captures actor and target. Owner self-reset of own MFA also supported (with password re-verification).

**Forced-minimum push for grace-period reminders**: per §22 Notification Preference Center, day-7 final reminder uses forced-minimum push (System announcements critical sub-trigger). Days 0–6 reminders use standard notification preferences (user can mute push if they want).

### 4.6 Refresh Token TTL & Offline Scenario

Cognito refresh tokens default to 30-day TTL, which is adequate for the platform's 72-hour offline hard limit (§15.10). The 30-day window means a tech who works offline for the full 72-hour limit and then takes another week off still has a valid refresh token waiting on return. Refresh-failure handling (per §15.10) preserves locally captured data through re-authentication, so token expiry does not cause data loss.

**Operational guard**: the refresh token TTL must not be reduced below 7 days without a corresponding reduction in the `offline_hard_limit_hours` tenant setting. Document this in the operational runbook.

### 4.7 Onboarding State Machine

Pass 4 Tier 3 #10 introduced the tenant signup wizard with resumable state. The state machine handles tenant creation, legal acceptance recording, optional phone verification, subscription tier selection, and trial-to-paid conversion.

#### 4.7.1 Wizard State Model

**Schema**:

```sql
tenant_signup (
    tenant_id                UUID PRIMARY KEY,
    signup_state             TEXT NOT NULL,
        -- 'step1_account' | 'step2_legal' | 'step3_phone' | 'step4_tier'
        -- | 'step5_confirm' | 'complete'
    signup_started_at        TIMESTAMPTZ NOT NULL,
    signup_completed_at      TIMESTAMPTZ NULL,

    -- Collected during step 1 (then propagated to tenant + user records)
    business_name            TEXT NOT NULL,
    trade                    TEXT NOT NULL,
    business_size            TEXT NOT NULL,
    zip                      TEXT NOT NULL,
    time_zone                TEXT NOT NULL
)
```

**Tenant table extensions**:

```sql
ALTER TABLE tenant ADD COLUMN current_subscription_tier_id UUID NOT NULL
    REFERENCES subscription_tier;
ALTER TABLE tenant ADD COLUMN trial_started_at TIMESTAMPTZ NULL;
ALTER TABLE tenant ADD COLUMN trial_ends_at TIMESTAMPTZ NULL;
ALTER TABLE tenant ADD COLUMN trial_length_days_override INTEGER NULL;
    -- set by operator if differs from system default
ALTER TABLE tenant ADD COLUMN stripe_customer_id TEXT NULL;
    -- populated on first paid conversion
```

**State transitions**:

| State | Next state | Trigger |
| :--- | :--- | :--- |
| (none) | `step1_account` | `POST /api/v1/signup` initiates signup |
| `step1_account` | `step2_legal` | Account created in Cognito; tenant record created |
| `step2_legal` | `step3_phone` | All required legal documents accepted |
| `step3_phone` | `step4_tier` | Phone verified OR explicitly skipped |
| `step4_tier` | `step5_confirm` | Tier selected (Trial or paid) |
| `step5_confirm` | `complete` | Trial confirmation OR paid Stripe payment success |

**Resumability**: a user logging in with `signup_state != 'complete'` is routed to wherever they left off. Wizard pre-fills fields from already-collected state. Users can navigate back through completed steps to review/edit (within scope — already-created Cognito account can't be undone).

**APIs** (per A73):

- `POST /api/v1/signup` — initiate signup; creates tenant in `step1_account` state
- `PUT /api/v1/signup/{tenant_id}/step{N}` — advance the wizard one step at a time
- `GET /api/v1/signup/{tenant_id}/state` — get current signup state for resumability

#### 4.7.2 Legal Acceptance Recording

Per A74, every legal document acceptance is captured with audit-grade fidelity.

**Schema**:

```sql
tenant_legal_acceptance (
    acceptance_id            UUID PRIMARY KEY,
    tenant_id                UUID NOT NULL REFERENCES tenant,
    user_id                  UUID NOT NULL REFERENCES user,
    document_type            TEXT NOT NULL,
        -- 'tos' | 'privacy' | 'eula' | 'marketing_email_optin'
    document_version_hash    TEXT NOT NULL,
        -- sha256 of document content at time of acceptance
    accepted_at              TIMESTAMPTZ NOT NULL,
    ip_address               INET NOT NULL,
    user_agent               TEXT NOT NULL
)
```

Multiple rows per (tenant_id, user_id, document_type) are allowed if document version changes and user re-accepts.

**Document version hashing**: each legal document's content is hashed at deployment. Hash changes when document content changes. Tenants whose accepted hash differs from current are prompted to re-accept on next login (Phase 2 — re-acceptance flow not in MVP).

#### 4.7.3 Onboarding Checklist Resumability

Per A77, the post-wizard checklist persists across sessions and across users in the tenant.

**Schema**:

```sql
tenant_onboarding_checklist (
    tenant_id                          UUID PRIMARY KEY,
    account_created                    BOOLEAN NOT NULL DEFAULT FALSE,
    legal_accepted                     BOOLEAN NOT NULL DEFAULT FALSE,
    tier_selected                      BOOLEAN NOT NULL DEFAULT FALSE,
    first_customer_added               BOOLEAN NOT NULL DEFAULT FALSE,
    first_customer_added_at            TIMESTAMPTZ NULL,
    catalog_setup                      BOOLEAN NOT NULL DEFAULT FALSE,
    catalog_setup_at                   TIMESTAMPTZ NULL,
    quickbooks_connected               BOOLEAN NOT NULL DEFAULT FALSE,
    quickbooks_skipped                 BOOLEAN NOT NULL DEFAULT FALSE,
    calendar_connected                 BOOLEAN NOT NULL DEFAULT FALSE,
    calendar_skipped                   BOOLEAN NOT NULL DEFAULT FALSE,
    team_invited                       BOOLEAN NOT NULL DEFAULT FALSE,
    team_skipped                       BOOLEAN NOT NULL DEFAULT FALSE,
    checklist_hidden                   BOOLEAN NOT NULL DEFAULT FALSE,
    checklist_dismissed_permanently    BOOLEAN NOT NULL DEFAULT FALSE
)
```

**Auto-completion detection**: existing event handlers in customer-create, catalog-item-create, OAuth-complete, team-invite-send domains invoke `tenant_onboarding_checklist::mark_complete(tenant_id, item)` when the corresponding action occurs via any path. Adding a customer via voice command triggers the same auto-completion as adding via the checklist's "Add now" button.

**Persistence is per-tenant** (not per-user): once an item is complete, every user in the tenant sees it as complete. This matches user expectations for shared setup tasks.

#### 4.7.4 Mobile Push Permission Tracking

Per A78, mobile push permission state is tracked per-device.

**Schema**:

```sql
mobile_push_permission_state (
    tenant_id                            UUID NOT NULL,
    user_id                              UUID NOT NULL,
    device_id                            UUID NOT NULL REFERENCES mobile_device_push_token,
    permission_state                     TEXT NOT NULL,
        -- 'not_asked' | 'granted' | 'denied_by_user_choice'
        -- | 'denied_by_os' | 'revoked_in_settings'
    last_state_change_at                 TIMESTAMPTZ NOT NULL,
    dismissable_banner_dismissed_at      TIMESTAMPTZ NULL,
    PRIMARY KEY (tenant_id, user_id, device_id)
)
```

Mobile app reads `permission_state` on launch. If `not_asked` and onboarding is complete, mobile setup phase fires (with pre-explainer screen before OS prompt). State changes propagate via `PUT /api/v1/users/me/devices/{device_id}/push-permission`.

**Banner reappearance logic**: when state is denied, dismissable banner shows on Today tab; user can dismiss (recorded in `dismissable_banner_dismissed_at`); banner reappears once after 7 days from dismissal; doesn't reappear after second dismissal.

#### 4.7.5 Trial Expiration Enforcement

Per A73, the `enforce_trial_expirations` Celery task (registered in §3.2) handles trial transitions.

**Pipeline**:

1. Hourly: query tenants where `trial_ends_at <= now()` AND `current_subscription_tier_id` is the trial tier
2. Transition tenant to `trial_expired` state (in subscription tier metadata; tier doesn't change, but a trial-expired flag activates the paywall)
3. Dispatch paywall notification (push + email + in-app banner via §3.5)
4. Tenant enters read-only mode: existing data visible; new data creation blocked; SMS sending blocked; voice intents available but limited to read-only operations

**Read-only enforcement** runs at the API layer: for tenants in trial-expired state, the API gateway middleware checks the tier flag and returns a structured 402 (Payment Required) response with `{paywall: true, message: ...}` for any write operation. Frontend handles 402 by surfacing the paywall.

**Pre-expiration warnings**: separate notifications dispatched at:
- 7 days before expiration (gentle)
- 3 days before (more urgent)
- 1 day before (final)
- Day of expiration (paywall active)

Implemented as scheduled Celery tasks reading from `tenant.trial_ends_at`.

#### 4.7.6 Tax Setup Just-In-Time Sub-Flow

Tax setup is the only contextual gate during onboarding. Tenants can use Pilot fully without tax setup until they attempt to generate an invoice.

**Detection**: server-side check on every quote-to-invoice conversion attempt and direct invoice creation attempt. If tax setup is incomplete (no `tax_jurisdiction` configured for the tenant), returns 412 (Precondition Required) with a structured payload that frontend uses to render the contextual sub-flow.

**Auto-detection**: tenant's primary tax jurisdiction is suggested from the ZIP code captured during signup step 1. User confirms or changes during the sub-flow.

After tax setup completes, subsequent invoice operations bypass the gate — the sub-flow only fires once.

### 4.8 Account Settings — Active Sessions and Data Export

Pass 4 Tier 2 #7 introduced active sessions management and personal data export request. MFA is covered in §4.5; profile and password management use existing user model. This section covers the two new capabilities.

#### 4.8.1 Active Sessions List + Revoke

Per A70, users can view all currently-logged-in sessions for their account with device + browser + last-active timestamp + approximate location. Per-session revoke and "Revoke all other sessions" affordances.

**Schema** (extends existing token storage):

```sql
user_session_metadata (
    session_id              UUID PRIMARY KEY,
    tenant_id               UUID NOT NULL,
    user_id                 UUID NOT NULL REFERENCES user,
    device_fingerprint      TEXT NOT NULL,
        -- User-Agent + characteristics
    display_label           TEXT NOT NULL,
        -- e.g., "Chrome on macOS", "Pilot mobile on iPhone"
    ip_address              INET NOT NULL,
    geolocation             TEXT NULL,
        -- approximate; city/state from IP geolocation
    created_at              TIMESTAMPTZ NOT NULL,
    last_active_at          TIMESTAMPTZ NOT NULL,
    revoked_at              TIMESTAMPTZ NULL
)
```

Populated on login from User-Agent parsing + IP geolocation lookup (MaxMind GeoLite2 free tier or equivalent — city-level accuracy adequate; not security-critical).

**APIs**:

- `GET /api/v1/users/me/sessions` — list all active sessions for requesting user
- `DELETE /api/v1/users/me/sessions/{session_id}` — revoke specific session (invalidates Cognito refresh token; clears access token cache)
- `POST /api/v1/users/me/sessions/revoke-others` — bulk revoke all sessions except the current one

**Revoke behavior**: revoking a session immediately invalidates the refresh token; the next API request from that session returns 401, forcing re-login.

**The "Revoke all other sessions" affordance** is the user's primary self-service security action when suspecting account compromise. UI placement is intentionally prominent on the Active Sessions page.

**Password change auto-revoke** (per Tier 2 #7 Decision 3): on successful password change, all sessions other than the current one are auto-revoked as a security best practice. User remains logged in on the changing device; other devices require re-login.

#### 4.8.2 Personal Data Export Request

Per A71, users can request a full export of their accessible tenant data with RBAC-scoped contents. Background job compiles the export; download link emailed to user when ready.

**Schema**:

```sql
data_export_request (
    export_id            UUID PRIMARY KEY,
    tenant_id            UUID NOT NULL,
    user_id              UUID NOT NULL REFERENCES user,
    requested_at         TIMESTAMPTZ NOT NULL,
    status               TEXT NOT NULL,
        -- 'pending' | 'processing' | 'ready' | 'expired' | 'failed'
    s3_path              TEXT NULL,                        -- set when ready
    signed_url           TEXT NULL,                        -- 7-day signed S3 URL
    expires_at           TIMESTAMPTZ NULL,
    data_scope           TEXT NOT NULL,
        -- 'full_tenant' (owner/accountant) | 'user_specific' (technician)
    failure_reason       TEXT NULL
)
```

**Frequency limit**: maximum one pending or recent (within 24 hours) request per user. Enforced at request time.

**Export pipeline** (`tasks/data_export_pipeline.py`):

1. Celery task processes pending exports
2. Queries data per RBAC scope (owner: full tenant; technician: only own jobs/time/expenses/communications)
3. Streams to S3 in chunks (avoids in-memory bloat for large tenants — important for tenants with years of data)
4. Generates CSV files per entity type: customers.csv, jobs.csv, quotes.csv, invoices.csv, time_entries.csv, expenses.csv, communications.csv
5. Bundles into ZIP with `MANIFEST.json` containing metadata (export request time, requesting user, tenant_id, data scope)
6. Generates signed S3 URL with 7-day expiration
7. Sends email to requesting user with download link via existing notification infrastructure
8. Updates `data_export_request.status` to `ready`

**APIs**:

- `POST /api/v1/users/me/data-exports` — request new export (subject to 24-hour frequency limit)
- `GET /api/v1/users/me/data-exports` — list recent exports for requesting user
- `GET /api/v1/users/me/data-exports/{export_id}` — get specific export status

**Email template**: new transactional email "Your data export is ready" with download link + expiration date (template `data_export_ready` per §18.8).

**Backend module**: `tasks/data_export_pipeline.py` for the Celery task; `services/data_export_compiler.py` for the streaming CSV/ZIP generation logic.

---

## 5. QuickBooks Integration

### 5.1 OAuth 2.0 Connection Flow

```
1. Contractor clicks "Connect QuickBooks"
   ↓
2. Backend generates state token (CSRF protection) + stores in Redis
   ↓
3. Redirect to:
   https://appcenter.intuit.com/connect/oauth2
   ?client_id=...&redirect_uri=...&state=...&scope=com.intuit.quickbooks.accounting
   ↓
4. Contractor authenticates with Intuit → grants access
   ↓
5. Intuit redirects to:
   /api/v1/integrations/quickbooks/callback?code=...&state=...&realmId=...
   ↓
6. Backend:
   a. Verify state token (CSRF check)
   b. Exchange authorization code for access + refresh tokens
   c. Encrypt tokens using Fernet (AES-128-CBC + HMAC-SHA256 symmetric)
   d. Store in integration_credential table (secret_json: {access_token_encrypted, refresh_token_encrypted})
   e. Store realm_id in app_service.external_account_id
   f. Trigger initial customer sync (Celery task)
```

**ngrok tunnel** (local development only): Exposes `localhost:8000` to `https://your-tunnel.ngrok-free.dev` for Intuit's HTTPS-required OAuth callback and webhook delivery.

### 5.2 Token Encryption & Refresh

**Encryption**: All OAuth tokens are encrypted with Fernet (`cryptography` library) before storage. The `ENCRYPTION_KEY` (32-byte URL-safe base64) is stored in AWS Secrets Manager.

**Token Refresh Logic** (in `services/quickbooks_sync.py`):
```python
# Automatic refresh: if token expires within 5 minutes, refresh before use
time_until_expiry = (credential.expires_at - datetime.now(UTC)).total_seconds()
if time_until_expiry < 300:
    await _refresh_qbo_token_impl(tenant_id, user_id, db)
```

The `tasks/quickbooks_token_refresh.py` Celery Beat task proactively refreshes all active tokens every 30 minutes.

### 5.3 Bi-Directional Sync Strategy

| Entity | Pilot → QB | QB → Pilot | Conflict Master |
| :--- | :---: | :---: | :--- |
| **Customers** | ✅ Yes | ✅ Yes | User choice (sync_preference) |
| **Quotes** | ✅ Yes (as Estimates) | ✅ Yes | Pilot |
| **Jobs** | ❌ No | ❌ No | Pilot only |
| **Invoices** | ✅ Yes | ✅ Yes | QB |
| **Payments** | ❌ No | ✅ Yes | QB |
| **Expenses** | ✅ Yes | ✅ Yes | User choice |
| **Tax Components** | ✅ Yes (via Tax Agency mapping) | ❌ No | Pilot |

**Sync Algorithm (Customer Example):**
```
Celery Beat fires sync_all_tenants_customers every 15 min
   ↓
For each tenant with active QB connection:
   1. Get last_synced_at from integration_sync_mapping
   2. Query QB: SELECT * FROM Customer WHERE MetaData.LastUpdatedTime > :last_sync
   3. For each QB customer:
      a. Check integration_sync_mapping by external_id
      b. If mapping exists: check for CONFLICT (both version tokens changed)
         - If CONFLICT: write to integration_sync_conflict → notify owner
         - If no conflict: UPDATE customer in Pilot
      c. If no mapping: CREATE customer + mapping record
   4. Update external_version_token in mapping
```

### 5.4 Conflict Detection & Resolution

### 5.4 Conflict Detection & Resolution

**Detection** (in `services/quickbooks_sync.py::detect_conflict()`):

```python
qb_changed     = qb_token != mapping.external_version_token
pilot_changed  = customer.updated_at.isoformat() != mapping.internal_version_token
CONFLICT       = qb_changed AND pilot_changed
```

**Resolution UI** (Pass 4 Tier 1 #2; backend in A49–A50): The QuickBooks conflict resolution UI inherits the design vocabulary established in §13.5 calendar conflict resolution, formalized as the bilateral integration conflict resolution pattern in §16.10.

- Surface: `Settings > Integrations > QuickBooks > Conflicts`
- Side-by-side two-column diff with field-level track-changes highlighting per §16.2
- Master-aware column ordering: Pilot-left for Quote conflicts; QB-left for Invoice conflicts; tenant override determines for Customer/Expense
- Two-button bottom action bar with master-aware primary-button treatment
- Deletion-conflict variants with distinct verb-based treatment (parallel to §13.5)
- Pre-commit staleness check per §16.4 with three 409 payload types: `server_changed`, `auto_recovered`, `stale`
- Voice scope: status-query-only via `list_pending_qb_conflicts` voice intent (per §6.2). No voice resolution due to accounting integrity stakes — refusal-with-redirect for resolution attempts.

**Schema extensions to `integration_sync_conflict`** (per A49):

```sql
ALTER TABLE integration_sync_conflict ADD COLUMN base_snapshot JSONB NOT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN field_diffs JSONB NOT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN pilot_modified_at TIMESTAMPTZ NOT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN pilot_modified_by_user_id UUID NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN qb_modified_at TIMESTAMPTZ NOT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN qb_modified_by_external_user_label TEXT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN auto_expire_at TIMESTAMPTZ NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN pre_warning_at TIMESTAMPTZ NULL;
```

**Resolution paths**:

- `accept_local` — push Pilot snapshot to QB
- `accept_remote` — write QB snapshot to Pilot
- `restore_and_accept_remote` — for `Deleted ↔ Modified`: restore Pilot entity from QB
- `recreate_and_keep_local` — for `Modified ↔ Deleted`: push Pilot snapshot back to QB
- `delete_both` — accept the deletion in both systems

**Per-entity auto-expiry** (per A50, Tier 1 #2 Decision 9): unlike calendar's ON-by-default, QB auto-expiry is OFF by default for all four entity types (Customers, Quotes, Invoices, Expenses) — accounting integrity stakes are higher and masters are heterogeneous. Tenants opt in per entity type with paired enable + direction settings (`qb_auto_expire_{entity}_enabled` + `qb_auto_expire_{entity}_direction`). When enabled, auto-expiry timing uses `qb_auto_expire_days` (default 60 — longer than calendar's 30 because accounting cadence is quarterly) and `qb_pre_warning_days` (default 14). Settings UI uses save-on-group-complete pattern (per Settings IA framework Decision 5) to prevent half-baked enable-without-direction state.

**Invoice-specific financial-delta callout** (per Tier 1 #2 Decision 6): for invoice conflicts only, the resolution view includes a financial-delta callout above the diff showing total amount delta, AR impact preview, tax-period spanning warning when applicable, and a deep-link out to the invoice in QB's web UI. This recognizes that invoice conflicts have downstream financial consequences (AR balances, tax filing) that calendar/customer/expense conflicts don't have.

**In-Flight Sync Indicator** (per §16.13): the QuickBooks sync surface uses the platform-wide pattern with QB-specific count semantics (pending entity changes in either direction).

**Auto-expiry Celery task**: `auto_expire_qb_conflicts_per_tenant` (per §3.2). Hourly cadence. Reads tenant per-entity settings, fires pre-warning notifications at `pre_warning_at`, commits to tenant-configured direction at `auto_expire_at`.

### 5.5 Webhook Handler

The `api/routes/webhooks.py` route handles real-time QB change notifications:
- Validates HMAC-SHA256 signature using `QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN`
- Dispatches sync task for changed entities immediately (bypasses 15-minute polling)

---

## 6. Voice AI Pipeline

### 6.1 End-to-End Architecture

```
User speaks
   ↓
Browser (Web) or Expo app (Mobile) captures audio
expo-av + WebSockets for streaming; Web MediaRecorder API for batch
   ↓
POST /api/v1/voice/command  (audio blob, multipart/form-data)
   ↓
FastAPI validates auth + permissions (voice.use required)
   ↓
HTTP call to Whisper server → http://whisper:8000/v1/audio/transcriptions
Model: Whisper Large-v3 (via faster-whisper-server)
Latency: 300–800ms
   ↓
Transcript text → HTTP call to Ollama → http://ollama:11434/api/generate
Model: llama3.1:8b
Prompt: System prompt + conversation context + user utterance
Output: {intent_type, entities} JSON
Latency: 150–400ms
   ↓
voice_action_router.execute_action(intent_type, entities, user, db, session)
   ↓
Intent handler executes business logic (see 6.2)
Updates context_window_json on conversation_session
   ↓
Returns structured JSON response:
{
    "action": "create_quote",
    "success": true,
    "message": "Created Quote for Tom Johnson. What would you like to add?",
    "data": {"quote_id": "...", "customer_id": "..."},
    "next_prompts": ["Add line items", "Send to customer"]
}
   ↓
Text-to-Speech: Native browser SpeechSynthesis API or Expo expo-speech
User hears audio confirmation
```

**Target latency:** < 2 seconds end-to-end (Whisper + Ollama + DB write)

### 6.2 Voice Intent Handlers (Registered in INTENT_HANDLERS)

All handlers are implemented in `services/voice_action_router.py`. Pass 3 added substantially to the registry; the intents below are organized by domain.

**Quote & customer creation intents** (Flow 1):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `create_quote` | `create_quote_via_voice` | "Create a quote for Mike's Diner" |
| `add_quote_line` | `add_line_via_voice` | "Add 10 feet of 12-gauge wire" |
| `create_customer` | `create_customer_via_voice` | "Create customer John Smith" |
| `create_job` | `create_job_via_voice` | "Create a service call job for Site 42" |
| `send_quote` | `send_quote_via_voice` | "Send the quote to the customer" — confirm-as-turn applies |

**Field operations intents** (Flows 1, 7):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `log_time_entry` | `log_time_entry_via_voice` | "Log 3 hours on the Johnson panel upgrade" — offline-capable per §15 |
| `add_expense` | `add_expense_via_voice` | "Add $45.99 expense for breakers from Home Depot" — offline-capable |
| `clock_in` | `clock_in_via_voice` | "Clock in to the Johnson job" — offline-capable |
| `clock_out` | `clock_out_via_voice` | "Clock out — 3.5 hours remaining" — captures ETC at clock-out per §14.3; offline-capable |
| `confirm_loto` | `confirm_loto_via_voice` | "LOTO confirmed" — offline-capable |
| `update_job_status` | `update_job_status_via_voice` | "Mark Davis as complete" — offline-capable |

**Query intents** (Flow 2):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `query_job_profit` | `get_job_profitability` | "What's the profit on the Johnson job?" |
| `query_job_etc_status` | `get_job_etc_status_via_voice` | "How are we tracking on the Davis job?" — returns actuals + ETC vs. quote |
| `query_pending_calendar_conflicts` | `query_pending_calendar_conflicts_via_voice` | "Do I have any pending sync conflicts?" |

**NEC / navigation / session management** (Flows 1):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `calculate_voltage_drop` | `calculate_nec_voltage_drop` | "Calculate voltage drop for 200 feet of 10 AWG" |
| `navigate` | `return_navigation_command` | "Show me active jobs" |
| `switch_session` | `switch_conversation_session_via_voice` | "Switch to the Johnson session" |
| `rename_session` | `rename_conversation_session_via_voice` | "Rename this session to 'Davis 200A panel'" |
| `delete_session` | `delete_conversation_session_via_voice` | "Delete this session" — confirm-as-turn applies |

**Schedule & dispatch intents** (Flow 3):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `schedule_job` | `schedule_job_via_voice` | "Schedule the Davis service call for tomorrow at 2pm" |
| `reassign_job` | `reassign_job_via_voice` | "Reassign the Davis job to Luis" — confirm-as-turn applies |
| `reschedule_job` | `reschedule_job_via_voice` | "Reschedule the Johnson panel upgrade to Thursday at 10am" — confirm-as-turn |
| `check_next_job` | `check_next_job_via_voice` | "What's my next job?" |

**Customer communications intents** (Flow 4 — all route through always-preview-before-send per PRD §3.7 / ARCH §16.7):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `tell_customer` | `tell_customer_via_voice` | "Tell Tom I'm 20 minutes out" — `on_my_way` template with live ETA |
| `tell_customer_running_late` | `tell_customer_running_late_via_voice` | "Tell Davis I'm running 30 minutes late" |
| `tell_customer_arrived` | `tell_customer_arrived_via_voice` | "Tell the customer I just arrived" |
| `tell_customer_completed` | `tell_customer_completed_via_voice` | "Tell Johnson the work is done" |

**Quote approval intents** (Flow 5 — confirm-as-turn applies):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `approve_quote` | `approve_quote_via_voice` | "Approve the Johnson quote" |
| `reject_quote` | `reject_quote_via_voice` | "Reject the Davis quote — pricing too aggressive" |
| `request_quote_edits` | `request_quote_edits_via_voice` | "Send the Davis quote back for edits — flag the discount" |

**Calendar conflict resolution intents** (Flow 6 — confirm-as-turn applies; refusal-with-redirect for blended attempts):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `resolve_calendar_conflict_local` | `resolve_calendar_conflict_local_via_voice` | "Accept the Pilot version of the Johnson conflict" |
| `resolve_calendar_conflict_remote` | `resolve_calendar_conflict_remote_via_voice` | "Use the calendar version of the Johnson conflict" |
| `restore_deleted_job_from_calendar` | `restore_deleted_job_from_calendar_via_voice` | "Restore the Davis job from calendar" — Deleted ↔ Modified |
| `delete_calendar_event_too` | `delete_calendar_event_too_via_voice` | "Delete the Davis calendar event too" — Deleted ↔ Modified |
| `recreate_calendar_event_from_local` | `recreate_calendar_event_from_local_via_voice` | "Recreate the Davis calendar event from Pilot" — Modified ↔ Deleted |
| `delete_pilot_job_from_conflict` | `delete_pilot_job_from_conflict_via_voice` | "Delete the Davis Pilot job" — Modified ↔ Deleted |

**Field issue resolution intents** (Pass 4 Tier 1 #1 — confirm-as-turn applies; refusal-with-redirect for deletion-conflict variants):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `list_pending_field_issues` | `list_pending_field_issues_via_voice` | "Do I have any field issues?" |
| `resolve_field_issue` | `resolve_field_issue_via_voice` | "Resolve Mike's time entry — use his version" |

**QuickBooks conflict status intents** (Pass 4 Tier 1 #2 — status-query only; no voice resolution per Tier 1 #2 Decision 8):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `list_pending_qb_conflicts` | `list_pending_qb_conflicts_via_voice` | "Do I have any QuickBooks conflicts?" |

**Customer SMS reply intents** (Pass 4 Tier 1.5 — confirm-as-turn applies; always-preview-before-send per §16.7):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `reply_to_customer_sms` | `reply_to_customer_sms_via_voice` | "Reply to John saying running 30 minutes late" |

**Help intents** (Pass 4 Tier 4 #14 — routes to AI-mediated help with RAG context):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `open_help` | `open_help_via_voice` | "Open help" / "I have a question" |
| `ask_help_question` | `ask_help_question_via_voice` | "Help me with QuickBooks setup" / "How do I create a quote?" |

### 6.3 Multi-Turn Context Management

The `conversation_session.context_window_json` JSONB field carries session state across multiple turns, enabling pronoun and reference resolution:

```json
{
    "active_quote_id": "uuid",
    "active_job_id": "uuid",
    "active_customer_id": "uuid",
    "active_site_id": "uuid",
    "last_action": "create_quote",
    "timestamp": "2026-04-20T14:30:00Z",
    "pending_confirmation": null,
    "safety_loto_verified": false
}
```

**Example multi-turn flow:**
```
User: "Create quote for Tom Johnson"
→ AI: "Created Quote for Tom Johnson. What would you like to add?"
   [context: active_quote_id = Q-001, active_customer_id = C-001]

User: "Add a 200 amp service panel"
→ AI: "Added 200 amp service panel to Tom's quote."
   [resolves "Tom's" from active_customer_id in context]

User: "Log 4 hours on it"
→ AI: "Which job is this for?"
   [no active_job_id in context — prompts for clarification]

User: "What's the total?"
→ AI: "The total for Tom Johnson's quote is $3,250."
   [resolves "total" to active_quote_id]
```

### 6.4 Conversation Sessions & Structured Message Payload

Conversation sessions are first-class entities — named, numbered, persisted, resumable. Each session is a sequence of messages with structured content payloads.

**Session schema** (extension of existing `conversation_session` table):

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `session_number` | INT NOT NULL | Monotonically increments per tenant; user-facing identifier ("#3 — Johnson panel quote") |
| `title` | TEXT NULL | User-overridable name; auto-generated by Llama from first meaningful exchange |
| `title_auto_generated` | BOOLEAN | TRUE if title is AI-generated and may auto-update; FALSE if user explicitly renamed |
| `context_window_json` | JSONB | Active references, pending confirmations, safety flags (see §6.3) |
| `archived_at` | TIMESTAMPTZ NULL | Set by `archive_old_sessions` Celery task when > 30 days inactive |

**Auto-generated titles**: when the first meaningful exchange completes (typically 2–3 turns in), an async Celery task calls Llama with a summarization prompt to generate a session title. As the session evolves, the title may be regenerated if `title_auto_generated = TRUE` and the topic shifts substantively. User rename via the `rename_session` voice intent or web UI sets `title_auto_generated = FALSE`, freezing the user's chosen title.

**Structured message payload** — `conversation_message.structured_content_json`:

```json
{
  "render_mode": "live | snapshot",
  "content_type": "quote_draft | job_etc_status | conflict_summary | text",
  "data": { ... type-specific payload ... },
  "captured_at": "2026-04-26T14:30:00Z"
}
```

- **Live mode**: render with current data fetched at view time. Used when the message refers to a still-evolving entity (e.g., "What's the ETC on the Davis job?" → live job status). The frontend re-fetches on view.
- **Snapshot mode**: render with frozen data captured at message time. Used for confirmation receipts, decisions made, "what we discussed at that turn." The data is fixed in the JSONB payload.
- The frontend distinguishes the two visually (live mode shows a refresh icon; snapshot mode is static).

### 6.5 GPU Instance Configuration

| Component | Details |
| :--- | :--- |
| **Instance** | EC2 g4dn.xlarge (NVIDIA T4, 16GB VRAM) |
| **Whisper** | `fedirz/faster-whisper-server` image, model: `turbo` (~1.5GB), port 8080 |
| **Ollama** | `ollama/ollama` image, model: `llama3.1:8b` (~4.7GB), port 11434 |
| **Capacity** | Handles up to 500 concurrent tenants before requiring a second instance |
| **Cost model** | Flat $384/month — unlimited transcriptions + unlimited intent parsing |

### 6.6 Confirm-as-Turn for Destructive Actions

Every voice intent that creates, modifies, or deletes durable data routes through an explicit confirmation turn before commit. This is a platform-wide pattern (also documented in §16.3 as a cross-cutting pattern).

**Implementation flow**:

1. Voice intent handler parses utterance → extracts entities → identifies the destructive operation
2. Handler does NOT immediately execute. Instead, it writes to `conversation_session.context_window_json.pending_confirmation`:
   ```json
   {
     "intent_type": "send_quote",
     "entities": {"quote_id": "uuid", "recipient": "tom@johnson.example.com"},
     "summary_prompt": "You're about to send the Johnson panel quote to tom@johnson.example.com — confirm?",
     "expires_at": "2026-04-26T14:32:00Z"
   }
   ```
3. AI returns the summary prompt as the response; user's next utterance is interpreted as confirmation
4. **Affirmative response** (yes / confirm / do it / go ahead / send it) → handler executes the actual API call; `pending_confirmation` cleared
5. **Non-affirmative response** (cancel / wait / no / let me think) → action aborted; `pending_confirmation` cleared; AI returns to passive listening
6. **Confirmation timeout** (default 60 seconds for active sessions; 24 hours for deferred-processed offline captures per §15.7): `pending_confirmation` expires; AI prompts for re-issue

**Affirmative-response classifier**: a small set of rule-based patterns plus a fallback to Llama for ambiguous responses ("uh, sure, I guess?"). Llama is asked specifically: "Did the user confirm or decline?" → `confirmed | declined | unclear`. Unclear responses trigger a re-prompt rather than a guess.

**Pre-resolution staleness check integration**: for confirmations involving multi-step operations (calendar conflict resolution, quote approval, mobile sync conflict resolution), the staleness check from §16.4 runs at confirmation time. If state has shifted, the AI re-reads the updated context aloud before committing.

**Refusal-with-redirect**: out-of-channel attempts (e.g., "accept the calendar version but change the time to 9 AM" — requires field-level edits voice cannot express) refuse cleanly and offer redirect: "I can pick a side, but I can't blend them. Want me to text you the link to edit on web?"

**Operations using confirm-as-turn**:
- Quote send (Flow 1)
- Quote approval / rejection (Flow 5)
- Calendar conflict resolution — all six variants (Flow 6)
- Mobile sync conflict resolution (Flow 7, deferred for offline captures)
- Schedule changes — reassign, reschedule (Flow 3)
- Customer comms send (Flow 4 — interfaces with always-preview rule per §16.7)
- Session deletion (Flow 1)

### 6.7 Deferred Voice Processing Pipeline (Offline-Captured Audio)

Voice audio captured while the device is offline (per §15.7) cannot be processed in real-time. The deferred pipeline upholds the optimistic-UI principle: tech sees "voice captured" not "voice failed"; the resulting intent runs through normal disambiguation/confirmation when transcription completes.

**Pipeline stages**:

```
Tech speaks (offline) → Audio captured locally on device
   ↓ [stays local until network available]
Device reconnects → Audio uploaded via POST /api/v1/voice/upload-audio
   (idempotency UUID + captured_at timestamp + context: screen, conversation_session_id)
   ↓
voice_command_log row created with processing_status = 'pending_upload' → 'uploading' → 'transcribing'
   ↓
process_voice_audio_async Celery task picks up the row:
  Whisper transcription (300–800ms)
  Llama intent parsing (150–400ms)
  ↓
processing_status → 'parsing' → 'completed' (or 'failed' on error)
   ↓
Intent routing:
  - Read-only intent: result returned via push notification ("'What's the profit on Johnson?' — answer: $1,240 margin")
  - Destructive intent requiring confirm-as-turn: confirmation prompt enqueued as a notification rather than blocking
   ↓
Tech sees notification → opens Voice tab → confirmation prompt rendered → tech responds
   ↓
On affirmative: API call commits; on non-affirmative: deferred intent cancelled
```

**`voice_command_log` schema extensions for deferred processing**:

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `captured_at` | TIMESTAMPTZ NOT NULL | Client-side capture time |
| `uploaded_at` | TIMESTAMPTZ NULL | When audio reached server |
| `transcribed_at` | TIMESTAMPTZ NULL | Whisper completion |
| `parsed_at` | TIMESTAMPTZ NULL | Llama completion |
| `processing_status` | TEXT NOT NULL | `pending_upload \| uploading \| transcribing \| parsing \| completed \| failed` |
| `audio_object_key` | TEXT | S3 key for the uploaded audio file |
| `idempotency_uuid` | UUID NOT NULL | For safe retry on upload |

**Deferred-confirmation timeout**: 24 hours via `expire_deferred_voice_confirmations` Celery task (§3.2). After expiry, the intent is auto-cancelled with a notification ("Your voice command 'send Johnson quote' was cancelled — too long since you spoke it. Please try again if you still want to send.").

**Stale-state risk for deferred destructive intents**: an intent captured at hour 0 may target an entity that has changed by hour 3. The pre-commit staleness check (§16.4) catches this; the AI surfaces it verbally at confirmation time: "The Johnson quote has been edited since you spoke this command — let me re-read it before sending."

### 6.8 NEC Code Assistance

The `calculate_nec_voltage_drop` handler provides:
- Voltage drop calculation: `VD = 2 × R × I × L / 1000`  (NEC wire resistance constants per AWG at 75°C)
- Conduit fill calculations
- Ampacity lookups

Reference corpus: `dev-docs/nec-resources/MVP NEC 2023 AI Reference Guide v3.0.md`

#### 6.8.1 NEC Calculation Function Surface & Return Contract

*(Rescued 2026-08-20 from the archived `pilot-local-ai-nec-calcs-design-model.md` — the durable design contract for the NEC engine.)*

The NEC engine exposes **11 calculation functions**:

| Function | Purpose |
|---|---|
| `calculate_conductor_ampacity()` | Base ampacity lookup per conductor/size/material |
| `apply_temperature_correction()` | Ambient-temperature ampacity correction factors |
| `apply_adjustment_factors()` | Bundling/conductor-count adjustment factors |
| `calculate_voltage_drop()` | `VD = 2 × R × I × L / 1000` (see §6.8 above) |
| `size_equipment_grounding_conductor()` | EGC sizing (NEC 250.122) |
| `size_grounding_electrode_conductor()` | GEC sizing (NEC 250.66) |
| `calculate_box_fill()` | Box volume/conductor fill (NEC 314.16) |
| `calculate_raceway_fill()` | Conduit/raceway fill percentage (NEC Ch. 9) |
| `calculate_motor_branch_circuit()` | Motor branch-circuit sizing (NEC 430) |
| `calculate_transformer_overcurrent_protection()` | Transformer OCPD sizing (NEC 450) |
| `calculate_service_or_feeder_load()` | Service/feeder load calculation (NEC 220) |

**Every function returns the same envelope** — this contract is what lets the voice layer render a uniform, auditable answer card regardless of which calculation ran:

```json
{
  "inputs": {},
  "formula": "",
  "intermediate_steps": [],
  "result": {},
  "source_references": [],
  "assumptions": [],
  "warnings": []
}
```

**NEC question answers follow a fixed format**: applicable edition and jurisdiction → question classification → relevant NEC provisions → known inputs → assumptions → calculation → result → compliance interpretation → exceptions or alternatives → items requiring AHJ confirmation → sources.

Example closing language (the AHJ-deference pattern every generated answer must end with):

> *"Based on the 2023 NEC and the supplied conditions, the calculated minimum conductor size is X. This conclusion depends on 75°C terminations, copper conductors, no local amendment, and the stated number of current-carrying conductors. Verify the adopted edition and interpretation with the local AHJ."*

---

## 7. API Design

### 7.1 Application Entry Point & Middleware Stack

**File:** `backend/app/main.py`

**Registered Middleware (execution order on inbound request):**
1. **`RequestIDMiddleware`** — Generates or validates `X-Request-ID` UUID; injects into `request.state.request_id`; echoes back in response header
2. **`idempotency_middleware`** — SHA-256 body hashing; 24-hour response caching per `Idempotency-Key` header; pessimistic row lock for in-progress requests
3. **`CORSMiddleware`** — Allowed origins: `localhost:3000` (Next.js web dev server); credentials: true

**SlowAPI Rate Limiter** is attached to `app.state.limiter` (not middleware position, but enforced via decorator on each route).

### 7.2 RESTful Conventions

#### Authenticated Endpoints (JWT required)

```
GET    /api/v1/{resource}               → List resources (cursor-paginated)
POST   /api/v1/{resource}               → Create resource
GET    /api/v1/{resource}/{id}          → Get specific resource
PATCH  /api/v1/{resource}/{id}          → Update resource (partial)
DELETE /api/v1/{resource}/{id}          → Soft-delete resource
POST   /api/v1/{resource}/{id}/{action} → Execute action
```

**Registered Route Prefixes:**

| Prefix | Router Module | Notes |
| :--- | :--- | :--- |
| `/api/v1/webhooks` | `webhooks.py` | QB HMAC-validated webhook handler |
| `/api/v1/auth` | `auth.py` | Login, token refresh, Cognito callbacks |
| `/api/v1/customers` | `customers.py` | CRM customer CRUD |
| `/api/v1/sites` | `sites.py` | Customer site management |
| `/api/v1/contacts` | `contacts.py` | Polymorphic entity contacts |
| `/api/v1/addresses` | `addresses.py` | Polymorphic entity addresses |
| `/api/v1/catalog` | `catalog.py` | Supplier items, pricing cache |
| `/api/v1/jobs` | `jobs.py` | Jobs, time entries, expenses, attachments |
| `/api/v1/quotes` | `quotes.py` | Quotes, lines, public links, acceptance |
| `/api/v1/voice` | `voice.py` | Voice command processing endpoint |
| `/api/v1/integrations` | `integrations.py` | QB OAuth connect/callback/disconnect |
| `/api/v1/audit` | `audit.py` | Audit log viewer (owner/accountant only) |
| (root) | `roles.py` | RBAC role management (owner only) |
| `/api/v1/health` | `health.py` | Service health checks |

#### Unauthenticated Test Endpoints (DEV/QA Only)

All authenticated endpoints have a `/test` suffix variant:
```
POST /api/v1/customers/test   → Same as POST /api/v1/customers but no JWT
```

**Guard** (FIND-001–049 allowlist fix, 2026-05-11): Test endpoints return `HTTP 200` **only when both conditions are true**:
1. `TEST_ENDPOINT_ENABLED=true`, **AND**
2. `ENVIRONMENT` is exactly `dev` or `qa` (allowlist — not a blocklist)

Any other combination returns `HTTP 403`. This is an **allowlist** pattern — any environment value not explicitly in `('dev', 'qa')` (including `demo`, `staging`, `production`, `uat`, `test`, or any unknown future name) is **automatically hard-blocked**. A blocklist pattern would allow unknown environment names to accidentally get access.

**Implementation**: `core/config.py::is_test_endpoint_allowed()` → `return settings.TEST_ENDPOINT_ENABLED and settings.ENVIRONMENT in ['dev', 'qa']`

### 7.3 Versioning Strategy

- **URL path versioning**: `/api/v1/`, `/api/v2/`
- **Major bump** (`v1 → v2`): Breaking changes (removed fields, changed types, removed endpoints)
- **Minor (implicit)**: Backward-compatible additions (new fields, new endpoints)
- **Deprecation headers**: `Deprecation`, `Sunset`, `Link` (RFC 8594)

### 7.4 Error Response Format (RFC 7807)

```json
{
    "type": "https://docs.pilotfortrades.com/errors/validation-error",
    "title": "Validation Error",
    "status": 422,
    "detail": "Invalid email format",
    "instance": "/api/v1/customers - req_a1b2c3d4",
    "errors": {
        "email": ["Must be a valid email address"]
    }
}
```

### 7.5 Rate Limiting

**Implementation:** `core/rate_limit.py` — SlowAPI + Redis DB 0

**Key design decisions:**
- Rate limits are **tenant-scoped**, not IP-scoped: All users within a tenant share a single pool
- Unauthenticated requests (login, auth) fall back to **IP-scoped** limits

| Tier | Limit | Notes |
| :--- | :--- | :--- |
| `free` | 100 req/hour | — |
| `standard` | 1,000 req/hour | **MVP default for all tenants** |
| `premium` | 5,000 req/hour | Post-MVP |
| `enterprise` | Unlimited | Post-MVP |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1699564800
Retry-After: 1800   (on 429 only)
```

### 7.6 Idempotency Keys

**Header:** `Idempotency-Key: <UUID v4>`  
**Applies to:** `POST`, `PATCH`, `PUT`, `DELETE`  
**Storage:** `idempotency_key` table in PostgreSQL (Redis fallback planned)  
**TTL:** 24 hours  
**Body validation:** SHA-256 hash of request body stored; reusing a key with a different body returns `409 Conflict`

| Scenario | HTTP Status | Behavior |
| :--- | :--- | :--- |
| First request | `200 / 201` | Execute; cache response |
| Identical retry | `200 / 201` | Return cached response (`X-Idempotency-Replay: true`) |
| Key reuse, different body | `422` | Error: key reused with different payload |
| Concurrent request | `409` | Error: request in progress (`locked_until` active) |

**Natural-Key Fallback Dedup for Offline Operations** (extends idempotency for the 72-hour offline scenario):

Mobile clients capture offline and may sync up to 72 hours later. The 24-hour idempotency window can have expired by then, but the operation must still not duplicate. The platform adds a per-operation natural-key check that runs in parallel with the idempotency lookup:

| Operation | Natural Key | Window |
| :--- | :--- | :--- |
| Time entry | `(user_id, job_id, clock_in_at)` | 7 days |
| Expense | `(user_id, job_id, captured_at, amount_cents)` | 7 days |
| LOTO check | `(user_id, job_id, captured_at)` | 7 days |
| Photo | `(user_id, job_id, captured_at, file_hash)` | 30 days |
| Job status change | `(user_id, job_id, captured_at, new_status)` | 7 days |
| Free-text note | `(user_id, job_id, captured_at, content_hash)` | 7 days |

If a natural-key match is found within the window, the existing record is returned with `X-Idempotency-Replay: true` (same semantics as the regular idempotency hit). The combination of the 24-hour idempotency window for hot-path retries and the natural-key fallback for delayed offline-sync covers the full 72-hour offline scenario plus the additional safety margin.

Mobile clients persist the client-generated UUID indefinitely in their local sync queue (per §15.8) so the idempotency key is reused across all retry attempts regardless of how long the offline period was.

### 7.7 Request ID Tracing

**Header:** `X-Request-ID: <UUID v4>` (client-provided or server-generated)  
**Implementation:** `core/middleware.py`  
**Propagation:** Injected into `request.state.request_id`; echoed in response headers; included in every structured log entry

### 7.8 Cursor-Based Pagination

All list endpoints use cursor-based pagination (not offset):
- **Why**: Consistent results (no missed/duplicate items on insert during iteration), better performance at scale, no `OFFSET` table scans

```
GET /api/v1/customers?cursor=eyJpZCI6ICJ1dWlkIn0&limit=50
```

### 7.9 Pre-Commit Staleness Check Pattern (409-and-Refresh)

A platform-wide concurrency pattern for write endpoints where a user has viewed a resource, made a decision, and is about to commit — but the underlying record may have changed in between (especially for human-pace decisions like approval review or conflict resolution). Endpoints that use this pattern accept expected-version timestamps and return `409 Conflict` with refreshed state when the underlying record has changed since the client last viewed it.

**Endpoints using this pattern**:

| Endpoint | Expected-Version Field | Source Section |
| :--- | :--- | :--- |
| `POST /api/v1/schedule/jobs/{id}/reschedule` | `expected_updated_at` | §13.7 |
| `POST /api/v1/schedule/jobs/{id}/assign` | `expected_updated_at` | §13.7 |
| `POST /api/v1/calendar/conflicts/{id}/resolve` | `expected_pilot_modified_at`, `expected_external_modified_at` | §13.5 |
| `POST /api/v1/quotes/{id}/approve` | `expected_quote_version_id` | §14.4 |
| `POST /api/v1/quotes/{id}/reject` | `expected_quote_version_id` | §14.4 |
| `POST /api/v1/mobile-sync/conflicts/{id}/resolve` | `expected_server_version_id` | §15.9 |

**Client behavior on 409**:

1. API returns 409 with the refreshed payload in the response body
2. Client refreshes the view UI with the new state
3. Surfaces a non-blocking banner: "This has been updated. Review and pick again."
4. User re-decides; on next submit, the new expected-version field is sent

**Voice path on 409**: when the staleness check fires during a confirm-as-turn flow (per §6.6), the AI surfaces the change verbally before re-confirming: "The Johnson quote has been edited since you started — let me re-read it before approving."

This pattern is documented as a cross-cutting platform pattern in §16.4.

---

## 8. Monitoring & Observability

> *Design goal. As built: structured logs, CloudWatch infrastructure metrics and 12 alarms with email notification — no ADOT/OpenTelemetry metrics, no X-Ray tracing, no PagerDuty/Slack paging (Known Limitations #4).*

### 8.1 Structured Logging

All logs are emitted as structured JSON for CloudWatch Insights:
```json
{
    "event": "api_request_completed",
    "timestamp": "2026-04-20T14:30:45.123Z",
    "level": "info",
    "request_id": "a1b2c3d4-...",
    "method": "POST",
    "path": "/api/v1/quotes",
    "status_code": 201,
    "duration_ms": 245,
    "tenant_id": "...",
    "user_id": "..."
}
```

### 8.2 OpenTelemetry Metrics

- **Collector**: AWS Distro for OpenTelemetry (ADOT) as sidecar
- **Standards**: OTel Semantic Conventions for HTTP (`http.server.request.duration`)
- **Types**: Counters (request count), Gauges (memory usage), Histograms (latency distribution)
- **Resource Attributes**: `service.name`, `service.version`, `deployment.environment`
- **Exemplars**: Trace IDs bound to latency histograms for "jump-to-trace" capability

### 8.3 Distributed Tracing (X-Ray + ADOT)

- **Trace propagation**: `X-Amzn-Trace-Id` header propagated through all service calls
- **Subsegments**: DB queries, external HTTP calls, SQS interactions instrumented individually
- **Sampling**: 1–5% in production; 100% in debug mode (env variable controlled)
- **Annotations**: `customer_id`, `tenant_id`, `quote_id` as indexed fields for trace search

**Example trace:**
```
POST /api/v1/quotes (245ms)
├─ Authentication / JWT validation (15ms)
├─ create_quote_business_logic (220ms)
│  ├─ DB: SELECT customers (8ms)
│  ├─ HTTP: Fetch material pricing cache (180ms)  ← SLOW — investigate
│  └─ DB: INSERT quotes (32ms)
└─ Response serialization (10ms)
```

### 8.4 CloudWatch Dashboards — Key Metrics

- Request count, error rate (4xx / 5xx)
- Latency (p50, p95, p99) per endpoint
- Active tenant count, new signups per day
- Voice command processing time (Whisper + Ollama combined)
- QB sync success rate, conflict count
- Database connections (vs. 100 max)
- ECS CPU / memory utilization per task
- GPU instance CPU / VRAM utilization

### 8.5 Alerting

| Severity | Channel | Conditions |
| :--- | :--- | :--- |
| **P1 — Critical** | PagerDuty | API completely down; error rate > 5%; DB connection failure |
| **P2 — High** | Slack | API p95 latency > 2s; DB connections > 80; GPU instance unhealthy |
| **P3 — Medium** | Email | QB sync failures; Voice AI p95 > 2.5s; high rate of 429 responses |

### 8.6 Service Level Objectives (SLOs)

| SLO | Target |
| :--- | :--- |
| **API Availability** | 99.9% uptime |
| **API Latency p95** | < 500ms |
| **Voice AI Latency p95** | < 2,000ms |
| **QB Sync Success Rate** | > 99% |

### 8.7 Monitoring Costs

| Component | Monthly Cost |
| :--- | :--- |
| CloudWatch Logs | ~$10 |
| CloudWatch Metrics + Dashboards | ~$15 |
| X-Ray | ~$5 |
| GuardDuty | ~$10 |
| Security Hub | ~$5 |
| **TOTAL** | **~$45/month** |

---

## 9. Security Architecture

### 9.1 Secrets Management

All secrets stored in **AWS Secrets Manager**. Rotation policy:
- Database password: Quarterly (automated via Secrets Manager rotation Lambda)
- QuickBooks OAuth keys: On demand (developer-managed)
- SendGrid / Telnyx API keys: Quarterly (manual)
- `ENCRYPTION_KEY` (Fernet): Annual (requires re-encryption migration)

### 9.2 Encryption

**At Rest:**
- RDS: AES-256 via AWS KMS-managed key
- S3: AES-256 via AWS KMS-managed key (default bucket encryption)
- ElastiCache: AES-256 at rest (Redis encryption enabled) — *as built: Redis unencrypted, Known Limitations #24*

**In Transit:**
- All external API traffic: TLS 1.3 (ALB + ACM certificates) — *as built: TLS 1.2+ ALB policy*
- Internal VPC traffic: TLS enforced for RDS and Redis connections — *as built: RDS only; Redis without TLS (Known Limitations #24)*

**Application-Level Encryption:**
- QuickBooks OAuth tokens: Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
- User passwords: stored and hashed by AWS Cognito (never in the application database)

### 9.3 Network Security

```
Public Subnets  → ALB only (ports 80/443 from 0.0.0.0/0)
      ↓
Private Subnets → ECS Tasks, RDS, Redis, GPU
      ↓
NAT Gateway     → Outbound internet access for private subnet services
```

**Security Groups (Least Privilege):**
- **ALB**: Allow `TCP 443` from `0.0.0.0/0`; `TCP 80` redirect to 443
- **ECS Tasks**: Allow `TCP 8000` from ALB security group only
- **RDS**: Allow `TCP 5432` from ECS security group only
- **Redis**: Allow `TCP 6379` from ECS security group only
- **GPU Instance**: Allow `TCP 8080` (Whisper) and `TCP 11434` (Ollama) from ECS security group only

### 9.4 Application Security

**Input Validation:** All API inputs validated through Pydantic v2 with strict type enforcement; `AwareDatetime` enforced on all timestamp fields (UTC Triple-Lock).

**SQL Injection Prevention:** All database queries use SQLModel / SQLAlchemy parameterized queries — no raw string interpolation in SQL.

**IDOR Prevention:** All resource lookups include `tenant_id` filter. The `require_permission()` dependency enforces tenant-scoped access on every authenticated route.

**Security Headers:**
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

**CSRF Protection:** OAuth state token stored in Redis with 10-minute TTL; validated on callback.

### 9.5 IAM Least Privilege

ECS task roles are scoped to only the AWS services the application requires:
```json
{
    "Effect": "Allow",
    "Action": [
        "secretsmanager:GetSecretValue",
        "s3:GetObject", "s3:PutObject",
        "logs:CreateLogStream", "logs:PutLogEvents",
        "xray:PutTraceSegments"
    ],
    "Resource": ["specific ARNs only"]
}
```

### 9.6 Security Monitoring

- **GuardDuty**: Automated threat detection (unusual API patterns, credential compromise)
- **Security Hub**: CIS AWS Foundations benchmark compliance
- **Audit Logs**: All security-relevant events logged via `audit.log_changes()` trigger on all 85 tables

### 9.7 GDPR Compliance

- **Right to Access**: `GET /api/v1/account/export` returns full tenant data export (planned)
- **Right to Deletion**: `DELETE /api/v1/account` triggers soft-delete cascade + scheduled hard-delete after 30-day grace period (planned)
- **Data Residency**: All data stored in `us-east-1`; no cross-region replication

---

## 10. Deployment & CI/CD

### 10.1 Docker Containerization

**Dockerfile** (`backend/Dockerfile`):
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.2 GitHub Actions CI/CD Pipeline

```yaml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run test suite
        run: pytest tests/ -v --cov=app
      - name: Security scan
        run: trivy fs .

  build:
    needs: test
    steps:
      - name: Build Docker image
        run: docker build -t pilot:${{ github.sha }} .
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login ...
          docker push $ECR_REPO:${{ github.sha }}

  migrate:
    needs: build
    steps:
      - name: Run database migrations (ECS Run Task)
        run: |
          aws ecs run-task \
            --cluster pilot-production \
            --task-definition pilot-migrate \
            --overrides '{"containerOverrides":[{"name":"app","command":["alembic","upgrade","head"]}]}'

  deploy:
    needs: migrate
    steps:
      - name: Blue-green deploy to ECS  # design goal; as built: ECS rolling + circuit breaker
        run: |
          aws ecs update-service \
            --cluster pilot-production \
            --service pilot-api \
            --force-new-deployment
```

### 10.3 Blue-Green Deployment

> *Design goal. As built: ECS rolling deploys with circuit-breaker rollback; blue/green was provisioned but never enabled (Known Limitations #18).*

```
ALB → 100% BLUE (current version)
          ↓
Deploy GREEN tasks (new image)
          ↓
ECS health checks pass (target group health)
          ↓
ALB traffic shift: 10% → 50% → 100% to GREEN
          ↓
BLUE tasks drained and terminated
```

**Timeline:** ~10 minutes total  
**Rollback:** Revert ALB weights to 100% BLUE in < 2 minutes  
**Zero downtime:** ALB connection draining ensures in-flight requests complete

### 10.4 Database Migrations (Alembic)

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "add invoice_public_link table"

# Apply to database
alembic upgrade head

# Rollback one revision
alembic downgrade -1
```

**Safety checks before any migration run:**
```python
# Warn on destructive operations
if 'DROP' in migration.doc:
    print("⚠️ WARNING: Contains DROP operation — verify backward compatibility")
if 'ALTER COLUMN' in migration.doc:
    print("⚠️ WARNING: May lock table — schedule maintenance window")
```

### 10.5 Rollback Procedures

**Application rollback:**
```bash
aws ecs update-service \
  --cluster pilot-production \
  --service pilot-api \
  --task-definition pilot-api:$PREVIOUS_REVISION
```

**Database rollback:**
```bash
# Always backup first
pg_dump $DATABASE_URL > backup_pre_rollback_$(date +%Y%m%d_%H%M%S).sql

# Rollback migration
alembic downgrade $TARGET_REVISION
```

### 10.6 Disaster Recovery

| Metric | Target |
| :--- | :--- |
| **RTO** (Recovery Time Objective) | 4 hours |
| **RPO** (Recovery Point Objective) | 1 hour |

**Backup coverage:** RDS daily automated + weekly manual snapshots; S3 versioning enabled; Terraform state in S3 with DynamoDB locking; archive of all DB dumps in `archive/db-backups/`.

---

## 11. Front-End Architecture

### 11.1 Strategic Direction

Pilot uses a **dedicated-app-per-persona** strategy rather than a universal codebase. Two distinct applications serve fundamentally different UX requirements:

| App | Framework | Target User | Primary UX Pattern |
| :--- | :--- | :--- | :--- |
| **Web Dashboard** | Next.js 16 (App Router) + Tailwind v4 | Owner, bookkeeper, office staff | Data-dense, mouse-and-keyboard; large tables, complex filtering, reporting |
| **Mobile App** | Expo SDK 54 + React Native 0.81 + Expo Router | Field technicians | High-contrast, voice-driven, offline-capable; designed for use with work gloves |

**Rationale (from `mvp-front-end-new-design.md`):**
- **Next.js** provides Backend-for-Frontend (BFF) security, server-side rendering, and App Router file-based routing — essential for a data-dense owner dashboard.
- **Expo Router** gives the mobile app file-based routing identical in mental model to Next.js App Router, reducing context-switch overhead for a solo founder.
- Both apps share Tailwind CSS configuration via the Turborepo workspace, creating a unified design system without a universal component abstraction.

### 11.2 Monorepo Architecture (Turborepo + pnpm)

Shared code between web and mobile is managed in a **Turborepo 2.x monorepo** using **pnpm 9.x workspaces**. The workspace root is at `frontend/`:

```
PILOT/
├── backend/                      ← FastAPI application
├── dev-docs/                     ← Project-level documentation
└── frontend/                     ← Turborepo Workspace root
    ├── apps/
    │   ├── web/                  ← Next.js 16 web dashboard (App Router + TypeScript + Tailwind v4)
    │   ├── mobile/               ← Expo SDK 54 + React Native 0.81 mobile app (iOS/Android)
    │   └── marketing/            ← Next.js 16 static-export marketing site (pilotfortrades.com)
    ├── packages/
    │   ├── shared-api/           ← Axios API client + TanStack Query hooks (@pilot/shared-api)
    │   ├── shared-types/         ← Auto-generated TypeScript interfaces from FastAPI OpenAPI JSON
    │   ├── ui/                   ← Shared UI primitives (shadcn/ui-compatible; @pilot/ui)
    │   ├── eslint-config/        ← Shared ESLint configs (base, Next.js, React internal)
    │   └── typescript-config/    ← Shared TypeScript configurations (base, nextjs, react-library)
    ├── package.json              ← pnpm workspace definitions + root scripts
    ├── pnpm-workspace.yaml       ← pnpm workspace glob patterns
    └── turbo.json                ← Turborepo task pipeline (build, dev, lint, check-types)
```

> **Package status (updated May 21, 2026)**: All five packages (`shared-api`, `shared-types`, `ui`, `eslint-config`, `typescript-config`) are now scaffolded and operational. Remaining planned package: `shared-utils` (Zod schemas, date/currency formatters) — to be created when cross-app utility sharing need arises during implementation.

**Root-level scripts** (`frontend/package.json`):

| Script | Command | Purpose |
| :--- | :--- | :--- |
| `pnpm dev` | `turbo run dev` | Start all app dev servers in parallel |
| `pnpm build` | `turbo run build` | Build all apps and packages |
| `pnpm sync-api-types` | Export OpenAPI JSON → `openapi-typescript` | Regenerate `shared-types` from FastAPI schema |
| `pnpm lint` | `turbo run lint` | Lint all packages |
| `pnpm check-types` | `turbo run check-types` | TypeScript type-check all packages |

### 11.3 Front-End Tech Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Package Manager** | pnpm 9.x | Fast, disk-efficient; required for `workspace:*` protocol |
| **Build System** | Turborepo 2.x | Parallel task execution, build caching across all apps/packages |
| **Web Framework** | Next.js 16 (App Router) | SSR, file-based routing, BFF security layer for tokens |
| **Mobile Framework** | Expo SDK 54 (React Native 0.81) | iOS/Android with native device access (mic, GPS, camera) |
| **Mobile Routing** | Expo Router 6.x | File-based routing for mobile, mirrors Next.js App Router conventions |
| **Server State / API** | TanStack Query (React Query) | API caching, background refresh, optimistic updates (shared via `packages/shared-api`) |
| **Client State** | Zustand | Lightweight state for complex UI flows (Quote Builder wizard) |
| **Web UI Components** | shadcn/ui + Tailwind v4 | MIT-licensed, copy-owned components; Tailwind v4 for web dashboard styling |
| **Mobile UI Components** | Gluestack-UI | MIT-licensed, Tailwind-native React Native components; supports large high-contrast field-tech targets |
| **Shared Design Tokens** | Tailwind config in `packages/ui` | Both web and mobile consume same color/spacing/font tokens |
| **Offline Database (Mobile)** | WatermelonDB (JSI SQLite adapter) | Relational offline storage for field technicians; syncs to FastAPI `/sync/push` + `/sync/pull` |
| **Voice / Audio (Mobile)** | expo-av + WebSockets | Streams audio chunks to FastAPI for < 200ms voice AI response times |
| **Voice / Audio (Web)** | Web Audio API (MediaRecorder) + WebSockets | Browser-native audio capture; WebSocket stream to FastAPI Whisper endpoint |
| **Type Safety** | Auto-generated from FastAPI OpenAPI | `packages/shared-types` generated via `pnpm sync-api-types` |
| **Real-time Updates** | Server-Sent Events (EventSource API) | Live dispatch board updates per §13.11; notification delivery per §3.5.6; SSE fallback to polling (web only) |
| **Authentication Client** | AWS Amplify Auth (Cognito JS SDK) | Cognito JWT integration; protected route guards; MFA enrollment wizard per §4.5; used by both web and mobile |
| **Stripe Payment Client** | Stripe.js + Stripe Elements | Subscription tier picker per §20.4 (tenant-side); customer-facing one-time invoice payment per §18.5 (public pages) |

**UI library rationale** (from `mvp-front-end-new-design.md` Appendix B–D):
- **shadcn/ui**: MIT-licensed, code is copied directly into the project (zero vendor lock-in), built on Tailwind v4.
- **Gluestack-UI**: MIT-licensed, Tailwind-native on React Native, zero freemium paywalls. Enables rapid high-contrast field-tech UI with standard Tailwind classes.
- **Tamagui avoided**: Core is MIT but premium "Bento" components require paid license (~$250+); custom compiler adds debugging overhead for solo founder.

### 11.4 Type Generation from FastAPI

TypeScript interfaces in `packages/shared-types` are auto-generated from FastAPI's OpenAPI spec using a two-step export script:

```bash
# From the frontend/ workspace root:
pnpm sync-api-types
```

This runs:
1. `backend/export_openapi_json.py` — imports the FastAPI app and writes `backend/openapi.json` to disk (no live server required)
2. `openapi-typescript ../backend/openapi.json -o ./packages/shared-types/src/api-schema.d.ts` — generates TypeScript definitions

This ensures `packages/shared-types/src/api-schema.d.ts` always stays in sync with Pydantic schema definitions in the backend, without requiring a running server.

---

## 12. Local Development Environment

### 12.1 Docker Stack (6 Containers)

The complete local development stack is defined in `docker-compose.yml` at the project root:

| Container | Image | Port | Purpose |
| :--- | :--- | :--- | :--- |
| `pilot_postgres` | `pgvector/pgvector:pg17` | 5432 | PostgreSQL 17 with pgvector extension |
| `pilot_redis` | `redis:7-alpine` | 6379 | Celery broker (DB 1), result backend (DB 2), rate limit (DB 0) |
| `pilot_celery_worker` | Built from `backend/Dockerfile` | — | Background task processor (concurrency: 2) |
| `pilot_celery_beat` | Built from `backend/Dockerfile` | — | Cron scheduler for periodic tasks |
| `pilot_ollama` | `ollama/ollama:latest` | 11434 | Llama 3.1 8B intent parsing |
| `pilot_whisper` | `fedirz/faster-whisper-server:latest-cpu` | 8080 | Whisper speech-to-text (model: turbo) |

**Start entire stack:**
```bash
docker compose up -d
```

**Data persistence:** PostgreSQL data is stored in the `backend_postgres_data` named Docker volume — persists across container restarts and `docker compose down`.

### 12.2 Development Terminal Setup (3 Terminals)

Celery worker and beat run automatically in Docker. Three manual processes are needed:

**Terminal 1 — ngrok tunnel** (required for QuickBooks OAuth and webhook callbacks):
```bash
ngrok http --domain=your-tunnel.ngrok-free.dev 8000
```
Public URL: `https://your-tunnel.ngrok-free.dev`

**Terminal 2 — FastAPI server** (with hot-reload):
```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Local API docs: `http://localhost:8000/docs`

**Terminal 3 — Frontend dev servers** (Next.js web + Expo mobile, runs in parallel via Turborepo):
```bash
cd frontend && pnpm dev
```
- Next.js web dashboard: `http://localhost:3000`
- Expo mobile (press `i` for iOS Simulator, `a` for Android, `w` for browser): `http://localhost:8081`
- To run a single app only: `cd frontend/apps/web && pnpm dev` or `cd frontend/apps/mobile && pnpm dev`

### 12.3 Key Environment Variables (`backend/.env`)

```bash
# Database
DATABASE_URL=postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev

# Celery (uses Docker service names when run inside containers)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# AI Services (Docker service names when run inside containers)
WHISPER_API_URL=http://localhost:8080/v1
WHISPER_MODEL=turbo
OLLAMA_API_URL=http://localhost:11434/api
OLLAMA_CHAT_MODEL=llama3.1:8b

# QuickBooks OAuth
QUICKBOOKS_CLIENT_ID=your_client_id_here
QUICKBOOKS_CLIENT_SECRET=your_client_secret_here
QUICKBOOKS_REDIRECT_URI=https://your-tunnel.ngrok-free.dev/api/v1/integrations/quickbooks/callback
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN=your_verifier_token_here

# Token encryption
ENCRYPTION_KEY=your_fernet_key_here   # generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Email / SMS
SENDGRID_API_KEY=your_sendgrid_api_key_here
SENDGRID_FROM_EMAIL=noreply@pilotfortrades.com
TELNYX_ACCOUNT_SID=your_telnyx_sid_here
TELNYX_AUTH_TOKEN=your_telnyx_token_here
TELNYX_FROM_NUMBER=+1XXXXXXXXXX

# Test endpoints
TEST_ENDPOINT_ENABLED=true
ENVIRONMENT=dev
TEST_TENANT_ID=00000000-0000-0000-0000-000000000001
TEST_USER_ID=00000000-0000-0000-0000-000000000002

# AWS Cognito (production only — not needed for local test-endpoint development)
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
```

### 12.4 One-Time Local Setup

```bash
# 1. Start Docker stack
docker compose up -d

# 2. Download Llama 3.1 8B model (~4.7GB, one-time)
docker exec -it pilot_ollama ollama pull llama3.1:8b

# 3. Set up Python virtual environment
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. Run database migrations
alembic upgrade head

# 5. Seed test data (creates test tenant + user for /test endpoints)
python -m migrations.seed_test_data
```

### 12.5 Database Backup (Local)

```bash
# Full backup (schema + data)
pg_dump -h localhost -U pilot_user -d pilot_dev \
  > archive/db-backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Schema only
pg_dump -h localhost -U pilot_user -s -x -O pilot_dev \
  > archive/db-backups/schema_dump_$(date +%Y%m%d_%H%M%S).sql

# Restore
psql -h localhost -U pilot_user -d pilot_dev \
  < archive/db-backups/backup_YYYYMMDD_HHMMSS.sql
```

**⚠️ CRITICAL**: Always backup before `docker compose down -v` (volume destruction).

---

## 13. Scheduling & Dispatch

### 13.1 Architecture Overview

Scheduling is the domain that coordinates *when* and *who* for every job on the platform. It sits between Sales & Quoting (which produces jobs) and Field Operations (which executes them), and integrates with three external systems: a map provider (for distance-matrix and geocoding), a calendar provider (for bi-directional sync with the tenant's company calendar), and a mobile GPS feed (for live ETA calculation).

The domain exposes three primary UI surfaces:

| Surface | Platform | Users | Purpose |
| :--- | :--- | :--- | :--- |
| **Dispatch Board** | Web | Owner, dispatcher | Plan and assign jobs across techs and time |
| **Today's Schedule** | Mobile | Technician | View assigned jobs in chronological order |
| **Calendar Settings** | Web | Owner | Connect company calendar, manage sync |

**Core principles:**

- **Pilot is the source of truth**: the dispatch board is authoritative; external calendar is a mirror
- **Conflict-aware**: double-booking, availability violations, and travel infeasibility are detected server-side and surfaced in UI
- **Manual-with-assist for MVP**: owner controls sequencing; system provides drive times and warnings but never auto-optimizes
- **Provider-abstract**: map and calendar integrations use abstract interfaces, Google Maps + Google Calendar as first implementations

### 13.2 Data Model

The scheduling domain introduces seven new tables in a dedicated `scheduling` PostgreSQL schema, plus additive column extensions to the existing `field_ops.job` table. The tables divide into three functional groups:

| Group | Tables | Purpose |
| :--- | :--- | :--- |
| **Assignment & availability** | `job_tech_assignment`, `tech_availability` | Who is assigned to which job; when each tech is available |
| **Calendar integration** | `tenant_calendar_integration`, `calendar_sync_log`, `calendar_sync_conflict` | OAuth connection to external calendar; sync audit and conflict resolution |
| **Schedule extensions** | `field_ops.job` (additive columns) | Scheduled timestamps, duration estimate, external event linkage |

Full DDL, index definitions, constraint rationale, migration ordering, and testing considerations live in the domain schema document: `dev-docs/analysis/scheduling-dispatch-db-schema.md`. That document is the authoritative source for the database design; this architecture section describes only the logical model and how the scheduling domain interacts with the rest of the platform.

**Key design decisions captured in the schema doc**:

- Many-to-many `job_tech_assignment` schema with MVP UI single-tech constraint enforced via DB-level partial unique index
- iCal RRULE-based recurring working hours (via `python-dateutil`); one-off PTO/unavailability blocks with GiST range indexing for conflict lookups
- One calendar integration per tenant (shared company calendar model for MVP)
- Append-only `calendar_sync_log` with 90-day hot retention consistent with audit policy
- Fernet-encrypted OAuth tokens stored via AWS Secrets Manager consistent with Section 9.1

### 13.3 Provider-Abstract Interfaces

> **Microsoft Calendar / Outlook sync re-evaluation trigger (FIND-139, Phase 4.2)**: `OutlookCalendarProvider` is deferred to Phase 2. Re-evaluate when **≥10 customers explicitly request Outlook integration** OR **90 days post-launch**, whichever comes first. No earlier — defer the scope creep risk.

Both map and calendar integrations are implemented behind abstract Python protocols to support provider swaps without code changes to consumers.

**Map provider interface** (`backend/integrations/map_provider/base.py`):

```python
from typing import Protocol
from decimal import Decimal

class Coordinates(TypedDict):
    lat: Decimal
    lng: Decimal

class DistanceMatrixResult(TypedDict):
    drive_time_seconds: int
    drive_distance_meters: int

class MapProvider(Protocol):
    async def geocode(self, address: str) -> Coordinates: ...
    async def reverse_geocode(self, coords: Coordinates) -> str: ...
    async def distance_matrix(
        self,
        origins: list[Coordinates],
        destinations: list[Coordinates],
        departure_time: datetime | None = None,
    ) -> list[list[DistanceMatrixResult]]: ...
```

Initial implementation: `GoogleMapsProvider` using the Distance Matrix API and Geocoding API. Configuration selects the provider at startup via `MAP_PROVIDER` environment variable. Alternate future implementations: `MapboxProvider`, `OSRMSelfHostedProvider`.

**Calendar provider interface** (`backend/integrations/calendar_provider/base.py`):

```python
class ExternalCalendarEvent(TypedDict):
    external_event_id: str
    starts_at: datetime
    ends_at: datetime
    title: str
    location: str | None
    description: str | None
    last_modified_at: datetime

class CalendarProvider(Protocol):
    async def oauth_authorize_url(self, redirect_uri: str, state: str) -> str: ...
    async def oauth_exchange_code(self, code: str) -> OAuthTokens: ...
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens: ...
    async def list_events(
        self,
        access_token: str,
        calendar_id: str,
        since_cursor: str | None,
    ) -> tuple[list[ExternalCalendarEvent], str]: ...
    async def create_event(
        self,
        access_token: str,
        calendar_id: str,
        event: JobScheduledEventPayload,
    ) -> str: ...
    async def update_event(
        self,
        access_token: str,
        calendar_id: str,
        external_event_id: str,
        event: JobScheduledEventPayload,
    ) -> None: ...
    async def delete_event(
        self,
        access_token: str,
        calendar_id: str,
        external_event_id: str,
    ) -> None: ...
```

Initial implementation: `GoogleCalendarProvider`. Future: `OutlookCalendarProvider`, `IcalFeedProvider`.

**Microsoft Calendar / Outlook sync re-evaluation trigger (FIND-139)**: Implement `OutlookCalendarProvider` when ≥10 customers explicitly request Outlook integration **OR** 90 days post-launch, whichever comes first.

### 13.4 Conflict Detection (Four-Class Severity)

Conflict classes are evaluated whenever a job is placed on the dispatch board (via drag-drop, voice command, or API). Evaluation happens in the `scheduling.conflict_service` module and is called from the dispatch API endpoints before any write. Pass 3 Flow 3 formalized the four-class pattern that is now reused across all platform conflict surfaces (calendar sync §13.5, mobile sync §15.6).

**Four conflict classes**:

| Class | Detection | Default UI Treatment |
| :--- | :--- | :--- |
| **Overlap** | GiST `tstzrange` overlap query against the same tech's other jobs | Warn; force-override allowed (`block` available for Phase 2) |
| **Availability** | Proposed `[start, end]` falls outside `tech_availability` working hours OR intersects PTO/unavailable blocks | Warn |
| **Travel** | For previous stop on same day: `previous_job.scheduled_end_at + drive_time > new_job.scheduled_start_at` (likewise for next stop) | Warn |
| **Info** | Advisory but not blocking, e.g., scheduled tightly (back-to-back), drive time approaching limit | Info-level (no warn) |

**Implementation detail — drive-time computation**:

For the tech's previous stop on the same day (ordered by `scheduled_start_at`), drive time is computed via the map provider's distance matrix. The result is cached server-side (per §13.8) keyed on `(origin, destination, hour-of-day)` to reduce API costs. Same check applies to the next stop if one exists.

All checks produce structured conflict records:

```python
class SchedulingConflict(BaseModel):
    conflict_class: Literal['overlap', 'availability', 'travel', 'info']
    severity: Literal['block', 'warn', 'info']
    detail: dict
    affected_job_id: UUID
    suggested_resolution: str | None  # human-readable suggestion
```

**UI behavior**: 

- `block`-severity conflicts prevent submission (Phase 2; reserved for hard policy violations like PTO when tenant configures strict mode)
- `warn`-severity conflicts surface as dismissable warnings on the dispatch board with a distinct visual treatment per class (per Pass 3 design tokens)
- `info`-severity conflicts surface as small inline annotations without blocking
- Voice-commanded scheduling actions are blocked at `block` severity; warnings prompt for confirm-as-turn ("there's a travel conflict — proceed anyway?")
- MVP ships with all conflicts at `warn` or `info`; `block` severity available for Phase 2 with tenant configuration

**Pre-commit staleness check** (per §7.9): write endpoints accept `expected_updated_at` and return 409 with refreshed conflict state when the underlying job has changed since the dispatcher last viewed it. The dispatch board re-renders with updated conflicts; dispatcher re-decides.

### 13.5 Bi-Directional Calendar Sync

The sync strategy closely mirrors the QuickBooks bi-directional pattern documented in Section 5. Modifications happen in both Pilot and the external calendar; a collision resolver handles conflicts.

This section serves as the reference instance of the **bilateral integration conflict resolution pattern** (§16.10). The QuickBooks integration (§5.4) inherits this same pattern. Future bilateral integrations (Salesforce, HubSpot, generic webhook integrations) inherit by default with deviations requiring explicit justification per §16.10. Pattern attributes are domain-determined: calendar's auto-expiry default is ON because the master is unambiguous; QB's is OFF because masters are heterogeneous. Calendar supports voice resolution because stakes are time-shifted; QB does not because accounting integrity stakes are higher.

**Push (Pilot → Calendar)**: when a job's `scheduled_start_at`, `scheduled_end_at`, `site_id`, or tech assignment changes, a Celery task (`push_job_to_calendar`) is enqueued. The task refreshes the access token if near expiry, calls the calendar provider's `create_event` (first sync) or `update_event` (subsequent), stores the returned `external_event_id` on the job, and logs the sync event to `calendar_sync_log`.

**Pull (Calendar → Pilot)**: a Celery Beat task runs every 5 minutes per active tenant integration. The task calls the calendar provider's `list_events` with the tenant's `last_sync_cursor`, matches returned events to existing jobs by `external_event_id`, applies changes when the external version is newer, creates new scheduled blocks for unmatched events, and updates `last_sync_cursor` / `last_sync_at`.

**Conflict detection**: when a pull detects a conflict (both sides modified since last sync), JSONB snapshots of both versions are written to `calendar_sync_conflict` and a notification is enqueued to the owner. Three conflict types are tracked:

| Conflict Type | Detection Trigger |
| :--- | :--- |
| `Modified ↔ Modified` | Both Pilot and calendar versions changed since last successful sync |
| `Deleted ↔ Modified` | Pilot job deleted; calendar event was modified afterward |
| `Modified ↔ Deleted` | Pilot job modified; calendar event was deleted afterward |

**Conflict diff payload** (per Pass 3 Flow 6 — populated at conflict-detection time for accurate field-level diff display):

```
calendar_sync_conflict
  id                           UUID PRIMARY KEY
  tenant_id                    UUID NOT NULL
  related_job_id               UUID NULL → field_ops.job
  conflict_type                TEXT NOT NULL  -- 'modified_modified' | 'deleted_modified' | 'modified_deleted'
  pilot_snapshot             JSONB NOT NULL    -- current Pilot state at detection
  external_snapshot            JSONB NOT NULL    -- current calendar state at detection
  base_snapshot                JSONB NULL        -- last shared state before conflict (NEW)
  pilot_modified_by_user_id  UUID NULL         -- who made the Pilot-side change
  pilot_modified_at          TIMESTAMPTZ NOT NULL
  external_modified_at         TIMESTAMPTZ NOT NULL
  detected_at                  TIMESTAMPTZ NOT NULL
  resolved_at                  TIMESTAMPTZ NULL
  resolution                   TEXT NULL  -- 'accept_local' | 'accept_remote' | etc.
  auto_resolved_stale          BOOLEAN NOT NULL DEFAULT FALSE
```

**Server-computed field-level diff**: `GET /api/v1/calendar/conflicts/{id}` returns `field_diffs`, a server-computed list of differing fields. For each field: `field_name`, `pilot_value`, `external_value`, `base_value`, `pilot_change` (`unchanged | modified | added | removed`), `external_change` (same enum). Pre-computing the diff server-side keeps the rendering consistent across web and voice readback paths.

**Resolution UI** (web at `/settings/integrations/calendar/conflicts/{id}`):

- Side-by-side two-column diff: Pilot on the left, external calendar on the right
- Field-level highlighting using platform-wide track-changes vocabulary (per §16.2): amber=modify, green=add, red=remove
- Two primary actions: "Use Pilot version" / "Use [Provider] version"
- Distinct deletion-conflict treatment: explicit-verb actions ("Restore from calendar", "Delete from calendar too", "Recreate calendar event", "Delete Pilot job")
- Conflict list sorted ascending by affected job's `scheduled_start_at` (soonest-impacting first); past-dated and unscheduled drop to bottom

**Pre-resolution staleness check** (per §7.9): `POST /api/v1/calendar/conflicts/{id}/resolve` accepts `expected_pilot_modified_at` and `expected_external_modified_at`; returns 409 with refreshed payload if state has shifted since the owner viewed the conflict.

**Resolution paths**:

- `accept_local` — keep Pilot version, push to calendar
- `accept_remote` — apply calendar version to Pilot
- `restore_from_calendar` — for `Deleted ↔ Modified`: recreate Pilot job from calendar's modified state
- `delete_calendar_too` — for `Deleted ↔ Modified`: push the deletion to calendar
- `recreate_calendar_event` — for `Modified ↔ Deleted`: push Pilot job back to calendar
- `delete_pilot_job` — for `Modified ↔ Deleted`: accept the calendar's deletion

**Two-tier auto-expiry configuration** (per §16.5 cross-cutting pattern):

System-wide defaults, configurable by Pilot platform admins:
- `system_calendar_conflict_auto_expire_days` — integer, default 30
- `system_calendar_conflict_warn_days_before` — integer, default 7

Per-tenant overrides in `tenant_setting`:
- `calendar_conflict_auto_expire_days` — integer NULL; null = use system default
- `calendar_conflict_pre_warning_days` — integer NULL; null = use system default
- `calendar_conflict_auto_expire_enabled` — boolean (default TRUE); FALSE disables auto-expiry for that tenant

Effective resolution: tenant override → system default → fallback constant. The `expire_stale_calendar_conflicts` Celery task (§3.2) reads effective values per tenant, sends pre-warning notifications at `(auto_expire_days - warn_days_before)`, and auto-resolves at `auto_expire_days` to `accept_local` (consistent with Pilot-as-source-of-truth posture). Auto-resolutions are flagged in `calendar_sync_log` with `auto_resolved_stale = TRUE` for audit distinguishability.

**Voice-active resolution** (per §6.2 / §6.6): owners can resolve calendar conflicts via voice from any platform surface (mobile or web) using confirm-as-turn. Six resolution intents cover all paths above; field-level edits route to refusal-with-redirect ("I can pick a side, but I can't blend them — want me to text you the link?").

**Failure handling**: sync failures (network errors, provider rate limits, expired refresh tokens) are retried with exponential backoff via Celery's built-in retry mechanism. After N retries, the integration's `sync_status` transitions to `error` and the owner is notified. The tenant's normal operations (dispatch, mobile app) are unaffected — they always operate against the Pilot database regardless of sync state. Conflicts remain resolvable while disconnected; resolutions queue locally and push once reconnected.

### 13.6 Celery Task Registry

New scheduled and event-driven tasks introduced by the scheduling domain:

| Task | Trigger | Purpose |
| :--- | :--- | :--- |
| `push_job_to_calendar` | Event-driven (job schedule changed) | Push Pilot job to external calendar |
| `pull_calendar_events` | Celery Beat, every 5 min per tenant | Pull external calendar changes into Pilot |
| `compute_customer_etas` | On-demand at request time (NOT event-driven — see note below) | Compute ETA for tech's next stop using latest stored GPS coordinates + Google Maps Distance Matrix |
| `notify_tech_of_assignment` | Event-driven (job assigned/reassigned) | Enqueue push + notification_outbox entry |
| `archive_calendar_sync_log` | Celery Beat, daily | Archive sync log rows > 90 days old (consistent with audit retention) |

**ETA computation pattern (FIND-115, Phase 4.2 clarification)**: ETA is computed **on-demand at request time only** — when the owner opens the dispatch board or the tech requests their ETA from mobile. The latest stored GPS coordinates from the DB are used at request time; no event-driven task fires on GPS updates. Cache: Redis keyed by `(origin_lat_rounded, origin_lng_rounded, dest_lat, dest_lng, hour_of_day)` with 15-minute TTL to minimize Google Maps API calls. No `compute_customer_etas` Celery Beat task exists. Do not add one — the request-time pattern avoids per-ping API costs.

**OAuth token refresh pattern (FIND-116, Phase 4.2 decision)**:
Calendar OAuth access tokens are refreshed **inline at API call time** — not via a dedicated Celery background task. Before any call to Google Calendar or Outlook APIs, the `calendar_service` module checks `tenant_calendar_integration.token_expires_at` against the current time plus a 5-minute buffer. If the token is expiring soon, it calls the provider's token endpoint using the stored (Fernet-encrypted) refresh token, persists the new access token and expiry time to the database, and then proceeds with the API call. This eliminates unnecessary background task overhead — tokens are only refreshed when a tenant actually uses the calendar feature. A dedicated `refresh_calendar_oauth_tokens` hourly task does NOT exist and should NOT be added.

**Receipt OCR implementation — RapidOCR + Llama 3.1 8B (FIND-062 APPLIED — B21 Task 6, 2026-05-19)**:
Receipt auto-fill (PRD-§3.4-F9) uses **RapidOCR** (`rapidocr-onnxruntime`) for image text extraction and **Llama 3.1 8B** (existing `pilot_ollama` container) for structured field parsing. Vendor decision made Phase 5.1 (FIND-137); implementation completed B21 Task 6 (FIND-062); FIND-062 → **APPLIED**.

- **RapidOCR**: open-source Python library (`rapidocr-onnxruntime==1.4.4` in `backend/requirements.txt`); CPU inference runs in the existing ECS Fargate app container — zero additional infrastructure, zero cloud cost.
- **Llama 3.1 8B**: already running on `pilot_ollama` (EC2 g4dn.xlarge); receives the raw OCR text and extracts structured fields (`vendor_name`, `total_cents`, `date`) via a targeted system prompt.
- **No new infrastructure required**: no AWS Textract IAM permissions, no GPT-4V API key, no additional Docker containers. RapidOCR is a pip dependency; Llama 3.1 8B is already loaded.
- **Pipeline**: S3 upload event → `process_receipt_ocr.delay()` triggered in `api/routes/photos.py` on `attachment.expense_id` → `tasks/receipt_ocr.py` Celery task → RapidOCR extracts text → Llama 3.1 8B parses fields → `job_expense.cost_cents` / `ocr_processed_at` / `ocr_source` patched if confidence ≥ threshold.
- **Schema**: `job_expense` table extended with `ocr_processed_at TIMESTAMPTZ NULL` + `ocr_source VARCHAR NULL` (migration `phase_fe_1_batch_b21_job_expense_ocr_`); schema diff ZERO.
- **Mock strategy**: `MockOcrService` following carrier-agnostic adapter pattern (§22) in `services/ocr_service.py` — returns fixture-based `{"vendor": "Home Depot", "total_cents": 4299, "date": "2026-05-16"}` in test environments without calling RapidOCR or Ollama. 16 tests in `backend/tests/batch_b21/test_receipt_ocr_pipeline.py`.
- **Cost model**: $0 per receipt (fully self-hosted); no per-call fees.

### 13.7 API Design

New endpoints under `/api/v1/schedule/` and `/api/v1/calendar/`. All follow existing conventions: RFC 7807 errors, cursor pagination, `Idempotency-Key` header support, RBAC enforcement via `require_permission()`.

| Method | Path | Purpose | Required Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/schedule/board` | Dispatch board data (jobs × techs × date range) | `schedule.manage` |
| `GET` | `/api/v1/schedule/today` | Current user's assigned jobs for today | `schedule.view_own` |
| `POST` | `/api/v1/schedule/jobs/{id}/assign` | Assign tech to job | `schedule.manage` |
| `POST` | `/api/v1/schedule/jobs/{id}/reschedule` | Change scheduled time | `schedule.manage` |
| `POST` | `/api/v1/schedule/jobs/{id}/check-conflicts` | Preview conflicts for proposed change | `schedule.manage` |
| `GET` | `/api/v1/schedule/availability/{user_id}` | Tech availability windows | `schedule.manage` or self |
| `POST` | `/api/v1/schedule/availability/{user_id}` | Set tech availability | `schedule.manage` or self |
| `POST` | `/api/v1/schedule/drive-times` | Batch drive-time calculation for sequence | `schedule.manage` |
| `POST` | `/api/v1/calendar/connect` | Initiate OAuth flow | `integrations.manage` |
| `GET` | `/api/v1/calendar/callback` | OAuth callback handler | (public with state token) |
| `POST` | `/api/v1/calendar/disconnect` | Disconnect calendar integration | `integrations.manage` |
| `GET` | `/api/v1/calendar/status` | Sync status and recent activity | `integrations.manage` |
| `GET` | `/api/v1/calendar/conflicts` | List pending sync conflicts | `integrations.manage` |
| `POST` | `/api/v1/calendar/conflicts/{id}/resolve` | Resolve conflict | `integrations.manage` |

### 13.8 Cost Considerations

**Map provider costs (Google Maps Platform at beta)**:

- Distance Matrix API: $5 per 1,000 elements (origin × destination pairs)
- Geocoding API: $5 per 1,000 requests
- Rate-limited per-tenant to prevent runaway costs

**Estimated usage at 100 customers, avg 5 jobs/day per tenant**:

- ~500 dispatch board operations/day × 10 distance-matrix elements = 5,000 elements
- ~100 new customer geocodes/day = 100 requests
- Monthly: ~150,000 matrix elements + ~3,000 geocodes = **~$770/month**

**Cost optimization strategies**:

- Cache drive times for (origin, destination, hour-of-day) tuples for 24 hours in Redis
- Batch distance-matrix calls (up to 25×25 per request)
- Defer ETA recomputation to GPS updates with >200m movement
- Post-MVP: evaluate self-hosted OSRM on the existing GPU instance (eliminates map API costs, adds ~$0 incremental infrastructure)

**Calendar provider costs (Google Calendar API)**:

- Free tier: 1M queries/day per Google Cloud project
- At 100 customers with 5-minute pull cycles: ~29K queries/day, well within free tier
- No material cost until well past 1,000 customers

### 13.9 Failure Modes & Recovery

| Failure Mode | Detection | Recovery |
| :--- | :--- | :--- |
| Map provider outage | HTTP error, timeout | Dispatch still works; drive times and ETAs show "unavailable" — owner can override manually |
| Calendar provider outage | OAuth refresh fails, API 5xx | Integration `sync_status = error`; tenant notified; dispatch unaffected |
| OAuth refresh token expired | Token refresh returns invalid_grant | Force-disconnect integration; notify owner to reconnect |
| Clock skew between Pilot and calendar | Sync detects future-dated events | Log warning; accept events as-is (provider time is source of truth) |
| Drive time calculation exceeds SLA | Request > 2s timeout | Return cached value if available; else return no drive time (warn badge hidden) |
| Tech GPS unavailable for ETA | No recent location update within 10 min | Omit ETA from customer comms; auto-ETA templates fall back to "Tech is on the way" |

### 13.10 Monitoring

New CloudWatch metrics and dashboards:

- `scheduling.conflicts.detected.count` — dispatch conflicts surfaced per hour
- `scheduling.conflicts.overridden.count` — warnings dismissed by owner
- `calendar_sync.push.success.count` / `calendar_sync.push.failure.count`
- `calendar_sync.pull.success.count` / `calendar_sync.pull.failure.count`
- `calendar_sync.conflicts.pending.gauge` — current count of unresolved sync conflicts
- `calendar_sync.conflicts.auto_expired.count` — conflicts auto-resolved past expiry threshold
- `map_provider.requests.count` (by API: geocode, reverse_geocode, distance_matrix)
- `map_provider.latency.p95.ms`
- `map_provider.cost.usd.gauge` — estimated monthly cost projection
- `dispatch_board.sse_connections.active.gauge` — current count of connected SSE clients
- `dispatch_board.sse_messages.delivered.count` — events pushed to clients per hour

New alarms:

- Calendar sync failure rate > 5% over 15 minutes
- Map provider cost projection > $1,500/month
- Pending sync conflicts > 20 for any tenant
- SSE connection drop rate > 10% over 5 minutes (indicates network or load balancer issue)

### 13.11 Dispatch Board Live Updates (Server-Sent Events)

The dispatch board uses Server-Sent Events (SSE) to push live updates to all connected dispatcher clients without polling. When a job is rescheduled, reassigned, or has its conflict status changed, all connected dispatchers see the update within seconds.

**Why SSE over WebSockets**: dispatch board updates are server → client only (no client-initiated push needed for live updates; mutations go through normal REST endpoints). SSE is simpler, works through standard HTTP infrastructure (no special WebSocket proxy configuration), and reconnects automatically on transient network failures. WebSockets would add complexity without value for this use case.

**Endpoint**: `GET /api/v1/schedule/board/stream` — opens an SSE connection scoped to the requesting user's tenant. Authenticated via JWT in the URL query parameter (SSE doesn't support headers for the initial handshake in browsers); the JWT is validated and immediately discarded — connection state carries `(tenant_id, user_id)` in server memory.

**Channel structure**:

- One SSE channel per tenant (`dispatch:{tenant_id}`)
- Multiple connected clients per tenant share the channel
- Cross-tenant isolation enforced at channel-name level — no broadcast can cross tenant boundaries

**Event types**:

| Event | Payload | Trigger |
| :--- | :--- | :--- |
| `job_scheduled` | `{job_id, tech_id, scheduled_start_at, scheduled_end_at}` | New job placed on the board |
| `job_rescheduled` | `{job_id, prev_start_at, new_start_at, prev_end_at, new_end_at}` | Existing job time changed |
| `job_reassigned` | `{job_id, prev_tech_id, new_tech_id}` | Tech assignment changed |
| `job_unassigned` | `{job_id, prev_tech_id}` | Job moved to unassigned column |
| `conflict_detected` | `{job_id, conflict_class, severity}` | New conflict surfaced for a placed job |
| `conflict_cleared` | `{job_id}` | Previous conflict resolved (via reschedule, reassignment, etc.) |
| `calendar_sync_status` | `{integration_id, status, pending_conflicts_count}` | Calendar integration status changed |

**Connection lifecycle**:

- Heartbeat: server sends a comment line every 15 seconds to keep the connection alive through proxies
- Reconnection: client retries with exponential backoff up to 60s; receives any missed events via `Last-Event-ID` header (server stores the last 100 events per channel for replay)
- Idle timeout: server closes connections idle > 5 minutes without an active client (defensive — most clients heartbeat, but defends against zombie connections)

**Multi-tenant scaling**: SSE connections are stateful and consume one ECS task thread per connection. At 100 customers with 1–2 dispatchers each, expect 100–200 active connections — well within Fargate task capacity. At scale > 1,000 customers, consider Redis Pub/Sub as the broadcast layer to decouple connection count from task count.

**Implementation files**:

- `services/dispatch_board_stream.py` — SSE handler, channel registry, event broadcaster
- `core/sse_middleware.py` — SSE-specific middleware (heartbeat, reconnection, idle timeout)
- Event broadcasts triggered by Celery tasks and write-path API endpoints via internal pub/sub channel

---

## 14. Quote Approval & Templates Architecture

The quote-to-cash lifecycle expanded substantially in Pass 3. This section covers the architectural elements introduced by Flow 5 (quote approval workflow) and Flow 2 (ETC capture).

### 14.1 Quote Line Item Visibility & Hierarchy

Pass 3 introduced two new fields on `quote_line_item`:

| Field | Type | Purpose |
| :--- | :--- | :--- |
| `is_visible_to_customer` | BOOLEAN NOT NULL DEFAULT TRUE | Internal-only items (notes, internal cost categorizations) hidden from the customer-facing proposal |
| `parent_line_item_id` | UUID NULL → quote_line_item(id) | Parent reference for sectioned line items; root items have NULL |

The hierarchy enables the **hybrid quote presentation style** (per §14.2): grouped sections with subtotals, child items rendered indented under their parent. Customer-facing rendering follows the visibility flag and the hierarchy; internal views show all items.

**Constraint**: a child line item cannot have a different `quote_id` from its parent. Enforced via composite foreign key `(quote_id, parent_line_item_id)` rather than just `parent_line_item_id` alone.

### 14.2 Three Quote Presentation Styles

Quotes carry a `presentation_style` field on `quote_version` (frozen at version time):

| Style | Customer-Facing Render |
| :--- | :--- |
| `clean` | Single all-in price with optional summary lines (no itemization) |
| `line_itemed` | Full itemization with quantities, descriptions, unit prices, line subtotals |
| `hybrid` | Sectioned with grouped subtotals; details shown per section using `parent_line_item_id` hierarchy |

The contractor selects style at quote creation; the customer sees only the chosen style on the public proposal. Style is preserved on the immutable version record so historical quotes always render in their original form.

### 14.3 ETC (Estimate-to-Complete) Capture System

Each `job_time_entry` row gains an ETC field set at clock-out time:

| Field | Type | Purpose |
| :--- | :--- | :--- |
| `etc_hours_remaining` | NUMERIC(6,2) NULL | Tech-provided estimate of hours remaining to complete the job at this clock-out |
| `etc_captured_at` | TIMESTAMPTZ NULL | When the ETC was captured (matches `clock_out_at` typically) |
| `etc_variance_note` | TEXT NULL | Optional note explaining a large variance from prior estimates |

**Variance threshold logic** (configurable per tenant):

- `etc_variance_note_required_pct` (default 10%): if a new ETC increases total projected hours (sum of actuals + ETC) by more than this percentage above the prior projection, the tech is required to provide a `etc_variance_note`. Enforced API-side; mobile UI surfaces the field as required.
- `etc_variance_owner_notify_pct` (default 50%): if the projection (actuals + ETC) exceeds the original quoted hours by more than this percentage, the owner is notified via `notification_outbox`. Triggered by the `notify_etc_variance_owners` Celery task (§3.2) running every 15 minutes.

**Projected cost calculation** (extends existing profitability rollup per §3.4):

```
projected_labor_cost_cents = (Σ(time_entry.hours) + Σ(latest_etc_hours_per_tech)) × hourly_rate_cents
projected_total_cents      = projected_labor_cost_cents + actual_material_cost_cents + projected_remaining_material_cost
projected_margin_pct       = (quoted_total_cents - projected_total_cents) / quoted_total_cents
```

The job detail page surfaces both **actual** (current state) and **projected** (with ETC factored in), enabling the contractor to see "where we'll end up" before completion. Below `margin_target_pct` (default 20%) jobs receive a visual indicator.

### 14.4 Quote Approval Workflow

When `require_approval_for_tech_quotes` tenant setting is ON (default for multi-user tenants; OFF for solo), tech-created quotes enter a pending state for owner review.

**State machine** (extends existing `quote_version.status` enum):

```
draft → submitted_for_approval → [approved | rejected | edit_requested]
                                       ↓                    ↓
                                  → sent → ...         → draft (loop)
```

**Pending edit storage during review**:

When the owner is reviewing a `submitted_for_approval` quote and makes inline edits, the edits are stored as **pending changes** on a separate table rather than committed to the quote version directly. This preserves the integrity of the tech's submitted version while the owner deliberates.

```
quote_pending_edit
  id                        UUID PRIMARY KEY
  tenant_id                 UUID NOT NULL
  quote_version_id          UUID NOT NULL → quote_version
  reviewer_user_id          UUID NOT NULL → user
  edit_type                 TEXT NOT NULL  -- 'line_item_modify' | 'line_item_add' | 'line_item_remove' | 'header_modify'
  affected_line_item_id     UUID NULL
  field_name                TEXT NULL  -- e.g., 'unit_price_cents', 'quantity', 'description'
  old_value                 JSONB NULL
  new_value                 JSONB NULL
  created_at                TIMESTAMPTZ NOT NULL
```

When the owner clicks "Approve with edits," the pending edits are committed atomically and a new `quote_version` is created with the merged content. If the owner clicks "Reject" or "Cancel review," pending edits are discarded.

**Approval comments and annotations**:

```
quote_approval_annotation
  id                      UUID PRIMARY KEY
  tenant_id               UUID NOT NULL
  quote_version_id        UUID NOT NULL → quote_version
  annotation_type         TEXT NOT NULL  -- 'line_item' | 'header' | 'overall'
  affected_line_item_id   UUID NULL
  comment                 TEXT NOT NULL
  author_user_id          UUID NOT NULL → user
  created_at              TIMESTAMPTZ NOT NULL
```

Top-level approval/rejection comments use `annotation_type = 'overall'`. Per-line comments (e.g., "Verify this material is in stock") use `annotation_type = 'line_item'` with the affected line referenced.

**API endpoints**:

| Method | Path | Purpose | Required Permission |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/quotes/{id}/submit` | Tech submits draft for approval | `quote.submit_for_approval` |
| `GET` | `/api/v1/quotes/pending-approval` | Owner queue of pending quotes | `quote.approve` |
| `POST` | `/api/v1/quotes/{id}/approve` | Approve (optionally with pending edits) | `quote.approve` |
| `POST` | `/api/v1/quotes/{id}/reject` | Reject with comment | `quote.approve` |
| `POST` | `/api/v1/quotes/{id}/request-edits` | Send back to tech with edits requested | `quote.approve` |
| `POST` | `/api/v1/quotes/{id}/pending-edits` | Stage an inline edit during review | `quote.approve` |
| `POST` | `/api/v1/quotes/{id}/annotations` | Add comment or annotation | `quote.approve` |

All approval endpoints use the pre-commit staleness check pattern (per §7.9): `expected_quote_version_id` is required; mismatched version returns 409 with refreshed state.

**Voice-initiated approval** (per §6.2 — confirm-as-turn applies): owners can approve, reject, or request edits via voice. Voice cannot make line-item edits — those route to the web review UI via refusal-with-redirect.

### 14.5 Quote Template System with Style and Versioning

Templates are first-class versioned entities with both system-curated and tenant-owned variants.

```
quote_template
  id                        UUID PRIMARY KEY
  tenant_id                 UUID NULL  -- NULL = system template; non-null = tenant-owned
  name                      TEXT NOT NULL
  presentation_style        TEXT NOT NULL  -- 'clean' | 'line_itemed' | 'hybrid'
  is_active                 BOOLEAN NOT NULL DEFAULT TRUE
  created_at                TIMESTAMPTZ NOT NULL

quote_template_version
  id                        UUID PRIMARY KEY
  template_id               UUID NOT NULL → quote_template
  version_number            INT NOT NULL
  content_json              JSONB NOT NULL  -- line items, sections, defaults
  changelog                 TEXT NULL  -- optional human-readable change description
  created_at                TIMESTAMPTZ NOT NULL
  created_by_user_id        UUID NOT NULL  -- system user for system templates
  UNIQUE (template_id, version_number)

quote_template_fork
  id                        UUID PRIMARY KEY
  source_system_template_id UUID NOT NULL  -- the system template that was forked
  tenant_template_id        UUID NOT NULL  -- the resulting tenant-owned template
  forked_at                 TIMESTAMPTZ NOT NULL
  forked_by_user_id         UUID NOT NULL
```

**System template update notification flow**:

When Pilot updates a system template (e.g., new NEC reference, pricing methodology improvement), a daily Celery task (`notify_system_template_updates` per §3.2) finds tenants whose recent quotes (last 30 days) used that template and enqueues notifications: "The 'Service Panel Upgrade' system template has been updated. Review and optionally adopt the changes for new quotes."

Tenants who have forked the template into tenant ownership (`quote_template_fork`) do NOT receive these notifications — they own their copy and are not affected by system updates.

### 14.6 Time-Limited Discounts with Margin Cap

```
quote_discount
  id                  UUID PRIMARY KEY
  tenant_id           UUID NOT NULL
  quote_id            UUID NOT NULL → quote
  discount_type       TEXT NOT NULL  -- 'percentage' | 'fixed_cents'
  discount_value      NUMERIC NOT NULL
  expires_at          TIMESTAMPTZ NOT NULL
  applied_by_user_id  UUID NOT NULL
  applied_at          TIMESTAMPTZ NOT NULL
```

**Margin cap enforcement** (server-side at quote write time):

When a discount is applied, the server computes the post-discount margin and compares against `max_discount_pct_owner` (tenant setting, default 15%). If the discount would push the margin below the cap, the API returns 422 with a structured error:

```json
{
  "type": "https://pilotfortrades.com/errors/margin-cap-exceeded",
  "title": "Discount exceeds margin cap",
  "status": 422,
  "detail": "This discount would reduce margin to 8.2%, below the 15% margin cap.",
  "current_margin_pct": 24.5,
  "post_discount_margin_pct": 8.2,
  "margin_cap_pct": 15.0,
  "hint": "Reduce the discount or contact the owner to override the cap."
}
```

The owner (with `quote.apply_discount` permission) can explicitly override by passing `override_margin_cap=true`; this is logged in the audit trail with full attribution.

---

## 15. Mobile Offline Operations Architecture

Pass 3 Flow 7 introduced offline-to-online sync as a first-class capability. This is the largest single architectural addition; offline-tolerant mobile is a defining MVP commitment.

### 15.1 Strategic Direction

**Optimistic UI is mandatory**: a tech in a basement cannot wait 30 seconds to find out whether their clock-in succeeded. Every offline-capable operation appears successful immediately on the device, with a non-disruptive "pending sync" badge until confirmation. This commits the platform to eventually-consistent semantics at the mobile boundary.

**Sync visibility is non-negotiable**: the tech must always know what's queued, what's in flight, and what failed. A silent backlog of unsynced data is a category-A bug — that's how data loss happens.

**Auto-resolve where possible; escalate where necessary**: most offline operations sync without conflict. A few create conflicts the tech can resolve on the phone. A small subset require the owner. The platform classifies conflicts into four severity tiers (per §15.6) and routes each to the right resolver.

**Photos are heavy; treat them differently**: time entries and expenses are kilobyte payloads. Photos are megabyte payloads. They get a separate upload pipeline with WiFi preference (per §15.5).

**Voice is captured offline; processed online**: there is no on-device transcription in MVP. Voice audio captured offline is stored locally and uploaded for processing when the device reconnects (per §6.7 / §15.7).

### 15.2 Offline-Capable Operations Contract

The platform commits to a specific list of operations that work fully offline. Anything not on the list must explicitly fail or queue with a clear message when triggered offline.

**Fully offline-capable**:
- Clock in / clock out (with ETC capture per §14.3)
- Time entry creation
- Expense capture (with attached photo via §15.5)
- Site / job photo capture
- Status changes on already-assigned jobs
- LOTO check confirmation
- Voice audio capture (deferred processing per §6.7 / §15.7)
- Free-text job notes
- NEC code calculations (math; cached NEC reference data on device)
- Change order creation against an already-assigned job

**Partial offline** (functional with caveats):
- Customer / job / material lookup — works for cached entities; UI shows "offline — limited data" for uncached records

**Not offline-capable** (explicitly online-only):
- Customer creation
- Quote send (server-rendered PDF + delivery)
- Customer comms send (preserves Flow 4 always-preview-with-live-ETA rule per §16.7)
- Calendar sync, QuickBooks sync, dispatch board, owner approval actions
- Voice command processing (capture is offline; processing requires online)

**Schema requirement**: offline-capturable tables (`job_time_entry`, `expense`, `photo`, `change_order`, `loto_check`, `job_status_change`, `job_note`) carry `client_capture_at TIMESTAMPTZ NULL`, distinct from `created_at` (server-side). The gap (`server_received_at - client_capture_at`) is queryable for offline-duration analysis and (for LOTO specifically) liability documentation.

### 15.3 Sync Queue State Model

Server-side append-only log captures every sync attempt per device per operation:

```
mobile_sync_event
  id                          UUID PRIMARY KEY
  tenant_id                   UUID NOT NULL
  user_id                     UUID NOT NULL
  device_id                   TEXT NOT NULL
  operation_type              TEXT NOT NULL
  operation_payload_summary   JSONB
  status                      TEXT NOT NULL  -- 'pending' | 'syncing' | 'succeeded' | 'failed' | 'conflict'
  conflict_severity           TEXT NULL  -- 'auto_silent' | 'auto_notice' | 'tech_resolvable' | 'owner_escalation'
  client_capture_at           TIMESTAMPTZ NOT NULL
  synced_at                   TIMESTAMPTZ NULL
  error_detail                JSONB NULL
  idempotency_uuid            UUID NOT NULL
  created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
```

Index on `(tenant_id, user_id, status)` for fast per-tech queue queries. 30-day hot retention; archived consistent with audit log policy (§3.2 `cleanup_mobile_sync_events`).

**API**: `GET /api/v1/mobile-sync/state/{user_id}` — admin view (owner/support) of a tech's sync state, paginated. Useful for owner reviewing tech sync state and for support troubleshooting.

### 15.4 Idempotency UUIDs with Natural-Key Fallback

Every offline-capable operation generates a client-side UUID v4 at capture time and persists it with the operation in the local queue. The UUID is sent as the `Idempotency-Key` header on every sync attempt for that operation, regardless of how many retries.

The platform's existing 24-hour idempotency window (§7.6) handles normal retries. For the 72-hour offline scenario where the window has expired, the natural-key fallback dedup (per §7.6 extension table) catches the duplicate based on operation-specific natural keys.

The combination — 24-hour idempotency hot path + natural-key 7-day window for offline scenarios — covers the full 72-hour offline limit plus safety margin.

### 15.5 Resumable Photo Upload Pipeline (S3 Multipart)

Photos use a separate upload pipeline from data sync, with WiFi preference and resumable chunked transfer.

**Implementation choice**: S3 multipart upload directly from client with signed URLs. Rationale: offloads heavy lifting to S3, avoids Pilot as a chunk-relay middleman, scales better at any tenant volume.

**API endpoints**:

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/v1/photos/initiate-upload` | Returns S3 multipart session ID + presigned chunk URLs + `pilot_photo_id` |
| `POST` | `/api/v1/photos/complete-upload` | Validates all chunks present; calls S3 CompleteMultipartUpload; finalizes photo record |

**Client SDK behavior**:

- Tracks per-chunk completion in local state
- Resumes from last-completed chunk on retry (skips already-uploaded chunks)
- Configurable chunk size (default 5MB)

**WiFi/cellular preference** (client-side scheduling; server doesn't enforce):

- Tenant setting `photo_upload_wifi_only` (default TRUE)
- User override: "Upload photos on cellular when offline > 24 hours"
- Photos waiting for WiFi appear in the sync queue with "WiFi pending" tag

**Server-side cleanup**:

- Incomplete S3 multipart sessions auto-expire after 24 hours via S3 lifecycle rule
- `cleanup_incomplete_photo_uploads` Celery task runs weekly to remove orphaned `photo` records whose multipart sessions never completed

**Local cleanup**:

- Tenant setting `photo_local_retention_days` (default 7) — synced photos kept on device this long, then auto-purged
- Client SDK manages purging; server tracks confirmation timestamps for auditability

### 15.6 Conflict Severity Classification Engine

When sync detects a conflict, the platform classifies it into one of four severity tiers (the four-class pattern formalized in §16.6).

| Class | Treatment | Trigger Examples |
| :--- | :--- | :--- |
| **`auto_silent`** | Sync proceeds; no notification | Time entry against still-valid assignment; expense category exists; photo uploads to expected job |
| **`auto_notice`** | Sync proceeds; toast or queue-surface note | Expense category renamed server-side (mapped automatically); minor field defaults updated since capture |
| **`tech_resolvable`** | Sync paused; appears in "Action needed"; tech picks resolution on phone | Job reassigned to another tech mid-shift; quote line item modified; expense exceeds tenant per-item limit |
| **`owner_escalation`** | Sync paused; flagged to owner; tech sees "sent to owner" status | Job deleted while tech worked it; severe data integrity issue; auth/permission boundary changes |

**Classification engine** (`services/mobile_sync_conflict.py`): per-operation rules in a configuration table (data-driven, not hardcoded) so the matrix can be tuned without code deploys. Returns a `SyncResolution` object with severity, auto-resolved flag, tech-action-required flag, owner-escalation-required flag, and resolution payload.

**Per-operation classification matrix** (shipped defaults; tunable per tenant in advanced cases):

| Operation | Trigger | Severity |
| :--- | :--- | :--- |
| Time entry | Job still assigned to tech | `auto_silent` |
| Time entry | Job reassigned to different tech | `tech_resolvable` |
| Time entry | Job deleted while tech worked it | `owner_escalation` |
| Time entry | Time overlaps existing entry (same tech) | `tech_resolvable` |
| Expense | Category exists, under limit | `auto_silent` |
| Expense | Category renamed server-side | `auto_notice` |
| Expense | Exceeds tenant per-item limit | `tech_resolvable` |
| Expense | Job deleted while expense captured | `owner_escalation` |
| Photo | Job exists | `auto_silent` |
| Photo | Storage limit exceeded | `tech_resolvable` |
| Photo | Job deleted while photo captured | `owner_escalation` |
| Status change | Tech-assigned, normal transition | `auto_silent` |
| Status change | Job already completed by another tech | `owner_escalation` |
| Change order | Quote version still active | `auto_silent` |
| Change order | Quote version superseded | `tech_resolvable` |
| LOTO check | Job still in progress | `auto_silent` |
| LOTO check | Job completed before LOTO sync arrived | `auto_notice` |

### 15.7 Voice Capture Offline, Process Online

Detailed pipeline architecture in §6.7. Summary of mobile-side responsibilities:

- Audio captured locally on device when offline; saved to local app storage with size limits per tenant policy
- Tech sees "Voice captured — will process when online" toast; no failure UX
- On reconnection, audio uploads via `POST /api/v1/voice/upload-audio` with idempotency UUID + capture timestamp + context (originating screen, conversation_session_id)
- Server-side processing pipeline (Whisper → Llama → intent routing) per §6.7
- Destructive intents fall into deferred-confirmation flow (24-hour timeout); confirmation prompt arrives as a notification, tech responds in normal voice or touch flow
- Pre-commit staleness check (§7.9) runs at confirmation time; if state has shifted, AI re-reads updated context aloud before committing

### 15.8 Force-Quit Recovery via Persistent Local Queue

Tech force-quits the app, drops the device, runs out of battery — all common. The sync queue must survive these events.

**Client-side persistence**:

- iOS: Core Data with synchronous writes for queue mutations
- Android: Room with transactional writes
- Cross-platform (Expo): SQLite via Expo's persistence APIs as the shared layer

**Each queue item carries**:
- Client UUID (idempotency key)
- Operation type
- Full request payload
- Status (`pending | syncing | succeeded | failed | conflict`)
- Retry count
- Last error
- Last attempt timestamp

**On app launch**:
- Load queue from local storage
- Mark "syncing" items as "pending" (idempotency keys + natural-key fallback handle duplicate protection on retry per §15.4)
- Resume normal sync trigger flow

**Cross-platform behavior tests** (per Flow 7 validation checklist):
- iOS: app force-quit → relaunch → queue resumes
- iOS: app backgrounded > 30 minutes → relaunch → queue resumes
- Android: app force-stop → relaunch → queue resumes
- Android: app killed by OS memory pressure → relaunch → queue resumes
- Both: device reboot mid-sync → relaunch → queue resumes

### 15.9 Tech-Resolvable Conflict Resolution Endpoints

When a conflict is classified as `tech_resolvable`, the tech resolves it on the phone via a vertical-stacked diff UI (phone-adapted from §13.5's web layout).

**API endpoints**:

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/v1/mobile-sync/conflicts/{id}` | Conflict detail: tech version, server version, classification, field-level diff |
| `POST` | `/api/v1/mobile-sync/conflicts/{id}/resolve` | Resolve: `use_local | use_server | escalate_to_owner` |

The conflict detail response uses the same field-level diff structure as calendar conflicts (per §13.5), enabling shared rendering logic across web and mobile.

**Pre-resolution staleness check** (per §7.9): `expected_server_version_id` is required; 409 returns refreshed state. Voice path uses confirm-as-turn (§6.6) for resolution.

**Audit**: every resolution logged to `mobile_sync_event` with status `succeeded` and a `resolution_action` field capturing which path was taken.

### 15.10 Owner Escalation Routing

When a conflict cannot be tech-resolved (severity `owner_escalation`) or the tech chooses to escalate, it routes to the owner.

```
mobile_sync_owner_escalation
  id                       UUID PRIMARY KEY
  tenant_id                UUID NOT NULL
  originating_user_id      UUID NOT NULL  -- the tech
  conflict_id              UUID NOT NULL  -- → mobile_sync_event
  escalated_at             TIMESTAMPTZ NOT NULL
  escalation_reason        TEXT NOT NULL  -- 'auto_severity' | 'tech_chose'
  status                   TEXT NOT NULL  -- 'pending' | 'resolved' | 'rejected'
  resolved_by_user_id      UUID NULL
  resolved_at              TIMESTAMPTZ NULL
  resolution_action        TEXT NULL  -- 'used_local' | 'used_server' | 'manual_edit' | 'rejected'
  resolution_payload       JSONB NULL
```

**API endpoints**:

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/v1/owner/mobile-sync-escalations` | List pending escalations for owner |
| `GET` | `/api/v1/owner/mobile-sync-escalations/{id}` | Detail with full conflict context |
| `POST` | `/api/v1/owner/mobile-sync-escalations/{id}/resolve` | Owner resolves with action + optional manual edit |

**Notification flow**: on escalation creation, push + `notification_outbox` entry to owner. On owner resolution, push to originating tech ("Your conflict was resolved by Sarah — your local data was kept").

**Web UI for resolution**: deferred to Pass 4. Design language inherits from §13.5 calendar conflict resolution.

### 15.11 Time-Bounded Offline Operation

Two thresholds:

- **Soft limit at 24 hours**: connection state indicator changes to "Long offline · N items"; tech sees one-time toast on app open
- **Hard limit at 72 hours**: app blocks new offline operations until a sync occurs; full-screen warning with manual sync trigger

**Tenant setting**: `offline_hard_limit_hours` (default 72; nullable for tenants who legitimately operate in extreme offline conditions, e.g., rural utility work, mining sites). Soft limit is fixed (UX threshold, not policy threshold).

**Refresh token TTL constraint** (per §4.6): the 72-hour hard limit is informed by Cognito's 30-day refresh token TTL. Reducing the refresh token TTL below 7 days requires a corresponding reduction in `offline_hard_limit_hours`.

### 15.12 Auth Expiry Handling with Disabled-Account Export

Per §4.6, the standard refresh token flow handles normal expiry. The edge case is tenant-disabled-the-user-mid-offline.

**Edge case flow**:
- Re-auth attempt fails permanently (account-disabled, not token-expired)
- UI surfaces: "Account disabled — contact your owner. Captured data is saved locally."
- Export affordance: "Email me a JSON copy of unsynced data" — tech enters an external email address; client SDK assembles a JSON dump and sends via local mail client (not via Pilot API since the account is disabled)
- After 30 days locally, captured data auto-purges to prevent indefinite retention on a disabled-user device

This preserves data integrity while respecting the owner's decision to disable the user.

### 15.13 Sync Triggers (Updated: Background Sync Now in MVP — see §16.12)

Sync runs on:

- App foreground transition (every time the app comes to foreground)
- OS network state change to online
- Periodic check every 30 seconds while app active and online
- Manual trigger from the queue surface ("Sync now" button)
- **Background sync** (server-initiated silent push as primary trigger; OS-scheduled opportunistic execution as fallback) — **now in MVP scope** per Pass 4 Tier 1 #3 (A51). See §16.12 for the authoritative background sync specification. The previous "Explicitly out of MVP scope" note below was superseded when A51 was pulled forward into MVP. (FIND-123 — Phase 4.2 correction)

### 15.14 Customer Comms Stay Online-Only

Per §16.7's always-preview-before-send rule, customer-facing comms cannot be sent offline. Voice intent capture works offline (per §6.7); the actual SMS/email send is blocked until online. Touch attempts to send a template card while offline compose-and-queue with a "preview pending" flag; on reconnection, the always-preview rule renders the message with live ETA before send. This preserves the one-way-door safety property of customer comms.

---

## 16. Cross-Cutting Platform Patterns

Pass 3 surfaced and formalized a set of cross-cutting patterns that now constitute Pilot's platform-wide implementation vocabulary. These are reused across multiple domains; new domains added in Phase 2 inherit these patterns by default. Deviations require explicit justification.

### 16.1 Pattern Inventory

| Pattern | First Established | Reuse Count |
| :--- | :--- | :--- |
| Track-changes diff vocabulary (amber/green/red) | Flow 5 (Quote approval) | 5 (quote approval §14, calendar conflict §13.5, mobile sync §15, mobile-conflict escalation §16.11, QB conflict §5.4 / §16.10) |
| Four-class severity pattern | Flow 3 (Dispatch conflicts) | 3 (dispatch §13.4, calendar sync §13.5, mobile sync §15.6) |
| Confirm-as-turn for destructive voice actions | Flow 1 (Voice quote creation) | All destructive voice intents §6.2 |
| Pre-commit staleness check (409-and-refresh) | Flow 3 (Dispatch board edits) | 8+ endpoints across §13.7, §13.5, §14.4, §15.9, §5.4, §16.11 |
| System default + tenant override two-tier configuration | Flow 6 (Calendar conflict auto-expiry) | Calendar §13.5, QB conflicts §5.4, background sync §17, sync indicator threshold §16.13; available platform-wide |
| Mobile owner status row + deep-link | Pass 2 QB sync | Extended for calendar §13.5, mobile sync §15.3, field issues §16.11, in-flight sync indicators §16.13 |
| Optimistic UI with pending badges | Flow 7 (Mobile offline) | All mobile offline-capable operations §15; settings UIs (Tier 2 #4) |
| Always-preview-before-send for one-way-door actions | Flow 4 (Customer comms) | Customer comms PRD §3.7; SMS replies §17; extensible to any future irreversible action |
| Bilateral integration conflict resolution pattern (formalized §16.10) | Flow 6 (Calendar) | Calendar §13.5, QuickBooks §5.4 |
| Mobile-to-web escalation pattern | Pass 4 Tier 1 #1 (Owner mobile-conflict UI) | Field issues §16.11; extensible to time-off requests, safety incidents, catalog requests |
| Background sync execution pattern | Pass 4 Tier 1 #3 (Background sync for mobile) | Mobile data queue §15, push token registry §17.10; extensible to periodic data refresh, future tech-to-tech messaging |
| Carrier-agnostic adapter layer pattern | Pass 4 Tier 1.5 (SMS via Telnyx) | SMS §17.1; extensible to other external service integrations (payment, mapping, email) |
| Subscription quota with soft/hard cap pattern | Pass 4 Tier 1.5 (SMS quota) | SMS quota §17.6; available for any future per-event metered feature |
| Lazy provisioning of external resource at first use | Pass 4 Tier 1.5 (Telnyx number) | Telnyx number §17.3; extensible to dedicated voice processing slots, customer-facing portal subdomains |
| In-Flight Sync Indicator with Pending Count | Pass 4 Tier 4 #12 (Dispatch board sync indicator refinement) | Calendar §13.5, QuickBooks §5.4, mobile data sync §15, background sync §17; extensible to any future sync surface |

### 16.2 Track-Changes Diff Vocabulary

A consistent visual language for diffs across the platform:

- **Amber** for modified fields (with prior value as struck-through helper text)
- **Green** for added fields ("(added)" annotation)
- **Red** for removed fields (strikethrough + "(removed)" annotation)

**Server-computed `field_diffs` payload structure** (used by §13.5 calendar conflicts, §15.9 mobile sync conflicts, §14.4 quote approval review):

```json
{
  "field_diffs": [
    {
      "field_name": "scheduled_start_at",
      "pilot_value": "2026-04-30T09:00:00Z",
      "external_value": "2026-04-30T10:00:00Z",
      "base_value": "2026-04-30T09:00:00Z",
      "pilot_change": "unchanged",
      "external_change": "modified"
    },
    {
      "field_name": "site_address",
      "pilot_value": "742 Main St",
      "external_value": null,
      "base_value": "742 Main St",
      "pilot_change": "unchanged",
      "external_change": "removed"
    }
  ]
}
```

The frontend renders the diff using the platform-wide track-changes color tokens (per Pass 1 design tokens). Computing the diff server-side ensures consistent rendering across web and voice readback paths.

### 16.3 Confirm-as-Turn for Destructive Voice Actions

Detailed in §6.6. Universal across the platform: every voice intent that creates, modifies, or deletes durable data routes through an explicit confirmation turn before commit. Implementation lives in `voice_action_router.py` with state stored in `conversation_session.context_window_json.pending_confirmation`.

### 16.4 Pre-Commit Staleness Check (409-and-Refresh)

Detailed in §7.9. Write endpoints accept expected-version timestamps and return `409 Conflict` with refreshed state when the underlying record has changed since the client last viewed it.

**Pattern checklist for any new write endpoint**:

1. Identify the entity's "version" field (typically `updated_at` or a dedicated version UUID)
2. Accept `expected_<version_field>` parameter on the write endpoint
3. Re-query the entity at write time; compare to expected
4. If mismatch: return 409 with the refreshed entity payload
5. Document the parameter in the endpoint's OpenAPI spec
6. Add client-side handler: refresh view, surface "this has been updated" banner, user re-decides

### 16.5 System Default + Tenant Override Two-Tier Configuration

Settings that need both platform-wide control and per-tenant flexibility use this pattern.

**Schema convention**:

```
-- Platform-wide defaults (admin-configurable)
platform_setting
  key                    TEXT PRIMARY KEY  -- e.g., 'system_calendar_conflict_auto_expire_days'
  value                  JSONB NOT NULL
  data_type              TEXT NOT NULL  -- 'integer' | 'string' | 'boolean'
  description            TEXT NOT NULL
  updated_by_user_id     UUID
  updated_at             TIMESTAMPTZ NOT NULL

-- Per-tenant overrides (in tenant_setting)
-- Tenant override columns are nullable; null = inherit system default
```

**Effective value resolution helper**:

```python
def get_effective_setting(
    tenant_id: UUID,
    tenant_setting_key: str,
    system_default_key: str,
    fallback: Any,
) -> Any:
    tenant_value = get_tenant_setting(tenant_id, tenant_setting_key)
    if tenant_value is not None:
        return tenant_value
    system_value = get_platform_setting(system_default_key)
    if system_value is not None:
        return system_value
    return fallback
```

**UI conventions**:

- Settings UIs distinguish "inherited from system default" (rendered with subtle annotation) from "tenant override" (rendered as actively configured)
- Allow override or revert-to-system-default
- Allow disable via separate boolean flag (e.g., `calendar_conflict_auto_expire_enabled`) when meaningful

**Settings using this pattern (Pass 3):**

- `calendar_conflict_auto_expire_days` / `system_calendar_conflict_auto_expire_days`
- `calendar_conflict_pre_warning_days` / `system_calendar_conflict_warn_days_before`

**Settings using this pattern (Pass 4 Tier 1):**

- `background_sync_push_interval_minutes` / `system_background_sync_push_interval_minutes` (per Pass 4 Tier 1 #3 Decision 4)
- `qb_auto_expire_*_enabled` family (per-entity-type for customers, quotes, invoices, expenses) (per Pass 4 Tier 1 #2 Decision 9)
- `qb_auto_expire_*_direction` paired settings (`accept_local | accept_remote` per entity type)
- `qb_auto_expire_days` / `system_qb_auto_expire_days` (default 60; Pass 4 Tier 1 #2 Decision 9)
- `qb_pre_warning_days` / `system_qb_pre_warning_days` (default 14)

**Settings using this pattern (Pass 4 Tier 1.5):**

- `sms_quota_cap_policy` (`soft | hard`; default `soft`; tenant-only override; per Tier 1.5 Decision 8)

**Settings using this pattern (Pass 4 Tier 2):**

- `voice_persona_tone` / system default `balanced` — tenant tone setting; per-user override allowed via three-tier resolution (per Tier 2 #6)
- `voice_persona_tone_user_override_allowed` — tenant policy whether per-user override is allowed (default TRUE; tenant-only)

**Settings using this pattern (Pass 4 Tier 4):**

- `tenant_sync_indicator_pending_amber_threshold` / `system_sync_indicator_pending_amber_threshold` (default 5; range 1–100; per §16.13)

**Pass 4 introduces a three-tier resolution chain extension** (per Settings IA framework Decision 6 / Tier 2 #4 Mockup C): some settings allow per-user overrides on top of the tenant + system tiers. The resolver helper extends to:

```python
def get_effective_setting_for_user(tenant_id, user_id, key, fallback=None):
    """Three-tier resolver: user → tenant → system → fallback."""
    if setting_allows_user_override(tenant_id, key):
        user_value = get_user_setting_override(tenant_id, user_id, key)
        if user_value is not None:
            return user_value
    tenant_value = get_tenant_setting(tenant_id, key)
    if tenant_value is not None:
        return tenant_value
    system_value = get_platform_setting(f"system_{key}")
    if system_value is not None:
        return system_value
    return fallback
```

**Settings allowing per-user override** (Pass 4 Tier 2):

- `voice_persona_tone` (per Tier 2 #6) — when `voice_persona_tone_user_override_allowed` is TRUE
- `background_sync_enabled` (per Tier 1 #3) — user can override own device behavior

User-level settings stored in `user_setting_override` table (per A53 from Tier 2 #4). Schema:

```sql
user_setting_override (
    tenant_id    UUID NOT NULL,
    user_id      UUID NOT NULL,
    setting_key  TEXT NOT NULL,
    value        JSONB NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, user_id, setting_key)
)
```

Available for any future setting where personal preference is appropriate within tenant policy.

### 16.6 Four-Class Severity Pattern

Conflicts and warnings classify into four severity tiers with proportional UI treatment:

| Tier | Routing |
| :--- | :--- |
| **Auto-silent** | System proceeds; no user notification |
| **Auto-with-notice** | System proceeds; toast or unobtrusive note |
| **User-resolvable** | System pauses; user picks resolution |
| **Escalation** | System pauses; routed to higher authority (owner, support) |

**Used in**:

- Dispatch conflicts (§13.4): `overlap`, `availability`, `travel`, `info`
- Calendar sync (§13.5): three lifecycle conflict types plus auto-resolved-stale state
- Mobile sync (§15.6): `auto_silent`, `auto_notice`, `tech_resolvable`, `owner_escalation`

The pattern recognizes that not every conflict needs the same level of attention. Routing classifications correctly is the difference between an attentive user and an alert-fatigued user.

### 16.7 Always-Preview-Before-Send for One-Way-Door Actions

For customer-facing communications (PRD §3.7) and any future irreversible action: every outbound message — whether voice-initiated, touch-initiated, or template-driven — renders a final preview to the originating user before commit. The user must explicitly confirm send.

**Implementation pattern**:

1. `POST /api/v1/communications/preview` — accepts template selection + context; returns rendered message body, recipient, channel; does NOT send
2. Frontend always calls preview before send
3. Preview UI shows the rendered content, recipient identity, channel selection
4. User can override channel on a per-message basis from the preview screen
5. User confirms send → separate `POST /api/v1/communications/send` endpoint actually dispatches

**Voice path**: voice intent captures the message → server renders the preview → AI reads the preview aloud → user confirms via confirm-as-turn (§6.6). For offline-captured voice intents (§15.7), the preview rendering happens at confirmation time on reconnection, with live ETA recomputed from current network position.

**Why this pattern**: customer comms are one-way doors (a wrong message cannot be unsent). The preview is the safeguard against accidental sends, voice misrecognitions, and stale ETAs. Offline support is not allowed to compromise this — captured intent waits for online preview.

### 16.8 Optimistic UI with Pending Badges

Used in §15 mobile offline operations. Universal pattern for any future async-write surface where the user shouldn't wait on server confirmation.

**Pattern**:

- Operation appears immediately successful in UI
- Affected entity carries a "pending sync" badge until confirmation
- Successful sync clears the badge
- Failed sync transitions badge to red with retry/resolve affordance
- Sync queue surface (per §15.3) provides ambient visibility

### 16.9 Mobile Owner Status Row + Deep-Link

Cross-surface integration health surfaces as a status row on the mobile Owner tab. Each row has:

- Color-coded dot (green = healthy; amber = pending action; red = error)
- Integration name
- Last sync time
- Count of pending items (when relevant)
- Deep-link to web for touch resolution OR voice resolution hint

**Currently used for**:

- QuickBooks sync (Pass 2)
- Calendar sync (§13.5)
- Mobile sync state (§15.3)

**Extensible to**: any future bi-directional integration or async-status surface.

### 16.10 Bilateral Integration Conflict Resolution Pattern

This pattern governs owner-resolves-conflict surfaces for any bilateral integration where both Pilot and an external system can modify the same entity. Reference instances: calendar sync (Pass 3 Flow 6, formalized in §13.5) and QuickBooks sync (Pass 4 Tier 1 #2, formalized in §5.4). Future bilateral integrations (Salesforce, HubSpot, generic webhook integrations) inherit this pattern by default; deviations require explicit justification.

**Pattern attributes that are domain-determined rather than fixed**:

- **Auto-expiry default**: ON when the master is unambiguous and silent fallback to a known direction is safe (calendar — Pilot is master). OFF when masters are heterogeneous or recovery cost is high (QuickBooks — different masters per entity type, accounting integrity stakes). Tenants can opt in/out per entity type via the §16.5 system-default-with-tenant-override pattern.
- **Voice resolution scope**: full active resolution when stakes permit (calendar). Status-query-only when stakes are too high for voice's confirm-as-turn safeguard (QuickBooks accounting data).
- **Column ordering and primary-button treatment**: master-aware (column with the master entity gets leftward primacy and primary-indigo button) when masters are heterogeneous. Reduces to fixed ordering when the master is uniform across all entity types within the integration.

**Pattern attributes that are fixed**:

- Side-by-side two-column diff with track-changes vocabulary (§16.2)
- Two-button bottom action bar with "Resolve later" escape
- Deletion-conflict distinct verb-based treatment (existence-level decisions use verb buttons rather than side-pickers)
- Pre-commit staleness check (§16.4)
- Modal-feeling but URL-routed (bookmarkable, refresh-able)
- Audit-but-no-undo (audit log preserves resolution; mistakes corrected via normal edit flows)
- Empty state teaches normalcy (informative, not alarming)
- Mobile owner status row + deep-link (§16.9)
- System-default + tenant-override auto-expiry (when applicable per the domain-determined attribute above; uses §16.5)

**Reference UI implementations**:

- §13.5 (Calendar conflict resolution architecture)
- §5.4 (QuickBooks conflict resolution; UI added in Pass 4 Tier 1 #2)

### 16.11 Mobile-to-Web Escalation Pattern

When mobile-originated activity requires owner judgment that the tech cannot or should not make autonomously, the activity is paused at the mobile origin, escalated to a web-side queue with push notification to the owner, resolved by the owner on web (or via voice for binary cases), and looped back to the originating tech with the resolution outcome reflected in their mobile experience. Resolution honors the pre-commit staleness check pattern (§16.4). Audit trail records both the originator and the resolver.

**Pattern characteristics**:

- *Origin*: a mobile-side action that classifies into a severity tier requiring owner involvement (per the four-class severity pattern §16.6, the "owner_escalation" class)
- *Routing*: persistent server-side queue + push notification + entry in the appropriate web `Approvals` sub-surface
- *Resolution*: web-only diff view inheriting the bilateral integration conflict resolution pattern's two-column treatment (§16.10), with voice resolution for binary cases
- *Loop closure*: originating mobile device receives status update, push notification, and persistent activity log entry
- *Auditability*: both originator and resolver are captured in the audit log

**Reference instance**: Pass 4 Tier 1 #1 (owner-side mobile-conflict resolution; backend in A47–A48).

**Future surfaces inheriting this pattern** (Phase 2): tech-submitted time-off requests, tech-flagged safety incidents, tech-requested catalog item additions, tech-flagged customer issues escalating to owner, tech-requested expense limit overrides.

**Distinct from §16.9 mobile owner status row + deep-link**: that pattern is read-only (mobile shows web status). This pattern is full round-trip (mobile creates, web resolves, mobile reflects).

### 16.12 Background Sync Execution Pattern

When a mobile queue requires execution outside of foreground app sessions, the platform uses an asymmetric implementation strategy with a uniform user experience. Reference instance: Pass 4 Tier 1 #3 (background sync for mobile data queue; backend in A51).

**Pattern attributes**:

- *Primary trigger*: server-initiated push (silent push on iOS, high-priority FCM on Android), rate-limited per device with a tenant-configurable interval (uses §16.5 system-default-with-tenant-override pattern; setting `background_sync_push_interval_minutes`, default 5)
- *Fallback trigger*: OS-scheduled opportunistic execution (BGAppRefreshTask on iOS, WorkManager periodic on Android); used when push delivery is delayed or throttled
- *Execution scope*: lightweight operations only; heavy operations (photos, voice audio, periodic data refresh) remain foreground-only unless explicitly upgraded
- *Conflict handling*: auto-resolves only in background (per §16.6 four-class severity pattern, only `auto_silent` and `auto_with_notice` classes commit in background); `tech_resolvable` and `owner_escalation` classes defer to foreground
- *Failure visibility*: every background run reports outcome to a tech-visible "last attempt" indicator on next app open; persistent failures (>3 consecutive) trigger a foreground notification
- *Platform-asymmetric implementation, uniform UX*: tech experience is identical across iOS and Android; underlying mechanisms differ

**Future surfaces inheriting this pattern** (Phase 2): periodic data refresh (pulling jobs/customers/quotes/etc. while backgrounded), background photo upload (if upgraded from foreground), tech-to-tech messaging delivery, future asynchronous server-to-mobile push delivery.

**Push token registry** is canonical infrastructure introduced by A51; reused by mobile-to-web escalation loop closure (§16.11) and any future surface requiring server-to-mobile push.

### 16.13 In-Flight Sync Indicator with Pending Count

A sync surface (calendar sync, QuickBooks sync, mobile data sync, background sync) renders its current state plus a count of pending operations that haven't yet completed. This pattern was formalized at Tier 4 #12 to address the operational gap where a binary "synced or syncing" indicator implied currency that wasn't always true between sync cycles.

**Five compositional states**:

| State | Pending count | Visual treatment |
| :--- | :--- | :--- |
| Synced (idle) | 0 | Green dot, "Synced · last 12s ago" |
| Synced (pending detected) | N>0, no active sync | Green dot below threshold (default 5); amber dot above. "Synced · 3 pending · syncing in 2m" |
| Syncing | N≥0 | Amber dot with pulse, "Syncing 3 changes..." |
| Sync error | N≥0 | Red dot, "Sync error · 3 pending · [Resolve]" with CTA to relevant resolution surface |
| Sync paused | N≥0 | Neutral dot, "Paused · 3 queued · [Resume]" |

**Hover/tap detail**: surfaces individual pending items as ambient awareness, capped at 5 items with "+N more" line for higher counts. Items are informational only — actions on individual items happen via the relevant resolution surface, not the indicator tooltip.

**Manual sync trigger**: inline "Sync now" link in the synced-with-pending state for owner-initiated immediate sync where applicable (calendar, QuickBooks, mobile foreground; not background sync because background sync is OS-scheduled).

**Tunable threshold** (per §16.5 system-default-with-tenant-override pattern):
- Tenant setting `tenant_sync_indicator_pending_amber_threshold` (default 5; range 1–100)
- System default `system_sync_indicator_pending_amber_threshold`
- Effective resolution: tenant → system → fallback constant 5

**Real-time updates** via SSE per §13.11. State changes (sync starts, completes, errors, count changes) push to active web sessions.

**Component design** (frontend): `<InFlightSyncIndicator surface="calendar|quickbooks|mobile|background">` is a single shared React/Gluestack component with surface-specific data hooks. Extends the L3 background indicator from the states catalog (Tier 3 #8/#9) — base `<BackgroundIndicator>` provides state-colored dot; `<InFlightSyncIndicator>` adds count display, hover detail, manual trigger, threshold awareness.

**Surface-specific count semantics**:

- **Calendar sync** (§13.5): pending changes detected in `calendar_sync_pending_change`; pending pushes from Pilot to external; resolve target on error: `/settings/integrations/calendar/conflicts`
- **QuickBooks sync** (§5.4): pending changes in `integration_sync_pending_change` (filtered for QB); resolve target: `/settings/integrations/quickbooks/conflicts`
- **Mobile-to-web data sync** (§15): count of items in mobile sync queue; resolve target: mobile sync queue surface (web for owners; on-device for tech) plus owner field-issues queue
- **Background sync** (§15.13 + §17.10 push token integration): count of items pending background sync from `mobile_sync_pending_operation` filtered for the device

**Mobile owner status row integration** (per §16.9): the existing mobile owner status row pattern incorporates the pending count when greater than zero. Format: `🟢 QuickBooks sync · 2 pending · next sync 1m` or `🔴 Calendar sync · sync error · [Resolve on web →]`.

This pattern earns its place in §16 because it generalizes across all four sync surfaces and is explicitly extensible to any future bilateral-sync integration (Salesforce, HubSpot, generic webhooks). Phase 2 surfaces inherit this pattern by default.

---

## 17. SMS Infrastructure

Tier 1.5 (Pass 4) introduced full bidirectional customer SMS communication. This chapter covers the SMS-specific infrastructure that supports Flow 4's outbound templated messaging plus the Tier 1.5 inbound and free-form reply additions. SMS is the most operationally complex external integration in MVP because it has multi-direction message flow, third-party provider integration, ongoing per-message billing, US carrier compliance requirements (A2P 10DLC), and tenant-facing subscription quota management.

### 17.1 Carrier Choice and Adapter Layer

**Carrier**: Telnyx is the MVP carrier. Selected over Twilio, Plivo, and SignalWire based on pricing (~$0.003 outbound segment vs. Twilio's $0.0079), simpler 10DLC onboarding flow, and competitive number rental (~$1/month).

**Adapter pattern**: All carrier interactions go through `services/sms_carrier.py` which defines the abstract `SmsCarrier` interface. The `TelnyxSmsCarrier` implementation handles MVP; a `MockSmsCarrier` supports integration testing without real API calls. Configuration is per-deployment via `SMS_CARRIER` environment variable; per-tenant carrier choice is Phase 2 if needed.

The interface:

```python
class SmsCarrier(ABC):
    def provision_number(self, area_code: str, tenant_id: UUID) -> ProvisionedNumber: ...
    def send_message(self, from_number: str, to_number: str, body: str) -> SendResult: ...
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool: ...
    def parse_inbound_webhook(self, payload: bytes) -> InboundMessage: ...
    def get_delivery_status(self, carrier_message_id: str) -> DeliveryStatus: ...
    def release_number(self, phone_number: str) -> None: ...
```

**Why the adapter abstraction**: telecom carriers have a long history of pricing changes, deliverability issues, acquisitions, and policy shifts. The interface is stable across providers because the underlying primitives (provision number, send, verify webhook, get status) are uniform across the industry. Cost: ~half a day of upfront work; benefit: future provider swaps are a one-class change.

### 17.2 A2P 10DLC Compliance

US carriers (T-Mobile, AT&T, Verizon) require business SMS senders to register their use case via The Campaign Registry. Without registration, messages are filtered with poor deliverability — they arrive late, or not at all.

**Registration components**:
- **Brand**: Pilot for Trades, registered with The Campaign Registry
- **Campaign**: "Customer service / appointment notifications for trades businesses" use case
- **Approval timeline**: 1–2 weeks brand approval; 1–2 weeks campaign approval; 4–6 weeks total before reliable deliverability

**Operational status**: Tom-owned pre-launch hygiene work; tracked in framework doc's pre-launch hygiene track. Failure to complete blocks reliable SMS delivery; SMS messages will still send but deliverability will be poor.

**Phase 2 considerations**: as Pilot scales to multiple tenants with different SMS volumes, additional campaigns may be required for differentiated use cases (e.g., marketing notifications separate from operational notifications). Initial campaign supports MVP scope only.

### 17.3 Number Provisioning Strategy

**Provisioning model**: One Telnyx phone number per tenant for MVP. Lazy provisioning at first SMS use rather than at tenant signup — prevents Telnyx number rental cost for tenants who never use SMS.

**Schema**: `tenant_phone_number` table tracks tenant → number assignment with carrier reference, monthly fee, and provisioning status. See A61 in backend additions ledger v5.2.

**Area code selection**: tenant's primary office area code is the default; if unavailable, system suggests three nearby alternatives. Once provisioned, the number is sticky — tenants cannot self-service swap to a different number in MVP.

**Add-on numbers**: tenants can request additional numbers via support channel in MVP at +$5/month per number (each additional number adds 100 segments to the tenant's monthly quota per §17.6). Self-service add-on UI is Phase 2.

**Provisioning failures**: rare but real (Telnyx API issues, area code completely unavailable). On failure, the original SMS attempt is queued; owner gets a notification to retry. Manual support intervention may be required for stubborn cases.

### 17.4 Inbound Message Routing

**Webhook flow**:

```
Customer SMS → Telnyx →
  POST /api/v1/webhooks/sms/telnyx-inbound (signature verified) →
  services/customer_communication_threading.py::route_inbound_message() →
  Match to thread → Notify tech + owner → Update web/mobile surfaces
```

**Threading logic**:
1. Match by sender phone → look up `customer.phone` for this tenant
2. Match by recipient phone → must equal a `tenant_phone_number` for this tenant
3. Find most recent active thread within 7-day window
4. If no recent thread: fall back to `customer.last_assigned_tech_id`
5. If still no match: park in `customer_communication_unrouted` table with owner alert

**Threading key**: `(tenant_id, customer_id, tech_id, tenant_phone_number_id)`. This allows multiple concurrent threads when multiple techs have communicated with the same customer.

**Edge case — customer texts cold (no prior outbound)**: routes to `customer.last_assigned_tech_id` if available; otherwise unrouted queue. Owner reviews unrouted messages and manually assigns to a thread.

**Edge case — customer phone number changes mid-conversation**: in-flight threads remain bound to the old number. New outbound goes to new number. Sophisticated thread merging is Phase 2.

### 17.5 Threading Schema

Two tables form the threading model:

```sql
customer_communication_thread (
    thread_id              UUID PRIMARY KEY,
    tenant_id              UUID NOT NULL,
    customer_id            UUID NOT NULL,
    tech_id                UUID NOT NULL,
    tenant_phone_number_id UUID NOT NULL REFERENCES tenant_phone_number,
    status                 TEXT NOT NULL,  -- 'active' | 'archived'
    first_message_at       TIMESTAMPTZ NOT NULL,
    last_message_at        TIMESTAMPTZ NOT NULL,
    message_count          INT NOT NULL DEFAULT 0,
    created_at             TIMESTAMPTZ NOT NULL,
    updated_at             TIMESTAMPTZ NOT NULL
)

customer_communication_message (
    message_id             UUID PRIMARY KEY,
    thread_id              UUID NOT NULL REFERENCES customer_communication_thread,
    direction              TEXT NOT NULL,  -- 'outbound' | 'inbound'
    channel                TEXT NOT NULL,  -- 'sms' (MMS Phase 2)
    body                   TEXT NOT NULL,
    segment_count          INT NOT NULL,
    status                 TEXT NOT NULL,  -- 'pending_send'|'sent'|'delivered'|'failed'|'received'
    carrier_message_id     TEXT,
    sent_at, delivered_at, received_at TIMESTAMPTZ,
    composition_method     TEXT,           -- 'template'|'free_form_text'|'free_form_voice'
    template_id            UUID NULL REFERENCES communication_template,
    voice_audio_id         UUID NULL REFERENCES voice_command_log,
    audit_user_id          UUID NOT NULL
)
```

**Coexistence with existing `customer_communication` table** (from A4): the threading model wraps the existing flat message table. Existing outbound rows backfill into threads at the v5.2 deployment. The `customer_communication` table itself is preserved for backward compatibility but new code reads/writes through the threading model.

### 17.6 Subscription Quota and Cap Enforcement

**Quota model**:
- Base: 100 SMS segments per month per tenant, included in $149 subscription
- Add-on numbers: each adds 100 segments to the quota
- Inbound messages: not counted against quota (Telnyx inbound cost ~$0.002, rolled into base)
- MMS: not in MVP

**Cap policy** (`tenant_setting.sms_quota_cap_policy`):
- `soft` (default): tenant gets billed for overages at $0.05/segment; sends continue normally
- `hard`: at 100% used, all outbound SMS is blocked until next billing cycle

**Period model**: `sms_quota_period` table; one row per tenant per billing cycle. Period boundaries align with subscription billing (not calendar month). Created by Celery task `rollover_sms_quota_periods`.

**In-month visibility**:
- Mobile composition zone shows segment count + remaining quota for the current message
- Web dashboard widget "SMS usage this month" shows current, projected month-end, policy
- Mobile owner status row appears when usage >70% (otherwise hidden)
- Notifications fire at 80% (push + email to owner) and 100% (push + email)

**Atomicity**: `consume_quota` increments atomically; rolls back on send failure (failed sends don't cost the tenant).

**Billing integration**: month-end overage billing is handled by existing subscription billing infrastructure; `overage_segments × $0.05` added as a line item.

### 17.7 Voice Intent Integration

A new voice intent `reply_to_customer_sms` extends the voice intent registry (§6.2) for free-form SMS reply composition.

**Trigger pattern**: "Reply to [customer name] saying [message body]"

**Identifier resolution**: most recent active thread for the requesting tech by default; explicit by name/job context if specified

**Flow**:
1. Voice captures audio via existing Whisper infrastructure
2. Transcribed body extracted; customer identifier resolved
3. Confirm-as-turn safeguard (§6.6): preview rendered; AI reads back including segment count and remaining quota
4. On confirmation, dispatches via `POST /api/v1/communications/threads/{thread_id}/reply`

**Always-preview-before-send** (§16.7) applies — voice cannot bypass preview.

**Voice composition can be initiated from any screen** per Flow 4's "Voice override anywhere" pattern, but resolves to the customer's most recent active thread for the requesting tech.

### 17.8 Notification Integration

Inbound SMS messages dispatch push notifications to:
- **The originating tech**: forced-minimum push (per Tier 2 #5 notification preferences) — cannot be muted by user override
- **The owner**: per Tier 2 #5 default policy for "Customer activity" category (push ON by default for owners; can be muted)

Push payload includes `thread_id` for deep-link routing — tapping the push opens the conversation thread screen on mobile.

**Web in-app banner** (if Tier 2 #5 ships with the in-app channel): inbound messages also fire an in-app banner for active web sessions; owner sees ambient awareness without leaving current page.

### 17.9 Audit and Compliance

Every SMS event is captured in `audit_log` per the existing audit infrastructure:

- Outbound message sent (template if applicable, body length, segment count, send_user_id, delivery status)
- Inbound message received (sender phone, threaded to which tech, body length)
- Free-form reply composed (composition_method: free_form_text vs free_form_voice; voice_audio_id if applicable)
- Number provisioned (tenant_id, area_code, provisioned_phone_number)
- Quota threshold notifications (80%, 100% triggers)
- Hard cap blocked send attempt (which tech, which customer, attempted body)

Owners can filter audit log by `category: 'sms_communication'` for compliance review, cost attribution, or dispute resolution.

### 17.10 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── webhooks_sms.py            # POST /api/v1/webhooks/sms/telnyx-inbound
│   │   ├── communications_threads.py  # thread CRUD, reply endpoints
│   │   ├── sms_quota.py               # GET /api/v1/sms/quota
│   │   └── tenant_phone_numbers.py    # provisioning endpoints
│   └── voice/
│       └── intents.py                 # reply_to_customer_sms intent handler added
├── services/
│   ├── sms_carrier.py                 # Adapter interface + TelnyxSmsCarrier + MockSmsCarrier
│   ├── customer_communication_threading.py  # routing logic
│   ├── sms_provisioning.py            # number provisioning at first use
│   └── sms_quota.py                   # quota check, consume, rollover
└── tasks/
    ├── rollover_sms_quota_periods.py  # daily Celery task
    └── monitor_sms_quota_thresholds.py  # hourly Celery task for 80/100% notifications
```

### 17.11 Cost Implications

Per-tenant SMS costs vary by usage. For an active tenant at 200 segments/month (well above included 100):

| Cost component | Monthly per-tenant |
| :--- | :--- |
| Number rental (Telnyx) | ~$1.00 |
| Outbound segments (100 × $0.003) | $0.30 |
| Inbound segments (100 × $0.002) | $0.20 |
| **Total Telnyx cost at 200 segments** | **~$1.50** |
| Tenant overage billing (100 × $0.05) | +$5.00 to tenant (Pilot revenue, not cost) |

At Pilot scale (100 tenants average, mixed usage), aggregate Telnyx cost ~$150–250/month. See Cost Analysis chapter for the full update.

### 17.12 Phase 2 Roadmap

Out of MVP scope per Tier 1.5 Decision 15:

- MMS / image attachments
- AI classification of customer intent ("customer wants to reschedule")
- Automated rescheduling suggestions
- Customer self-service reschedule links
- Multi-channel threading (SMS + email continuity)
- Per-tech Telnyx numbers
- AI-suggested replies for techs
- Self-service number purchasing UI
- Voice calls inbound/outbound through Telnyx
- WhatsApp / iMessage business integration
- Per-tenant carrier choice
- Scheduled message sending

---

## 18. Customer-Facing Public Surfaces Architecture

Pass 4 Tier 4 #13 introduced the customer-facing public surfaces — pages that customers (non-Pilot users) access via signed-URL links sent in emails or SMS. This chapter covers the architecture supporting these surfaces: signed URL infrastructure, Stripe one-time payment for invoices with amount variance, email template rendering with tenant brand customization, customer comment storage on entities, and the short-link redirect infrastructure.

### 18.1 Strategic Direction

Customer-facing surfaces are the only Pilot surfaces a non-tenant user sees. Three architectural principles drive the design:

- **Tenant-branded, not Pilot-branded**: pages render with the tenant's logo, brand color, signature, and footer. Pilot brand presence is limited to a small "Powered by Pilot for Trades" footer link. The customer's mental model is "I'm interacting with [tenant]," not "I'm using Pilot."
- **Signed URL is the only authentication**: the customer's email inbox is the implicit verification mechanism — clicking the link from email implies access to that email account. No additional 6-digit-code dance. URLs expire 90 days from generation.
- **Comments are entity-bound, not communication-channel-bound**: customer comments on accept/decline/payment are stored on the entity (quote, payment) — not routed into customer comm threads. This matches the semantics: comments ARE the action context, not separate messages.

### 18.2 Signed URL Infrastructure

Public URLs use HMAC-signed tokens with embedded payload validation:

- **URL format**: `https://app.pilotfortrades.com/q/{signed_token}` (quote) or `/i/{signed_token}` (invoice)
- **Token payload**: `link_id` (UUID), `link_type` (quote | invoice), `expiration` (ISO timestamp), `customer_id` (for verification)
- **Signature**: HMAC-SHA256 with per-deployment secret stored in Secrets Manager (per §9.1)
- **Expiration**: 90 days from generation
- **Revocation**: tenant can manually revoke any link via `POST /api/v1/quotes/{id}/public-link/revoke` — invalidates the token immediately; subsequent access shows expired page

**Schema** (extends existing `quote_public_link` and `invoice_public_link`):

```sql
ALTER TABLE quote_public_link ADD COLUMN signed_token TEXT NOT NULL;
ALTER TABLE quote_public_link ADD COLUMN expires_at TIMESTAMPTZ NOT NULL;
ALTER TABLE quote_public_link ADD COLUMN revoked_at TIMESTAMPTZ NULL;
ALTER TABLE quote_public_link ADD COLUMN created_by_user_id UUID NOT NULL;

-- (parallel ALTERs for invoice_public_link)
```

**Verification at request time**:

1. Decode signed token; validate HMAC signature against deployment secret
2. Check `expiration < now()` → return expired page if true
3. Check `revoked_at IS NULL` → return expired page if revoked
4. Look up entity (quote or invoice) by `link_id`; verify `customer_id` matches the entity's customer
5. Render page with current entity state (state-aware revisit handling per §18.6)

**No tenant authentication** on these requests — the signed URL is the credential. Each request hits a public route handler that does not require Cognito JWT.

### 18.3 Short-Link Redirect Infrastructure

When a tenant sends a quote or invoice via SMS (per §17), the SMS body includes a shortened URL to reduce segment count:

- **Domain**: `pilot.tr` (or similar; Pilot-owned)
- **Short code format**: 5–8 character base62 random; collision-checked at generation
- **Resolution**: `GET /api/v1/short/{short_code}` resolves to full signed URL and 302-redirects

**Schema**:

```sql
public_link_short_code (
    short_code           TEXT PRIMARY KEY,    -- base62 random
    link_type            TEXT NOT NULL,        -- 'quote' | 'invoice'
    link_id              UUID NOT NULL,        -- references quote_public_link or invoice_public_link
    created_at           TIMESTAMPTZ NOT NULL,
    click_count          INTEGER NOT NULL DEFAULT 0,
    last_clicked_at      TIMESTAMPTZ NULL
)
```

**Click tracking** captures user-agent, IP, timestamp on each redirect (denormalized counter on the row plus optional `public_link_click_log` for full audit). Phase 2 analytics surface this data; for MVP it's captured but not surfaced.

**MVP fallback**: if the `pilot.tr` domain isn't ready at MVP launch, full URLs in SMS are acceptable (just longer). Short-link infrastructure is forward-compatible — switching SMS templates to use short links is a content change, not an architectural change.

### 18.4 Public Page Routing

Public pages live at separate routes that bypass standard Cognito authentication middleware:

| Route | Purpose |
| :--- | :--- |
| `GET /api/v1/public/quotes/{signed_token}` | Returns quote payload for rendering |
| `POST /api/v1/public/quotes/{signed_token}/accept` | Customer accepts with optional comment |
| `POST /api/v1/public/quotes/{signed_token}/decline` | Customer declines with reason + comment |
| `GET /api/v1/public/invoices/{signed_token}` | Returns invoice payload for rendering |
| `POST /api/v1/public/invoices/{signed_token}/payment-intent` | Initiates Stripe Payment Intent (per §18.5) |
| `POST /api/v1/public/invoices/{signed_token}/confirm-payment` | Frontend confirms Stripe Elements payment |

**Middleware stack for public routes**:

- Standard rate limiting (per §7.5) — applied per-IP since no tenant context yet
- Idempotency keys (per §7.6) for write operations
- Request ID tracing (per §7.7)
- **Skipped**: Cognito JWT validation, RBAC permission decorators

The `require_permission()` FastAPI dependency is NOT applied to these routes. Authorization is purely the signed URL.

### 18.5 Stripe One-Time Payment for Invoices with Amount Variance

Customers pay invoices via the public link using Stripe Elements (PCI-compliant; raw card never touches Pilot servers). Same Stripe account and customer record as subscription billing (§20). Different API surface — Payment Intents instead of Subscriptions.

**Payment flow**:

1. Customer clicks "Pay this invoice" on public invoice page
2. Frontend calls `POST /api/v1/public/invoices/{token}/payment-intent` with the customer-entered amount
3. Backend creates Stripe Payment Intent via Stripe API; returns client_secret
4. Frontend uses Stripe Elements with client_secret to collect card details and submit payment
5. Stripe processes payment; webhook fires
6. Backend records payment with actual amount paid + variance + comment
7. Frontend redirects to confirmation page

**Amount variance handling**:

- Customer can adjust the payment amount (up or down) from the invoice total
- When amount differs from invoice total, frontend requires a comment field (2000 char max) explaining the variance
- Backend validates: comment is required if `customer_amount != invoice_total`; payment is not processed without comment
- Variance is recorded on the payment record:

```sql
ALTER TABLE payment ADD COLUMN stripe_payment_intent_id TEXT;
ALTER TABLE payment ADD COLUMN customer_payment_comment TEXT NULL;
ALTER TABLE payment ADD COLUMN amount_variance_cents INTEGER NULL;
ALTER TABLE payment ADD COLUMN paid_via TEXT;  -- 'stripe' | 'check' | 'bank_transfer' | 'other'
```

**Underpayment**: invoice balance updates to `invoice_total - amount_paid`; remaining balance recorded as receivable. QuickBooks sync (§5) handles partial payments natively.

**Overpayment**: variance recorded with positive value; tenant reviews via UI and decides handling (refund via Stripe, credit forward, accept). UI shows "Customer paid $X over invoice total — review."

**Stripe webhook handler** (extends the webhook endpoint introduced in §20 for Subscriptions):

- `payment_intent.succeeded` → record payment, update invoice balance, trigger Customer Activity notification
- `payment_intent.payment_failed` → surface failure to customer-facing UI; payment retries handled by Stripe; tenant notified after final failure
- Webhook signature verified using Stripe webhook signing secret stored in Secrets Manager

**Stripe Connect consideration** (Phase 2 review point): for MVP, Pilot uses a single Stripe account; customer payments accumulate in Pilot's account (superseded by ADR-0019: Stripe Connect Express with direct charges, so Pilot never holds tenant customer funds); disbursement to tenants is a separate financial process (TBD). Stripe Connect would route payments directly to tenant Stripe accounts — cleaner architecture but more complex setup. Worth reviewing before MVP launch given financial implications.

### 18.6 State-Aware Revisit Handling

Customers revisiting a public link after taking action see the resulting state, not the original action buttons. Routing logic at the public page handler:

| Entity state | Renders |
| :--- | :--- |
| Quote `sent` (not yet acted) | Accept/Decline buttons visible |
| Quote `accepted` | Confirmation page with date + customer comment |
| Quote `declined` | Decline confirmation with reason + comment |
| Quote `expired` | Expired page; suggest contacting tenant for fresh link |
| Invoice unpaid | Pay button + alternative payment methods |
| Invoice partially paid | Payment history + remaining balance + "Pay remaining" / "Pay different amount" |
| Invoice fully paid | Paid confirmation with payment history |

This prevents accidental double-actions. The signed URL is the same; the page renders state-aware.

### 18.7 Customer Comment Storage (Entity-Bound)

Comments are stored on the entity, not in communication threads. Implementation per A83:

**Quote acceptance**:

```sql
ALTER TABLE quote ADD COLUMN customer_acceptance_comment TEXT NULL;
ALTER TABLE quote ADD COLUMN customer_accepted_at TIMESTAMPTZ NULL;
ALTER TABLE quote ADD COLUMN customer_email_at_action TEXT NULL;
```

**Quote decline**:

```sql
ALTER TABLE quote ADD COLUMN customer_decline_comment TEXT NULL;
ALTER TABLE quote ADD COLUMN customer_decline_reason TEXT NULL;
  -- enum: 'pricing' | 'scope' | 'timing' | 'other_contractor' | 'other'
ALTER TABLE quote ADD COLUMN customer_declined_at TIMESTAMPTZ NULL;
```

**Invoice payment**:

```sql
-- Already added in §18.5: customer_payment_comment, amount_variance_cents
```

**UI integration**: quote detail page surfaces the customer's comment prominently when present:

```
┌────────────────────────────────────────────┐
│ Quote QU-1024 — ACCEPTED                   │
│                                            │
│ Accepted by Sarah Johnson                  │
│ on April 27, 2026 at 2:14 PM               │
│                                            │
│ Customer comment:                          │
│ "Let's get started ASAP — when can you     │
│ begin?"                                    │
└────────────────────────────────────────────┘
```

**Notifications**: comment events trigger Customer Activity notifications per Tier 2 #5 (covered in §22 Notification Preference Center, Round 2B). Notification body includes the comment text.

**One-way for MVP**: tenant cannot reply to a customer comment from this entity-bound surface. If tenant wants to respond, they use existing Customer Comms (§17 SMS or §3.7 email). Phase 2 may add reply infrastructure if user demand justifies.

### 18.8 Email Template Rendering Pipeline

Per A82, MVP ships with 16 transactional email templates rendered through a unified pipeline that applies tenant branding to customer-facing templates while using Pilot standard branding for internal templates.

**Schema**:

```sql
email_template (
    template_id          TEXT PRIMARY KEY,    -- 'quote_sent', 'invoice_sent', 'welcome', etc.
    display_name         TEXT NOT NULL,
    category             TEXT NOT NULL,        -- 'customer_facing' | 'internal'
    subject_template     TEXT NOT NULL,        -- with variable substitution
    body_html_template   TEXT NOT NULL,
    body_plain_template  TEXT NOT NULL,        -- text fallback
    variables            JSONB NOT NULL,       -- supported variables
    is_active            BOOLEAN NOT NULL DEFAULT TRUE
)

tenant_email_branding (
    tenant_id            UUID PRIMARY KEY,
    logo_s3_path         TEXT NULL,
    brand_color_hex      TEXT NULL,            -- defaults to Pilot brand-indigo
    email_signature      TEXT NULL,            -- 500 char max
    custom_footer        TEXT NULL,            -- 200 char max
    updated_at           TIMESTAMPTZ NOT NULL
)
```

**Rendering pipeline** (`services/email_template_renderer.py`):

1. Take `template_id` + context payload (customer name, quote total, signed URL, etc.)
2. Resolve variables from context
3. For `customer_facing` category: apply tenant branding (logo, color, signature, footer) from `tenant_email_branding`
4. For `internal` category: use Pilot standard branding
5. Render HTML body and plain text body
6. Return ready-to-send payload for SendGrid

**16 MVP templates**:

| ID | Audience | Trigger |
| :--- | :--- | :--- |
| `welcome` | Tenant owner | Tenant signup completion |
| `email_verification` | Any user | Email verification request |
| `quote_sent` | Customer | Tenant sends quote |
| `quote_accepted` | Tenant | Customer accepts quote |
| `quote_declined` | Tenant | Customer declines quote |
| `quote_expiring` | Customer | 3 days before quote expiration |
| `invoice_sent` | Customer | Tenant sends invoice |
| `payment_received_tenant` | Tenant | Stripe payment success |
| `payment_received_customer` | Customer | Stripe payment success (receipt) |
| `payment_failed` | Customer | Stripe payment failure |
| `subscription_renewal` | Tenant | Stripe subscription renewal |
| `subscription_payment_failed` | Tenant | Stripe subscription payment failure |
| `trial_expiring` | Tenant | Per Tier 3 #10 trial expiration warnings |
| `trial_expired` | Tenant | Per Tier 3 #10 trial expiration |
| `password_reset` | Any user | Password reset request |
| `mfa_reset_by_owner` | Affected user | Per §4.5 owner reset of user MFA |
| `data_export_ready` | Requesting user | Per §4.5 / Tier 2 #7 data export completion |

**Tenant branding settings UI**: lives at `Settings > Communications > Email branding`. Owner-only edit. Provides:

- Logo upload via S3 presigned URL pattern (consistent with §15.5 photo upload)
- Brand color picker (validates contrast against white background)
- Signature multi-line text input
- Custom footer text input
- Live preview using sample template
- "Send test email to my address" affordance for verification

**Customer-facing branding policy**: customer-facing templates render with tenant branding to feel like the tenant's communication. Internal templates (welcome, password reset, MFA reset, etc.) use Pilot standard branding because the tenant is the recipient — they don't need their own brand back at them.

### 18.9 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── public_quotes.py          # /api/v1/public/quotes/* — signed-URL routes
│   │   ├── public_invoices.py        # /api/v1/public/invoices/* — signed-URL routes
│   │   ├── public_short_redirect.py  # /api/v1/short/{short_code} — short-link redirect
│   │   ├── webhooks_stripe.py        # Stripe webhook handler (extends from §20)
│   │   └── tenant_email_branding.py  # tenant branding CRUD
│   └── ...
├── services/
│   ├── public_link_signer.py         # HMAC token sign/verify
│   ├── short_link_resolver.py        # short code generation + resolution
│   ├── email_template_renderer.py    # template + branding rendering
│   ├── stripe_payment.py             # one-time payment integration
│   └── ...
└── tasks/
    └── stripe_cleanup.py              # cleanup_incomplete_stripe_payment_intents (per §3.2)
```

### 18.10 Audit Logging

Every customer-side action is captured in audit log per §16.5 audit log convention. Captured events:

- Quote viewed via public link (with customer email at access time)
- Quote accepted (timestamp, comment, customer email)
- Quote declined (timestamp, reason, comment, customer email)
- Invoice viewed via public link
- Invoice payment attempted (success or failure; amount; variance)
- Public link revoked (actor, link, reason)

Customer email captured at action time provides the audit trail for "who acted on this quote." No Pilot user account exists for customers, but the audit log captures what email was used to act on the entity.

### 18.11 Phase 2 Considerations

Out of MVP scope per Tier 4 #13:

- Customer registration with full account access (explicitly removed)
- Comment replies from tenant back to customer (use Customer Comms for now)
- Full template editing by tenants (structured customization only in MVP)
- PDF or print-friendly view of public quote/invoice
- Multi-language customer-facing pages
- Custom domain for tenant short links (MVP uses pilot.tr or similar Pilot-owned domain)
- Stripe Connect for direct-to-tenant payment routing (architectural review point)
- Customer-facing analytics ("opened quote 3 times before accepting")
- Bulk quote/invoice send to customer list
- Quote / invoice expiration custom intervals (currently fixed at 90 days)

---

## 19. Help System Architecture

Pass 4 Tier 4 #14 introduced AI-mediated help with RAG retrieval over a markdown corpus. This chapter covers the architecture: corpus storage and structure, embedding pipeline, help AI agent, RAG retrieval, chat session management, anonymization pipeline, and voice integration.

### 19.1 Strategic Direction

Help should feel like a continuation of how Pilot users already interact with the product, not a separate paradigm. Pilot is voice-first AI-first; help is too. Three architectural principles:

- **Markdown in S3 is both the corpus AND the human articles**: same files serve AI retrieval (chunked + embedded) and direct article reading (rendered when surfaced as "Read full article")
- **Same Llama 3.x infrastructure as voice intents**: separate prompt + RAG context, not a separate model. Compute capacity shared; routing happens at the prompt layer
- **Capture for training data with anonymization at the pipeline stage**: sessions retained 90 days unscrubbed for debugging + history; then anonymized and rolled into training corpus

### 19.2 Markdown Corpus Storage and Structure

Help articles are markdown files in S3 with structured frontmatter. The structure works for both human reading and AI retrieval.

**S3 structure**:

- Bucket: `pilot-help-content` (with versioning enabled)
- Path: `s3://pilot-help-content/{language}/{category}/{article_id}.md`
- Public read: disabled — articles served via authenticated API
- IAM policy: Lambda + Celery worker can read; Tom can write via console or programmatic upload

**Frontmatter schema**:

```yaml
---
article_id: setup-quickbooks-integration
title: Connect QuickBooks Online to Pilot
category: integrations
related_concepts: [sync, oauth, accounting, mapping]
ui_surfaces: [/settings/integrations/quickbooks, /onboarding/checklist#quickbooks]
related_articles: [resolve-qb-sync-conflicts, qb-sync-troubleshooting]
last_updated: 2026-04-27
audience: [owner, accountant]
---

# Article content in markdown follows
```

**Frontmatter field semantics**:

| Field | Purpose |
| :--- | :--- |
| `article_id` | Unique slug for cross-references and stable URLs |
| `title` | Human-readable title |
| `category` | Top-level grouping (integrations, voice-ai, settings, billing, onboarding, etc.) |
| `related_concepts` | Tags for cross-article retrieval |
| `ui_surfaces` | App routes / anchors where article is contextually relevant (drives context-aware help opener — see §19.5) |
| `related_articles` | Explicit cross-references for "see also" suggestions |
| `last_updated` | ISO date of last content update |
| `audience` | Roles this article is relevant for (used for retrieval filtering) |

**Initial corpus scope** (MVP target ~60 articles, Tom-owned content authoring):

| Category | Approximate article count |
| :--- | :--- |
| Getting started / onboarding | 8 |
| Voice AI / voice intents | 6 |
| Quote workflow | 8 |
| Job management / dispatch | 8 |
| Customer management | 6 |
| Customer messaging (SMS, email) | 5 |
| Invoicing & billing | 6 |
| QuickBooks integration | 4 |
| Calendar integration | 3 |
| Settings & configuration | 4 |
| Mobile-specific (offline, sync) | 4 |
| Account & security (MFA, password) | 4 |

### 19.3 Embedding Pipeline

Articles are chunked at section boundaries (each `##` heading starts a new chunk) and embedded into pgvector for semantic retrieval.

**Schema**:

```sql
help_article (
    article_id              TEXT PRIMARY KEY,
    s3_path                 TEXT NOT NULL,
    title                   TEXT NOT NULL,
    category                TEXT NOT NULL,
    frontmatter_metadata    JSONB NOT NULL,
    last_content_hash       TEXT NOT NULL,           -- sha256 of content for change detection
    last_processed_at       TIMESTAMPTZ NOT NULL,
    last_updated            DATE NOT NULL,
    audience                TEXT[] NOT NULL          -- array of role names
)

help_article_chunk (
    chunk_id                    UUID PRIMARY KEY,
    article_id                  TEXT NOT NULL REFERENCES help_article(article_id),
    chunk_order                 INTEGER NOT NULL,    -- preserve original order
    section_title               TEXT NOT NULL,       -- the ## heading
    chunk_text                  TEXT NOT NULL,
    chunk_text_with_metadata    TEXT NOT NULL,       -- frontmatter + section + content; what gets embedded
    embedding                   vector(1536) NOT NULL,
    token_count                 INTEGER NOT NULL
)

CREATE INDEX help_article_chunk_embedding_hnsw_idx ON help_article_chunk
    USING hnsw (embedding vector_cosine_ops);
```

**Chunking rules**:

- Minimum chunk size: 100 tokens (very short sections merged with adjacent)
- Maximum chunk size: 800 tokens (long sections split at sub-section or paragraph boundaries)
- Each chunk includes article frontmatter as a context header (so retrieved chunks carry their metadata)

**Embedding model**: OpenAI `text-embedding-3-small` for MVP (1536 dimensions, low cost — ~$0.00002 per 1K tokens). Estimated cost at MVP scale: $0.60 one-time for full corpus + $0.10/month for query embeddings at moderate usage. Open-source alternative (Sentence-BERT family) is feasible if avoiding OpenAI dependency is preferred.

**Pipeline trigger**:

- S3 event notification on article upload/update (via S3 event → SQS → Celery)
- Manual trigger via admin endpoint
- Weekly scheduled re-embedding pass (catches missed events)

**Pipeline steps** (`tasks/help_corpus.py::process_help_article`):

1. Fetch markdown from S3
2. Parse frontmatter
3. Chunk by section boundaries
4. Compute content hash; skip if unchanged from `last_content_hash`
5. Embed each chunk via OpenAI API
6. Store/update chunks in `help_article_chunk` (delete old chunks for changed articles, insert new)
7. Update `help_article` with new hash and `last_processed_at`

**Update latency**: total time from edit-and-upload to AI-aware is typically 1–2 minutes (S3 event → Celery worker → OpenAI embedding API → pgvector write).

### 19.4 Help AI Agent

The help agent uses the same Llama 3.x infrastructure as voice intents (per §6) with a distinct prompt template and RAG context injection.

**Prompt template** (`prompts/help/help_agent.md`):

```
You are Pilot's help assistant — a friendly, concise guide for users navigating
Pilot for Trades, an AI-first SaaS platform for small electrical contractors.

[System constraints — see §19.7 knowledge boundaries]

[RAG retrieved chunks injected here as Pilot product knowledge]

[User's surface context payload injected here, if available]

[Conversation history]

User question: {user_message}

Respond in {voice_persona_tone} tone. Keep responses concise; offer follow-up
actions where appropriate (Read full article, Walk me through it).
```

Three tone variants per voice persona (per §16.5 / Tier 2 #6): `help_agent_conservative.md`, `help_agent_balanced.md`, `help_agent_playful.md`.

**Routing**: voice intent registry routes `open_help` and `ask_help_question` intents to the help endpoint (`POST /api/v1/help/chat`). Same Ollama model serves both voice intents and help queries; routing happens at the prompt layer.

**Streaming response support**: HTTP chunked transfer encoding for token-by-token rendering on client. For MVP, full response can be returned non-streamed if streaming infrastructure isn't ready.

### 19.5 RAG Retrieval

When a user query arrives:

1. **Embed user query** via OpenAI embedding API
2. **Filter chunks by audience role** (technician queries don't pull owner-only chunks)
3. **Optional category filter** if context payload suggests a category
4. **pgvector cosine similarity search** returns top-K (default K=5) most-relevant chunks
5. **Inject chunks into prompt** as Pilot product knowledge context

**Retrieval API** (internal to A84):

```
POST /api/v1/help/retrieve
Request:  { query_embedding: vector, role: text, category_hint: text?, k: int }
Response: { chunks: [{ article_id, section_title, chunk_text, score }, ...] }
```

**Context-aware help opener**: when user opens help from a settings page or flow surface, frontend sends a context payload to the AI for grounded responses:

```json
{
    "route": "/settings/integrations/quickbooks",
    "entity_type": null,
    "recent_actions": ["viewed_qb_conflict", "opened_settings", "changed_setting"],
    "user_role": "owner",
    "tenant_metadata": { "size": "small", "trade": "electrical" }
}
```

**Privacy boundary on context**: action *types* only, never entity contents. No quote numbers, customer names, amounts, etc. The action-type vocabulary is a small enumerated list captured client-side ephemerally — not stored server-side.

This context lets the AI ground its initial message: "I see you're on the QuickBooks integration page. What can I help you with?" — much better than cold context.

### 19.6 Chat Session Management

Help conversations are organized into sessions persisted server-side.

**Schema**:

```sql
help_chat_session (
    session_id              UUID PRIMARY KEY,
    tenant_id               UUID NOT NULL,
    user_id                 UUID NOT NULL,
    started_at              TIMESTAMPTZ NOT NULL,
    last_activity_at        TIMESTAMPTZ NOT NULL,
    title                   TEXT NULL,                -- auto-generated via A11 pattern
    outcome                 TEXT NULL,                -- 'resolved' | 'escalated' | 'abandoned'
    message_count           INTEGER NOT NULL DEFAULT 0,
    anonymized_at           TIMESTAMPTZ NULL          -- set when anonymization pipeline runs
)

help_chat_message (
    message_id              UUID PRIMARY KEY,
    session_id              UUID NOT NULL REFERENCES help_chat_session,
    role                    TEXT NOT NULL,             -- 'user' | 'assistant'
    content                 TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL,
    context_payload         JSONB,                     -- user messages: surface context
    retrieved_chunks        JSONB,                     -- assistant messages: which chunks fed RAG
    voice_used              BOOLEAN NOT NULL DEFAULT FALSE
)
```

**Session continuity**:

- **Within-session**: opening help, asking question, navigating elsewhere, opening help again — same conversation continues
- **Cross-session**: full close (✕) or sign-out → next help session opens clean
- **Multi-device**: sessions are per-device in MVP; not synced across user's devices

**Session title generation**: reuses A11 (Ollama-generated session titles) with help-specific prompt. Titles render in the "Past conversations" surface for user recall.

### 19.7 AI Knowledge Boundaries and Escalation

The help AI is scoped via system prompt to "how to use Pilot" knowledge plus surface context. Explicit boundaries:

- Does NOT take actions on behalf of the user
- Does NOT access tenant-specific data (no "show me my last quote" — that's voice intent system)
- Does NOT provide financial / legal / compliance advice
- Does NOT make product roadmap commitments
- Does NOT operate outside Pilot domain

**Three escalation triggers** route stuck users to feedback submission:

1. User explicitly asks for human help ("I want to talk to a real person")
2. AI low-confidence after 3 turns (the AI has tried twice; user is still stuck)
3. Question outside Pilot scope (legal, financial, technical issues with user's specific data)

In all cases, AI surfaces feedback submission flow with category pre-set to "Question" and conversation context pre-filled.

### 19.8 Voice Integration

Help is voice-accessible. Voice intent grammar from §6.2:

| Intent | Behavior |
| :--- | :--- |
| `open_help` | Opens help chat panel (web) or full-screen (mobile); AI prompts "What can I help you with?" |
| `ask_help_question` | Routes the user's utterance directly as the first help query |

**Voice readback of AI responses**: uses the user's effective voice persona tone (per §16.5 / Tier 2 #6). Per §6.6 confirm-as-turn, no destructive actions in help — pure information retrieval — so no confirm-before-commit needed. Always-preview-before-send (§16.7) doesn't apply for the same reason.

**Voice-only mode**: user invokes help via voice; AI responds via TTS automatically; ongoing conversation can stay voice-only until user types or taps to switch to text.

### 19.9 Anonymization Pipeline (Training Data Capture)

Per Tier 4 #14 Decision 13, help chat sessions are captured for training data with anonymization at the 90-day boundary.

**Three-tier retention model**:

| Tier | Duration | Purpose |
| :--- | :--- | :--- |
| Active session | Until user closes chat | Real-time conversation state |
| Recent (unscrubbed) | 90 days | Debugging, user history recall, training pipeline source |
| Training corpus (anonymized) | Permanent | Model fine-tuning and content improvement |

**Anonymization pipeline** (`tasks/help_corpus.py::anonymize_help_sessions`, daily):

1. Identify sessions where `last_activity_at <= now() - 90 days` AND `anonymized_at IS NULL`
2. For each session:
   - Iterate messages
   - Run PII detection (regex + NER)
   - Replace PII with placeholders: `[email]`, `[phone]`, `[person]`, `[business]`, `[address]`, `[id]`
   - Strip tenant_id and user_id references
   - Save anonymized version to `help_training_corpus` (separate table)
   - Set `anonymized_at` on original session
   - After all messages processed, delete original `help_chat_session` and `help_chat_message` rows

**`help_training_corpus` schema**:

```sql
help_training_corpus (
    corpus_id                       UUID PRIMARY KEY,
    original_session_id_hash        TEXT NOT NULL,    -- one-way hash; tracking but not reversal
    anonymized_message_history      JSONB NOT NULL,
    anonymized_context_payload      JSONB,
    category_inferred               TEXT NULL,        -- AI-classified for filtering training data
    outcome                         TEXT NOT NULL,
    anonymized_at                   TIMESTAMPTZ NOT NULL
)
```

**PII detection rules** (initial set, refined during testing):

- Email addresses (regex `[\w._%+-]+@[\w.-]+\.[a-zA-Z]{2,}`) → `[email]`
- Phone numbers (US format detection) → `[phone]`
- Names (NER model or simple capitalized-word heuristic) → `[person]`
- Business names (capitalized phrases ending in business suffixes) → `[business]`
- Addresses (street number + word + street suffix) → `[address]`
- Long alphanumeric IDs (UUIDs, account numbers) → `[id]`

**User-facing transparency**: small note in help chat panel: "Pilot uses help conversations to improve our help content. Personal information is removed before use. [Learn more]" — link opens a help article explaining the pipeline.

**User deletion request** (Phase 2 surface; backend stub for MVP): `POST /api/v1/help/sessions/delete-all` deletes all help chat sessions for the requesting user. Stub endpoint exists; full UX is Phase 2.

### 19.10 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── help_chat.py              # /api/v1/help/chat — main chat endpoint
│   │   ├── help_sessions.py          # session list / detail / mark-read
│   │   ├── help_articles.py          # GET /api/v1/help/articles/{id} — article delivery
│   │   └── feedback.py               # /api/v1/feedback — submission endpoint
│   └── voice/
│       └── intents.py                # open_help, ask_help_question intent handlers added
├── services/
│   ├── help_agent.py                 # prompt rendering + Ollama calling for help AI
│   ├── help_retrieval.py             # RAG retrieval via pgvector
│   ├── help_corpus.py                # corpus management
│   └── pii_anonymizer.py             # PII detection + replacement utilities
├── tasks/
│   └── help_corpus.py                # process_help_article (event-driven) + anonymize_help_sessions (daily)
└── prompts/
    └── help/
        ├── help_agent_conservative.md
        ├── help_agent_balanced.md
        └── help_agent_playful.md
```

### 19.11 Selective Contextual Help Anchors

Per Tier 4 #14 Decision 1, "?" icons are placed selectively on complex surfaces rather than universally. Anchor placement list:

| Surface | Help anchors |
| :--- | :--- |
| `Settings > Integrations > QuickBooks` | next to "Auto-expire" toggle, "Sync direction" picker |
| `Settings > Integrations > Calendar` | next to "Auto-expire" toggle |
| `Settings > Notifications > Preferences` | inline annotation explainer + "Why is this locked?" |
| `Settings > Sync & Storage > Background sync` | next to "Push interval" setting |
| `Settings > Voice AI > Persona tone` | next to the tone cards |
| `Settings > Subscription & Billing > SMS quota` | next to "Cap policy" setting |
| `Settings > Operations > Margin buckets` | next to bucket boundary editor |
| `Settings > Tax configuration` | next to tax rate field |
| `My Account > MFA methods` | next to each method type card |
| Field issues queue | next to severity class indicator |
| Calendar conflict resolution | next to deletion-conflict treatment buttons |
| QuickBooks conflict resolution | next to master direction indicator |
| Quote approval queue | next to "Approval required" annotation |
| Onboarding — Tax setup sub-flow | inline help on jurisdiction selection |

Selective placement keeps content authoring scope manageable. Tom owns content for each contextual help target.

### 19.12 Phase 2 Considerations

Out of MVP scope per Tier 4 #14:

- Diagnostic data attachment for bug reports (text-only feedback in MVP)
- Ticket system replacing email feedback intake
- Multi-language help content
- Help chat session sync across devices
- Community forum / user-to-user help
- AI-generated article suggestions (AI suggests new articles based on common queries with no good RAG match)
- Admin UI for help content editing (S3 + repo workflow for MVP)
- Help analytics dashboard for Tom (most-common queries, articles never retrieved, low-confidence answers)
- User-initiated help chat data deletion self-service (backend stub in MVP)
- Voice-only proactive help suggestions
- Real-time conversation streaming with progressive token rendering (full response for MVP if streaming infrastructure not ready)
- AI confidence scoring exposed to users
- Personalized help suggestions based on user history

---

## 20. Subscription Tier + Stripe Integration Architecture

Pass 4 Tier 3 #10 introduced the multi-tier subscription model with trial-as-tier framing and Stripe Subscriptions integration. Pass 4 Tier 4 #13 introduced Stripe Payment Intents for one-time invoice payments. This chapter covers the subscription tier infrastructure, Stripe integration architecture, payment flows, webhooks, and tier limit enforcement.

### 20.1 Strategic Direction

> **v3.0 Update (July 9, 2026)**: Pricing model updated to Founders/Trial/Starter/Teams. Schedule Lanes replace Dispatch Slots. Enterprise removed. See §20.2 seed data table below. Full decisions in `gtm-pricing-strategy-v1.md` v3.0.

Three architectural principles drive the design:

- **Trial-as-tier framing**: the trial is a subscription tier with `is_trial=true`, $0 price, 14-day duration, Starter-level limits, hard cap enforcement (no overages — SMS and Voice AI blocked at limit, no credit card required). Full feature parity with Starter. No special "trial mode" branching in the codebase — every code path that asks "what tier is this tenant on?" gets a clean answer via the tier system.
- **Data-driven tier configuration**: tier metadata (name, price, schedule lane count, SMS segments, Voice AI minutes) lives in the `subscription_tier` table. Adding/editing tiers is a DB update, not a code change. MVP launches with four plans: Founders (time-limited), Trial (14-day), Starter ($49), Teams ($149). Enterprise deactivated (`is_active=false`).
- **Stripe Subscriptions for recurring billing; Stripe Payment Intents for one-time invoice payments**: same Stripe account, parallel API surfaces. Per §18.5, customer payments on invoices use Payment Intents; per §20.4, tenant subscription billing uses Subscriptions. Both API surfaces share the webhook handler.

### 20.2 Subscription Tier Schema

**Schema** (per A75):

```sql
subscription_tier (
    tier_id                          UUID PRIMARY KEY,
    tier_name                        TEXT NOT NULL,
        -- 'trial' | 'starter' | 'professional' | 'enterprise' | ...
    display_label                    TEXT NOT NULL,        -- user-facing label
    monthly_price_cents              INTEGER NOT NULL,     -- 0 for trial
    is_trial                         BOOLEAN NOT NULL,     -- true only for trial tier
    trial_duration_days              INTEGER NULL,         -- set for trial tier; system default
    max_users                        INTEGER NOT NULL,
    max_sms_segments_per_month       INTEGER NULL,
        -- null = unlimited; otherwise enforced (overage billing per §17.6)
    is_active                        BOOLEAN NOT NULL DEFAULT TRUE,
        -- true if available for new signups
    display_order                    INTEGER NOT NULL,     -- order in tier picker UI
    stripe_price_id                  TEXT NULL,
        -- Stripe Price ID for paid tiers; null for trial
    created_at                       TIMESTAMPTZ NOT NULL,
    updated_at                       TIMESTAMPTZ NOT NULL
)
```

**MVP seed data (v3.0 — July 9, 2026)**:

| tier_name | display_label | monthly_price_cents | is_trial | schedule_lanes | voice_ai_min | sms_segs | is_active | trial_duration_days |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| founders | Founders | 4900 | FALSE | 5 | 90 | 100 | TRUE (until cap) | NULL |
| trial | Trial | 0 | TRUE | 5 | 90 | 100 (hard cap) | TRUE | 14 |
| starter | Starter | 4900 | FALSE | 5 | 90 | 100 | TRUE | NULL |
| teams | Teams | 14900 | FALSE | 20 | 300 | 500 | TRUE | NULL |
| ~~enterprise~~ | ~~Enterprise~~ | ~~49900~~ | FALSE | ~~75~~ | ~~1000~~ | ~~2500~~ | **FALSE** | NULL |

> **Schedule lane add-ons**: +1 lane $10/mo · +5 lanes (pack) $40/mo. The `subscription_tier` table does not store add-on state; add-ons are tracked separately as `tenant_product_feature_override` rows.
>
> **Note on `max_users`**: User count limit removed. Unlimited users on all plans. The `max_users` column on `subscription_tier` remains in the schema but is set to `-1` (unlimited) for all active plans. The enforcement gate is schedule lane count, not user count.

Tier prices are data-driven — adding new tiers is a DB insert; the tier picker UI reads from the table at render time. `founders` plan deactivates via `is_active=false` when the cohort cap is reached; existing Founders remain grandfathered indefinitely.

### 20.3 Subscription Usage Tracking

**Schema** (per A75):

```sql
tenant_subscription_usage (
    tenant_id              UUID PRIMARY KEY REFERENCES tenant,
    period_start           TIMESTAMPTZ NOT NULL,
        -- aligned to subscription billing cycle
    period_end             TIMESTAMPTZ NOT NULL,
    current_user_count     INTEGER NOT NULL,
    current_sms_segment_count INTEGER NOT NULL
        -- links to A65 SMS quota model in §17.6
)
```

**MVP scope**: tracks two metrics — current user count and current SMS segment count. Other dimensions (voice intent count, quote count, customer count, API call count) are deferred to Phase 2 because they create infrastructure that may not match what eventually gets monetized.

**Update triggers**:

- User-add events update `current_user_count`
- SMS-send events update `current_sms_segment_count` (per §17.6)

**Period rollover**: scheduled Celery task `rollover_sms_quota_periods` (per §3.2) creates new usage rows at subscription billing cycle boundaries.

### 20.4 Stripe Subscriptions Integration

Per A76, Stripe Subscriptions handle recurring billing for paid tiers.

**Stripe Customer record creation**: at first paid conversion, Pilot creates a Stripe Customer record with the tenant's billing email and metadata. Stored as `tenant.stripe_customer_id`. Reused for subsequent tier changes.

**Subscription lifecycle**:

1. Tenant selects paid tier in onboarding wizard (or `Settings > Subscription & Billing > Upgrade plan`)
2. Frontend uses Stripe Elements to collect card details
3. Backend creates Stripe Subscription via Stripe API with the tier's Stripe Price ID
4. Stripe processes initial payment; webhook fires `customer.subscription.created`
5. Backend confirms tier activation; tenant's `current_subscription_tier_id` updates
6. Recurring billing handled by Stripe; webhook fires `invoice.paid` on each cycle

**Conversion from trial**: when a trial tenant converts, the transition is:

1. Tenant submits Stripe Payment Method via Stripe Elements
2. Backend creates Stripe Customer + Subscription (with the chosen paid tier's Price ID)
3. On webhook confirmation, tenant transitions: `is_trial=true` → `is_trial=false`; `trial_ends_at` cleared; `current_subscription_tier_id` updated
4. No interruption to data or feature access — same tenant, same data, different tier

**APIs**:

- `POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial` — initiate conversion; expects Stripe Payment Method ID from frontend
- `POST /api/v1/tenants/{tenant_id}/subscription/change-tier` — change between paid tiers (Phase 2 surface; backend supports for MVP)

### 20.5 Stripe Payment Intents Integration (One-Time Invoice Payments)

Per §18.5 (Customer-Facing Public Surfaces) and A81, Stripe Payment Intents handle one-time invoice payments from customers via the public invoice link.

**Architecture summary** (full detail in §18.5):

- Customer enters payment amount on public invoice page (can vary from invoice total; comment required when variance)
- Frontend calls `POST /api/v1/public/invoices/{token}/payment-intent` with amount
- Backend creates Stripe Payment Intent; returns client_secret
- Frontend uses Stripe Elements to collect card and submit
- Stripe processes; webhook fires `payment_intent.succeeded` (or `payment_intent.payment_failed`)
- Backend records payment with actual amount + variance + comment

Same Stripe account as Subscriptions. Same Stripe Customer record (created on first interaction with the tenant — either subscription or invoice payment, whichever comes first).

### 20.6 Stripe Webhook Handler

Single webhook endpoint handles events from both Subscriptions and Payment Intents:

- Endpoint: `POST /api/v1/webhooks/stripe`
- Signature verification using Stripe webhook signing secret stored in Secrets Manager (per §9.1)
- Failure to verify signature returns 401 (Stripe retries per its policy)

**Handled events**:

| Event | Handler |
| :--- | :--- |
| `customer.subscription.created` | Confirm tier activation; record `stripe_customer_id` if first interaction |
| `customer.subscription.updated` | Handle tier changes (e.g., upgrade from Starter to Professional) |
| `customer.subscription.deleted` | Handle cancellation (Phase 2 self-service flow; MVP requires support contact) |
| `invoice.paid` | Confirm recurring subscription payment success |
| `invoice.payment_failed` | Trigger Stripe retry sequence; if exhausted, transition tenant to "payment failed" state |
| `payment_intent.succeeded` | Record one-time invoice payment per §18.5 |
| `payment_intent.payment_failed` | Surface failure to customer-facing UI per §18.5 |

**Idempotency**: webhook events are idempotent — processing the same event ID twice produces the same result. Stripe may retry events; handler uses event ID as idempotency key against `stripe_webhook_event_processed` table (deduplication).

### 20.7 Tier Limit Enforcement

**User-add flow**:

1. Tenant attempts to add a new user (invitation flow)
2. Backend checks `tenant_subscription_usage.current_user_count >= tier.max_users`
3. If limit reached: return 403 with structured payload `{tier_limit_reached: true, current_tier: ..., max_users: ..., upgrade_url: ...}`
4. Frontend renders Er3 (validation error per Tier 3 #8/#9 states catalog) with "Upgrade tier" CTA

**SMS-send flow**: per §17.6 SMS quota model.

**Phase 2**: feature-based limits as tier differentiation expands beyond user count. Schema accommodates additional limits via per-tier feature flags table (Phase 2).

### 20.8 Trial Expiration Read-Only State

When a tenant's trial expires (per §4.7.5), they enter "trial expired" state with read-only access plus paywall:

**Read-only enforcement** (API gateway middleware):

- For tenants in trial-expired state, write operations return 402 (Payment Required) with `{paywall: true, paywall_message: "..."}`
- Frontend handles 402 by surfacing the paywall (same tier picker UI as wizard step 4)
- Read operations continue working — data is preserved through expiration

**Conversion at trial end**: same flow as conversion during trial (per §20.4) — customer picks paid tier, submits payment, transitions to paid state.

### 20.9 Operator Overrides

Per §4.3.X Operator Role, operator can override per-tenant tier values:

- `tenant_tier_override.override_tier_id` — force tenant to a specific tier without payment
- `tenant_tier_override.override_trial_length_days` — extend trial for specific tenant
- `tenant_tier_override.override_reason` — required operator note
- Audit-logged

For MVP, operator manages via direct DB updates (per §4.3.X). Phase 2 introduces hidden Pilot routes for operator admin UI.

### 20.10 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── webhooks_stripe.py            # Stripe webhook handler (Subscriptions + Payment Intents)
│   │   ├── subscription_tiers.py         # GET /api/v1/subscription-tiers — tier picker data
│   │   ├── tenant_subscription.py        # GET/PUT /api/v1/tenants/{tenant_id}/subscription
│   │   └── ...
│   └── ...
├── services/
│   ├── stripe_subscriptions.py           # Subscription creation + lifecycle
│   ├── stripe_payment_intents.py         # One-time payment integration (per §18.5)
│   ├── tier_limit_enforcer.py            # User-add and SMS-send limit checks
│   ├── trial_management.py               # Trial state machine; expiration enforcement
│   └── ...
└── tasks/
    ├── enforce_trial_expirations.py      # per §3.2
    └── stripe_cleanup.py                  # cleanup_incomplete_stripe_payment_intents (per §3.2)
```

### 20.11 Phase 2 Considerations

Out of MVP scope:

- Stripe Customer Portal for self-service payment method management (MVP has read-only display)
- Annual billing tier discount
- Coupon / promo code support
- Self-service tier upgrade with proration
- Stripe Connect for direct-to-tenant invoice payment routing (architectural review point — Tom should review before MVP launch given financial implications; see §18.5)
- Per-customer pricing overrides
- Multi-currency support
- Self-service tenant cancellation (MVP requires support contact for cancellation)
- Feature-based limits beyond user count and SMS quota
- Usage-based pricing per category (voice intent count, quote count, etc.)

---

## Cost Analysis

### Total Infrastructure Cost (100 Customers — MVP)

| Category | Service | Monthly Cost |
| :--- | :--- | :--- |
| **Compute** | ECS Fargate (2 tasks) | $30 |
| | EC2 GPU g4dn.xlarge | $384 |
| | Lambda | $5 |
| | Application Load Balancer | $20 |
| | NAT Gateway | $32 |
| **Subtotal Compute** | | **$471** |
| **Database** | RDS PostgreSQL (Multi-AZ micro) | $43 |
| | ElastiCache Redis (micro) | $15 |
| **Subtotal Database** | | **$58** |
| **SMS Infrastructure** | Telnyx number rentals (100 tenants × ~$1) | $100 |
| | Telnyx outbound SMS (~10K segments/mo aggregate × $0.003) | $30 |
| | Telnyx inbound SMS (~5K segments/mo × $0.002) | $10 |
| **Subtotal SMS** | | **$140** |
| **Stripe Processing** | Subscription billing fees (~2.9% + $0.30 per transaction) | est. ~$200 |
| | One-time invoice payment fees (~2.9% + $0.30) | est. ~$50 |
| **Subtotal Stripe** | | **~$250** (passed through to tenants in pricing; not net cost to Pilot) |
| **AI Help System** | OpenAI text-embedding-3-small (corpus: ~$1 one-time + queries) | $5 |
| | S3 help corpus storage | $2 |
| **Subtotal AI Help** | | **$7** |
| **Storage** | S3 — photos + voice audio + multipart staging | $12 |
| **Monitoring** | CloudWatch (logs + metrics) | $36 |
| | GuardDuty + Security Hub | $15 |
| **Subtotal Monitoring** | | **$51** |
| **Security** | Secrets Manager | $2 |
| | VPC Endpoints | $13 |
| | KMS | $1 |
| **Subtotal Security** | | **$16** |
| **CI/CD** | ECR + S3 (Terraform state) | $2 |
| **Data Transfer** | ~600GB outbound (incl. SSE traffic + photo uploads) | $54 |
| **Map Provider** | Google Maps (per §13.8) | $77 |
| **GRAND TOTAL** (excluding pass-through Stripe fees) | | **~$888/month** |

**Per-customer cost:** $8.88/month
**Gross margin at $149/month:** 94.0%

**Pass 3 cost delta from v3.2 baseline ($643/month)**:

- S3 increased $5 → $12: voice audio storage for offline-captured commands; photo multipart upload staging area
- CloudWatch increased $34 → $36: new metrics for SSE connections, calendar sync conflicts, mobile sync events, voice deferred processing pipeline
- Data transfer increased $45 → $54: SSE persistent connections (~9GB/month per active dispatcher); photo uploads for tech-captured documentation
- Map provider added as separate line ($77/month at 100 customers per §13.8 estimate; previously omitted from totals despite being referenced in §13.8)

**Pass 4 Tier 1.5 cost delta from Pass 3 baseline ($741/month)**:

- SMS Infrastructure added as a new $140/month line item: Telnyx number rentals, outbound and inbound SMS at typical 100-tenant aggregate volume
- Number rental dominates at $100; per-message costs scale roughly with tenant SMS activity
- Tenant overage billing at $0.05/segment generates Pilot revenue when tenants exceed 100-segment included quota; not reflected in cost analysis (it's revenue, not cost)
- A2P 10DLC registration is a one-time setup cost (~$50 brand registration + per-campaign fees) and does not appear in monthly recurring

**Pass 4 close cost delta from Pass 4 Tier 1.5 baseline ($881/month)**:

- AI Help System added: $7/month for OpenAI embeddings (corpus + query embeddings) + S3 help corpus storage. Embedding model alternative (open-source Sentence-BERT) is feasible if avoiding OpenAI dependency is preferred, with ~equivalent monthly cost
- Stripe Processing fees are pass-through (tenant pays via subscription pricing or invoice surcharge); not net cost to Pilot but worth tracking — estimated $250/month at 100-tenant aggregate volume
- One-time costs not in monthly recurring: A2P 10DLC registration (~$50 brand + per-campaign fees), Stripe account setup, domain registration (`pilotfortrades.com`, optional `pilot.tr` short link), SendGrid sender domain SPF/DKIM/DMARC setup

### Scaling Economics

| Scale | Monthly Cost | Per-Customer Cost | Gross Margin (at $149) |
| :--- | :--- | :--- | :--- |
| 100 customers | $888 | $8.88 | 94.0% |
| 500 customers | $1,672 | $3.34 | 97.8% |
| 1,000 customers | $2,957 | $2.96 | 98.0% |

**Key insight:** Costs scale sub-linearly because the GPU instance, NAT Gateway, ALB, and monitoring are fixed costs amortized across a growing customer base. Map provider and S3 costs scale roughly linearly with customer count; data transfer scales with both customer count and tenant activity. SMS costs scale roughly linearly with customer count, so at 500 customers SMS is ~$700; at 1,000 it's ~$1,400. AI Help embedding queries scale with active help usage but query embedding cost is negligible at scale.

**Cost optimization opportunities (Phase 2)**:

- Self-host OSRM on the existing GPU instance — eliminates the $77+/month map provider cost at 100 customers, growing to several hundred at scale
- Reserved Instance for the GPU (3-year commitment): ~30% reduction on the $384/month
- Optimize SSE connection density via Redis Pub/Sub at scale > 1,000 customers (per §13.11)

---

## Appendices

### A. Glossary

| Term | Definition |
| :--- | :--- |
| **ACM** | AWS Certificate Manager |
| **ADOT** | AWS Distro for OpenTelemetry |
| **ALB** | Application Load Balancer |
| **CITEXT** | Case-Insensitive TEXT PostgreSQL extension |
| **ECS** | Elastic Container Service (Fargate = serverless) |
| **ETC** | Estimate to Complete — tech-provided remaining-hours estimate captured at clock-out (per §14.3) |
| **HNSW** | Hierarchical Navigable Small Worlds (pgvector index type) |
| **IAM** | Identity and Access Management |
| **IDOR** | Insecure Direct Object Reference (security vulnerability) |
| **JWT** | JSON Web Token (RS256-signed by Cognito) |
| **JWKS** | JSON Web Key Set (Cognito's public key endpoint) |
| **KMS** | Key Management Service |
| **LOTO** | Lock Out Tag Out (electrical safety procedure) |
| **MFA** | Multi-Factor Authentication |
| **NEC** | National Electrical Code (2023 edition) |
| **OAuth** | Open Authorization (2.0) |
| **OIDC** | OpenID Connect |
| **pgvector** | PostgreSQL extension for vector similarity search |
| **RBAC** | Role-Based Access Control |
| **RDS** | Relational Database Service |
| **RFC 7807** | Problem Details for HTTP APIs (error format standard) |
| **SLO** | Service Level Objective |
| **SQS** | AWS Simple Queue Service |
| **SSE** | Server-Sent Events — one-way HTTP push protocol used for live dispatch board updates (per §13.11) |
| **TIMESTAMPTZ** | Timezone-aware timestamp (PostgreSQL) |
| **VPC** | Virtual Private Cloud |
| **WAF** | Web Application Firewall |

### B. Key Technical Decisions

| Decision | Choice | Rationale |
| :--- | :--- | :--- |
| **Database** | PostgreSQL over MongoDB | ACID compliance, pgvector for AI, mature ecosystem |
| **Container orchestration** | ECS Fargate over EKS | $73/month savings; simpler ops for solo founder |
| **AI compute** | Local GPU (g4dn.xlarge) over cloud APIs | Unlimited usage, zero per-request cost, data privacy |
| **LLM** | Ollama (Llama 3.1 8B) over OpenAI | $0 vs $30–100/month; no third-party data exposure |
| **Frontend approach** | Dedicated Next.js + Expo over universal codebase | Each persona needs fundamentally different UX |
| **Pagination** | Cursor-based over offset | Consistent results, better scale, no `OFFSET` scans |
| **Deployment** | Blue-green via ALB over rolling (design goal; as built: ECS rolling + circuit breaker) | Zero downtime, instant rollback in < 2 minutes |
| **Rate limiting** | Tenant-scoped over IP-scoped | Multi-user tenants share a pool; IP is unreliable for SaaS |
| **Test endpoints** | `/test` suffix pattern | Eliminates JWT mocking in all 283 tests; blocked in prod |
| **Map provider** | Provider-abstract interface, Google Maps first | Enables vendor-neutral code; swap to Mapbox or self-hosted OSRM without refactor |
| **Calendar provider** | Provider-abstract interface, Google Calendar first | Same rationale; avoids lock-in |
| **Tech assignment** | Many-to-many schema, single-tech UI for MVP | Phase 2 multi-tech crews require no migration |
| **Route optimization** | Manual with drive-time assist for MVP | Automatic optimization deferred to Phase 2; solo operators prefer manual control |
| **Dispatch source of truth** | Pilot is authoritative, calendar mirrors | Consistent with QuickBooks sync pattern |
| **Calendar sync scope** | One shared company calendar per tenant | Matches solo-operator mental model; multi-tech-personal-calendar deferred to Phase 2 |
| **Conflict severity classification** | Four-class pattern (auto-silent / auto-notice / user-resolvable / escalation) | Pattern reused 3× in Pass 3 (dispatch §13.4, calendar §13.5, mobile sync §15.6); avoids alert fatigue |
| **Voice destructive-action safeguard** | Confirm-as-turn for every destructive intent | Universal across the platform; mirrors the always-preview rule for customer comms; catches voice misrecognitions before commit |
| **Diff display vocabulary** | Track-changes amber/green/red, server-computed `field_diffs` | Reused 4× (quote review, calendar conflict, mobile sync, future QB); single mental model across all compare-and-pick surfaces |
| **Two-tier configuration** | System default + nullable tenant override with explicit disable flag | Platform admins retain global control during incidents; tenants get flexibility; first applied to calendar conflict auto-expiry |
| **Mobile offline scope** | Explicit operations contract; not "best effort offline" | Avoids silent data-loss surprises; commits the platform to support what it claims to support |
| **Photo upload pipeline** | S3 multipart with signed URLs, separate from data sync | Resumable; offloads chunk handling to S3; WiFi-preference client-side scheduling |
| **Voice offline strategy** | Capture local, process online (deferred pipeline) | Preserves optimistic UI; no on-device ML for MVP; sub-2-sec latency target only applies to online captures |
| **Sync trigger model** | Foreground + network-change + 30s poll + manual; no background sync | Battery cost and iOS background-task constraints; most techs return to app frequently enough |
| **Offline hard limit** | 72-hour default with tenant override | Prevents indefinite local data accumulation; aligned with Cognito refresh token TTL; opt-out for legitimate extended-offline trades |
| **Owner escalation UI** | Web-only at MVP; mobile touch deferred to Pass 4 | Low-frequency surface; design language inherits from §13.5 calendar conflict resolution |
| **Dispatch live updates** | Server-Sent Events (SSE) over WebSockets | Server → client only; works with standard HTTP infrastructure; auto-reconnect; lower complexity for MVP |

### C. Security Checklist

- ✅ All secrets stored in AWS Secrets Manager (never in code or env files committed to git)
- ✅ Encryption at rest (KMS) for RDS, S3, ElastiCache — *as built: ElastiCache not encrypted (Known Limitations #24)*
- ✅ Encryption in transit (TLS 1.3) for all API and database connections — *as built: TLS 1.2+ at the ALB; Redis without TLS*
- ✅ Private subnets for all services (ECS, RDS, Redis, GPU)
- ✅ IAM least-privilege (ECS task roles scoped to minimum required permissions)
- ✅ MFA is available for all tenant users, tenant policy controls whether it's required
- ✅ Audit logging for all data mutations (85 tables via PostgreSQL triggers)
- ✅ IDOR prevention: all resource lookups include `tenant_id` filter
- ✅ CSRF protection on QuickBooks OAuth (state token, 10-min TTL)
- ✅ Idempotency keys prevent duplicate financial records
- ✅ Test endpoints blocked in staging/production (`TEST_ENDPOINT_ENABLED=false`)
- ✅ No PCI-DSS scope: all payment card data handled by PSP (Stripe) via token vaulting

### D. Useful Commands Reference

**Docker:**
```bash
docker compose up -d                              # Start all 6 containers
docker compose up -d postgres redis celery_worker celery_beat  # Backend only (no AI)
docker compose logs -f celery_worker              # Monitor Celery worker
docker compose restart celery_worker              # Restart worker after code change
docker compose down                               # Stop (preserves data volumes)
docker compose down -v                            # Stop + destroy volumes (DATA LOSS!)
```

**Alembic (migrations):**
```bash
alembic revision --autogenerate -m "description"  # Generate migration
alembic upgrade head                               # Apply all pending migrations
alembic downgrade -1                               # Rollback one revision
alembic history --verbose                          # Show migration history
```

**Celery (from project root):**
```bash
docker exec -it pilot_celery_worker celery -A core.celery_app inspect registered
docker exec -it pilot_celery_worker celery -A core.celery_app inspect active
docker compose logs celery_beat | grep "Sending due task"
```

**AI Stack verification:**
```bash
# Test Ollama (Llama 3.1 8B)
curl http://localhost:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "Say SUCCESS", "stream": false}'

# Test Whisper (requires audio file)
curl http://localhost:8080/v1/audio/transcriptions \
  -H "Content-Type: multipart/form-data" \
  -F file="@path/to/your-sample.m4a" \
  -F model="turbo"
```

**AWS CLI (production):**
```bash
aws ecs update-service --cluster pilot-production --service pilot-api --force-new-deployment
aws ecs describe-services --cluster pilot-production --services pilot-api
aws rds describe-db-instances --db-instance-identifier pilot-production
aws secretsmanager get-secret-value --secret-id pilot/production/database
```

**Terraform:**
```bash
terraform init
terraform plan -var-file=environments/production/terraform.tfvars
terraform apply -var-file=environments/production/terraform.tfvars
terraform destroy  # ⚠️ Only in dev/staging
```

NOTE: need to add map provider and calendar sync debugging commands post-implementation.
- The `schedule.manage` and `schedule.view_own` permissions were identified in the Pass 2 backend additions doc. Verify they're wired into the RBAC seeding (permissions are documented in `scheduling-dispatch-db-schema.md`).
 
### E. External Resources

| Resource | URL |
| :--- | :--- |
| FastAPI docs | https://fastapi.tiangolo.com |
| SQLModel docs | https://sqlmodel.tiangolo.com |
| PostgreSQL 17 docs | https://www.postgresql.org/docs/17/ |
| pgvector | https://github.com/pgvector/pgvector |
| Alembic docs | https://alembic.sqlalchemy.org |
| Whisper (faster-whisper-server) | https://github.com/fedirz/faster-whisper-server |
| Ollama | https://ollama.ai |
| Terraform AWS Provider | https://registry.terraform.io/providers/hashicorp/aws |
| QuickBooks API | https://developer.intuit.com/app/developer/qbo/docs/api |
| Turborepo | https://turbo.build/repo |
| Next.js App Router | https://nextjs.org/docs/app |
| Expo | https://docs.expo.dev |

---

## Document End

**Version History:**
- v1.0 (2025-10-15): Initial version
- v2.0 (2025-11-07): Complete redesign with all 10 architectural components
- v3.0 (2026-04-20): Full update reflecting current implementation — new frontend architecture (Next.js + Expo monorepo), validated Celery task registry, validated auth/RBAC/idempotency/rate-limiting implementation, local dev environment documentation, corrected API route prefix (`/api/v1/`), updated tech stack (Python 3.14+, faster-whisper-server turbo model)
- v5.1 (2026-05-15): Phase 4.2 traceability remediation — doc-only corrections: §2.1 trigger count corrected from "~85 tables" to "130+" (FIND-053); §4.5 MFA lockout boundary note added — Cognito is the enforcement layer, not Pilot schema (FIND-170); §13.3 OutlookCalendarProvider re-evaluation trigger added (FIND-139); §13.6 ETA computation clarified as on-demand at request time with Redis cache, not event-driven Celery task (FIND-115); §13.6 OAuth token refresh confirmed as inline pattern with explicit note against adding background task (FIND-116); §15.13 heading corrected — background sync IS in MVP per A51/§16.12 (FIND-123).
- v5.2 (2026-05-16): Phase 5.1 traceability report — §13.6 Receipt OCR vendor decision added: RapidOCR (`rapidocr-onnxruntime`) + Llama 3.1 8B on existing `pilot_ollama`; no new infrastructure or API cost; vendor decision closes FIND-137 → APPLIED.
- v5.3 (2026-05-19): Phase 4.4 B21 source doc updates — §13.6 Receipt OCR updated from "B20 Task 10" target to "B21 Task 6 APPLIED"; confirmed `services/ocr_service.py` + `tasks/receipt_ocr.py` + `rapidocr-onnxruntime==1.4.4` live; `job_expense` schema extended (`ocr_processed_at`, `ocr_source`); FIND-062 → APPLIED. Also corrects v5.2 header omission (version history had v5.2 but header remained v5.1).
- v5.4 (2026-07-09): Pricing evolution — §20 Subscription Tier + Stripe Integration Architecture updated to the 2-tier Founders/Starter/Teams model with a 14-day Trial tier; Schedule Lanes replace Dispatch Slots as the licensing unit (Starter=5 lanes, Teams=20 lanes; add-on packs); Founders time-limited cohort plan added (6 months free, then $49/mo locked at Starter limits); Enterprise removed (`is_active=false`). §20.1–§20.2 strategic direction and seed data table updated; aligns arch with mvp-prd v3.3 and `gtm-pricing-strategy-v1.md` v3.0. Also corrects line-1 stray `s` typo and reconciles header date (was May 19, predating the July 9 §20 update).
- v3.1 (2026-04-22): Frontend architecture update — reflects scaffolded Turborepo monorepo (pnpm 9.x, Turborepo 2.x, Next.js 16/Tailwind v4/React 19, Expo SDK 54/RN 0.81/Expo Router 6); finalized UI library selection (shadcn/ui web + Gluestack-UI mobile); updated `packages/` tree to match actual structure (`typescript-config`, `ui`, `eslint-config`); updated type-generation to file-export pattern (`pnpm sync-api-types`); added Terminal 3 for frontend dev; updated hosting note (App Runner for Next.js SSR); updated CORS origins
- v3.2 (2026-04-23): Added Section 13 (Scheduling & Dispatch) — bi-directional calendar sync, dispatch board, provider-abstract interfaces for map and calendar, new Celery tasks, new API endpoints under /api/v1/schedule/ and /api/v1/calendar/. Database schema maintained in dev-docs/analysis/scheduling-dispatch-db-schema.md.
- v4.0 (2026-04-26): Major update reflecting Pass 3 design completion. **Extensions to existing sections**: §3.2/§3.3 add Pass 3 Celery tasks (calendar conflict expiry, ETC variance notifier, photo upload cleanup, voice deferred processor, mobile sync cleanup, system template notifier); §4.3 adds Pass 3 RBAC permissions (quote.submit_for_approval, quote.approve, voice.manage_own_sessions, etc.); §4.6 added for refresh token TTL constraint vs. offline scenario; §5.4 adds cross-references to inheriting calendar conflict resolution patterns; §6.2 voice intent registry expanded to ~30 intents organized by domain; §6.3-§6.7 added comprehensive sections for conversation sessions, structured message payload (live/snapshot modes), confirm-as-turn pattern, and deferred voice processing pipeline; §7.6 adds natural-key fallback dedup for the 72-hour offline scenario; §7.9 added for the platform-wide pre-commit staleness check pattern; §13.4 upgraded to four-class severity; §13.5 substantially extended with conflict diff payload schema, server-computed field_diffs, two-tier auto-expiry, voice-active resolution; §13.10 monitoring extended; §13.11 added for Server-Sent Events infrastructure for live dispatch board. **New chapters**: §14 Quote Approval & Templates Architecture (line item visibility/hierarchy, three quote presentation styles, ETC capture system, quote approval workflow with pending edit storage, template versioning with system/tenant fork, time-limited discounts with margin cap); §15 Mobile Offline Operations Architecture (offline-capable operations contract, sync queue state model, idempotency UUIDs with natural-key fallback, S3 multipart resumable photo uploads, conflict severity classification engine with per-operation matrix, voice deferred processing, force-quit recovery, owner escalation routing, time-bounded offline operation, auth expiry with disabled-account export); §16 Cross-Cutting Platform Patterns (formalizes 8 platform-wide patterns: track-changes diff vocabulary, four-class severity, confirm-as-turn, pre-commit staleness check, system default + tenant override two-tier configuration, optimistic UI with pending badges, mobile owner status row, always-preview-before-send). **Cost Analysis** updated for Pass 3 infrastructure additions (S3 staging for photos and voice audio, SSE data transfer overhead, map provider as separate line); pricing updated to validated $149/month. Pass 3 entries added to Appendix B Key Technical Decisions and Appendix A Glossary.

**Next Review:** After Pass 4 design completion (polish, states, onboarding, owner-side mobile-conflict resolution UI)

**Contact:** Tom Lang (Founder) — tom@pilotfortrades.com

---

*This document represents the authoritative technical architecture for Pilot for Trades as of April 2026. All design decisions prioritize cost optimization, developer velocity, and production readiness for a solo-founder MVP targeting electrical contractors.*
