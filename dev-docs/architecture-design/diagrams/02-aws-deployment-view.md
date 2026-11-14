# AWS Deployment View — where it runs

*Dashed arrows run from today's component to its enterprise upgrade. The production topology as built and defined in Terraform (`infrastructure/terraform/environments/production/`, which composes the six modules in `infrastructure/terraform/modules/`). Solid = built. Dashed orange = enterprise path (designed for, not built). See the [diagram index](README.md) for the legend and sources.*

> **State today:** this is the as-built topology from July–September 2026. At hibernation the stack was deliberately torn down to a near-zero cost floor ([ADR-0020](../pilot-adr-log.md), [ADR-0021](../pilot-adr-log.md)); only the marketing site's S3 bucket and CloudFront distribution remain. Restart is `terraform apply` plus data provisioning ([ADR-0016](../pilot-adr-log.md)), documented in the [ops runbook](../../devops/aws-ops-runbook.md).

## 1. Network and runtime topology

```mermaid
flowchart TB
  users(["Users<br/><i>browsers · mobile apps</i>"])
  dns["<b>DNS — Cloudflare</b><br/>pilotfortrades.com · p4tsites.com<br/><i>Route 53 for pilotfortrades.com<br/>before hibernation</i>"]
  cf["<b>CloudFront</b><br/>marketing CDN · HTTPS only"]
  s3m[("<b>S3 marketing</b><br/>private · CloudFront OAC only")]
  ext(["External APIs<br/><i>Stripe · QuickBooks · Telnyx · SendGrid …</i>"])

  subgraph vpc["VPC 10.0.0.0/16 · us-east-1 · two availability zones (1a, 1b)"]
    subgraph pub["Public subnets — 10.0.1.0/24 · 10.0.2.0/24"]
      alb["<b>Application Load Balancer</b><br/>TLS 1.2+ policy (1.3 preferred) · HTTP → HTTPS<br/>app.* and *.p4tsites.com → web<br/>everything else → API"]
      nat["<b>NAT gateway</b> · 1a<br/>outbound calls to external APIs"]
      bastion["<b>Bastion host</b><br/>SSH · IP allowlist<br/>admin tunnel to RDS"]
    end

    subgraph priv["Private subnets — 10.0.10.0/24 · 10.0.11.0/24 · no public IPs"]
      subgraph ecs["ECS Fargate cluster · tasks spread across 1a/1b · auto-rollback on failed deploys (api · worker · web)"]
        web["<b>web</b> ×1<br/>Next.js :3000"]
        api["<b>api</b> ×2<br/>FastAPI :8000"]
        worker["<b>worker</b> ×2<br/>Celery"]
        beat["<b>beat</b> ×1<br/>Celery scheduler"]
      end
      rds[("<b>RDS PostgreSQL 17</b><br/>Multi-AZ primary + standby<br/>KMS-encrypted · Performance Insights<br/>daily backups · 28-day point-in-time restore<br/>weekly manual snapshots")]
      redis[("<b>ElastiCache Redis 7</b><br/>single node")]
      gpu["<b>GPU EC2 g4dn.xlarge</b> · 1a<br/>Whisper + Llama · encrypted EBS"]
      lam["<b>Cognito Lambdas</b><br/>post-confirmation · post-auth"]
    end

    vpce["<b>VPC endpoints</b><br/>S3 · Secrets Manager<br/>private access, no internet hop"]
  end

  waf["AWS WAF<br/>on ALB + CloudFront"]:::path
  nat2["NAT gateway per AZ<br/>no single-AZ egress"]:::path
  scale["ECS service autoscaling<br/>target tracking on api / worker"]:::path
  redisha["Redis replication group<br/>Multi-AZ · TLS · at-rest encryption"]:::path
  gpuha["GPU Auto Scaling group<br/>second AZ"]:::path

  users --> dns
  dns -- "pilotfortrades.com · www" --> cf
  cf --> s3m
  dns -- "api. · app. · *.p4tsites.com" --> alb
  alb --> web
  alb --> api
  api --> rds
  api --> redis
  api -- "voice" --> gpu
  worker --> rds
  worker --> redis
  beat --> redis
  lam --> rds
  ecs --> vpce
  ecs --> nat
  nat --> ext

  alb -.-> waf
  nat -.-> nat2
  ecs -.-> scale
  redis -.-> redisha
  gpu -.-> gpuha

  classDef path stroke:#c77700,stroke-width:2px,stroke-dasharray:6 4;
  linkStyle 16,17,18,19,20 stroke:#c77700,stroke-width:2px;
```

## 2. Security, operations, and delivery

```mermaid
flowchart LR
  gh(["GitHub Actions"])

  subgraph delivery["Delivery — no long-lived AWS keys in CI"]
    oidc["<b>IAM OIDC role</b><br/>short-lived credentials"]
    ecr["<b>ECR</b><br/>4 repos · api · worker · beat · web"]
    deploy["<b>ECS rolling deploy</b><br/>100% healthy minimum<br/>circuit-breaker rollback"]
  end

  subgraph runtime["Runtime"]
    ecs["<b>ECS services</b><br/>separate task + execution roles<br/>scoped secret access"]
    data["<b>RDS · Redis · S3 assets</b>"]
  end

  subgraph secrets["Secrets and keys"]
    sm["<b>Secrets Manager</b><br/>11 secrets · DB, Redis, Stripe,<br/>QuickBooks, Telnyx, SendGrid, …"]
    kms["<b>KMS key</b> · customer-managed<br/>RDS · EBS · all 11 secrets<br/>S3 assets · Cognito email codes"]
    acm["<b>ACM certificates</b><br/>TLS for ALB + CloudFront"]
  end

  subgraph observe["Monitoring"]
    cw["<b>CloudWatch</b><br/>logs · dashboard · 12 alarms<br/>p95 latency · error rate · CPU/memory<br/>RDS · Redis · GPU · Lambda"]
    alarms["<b>SNS</b><br/>alarm email"]
  end

  subgraph posture["Security posture"]
    gd["<b>GuardDuty</b><br/>threat detection"]
    sh["<b>Security Hub</b><br/>AWS Foundational + CIS benchmarks"]
    cfg["<b>AWS Config</b><br/>configuration recorder<br/>required-tags rule"]
  end

  soc2["SOC 2 Type II audit<br/><i>built to the controls —<br/>not audited</i>"]:::path
  bluegreen["CodeDeploy blue/green<br/><i>green target group already staged</i>"]:::path

  gh -- "assume role" --> oidc
  oidc --> ecr
  oidc --> deploy
  ecr --> deploy
  deploy --> ecs
  ecs -- "read at start-up" --> sm
  sm --> kms
  data --> kms
  ecs --> cw
  data --> cw
  cw --> alarms
  gd -- "findings" --> sh
  cfg -- "findings" --> sh

  posture -.-> soc2
  deploy -.-> bluegreen

  classDef path stroke:#c77700,stroke-width:2px,stroke-dasharray:6 4;
  linkStyle 13,14 stroke:#c77700,stroke-width:2px;
```

## Why it's built this way

- **Cost cap as a design constraint.** The platform was designed to run for about $888/month at 100 customers under a $1,000 design cap. That drives the small instance classes, the single NAT gateway and the single Redis node — each a deliberate, documented trade-off, not an oversight. See [ADR-0001](../pilot-adr-log.md) (Fargate-first), [ADR-0002](../pilot-adr-log.md) (owned GPU) and [ADR-0003](../pilot-adr-log.md) (single Multi-AZ RDS).
- **Only the load balancer, CloudFront and an IP-allowlisted SSH bastion are reachable from the internet.** The services, database, cache and GPU sit in private subnets with no public IPs; the marketing bucket is reachable only through CloudFront.
- **Data that matters is protected by default.** The database is Multi-AZ, with daily automated backups (any point in the last 28 days can be restored) plus weekly manual snapshots kept indefinitely; one customer-managed KMS key encrypts the database, disks, secrets and asset storage; secrets live in Secrets Manager and are read at start-up rather than baked into images.
- **Deploys are designed not to take the site down.** Rolling ECS deploys keep 100% of healthy tasks until the new ones pass health checks, and roll back automatically if they don't.

## Enterprise path

| Upgrade | Why it's next | Starting point already in place |
|---|---|---|
| AWS WAF on the ALB and CloudFront | Managed protection against common web attacks and bots | TLS 1.2+ policy (TLS 1.3 preferred) on the ALB; Cloudflare Turnstile on public forms |
| NAT gateway per AZ | Removes the one remaining single-AZ dependency for outbound calls | Subnets and route tables already split across two AZs |
| ECS service autoscaling | Scale api/worker on load instead of fixed counts | Services already stateless, spread across AZs, behind the ALB |
| Redis replication group (Multi-AZ, TLS, at-rest encryption) | High availability and encryption for the broker/cache | Called out in the Terraform as the "Phase 2 upgrade path" |
| GPU Auto Scaling group / second AZ | Removes the single voice-AI instance as a capacity ceiling and failure point | [ADR-0002](../pilot-adr-log.md) records the scaling trigger (≈500 tenants or p95 > 2.5 s) |
| RDS read replica / RDS Proxy | Offload reporting reads; pool connections at higher task counts | Multi-AZ instance, Performance Insights and connection alarms already on |
| CodeDeploy blue/green for the API | Instant cut-over and rollback between two task sets | Second ("green") API target group already provisioned |
| SSM Session Manager in place of the bastion | Audited admin access with no open SSH port | GPU instance already has the SSM policy attached |
| AWS Backup plan with cross-region copies / DR | Automates the weekly snapshot and survives a full-region outage | Daily automated backups with 28-day point-in-time restore, weekly manual snapshots, and the restart runbook |
| SOC 2 Type II audit | Independent attestation | Security Hub (Foundational + CIS), Config, GuardDuty, KMS, audit-event logging — technical design follows the SOC 2 security criteria; built to the controls, not audited |

## Sources

`infrastructure/terraform/modules/{networking,compute,database,security,storage,monitoring}/main.tf` · `infrastructure/terraform/environments/production/main.tf` · `.github/workflows/deploy-production.yml` · [ADR log](../pilot-adr-log.md) · [AWS infrastructure as-built](../../devops/aws-infrastructure-as-built.md)
