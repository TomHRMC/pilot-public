# Subscription & Pricing — Master Reference (MANDATORY — never deviate)

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

> **Added 2026-08-30** (Tom mandate, after PLP-FIX-1: a phantom `quotes_per_month` entitlement gate 402'd ALL quote creation because it contradicted the pricing model — and its seed rows never existed). Everyone touching plans, prices, limits, entitlements, usage quotas, upgrade prompts, or billing surfaces must know and follow this file.

**Master definition (product truth)**: [`dev-docs/product-requirements/mvp-prd.md`](../../dev-docs/product-requirements/mvp-prd.md) **§3.11 "Subscriptions & Usage" → Pricing Table + feature rows** — the ONLY authoritative definition of Pilot's subscription plans, prices, included allowances, limits, enforcement modes, and overage rates.

**Runtime mapping (implementation truth)**: `dev-docs/pilot-operations.md` _(private)_ §2 (Product Plan Hierarchy) · §3 (Subscription Tier Model) · §5 (Founders/Charter Cohort Model) · §6 (Per-Tenant Overrides). Charter mechanics: GTM v3 §6 + locked decisions D16/D17.

**Snapshot (2026-08-30)** — *if this ever disagrees with PRD §3.11, **the PRD wins** — flag the drift to Tom; never "fix" it yourself:*

| Plan | Price | Schedule lanes | Voice AI | SMS segs | Enforcement |
|---|---|---|---|---|---|
| **Charter** (12-cap cohort, formerly "Founders") | $0 × 90 days → **$49/mo locked for life** (billed monthly) | 5 | 90 min/mo | 100/mo | no overages in free period; soft after; free period operator-extendable (case by case; not an advertised offer) |
| **Trial** | $0 × 14 days | 5 | 90 | 100 | **block** (hard cap, no card) |
| **Starter** | **$49/mo** annual · $59/mo month-to-month | 5 | 90 | 100 | **soft** — overage: Voice $0.05/min, SMS $0.05/seg |
| **Teams** | **$149/mo** annual · $179/mo month-to-month | 20 | 300 | 500 | **soft** — same overage rates |

Add-ons: +1 lane $10/mo · +5 lanes pack $40/mo · +100 SMS segs per extra Telnyx number at +$5/mo.

**Unlimited on ALL plans — never gate these**: users, jobs, quotes, invoices, customers, QB syncs, emails, calendar syncs.

**Only three gated/metered features exist**: `schedule_lanes` (block), `voice_ai_minutes` (soft + overage), `outbound_sms_segments` (soft + overage). There is intentionally **no** `quotes_per_month`, job, invoice, or user limit.

## Non-negotiables

1. **Never invent** plan names, prices, allowances, limits, enforcement modes, or overage rates. Every value must trace to PRD §3.11 (product) and the seeded `product_plan_product_feature_version` rows (runtime).
2. **Phantom-gate rule**: never design an entitlement gate, paywall branch, or upsell gate for a feature the master marks unlimited. A gate requires BOTH a PRD §3.11 pricing line AND seeded `product_feature` + ppfv rows — a wiring without both is a phantom gate (report it to the Architect).
3. **Voice UI-specific**: voice-session limit and upsell UX (e.g., Voice-AI-minutes usage) must follow the master allowances and **soft-cap semantics** — soft-capped features (Voice AI, SMS) never hard-block a field tech mid-task; design usage meters, 80%/100% threshold notices, and after-the-fact overage summaries instead. Only `schedule_lanes` and the trial are block-enforced. Quotes, jobs, invoices, and customers are unlimited — voice flows for them never carry limit UX of any kind.
4. If work seems to require a value not in the master → **STOP and ask Tom**. The master changes only via Tom-approved PRD edits (Architect-owned); the Architect refreshes this snapshot in the same change — that is how updates reach every mode automatically.
