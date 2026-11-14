# How the Work Was Planned, Governed, and Verified

*This folder, in the private build, held the delivery apparatus that ran the project: a master launch plan, its dated archives, a batch registry, and a formal launch gate. Those documents contained internal sequencing, open decisions, and Charter-member planning, so they were curated out of this public snapshot. The one exception is the **ADR decision log**, which records only decision *rationale* — information that exists nowhere else and carries no sensitive planning — so it is kept in this public repo as first-class proof (see [`pilot-adr-log.md`](../architecture-design/pilot-adr-log.md)). What follows is the public synthesis — what the apparatus contained, how it was structured, and how analysis and delivery were actually performed. It's here because the **governance is itself a core piece of the proof**: it's what separates a disciplined AI-augmented build from a fast pile of confident debt.*

---

## What the apparatus contained

- **A master launch plan** (single source of truth) — versioned through ~50 revisions across the build window (Mar → Sep 2026), each revision a dated, one-paragraph changelog entry recording exactly what closed, what opened, and what it touched.
- **Five dated archives** (July → August) — completed work swept out of the live plan at each phase exit, leaving a visible paper trail of sustained output rather than a single end-state snapshot.
- **An ADR decision log** (through ADR-0021) — the architectural source of truth, a required "start-here" read, with decisions cited inline as authority. **Included in this public repo:** [`pilot-adr-log.md`](../architecture-design/pilot-adr-log.md).
- **A batch registry** — every unit of work as an append-only row with a stable ID, never renumbered.
- **A 16-row Founder Launch Gate** — the release checklist, each row owner-assigned, with explicit on-the-record *non-gates* (items deliberately deferred, decided in the open rather than quietly dropped).

## How it was structured

Work was decomposed into **named batches** (e.g. `PLP-FIX-7`), each owned by a role-labeled AI engineer (Python / React / React Native / DevOps / UI-designer) and orchestrated by a "Pilot Architect" role. Batches were sequenced into **phases** — Pre-Founder Core → Full UI Suite → Fix Sprint → Founder Gate → Post-Founder — with a late-August re-sequence when the strategy shifted to "founders *are* the beta."

Every batch opened as a **full-scope card**: inclusions, *explicit exclusions*, and exit criteria written before work began. The plan itself stayed lean — it linked out to the detailed design docs, prompts, and ADRs rather than inlining them, so the single source of truth never became unreadable.

## How analysis and delivery were performed

- **Propose → gate → verify loop.** The Architect authored a design doc and an engineer prompt → **the human ruled on every open decision** → the AI engineer executed and appended a completion summary to the batch's own prompt doc → **the human personally ran a verification plan against the AWS environment** (built to production spec; it never carried customer traffic) → residual findings spawned the next FIX batch. An entire 11-batch September hardening series was generated this way, straight from that testing.
- **Status-flip-only close protocol (ADR-0018).** A batch was closed only by the Architect flipping its status to `✅ YYYY-MM-DD`, adding a one-line registry row, and updating the gate — append-only, stable IDs, never renumbered. "Done" was a recorded event with a date, not a claim.
- **Guardrails enforced in the workflow.** A zero-regression error-coverage ratchet blocked any new uncovered error path; an MSW fixture-fidelity harness kept mocks contract-faithful; a DDL-only seed rule kept schema changes honest; every batch reported an exact passing/failing test delta.
- **Review and roll-forward.** Open operational items were reviewed on a weekly cadence; completed work was archived at each phase exit; phase promotions required explicit human sign-off.

## Accurate status at hibernation (2026-09-07)

- **Charter build: complete except three open items** — signup wizard, trial + usage-metered billing, cohort cap, Charter→Teams upgrade and operator/platform shell were all built; the open engineering items were the mobile offline-sync layer (~70%, mid-integration), an owner-MFA-reset escape hatch, and a mobile UX up-design.
- **Founder Launch Gate: carried to founder-ready, then deliberately hibernated** — apart from the three open engineering items above, the gate's remaining rows were go-to-market ops (live-mode Stripe bootstrap audit, App Store / Play binaries, a full production E2E pass, recruiting the first 3–5 Charter founders), deferred on purpose.
- **No paying customer was ever onboarded — by design;** the Charter founders were to be the beta.
- **Intentional hibernation** — the AWS stack was torn down toward near-zero cost, DNS parked, a static hold page left up, with a documented restart runbook (about one day of runbook work; allow about a week of calendar time). Paused, not abandoned.

## What this demonstrates

The point isn't that a lot got built. It's that it was built the way a funded engineering org is *supposed* to run — scoped cards with explicit exclusions, a formal release gate with honest non-gates, an ADR log as the decision authority, a human-owned verify step on every batch, a regression ratchet, and a dated paper trail — except it was one person directing an AI team. Tenant isolation is application/query-layer enforced (Postgres RLS not enabled; a documented hardening item), and that too was tracked in the open rather than glossed. Governance like this is the difference between AI as a force-multiplier and AI as a liability generator — and running it is exactly the judgment a fractional CTO brings.

---

*For the operating model and the agent roles, see [`../../METHOD.md`](../../METHOD.md); for the failure modes the guardrails were built to contain, [`../../AI-PITFALLS.md`](../../AI-PITFALLS.md); for the measured scale and proof metrics, [`../diligence/Pilot-for-Trades-Proof.md`](../diligence/Pilot-for-Trades-Proof.md).*
