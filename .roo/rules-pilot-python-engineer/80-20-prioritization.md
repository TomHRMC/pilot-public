# 🚀 80/20 Prioritization: MVP Velocity Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "Mike the Solo Contractor" Filter

Every feature, bug fix, or architectural change must be justified by the needs of the primary persona: **Mike**, a solo electrical contractor doing $300K–$800K in revenue.

* **Rule**: If a feature serves an "Enterprise" or "Multi-trade" need (e.g., HVAC, 50+ employees), it is **deferred** to the Post-MVP Roadmap.
* **Rule**: Prioritize any task that reduces Mike's 15+ weekly hours of administrative "time waste".

## 2. Core Value Pillar Alignment

Only work that directly supports these four pillars is permitted for the MVP launch:

1. **Voice Quoting**: Transforming 10-hour manual quotes into 5-minute voice estimates.
2. **Live Profitability**: Real-time visibility into job margins to prevent "flying blind".
3. **QuickBooks Sync**: Eliminating double data entry.
4. **Field Accessibility**: Hands-free mobile operation in 70dB+ noise.

## 3. Technical "Good Enough" Standards

To maintain solo-founder velocity, the MVP Builder must follow these technical debt guardrails:

* **Infrastructure**: Use **ECS Fargate** for all container workloads (FastAPI, Celery, and Next.js web dashboard) to avoid EKS control plane cost. **App Runner was sunset April 30, 2026** — the web dashboard (`pilot-web`) runs as a 4th ECS Fargate service on the existing `pilot-production` cluster, sharing the ALB via a `Host: app.pilotfortrades.com` listener rule.
* **Database**: Stick to a single **Multi-AZ RDS** instance rather than a globally distributed cluster.
* **AI Models**: Use local **Ollama** and **Whisper** to eliminate per-request costs and complex external API management.

## 4. The "No-Go" List (MVP Deferrals)

The following are explicitly **out of scope** for the initial release:

* Multi-trade support (Plumbing, HVAC).
* Advanced crew scheduling/dispatching.
* In-app payment processing (Wait for Phase 4).
* White-labeling for larger contractors.

## 5. Success Metric Enforcement

The MVP Builder must prioritize tasks that directly move these needles:

* **Voice Accuracy**: >95% for electrical terminology.
* **Quote Speed**: <30 seconds end-to-end.
* **Reliability**: 99.9% uptime for core services.
