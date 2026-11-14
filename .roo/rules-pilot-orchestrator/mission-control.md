# 🛰️ Mission Control: Pilot for Trades Orchestration Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. Core Mission & North Star Metrics

The Orchestrator must ensure all technical plans protect these "non-negotiable" MVP metrics:

* **Infrastructure Budget**: Total monthly cost must stay between **$600–$1,000/month** for the first 100 customers.
* **Unit Economics**: Target a per-customer infrastructure cost of **~$8.88/month (~$888/month at 100 customers, under a $1,000 cap)**.
* **Voice Latency (p95)**: End-to-end voice command processing must be **< 2 seconds**.
* **API Latency (p95)**: Standard REST requests must respond in **< 500ms**.
* **Reliability**: Maintain a **99.9% availability SLO** and **99% QuickBooks sync success rate**.

## 2. Delegation Strategy & Guardrails

When using the `new_task` tool to spin up specialized modes, the Orchestrator **must** include these specific guideposts:

| Specialized Mode | Mandatory Guardrail to Include in Task |
| --- | --- |
| **Pilot for Trades Architect** | Must prioritize **ECS Fargate** over EKS and utilize the **g4dn.xlarge** GPU instance for cost-efficiency. |
| **Voice AI Specialist** | Tasks must explicitly reference the **Whisper Large-v3** and **Ollama Llama 3.1 8B** local pipeline. |
| **Integrations Lead** | All QuickBooks tasks must enforce **X-Idempotency-Key** headers and **OAuth 2.0** security. |
| **Electrical Expert** | Any quoting or calculation logic must be validated against **NEC code compliance**. |
| **DevOps Engineer** | Deployments must follow the **Blue-Green strategy** with a **< 2 minute rollback** time. |
| **Test Engineer** | Sync tests must verify **zero duplicate entries** in the database and QuickBooks. |

## 3. Phase-Gating (PRD Alignment)

The Orchestrator must prevent "feature creep" by strictly adhering to the **MVP Implementation Timeline**:

1. **Phase 1 (Foundation)**: Focus on AWS Infrastructure, the Core API, and the basic Voice interface.
2. **Phase 2 (Core Features)**: Focus on the Quote Engine, Profitability Dashboard, and QuickBooks OAuth.
3. **Phase 3 (Mobile & Optimization)**: Focus on React Native development and final performance tuning.

## 4. Error Handling & Conflict Resolution

* **Financial Data**: If a task involves money or sync, the Orchestrator must mandate **RFC 7807 error formats**.
* **System Conflicts**: Any architectural change that increases costs by **> 10%** must be flagged to the Founder (User) immediately for manual approval.
