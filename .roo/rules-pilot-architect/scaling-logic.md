# 📈 Scaling Logic: Growth & Resource Management

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. Sub-Linear Scaling Philosophy
Ensure that infrastructure costs do not grow at the same rate as the customer base. Maximize the utility of fixed-cost items (GPU instance, NAT Gateway, ALB, Monitoring) before adding redundant units.

## 2. Infrastructure Scaling Tiers
The Architect must design toward these predefined tiers based on validated economics:

| Component | MVP (100 Users) | Growth (500 Users) | Scale (1,000 Users) |
| --- | --- | --- | --- |
| **ECS Fargate** | 2 Tasks (0.25 vCPU) | 4 Tasks | 8 Tasks |
| **RDS PostgreSQL** | db.t4g.micro | db.t4g.small | db.t4g.medium |
| **ElastiCache** | cache.t4g.micro | cache.t4g.small | cache.t4g.medium |
| **EC2 GPU** | 1 x g4dn.xlarge | 1 x g4dn.xlarge | 2 x g4dn.xlarge |
| **Monthly Cost** | **~$888** | **~$1,672** | **~$2,957** |
| **Cost Per User** | **$8.88** | **$3.34** | **$2.96** |

## 3. Component-Specific Scaling Triggers
Do not scale prematurely. Use these specific thresholds:

### Compute (ECS Fargate)
* **Trigger**: CPU Utilization > 70% or Memory > 80% for 3 consecutive 5-minute periods.
* **Action**: Increment task count by 2 until the next tier is reached.

### Database (RDS)
* **Trigger**: Storage reaching 80% capacity or CPU consistently > 60%.
* **Action**: Enable **RDS Storage Autoscaling** first. Upgrade instance class only if `work_mem` or connection limits (100 max) are exhausted.

### Voice AI (GPU)
* **Trigger**: Voice AI Latency (p95) exceeds **2.5 seconds** due to queue depth in Whisper/Ollama.
* **Action**: Provision a second **g4dn.xlarge** and update the ALB to distribute traffic.

### Real-time Connections (SSE / Dispatch Board)
* **Constraint**: SSE connections consume one ECS task thread per connection. At MVP, 100-200 active connections fit within Fargate capacity.
* **Trigger**: Nearing 1,000 customers or ECS thread exhaustion due to idle dispatch boards.
* **Action**: Shift from direct FastAPI SSE to a **Redis Pub/Sub** broadcast layer to decouple connection count from task thread limits.

### External APIs (Google Maps & Telnyx)
* **Trigger**: Map provider costs exceeding $1,500/month or hitting hard API rate limits.
* **Action**: Initiate Phase 2 optimization: migrate from Google Maps Distance Matrix to a self-hosted OSRM container running on the existing GPU instance to eliminate variable costs.

## 4. Optimization Before Scaling
Before upgrading resources, verify:
* **HNSW Indexes**: Ensure `pgvector` similarity searches are utilizing indexes to minimize CPU load.
* **API Caching**: Ensure Map API distance-matrix calculations are cached in Redis (24-hour TTL) keyed by `(origin, destination, hour-of-day)`.