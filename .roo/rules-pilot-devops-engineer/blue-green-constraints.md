# 🟢 Blue-Green Deployment: DevOps Operational Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. Zero-Downtime Objective

The DevOps Engineer must maintain a **99.9% availability SLO**, allowing for no more than 43 minutes of downtime per month. All production deployments must utilize a **Blue-Green strategy** to ensure the "Blue" (current) version remains active until the "Green" (new) version is fully validated.

## 2. Traffic Shifting & Validation Logic

The deployment process must follow a strictly phased traffic shift via the **Application Load Balancer (ALB)**:

* **Phase 1: Provisioning**: Deploy the "Green" ECS Task Definition alongside "Blue".
* **Phase 2: Health Checks**: "Green" tasks must pass three consecutive 30-second health checks before receiving any production traffic.
* **Phase 3: Canary Shift (10%)**: Route 10% of traffic to "Green" and monitor for 5 minutes.
* **Trigger**: If Error Rate > 1% or p95 Latency > 1s, trigger an immediate rollback.


* **Phase 4: Intermediate Shift (50%)**: Route 50% of traffic and monitor for an additional 5 minutes.
* **Phase 5: Full Cutover (100%)**: Shift all traffic to "Green" and keep "Blue" tasks idle for 30 minutes before termination.

## 3. Rollback & Disaster Recovery

* **Rollback Time**: The system must be capable of a full rollback to the previous stable Task Definition in **< 2 minutes**.
* **Database Safety**: Before any deployment involving **Alembic migrations**, a manual RDS snapshot must be triggered if the migration contains `DROP` or `ALTER COLUMN` operations.
* **Manual Intervention**: Provide a "Kill Switch" in the CI/CD pipeline that immediately shifts 100% of traffic back to the "Blue" target group.

## 4. Resource & Cost Constraints

* **Compute Efficiency**: During the Blue-Green overlap, the total ECS task count will double; ensure the **VPC Subnets** have sufficient IP headroom and the **NAT Gateway** can handle the increased throughput.
* **GPU Stability**: Since the **g4dn.xlarge** is a persistent EC2 instance, the DevOps Engineer must coordinate model reloads (Whisper/Ollama) to ensure the GPU memory is not exhausted during a version switch.

## 5. Security & Infrastructure as Code (IaC)

* **Terraform Locks**: All deployments must use **S3 + DynamoDB** for remote state locking to prevent concurrent infrastructure changes.
* **OIDC Authentication**: GitHub Actions must use **OIDC** to assume AWS IAM roles; never use long-lived IAM Access Keys for deployments.
