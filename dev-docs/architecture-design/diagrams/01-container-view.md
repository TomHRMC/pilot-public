# Container View — what runs, and how it connects

*C4 level 2, in two parts. Every box is a separately deployable unit or a managed service it depends on; every arrow is a call that exists in the code. Solid = built. Dashed orange = enterprise path (designed for, not built). See the [diagram index](README.md) for the legend and sources.*

## 1. The request path — people, apps, identity, data

```mermaid
flowchart TB
  prospect(["Prospect"])
  tech(["Field technician<br/><i>iOS · Android</i>"])
  cust(["Contractor's customer<br/><i>quote · invoice links · microsite</i>"])
  owner(["Owner / office staff<br/><i>browser</i>"])

  subgraph clients["Client apps — frontend/ · pnpm + Turborepo · shared OpenAPI-generated types"]
    direction LR
    mkt["<b>Marketing site</b><br/>Next.js static export<br/>S3 + CloudFront"]
    mobile["<b>Mobile app</b><br/>Expo · React Native<br/>offline store + sync engine<br/><i>(integration in progress)</i>"]
    web["<b>Web app</b><br/>Next.js App Router · SSR<br/>public /q /i /invite pages<br/>tenant microsites *.p4tsites.com"]
  end

  subgraph identity["Identity — AWS Cognito"]
    cognito["<b>User pool</b><br/>MFA: TOTP + SMS<br/>12-char password policy"]
    lambdas["<b>Lambda triggers</b><br/>post-confirmation · post-auth"]
  end

  api["<b>API</b> — FastAPI · REST /api/v1 · OpenAPI contract<br/>RBAC · tenant scoping · idempotency keys · audit events<br/>rate limiting on selected public routes"]

  subgraph data["Data"]
    direction LR
    s3[("<b>S3 assets</b><br/>versioned · encrypted")]
    redis[("<b>Redis 7</b><br/>cache · Celery broker")]
    pg[("<b>PostgreSQL 17</b><br/>pgvector · FK / CHECK / EXCLUDE<br/>tenant_id on tenant-owned tables")]
  end

  subgraph ai["Voice AI — private GPU tier · no third-party generative AI"]
    direction LR
    whisper["<b>① Whisper large-v3</b><br/>speech-to-text"]
    llama["<b>② Llama 3.1 8B</b> via Ollama<br/>intent parsing"]
  end

  sso["Enterprise SSO — SAML / OIDC<br/><i>sso_provider + user_sso_identity<br/>tables already in schema</i>"]:::path
  rls["Postgres row-level security<br/><i>defense-in-depth on the<br/>existing tenant_id columns</i>"]:::path

  prospect --> mkt
  tech --> mobile
  cust --> web
  owner --> web

  mkt -- "lead capture" --> api
  mobile -- "HTTPS · JSON · Cognito JWT" --> api
  web -- "HTTPS · JSON · Cognito JWT" --> api
  mobile & web -- "sign-in · MFA" --> cognito
  cognito --> lambdas
  lambdas -- "provision tenant + user" --> pg

  api --> s3
  api --> redis
  api --> pg
  api -- "voice: ① audio → transcript · ② transcript → intent" --> ai

  cognito -.-> sso
  pg -.-> rls
  lambdas ~~~ sso

  classDef path stroke:#c77700,stroke-width:2px,stroke-dasharray:6 4;
  linkStyle 15,16 stroke:#c77700,stroke-width:2px;
```

## 2. Background work and integrations

```mermaid
flowchart LR
  beat["<b>Celery beat</b><br/>scheduler<br/>exactly one instance"]
  api["<b>API</b><br/>FastAPI"]
  redis[("<b>Redis 7</b><br/>broker")]
  worker["<b>Celery worker</b><br/>notification outbox · SMS<br/>QuickBooks sync<br/>profitability rollups"]
  pg[("<b>PostgreSQL 17</b>")]

  subgraph byapi["Called by the API"]
    stripe["<b>Stripe</b><br/>Connect + Billing"]
    misc["<b>Google Maps</b><br/><b>Cloudflare Turnstile</b>"]
  end

  subgraph byworker["Called by the worker"]
    qbo["<b>QuickBooks Online</b>"]
    telnyx["<b>Telnyx</b><br/>10DLC SMS"]
    sendgrid["<b>SendGrid</b><br/>email"]
    expo["<b>Expo Push</b>"]
  end

  subgraph identity["Cognito (auth messaging)"]
    cognito["<b>User pool</b>"]
    emailer["<b>Custom email sender</b><br/>Lambda · KMS-decrypted"]
    sns["<b>AWS SNS</b><br/>MFA one-time codes"]
  end

  api -- "enqueue" --> redis
  beat -- "schedule" --> redis
  redis --> worker
  worker --> pg

  api <-- "charges ⇄ webhooks<br/>signature-verified" --> stripe
  api -- "maps · bot checks" --> misc
  worker -- "two-way sync" --> qbo
  worker -- "texts" --> telnyx
  worker -- "email" --> sendgrid
  worker -- "push" --> expo
  qbo -- "change webhooks" --> api
  telnyx -- "inbound SMS ·<br/>delivery receipts" --> api

  cognito -- "OTP SMS" --> sns
  cognito --> emailer
  emailer -- "branded auth email" --> sendgrid
```

## What each container is

| Container | Technology | Responsibility | Source |
|---|---|---|---|
| Web app | Next.js (App Router), Tailwind, shadcn/ui, TanStack Query | Office/admin UI; public quote, invoice and invite pages; SSR tenant microsites on `*.p4tsites.com` | `frontend/apps/web/` |
| Mobile app | Expo / React Native, gluestack-ui | Field technician app; on-device store and sync engine built, integration in progress | `frontend/apps/mobile/` |
| Marketing site | Next.js static export | Public site and lead capture (`/api/v1/marketing/waitlist`) | `frontend/apps/marketing/` |
| API | FastAPI (Python 3.14), SQLModel | All business logic behind one versioned REST contract (`backend/openapi.json`); RBAC, tenant scoping, idempotency, audit events, rate limiting on selected public routes (Known Limitations #28) | `backend/api/`, `backend/core/` |
| Celery worker | Celery 5 | Async work: notification outbox, SMS, QuickBooks sync, profitability rollups | `backend/tasks/` |
| Celery beat | Celery 5 | Scheduled jobs; pinned to one instance so jobs never double-fire | `backend/tasks/`, `infrastructure/terraform/modules/compute/main.tf` |
| PostgreSQL 17 | RDS, pgvector | System of record; integrity enforced in the database (foreign keys, CHECK and EXCLUDE constraints) | `dev-docs/db-design/pilot-db-schema-v2.6h.json` |
| Redis 7 | ElastiCache | Celery broker and cache | `infrastructure/terraform/modules/database/main.tf` |
| Voice AI | Whisper large-v3, Llama 3.1 8B (Ollama) on a GPU instance | Speech-to-text and intent parsing with no per-call AI vendor cost ([ADR-0002](../pilot-adr-log.md)) | `backend/services/` |
| Cognito + Lambdas | Cognito user pool; three Python 3.12 Lambdas | Sign-in and MFA; tenant/user provisioning on sign-up; new-device checks; branded auth email | `backend/lambda/`, `infrastructure/terraform/modules/security/main.tf` |

## Enterprise path shown here

- **Enterprise SSO (SAML/OIDC).** The `sso_provider` and `user_sso_identity` tables are already in the schema; wiring them to Cognito federation is the remaining work.
- **Postgres row-level security.** Tenant isolation is enforced in the application/query layer today and covered by a dedicated isolation test suite. Turning on RLS is an additive migration on the existing `tenant_id` columns — defense-in-depth, not a redesign. See [Known Limitations](../../diligence/Pilot-Known-Limitations.md).
