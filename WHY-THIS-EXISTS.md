# Why This Exists

**The thesis:** one experienced architect, directing a disciplined multi-agent AI workflow, can produce engineering built to production standards — at a fraction of the time and cost a conventional team would need. This repository is the **evidence**, not the offer.

It was built to answer a question I kept getting asked (and kept asking myself): *when you take AI seriously as an engineering force-multiplier, and you put real senior judgment and guardrails around it, how far can one person actually get?* The answer is in this repo — measured and dated. Code, schema and test figures can be re-counted from this snapshot; commit and timeline figures come from the private original's history (see `PROVENANCE.md`).

---

## What this is

- A **capability demonstration** and the **launching pad for HotRMC**, my fractional-CTO practice. The point is to show — not assert — that I have direct, hands-on command of AI and AI-driven software delivery, applied to a real, hard problem rather than a toy.
- A **personal R&D build / lab**: *Pilot for Trades*, a full-stack, multi-tenant field-service platform for electrical contractors. The product is the **vehicle** — a deliberately demanding target (voice AI, payments, accounting sync, offline mobile, compliance math) chosen because easy problems prove nothing.
- A record of a **repeatable delivery method** — the operating model, the agent roles, and the guardrails — checked into the repo itself (`METHOD.md`, `AI-PITFALLS.md`, `.roomodes`, `.roo/rules-pilot-*`).

## What this is *not*

- **Not a product being marketed or sold.** Nothing is live or taking signups, and there is no sales motion. The marketing site, pricing pages and signup flow built for a launch that never happened are included as source only. It is a portfolio asset.
- **Not an operating business.** It was never released, has **no customers and no real user data**, and was intentionally hibernated at a founder-ready gate — by design, not by failure. Reaching "ready" and stopping on purpose was the point.
- **Not a team effort.** 100% solo — every commit in the private original's history is mine. That is the whole claim — remove the "solo" and the demonstration means nothing.
- **Not "vibe-coded."** It was governed: an architect-owned loop, zero-regression gates, and explicit guardrails that removed the AI's latitude to drift (see `AI-PITFALLS.md`). Fast *and* correct, not fast *then* sorry.
- **Not certified or audited.** The technical design follows the **SOC 2 security criteria (logging, encryption, least privilege) — built to the controls, not audited.** There are no organizational controls behind it, and nothing here is certified, compliant, or auditor-reviewed.
- **Not fundraising.** This isn't a pitch for investment in this product.

*(If you're interested in the asset itself, or in applying this kind of delivery to your own product or team, that's a real conversation — see **Let's talk** below. But the repo exists to demonstrate capability, not to transact.)*

---

## The case, in measured numbers

Code, schema and test figures below can be re-counted from this snapshot (small deltas reflect curation). Commit counts, active days and the timeline come from the private original's git history, which is not published here; `PROVENANCE.md` explains how they were measured. *How these numbers were derived and verified:* [`dev-docs/diligence/README.md`](dev-docs/diligence/README.md). (Full provenance in `PROVENANCE.md`.)

| What it took | What it produced |
|---|---|
| **1 person** | **~252,000 lines** of application code (AI-written, human-directed) across ~1,380 files |
| **~6 months of full-time build** (first commit 2026-03-02 → last 2026-09-07), after ~4–6 months of part-time research and design | **193 PostgreSQL tables**, **74 API route modules** (~700 operations: ~370 production + ~330 env-gated `/test` twins) |
| **156 active build days** (782 commits, private history) | **~8,000 automated tests** (~4,950 backend + ~3,070 frontend; ~234K test LOC, near 1:1 with app code); **76% backend coverage**, measured 2026-10-13 ([report](dev-docs/testing-support/backend-coverage-report-2026-10-13.md)) |
| **9+ AI agents across 6 LLMs**, 12 defined roles | **Twelve integrations** (Stripe incl. Connect, QuickBooks Online, Google Calendar, Telnyx, SendGrid, Cognito, S3/Lambda, Expo push, local Whisper + Llama, Cloudflare Turnstile, Google Maps, OpenAI help-article embeddings) |
| **~$888/month** modelled infrastructure cost at 100 customers (design target, under a $1,000 cap) | **~94% infrastructure margin** at the $149 Teams-annual price (~82–85% at the $49–$59 tiers), before payment and SMS fees; **no per-request inference cost for voice AI** (models run on a fixed-cost GPU) |

**The productivity-and-cost case (illustrative, not a measured claim):** a multi-tenant, full-stack B2B SaaS of this surface area — web + mobile + marketing, 193 tables, ~700 API operations, twelve integrations — conventionally staffs **a team of 20–30 engineers for about a year** (a conservative, size-based estimate; formal models such as COCOMO II put it higher), at a fully-loaded build cost commonly in the **low-to-mid seven figures**. This was **one person, in about six months of full-time build, at a tooling cost that is a rounding error against a single engineer's salary.** The orders of magnitude are the point; treat the comparison as an industry-norm illustration, and the one-person / six-month / measured figures as the hard facts.

---

## What it demonstrates about how I work

For a prospective fractional-CTO client, the repo is a working answer to the questions that actually matter:

- **I use AI as an engineering organization, not an autocomplete.** Twelve specialized agent roles, multiple frontier models routed to what each does best, a human owning every decision that is expensive to reverse.
- **I make AI *reliable*.** The hard part isn't getting AI to produce code — it's keeping it correct. `AI-PITFALLS.md` documents seven real failure modes from this build and the guardrail that contained each. That system of judgment is the transferable asset.
- **I architect for production, not demos.** Transactional money as integer cents (no floating-point money columns), 100% timezone-aware storage, 697 foreign keys, infrastructure as code, rolling deploys with automatic rollback, a technical design built to SOC 2 security criteria — the expensive-to-change decisions are made correctly.
- **I build to a budget.** Cost and margin were design constraints from day one, not an afterthought — a sub-$1,000/month design cap for the 100-customer configuration.
- **I'm honest about the edges.** Where the build stopped short (offline-sync mid-integration, coverage thin in background workers, RLS not yet enabled) is documented plainly. Knowing — and disclosing — where AI still needs the human-in-the-loop is itself the senior skill on display.

That is what HotRMC brings to a client: not "AI will write your code," but **"an experienced architect who can wield AI to deliver software built to production standards at a fraction of the usual time and cost — reliably, and with the judgment to know where it must not cut corners."**

---

## Where to go next

- **How it was built** → [`METHOD.md`](METHOD.md) — the operating model, agent roles, and guardrail system.
- **How AI was kept reliable** → [`AI-PITFALLS.md`](AI-PITFALLS.md) — real failure modes and the guardrails that contained them.
- **How the work was governed** → [`dev-docs/analysis/Pilot-Delivery-and-Governance.md`](dev-docs/analysis/Pilot-Delivery-and-Governance.md) — the batch / phase / gate apparatus and the propose → gate → verify loop.
- **Proof the artifact is real** → [`PROVENANCE.md`](PROVENANCE.md) — build provenance, measured scale, integrations, and what was changed to publish safely.
- **The engineering, examined** → [`dev-docs/diligence/`](dev-docs/diligence/) — measured scale and coverage; AI-run, adversarially prompted code-quality and database reviews (directed and edited by me); security & compliance architecture and IP/licensing posture; a consolidated known-limitations ledger; my own stress-test of the build; and the full build story.
- **The proof, visually** → [`dev-docs/visuals/`](dev-docs/visuals/) — the proof-suite graphics.
- **The stack and how to read the code** → [`README.md`](README.md).

## Let's talk

Built by **Tom Lang** — **HotRMC** (fractional CTO). If you want this kind of leverage applied to your product or team — or you have a serious question about the asset itself — reach me at **tom@hotrmc.com**.
