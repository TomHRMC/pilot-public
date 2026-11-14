# Pilot for Trades — Architecture Diagrams

*How Pilot is built today, and where it goes next on the enterprise path. Each diagram is drawn from the code and Terraform in this repo, not from aspiration. Each page lists the code and Terraform files it was drawn from.*

## Diagrams

| # | View | What it answers |
|---|---|---|
| 1 | [Container view](01-container-view.md) | What runs, who uses it, and how the apps, API, data stores, voice AI, background workers and third-party services connect |
| 2 | [AWS deployment view](02-aws-deployment-view.md) | Where it runs: the network topology, the runtime services, and the security, monitoring and delivery controls around them |
| 3 | [Security and tenant isolation](03-security-tenant-isolation.md) | How a request is trusted: one authenticated write end to end, and the check that guards each kind of caller |
| 4 | [Voice AI pipeline](04-voice-ai-pipeline.md) | How a spoken command becomes a saved record on Pilot's own GPU, online or offline, and how destructive actions are confirmed |
| 5 | [Delivery and governance](05-delivery-and-governance.md) | How a change is designed, gated, tested and shipped: the human-directed AI-agent workflow and the deploy pipeline |
| 6 | [Enterprise maturity map](06-enterprise-maturity-map.md) | The one-page summary: built today vs. the next step, across nine dimensions |

Start with **6** for the summary, or **1** for the big picture.

## Legend

| Style | Meaning |
|---|---|
| Solid box / solid arrow | **Built.** It exists in the code or Terraform and was deployed to the AWS environment (built to production spec; it never carried customer traffic). |
| Dashed orange box / dashed orange arrow | **Enterprise path.** Designed for, not built. The arrow runs *from* today's component *to* its upgrade. |
| Rounded box | A person or an external system |
| Cylinder | A data store |

The pages are written in [Mermaid](https://mermaid.js.org/), which GitHub renders natively, so the diagrams stay in version control next to the code they describe and are updated the same way.

Pre-rendered PNGs of each diagram are in [`images/`](images/), for slides and offline viewing:

| PNG | Page and section |
|---|---|
| `pilot-arch-request-path.png` | 1 · The request path |
| `pilot-arch-background-integrations.png` | 1 · Background work and integrations |
| `pilot-infra-network-topology.png` | 2 · Network and runtime topology |
| `pilot-infra-security-ops.png` | 2 · Security, operations, and delivery |
| `pilot-security-write-sequence.png` | 3 · One authenticated write, end to end |
| `pilot-security-trust-boundaries.png` | 3 · Every way in, and what guards it |
| `pilot-voice-pipeline.png` | 4 · The pipeline |
| `pilot-voice-confirmation.png` | 4 · Confirm-as-turn |
| `pilot-delivery-agent-workflow.png` | 5 · Making a change |
| `pilot-delivery-release-pipeline.png` | 5 · Shipping it |
| `pilot-overview-maturity-map.png` | 6 · Enterprise maturity map |

## State today

The AWS stack is **hibernated**. It was deliberately torn down to a near-zero cost floor, and only the marketing site's S3 bucket and CloudFront distribution remain ([ADR-0020](../pilot-adr-log.md), [ADR-0021](../pilot-adr-log.md)). The diagrams show the topology as built and run. Restart is `terraform apply` plus data provisioning ([ADR-0016](../pilot-adr-log.md)).

## Honest framing

These diagrams are meant to hold up under diligence, so they don't overclaim:

- **Tenant isolation** is enforced in the application and query layer and covered by a dedicated isolation test suite. Postgres row-level security is on the enterprise path, not on today.
- **SOC 2:** the technical design follows the SOC 2 security criteria (Security Hub with the AWS Foundational and CIS benchmarks, Config, GuardDuty, KMS, audit events) — built to the controls, not audited; no organizational controls.
- **Enterprise SSO:** the schema is ready (`sso_provider`, `user_sso_identity`). Cognito federation is not wired up.

For the full list, see [Known Limitations](../../diligence/Pilot-Known-Limitations.md).

## Related

- [ADR log](../pilot-adr-log.md): the decisions behind each trade-off
- [AWS infrastructure as-built](../../devops/aws-infrastructure-as-built.md)
- [AWS ops runbook](../../devops/aws-ops-runbook.md)
