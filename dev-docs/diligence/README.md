# Diligence & Capability Evidence

*This folder holds the evidence behind the project: measured scale and coverage, AI-run engineering reviews, the security/compliance/IP posture, a consolidated known-limitations ledger, and the build story. It exists to show — not assert — the engineering judgment behind an AI-augmented, solo-built platform built to production standards and never operated in production.*

---

## How these documents were produced (and why the numbers are trustworthy)

Code, schema, test and history figures in these documents were **measured on the original private repository** — source files, git history, the schema's golden-master definition, and the actual test runners. Modelled figures — run cost, margin, GPU sizing — are labelled as modelled. Code, schema and test figures can be re-checked against this public snapshot (expect small deltas from curation); commit and timeline figures come from the private history and are documented in [`../../PROVENANCE.md`](../../PROVENANCE.md).

- **The analysis was performed by an AI assistant working through the real codebase**, under my direction — reading source, counting with the repo's own tooling (`grep`/`find`/`git`), inspecting the schema JSON, and running three separate AI review passes (backend, web, mobile), each prompted to act as a skeptical senior engineer, read the actual files rather than the docs, and report weaknesses rather than praise. The analysis ran against the full private repository; this public snapshot is a curated subset of it. No human third party has reviewed this code.
- **I ran the test-coverage measurements myself** — `pytest --cov` (backend) and `vitest` / `jest --coverage` (web/mobile) on the real code — and the reported figures (76% backend, ~71% web, ~75% mobile, 2026-10-13) are recorded verbatim from those runs.
- **I directed, reviewed, and own every document.** The AI did the labor; I set the scope, ruled on framing, and verified the claims against what I know of the build.

**Reproducible, not infallible.** The point isn't "an AI said so, trust it." It's that **anything here except the git-history figures can be checked against this repository** — re-run the counts and re-read the files (re-running the coverage needs the private original's environment; the recorded reports are in `dev-docs/testing-support/`). If a code, schema or test number can't be reproduced within curation deltas, treat it as an error and tell me; the codebase is the final authority, and these documents are only ever a faithful read of it.

There's a deliberate symmetry worth noting: **this evaluation was produced the same way the product was** — AI performing the work against a ground-truth source, a human directing and verifying. The honesty discipline that governs the build (name the weaknesses, measure don't assert, disclose before you're asked) governs its evaluation too.

*Produced across the build-review work of October 2026. Dated figures carry their measurement date inline.*

---

## Index

**Start / overview**
- [`Pilot-for-Trades-Proof.md`](Pilot-for-Trades-Proof.md) — the measured scale and coverage (scale, tests, coverage, integrations, timeline).
- [`Pilot-Build-Story.md`](Pilot-Build-Story.md) — the end-to-end narrative: business need → build → stack → method → governance → status.

**Engineering, examined**
- [`Pilot-Self-Review.md`](Pilot-Self-Review.md) — my own adversarial stress-test of the repo, with findings drawn from the code, Terraform and docs.
- [`Pilot-Code-Quality-Assessment.md`](Pilot-Code-Quality-Assessment.md) — three AI-run, adversarially prompted reviews (backend / web / mobile), with my responses.
- [`Pilot-Database-Assessment.md`](Pilot-Database-Assessment.md) — the schema graded from a data-architect's seat.

**Posture: security, compliance, IP**
- [`Pilot-Security-Architecture.md`](Pilot-Security-Architecture.md) — identity, secrets, encryption, hardening, supply chain, threat model.
- [`Pilot-Compliance-by-Design.md`](Pilot-Compliance-by-Design.md) — TCPA/10DLC, PCI scoping, privacy/data lifecycle.
- [`Pilot-IP-and-Licenses.md`](Pilot-IP-and-Licenses.md) — code ownership and open-source license posture.

**Honest edges**
- [`Pilot-Known-Limitations.md`](Pilot-Known-Limitations.md) — the consolidated ledger of known gaps.

**Operations**
- [`Pilot-Operations-and-Resilience.md`](Pilot-Operations-and-Resilience.md) — IaC, deploy pipeline, backups, DR, observability (and its gap).

**Related, elsewhere in the repo**
- [`../analysis/Pilot-Delivery-and-Governance.md`](../analysis/Pilot-Delivery-and-Governance.md) — how the work was planned, governed, and verified.
- [`../visuals/`](../visuals/) — the proof-suite graphics.
- [`../../METHOD.md`](../../METHOD.md) · [`../../AI-PITFALLS.md`](../../AI-PITFALLS.md) · [`../../PROVENANCE.md`](../../PROVENANCE.md) — the method, the guardrails, and the artifact's provenance.
