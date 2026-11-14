# Subscription & Pricing — Master Reference (MANDATORY — never deviate)

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

> **Added 2026-08-30** (Tom mandate, after PLP-FIX-1: a phantom `quotes_per_month` entitlement gate 402'd ALL quote creation because it contradicted the pricing model — and its seed rows never existed). Everyone touching plans, prices, limits, entitlements, usage quotas, upgrade prompts, or billing surfaces must know and follow this file.

**Master definition (product truth)**: [`dev-docs/product-requirements/mvp-prd.md`](../../dev-docs/product-requirements/mvp-prd.md) **§3.11 "Subscriptions & Usage" → Pricing Table + feature rows** — the ONLY authoritative definition of Pilot's subscription plans, prices, included allowances, limits, enforcement modes, and overage rates.

**Strategy companion (Charter program + messaging)**: `dev-docs/marketing-analysis/pilot-gtm-strategy-v3.md` _(private)_ §5 (pricing architecture) · §6 (Charter program) + locked decisions D15–D17 (12-cap · 90 days free · $49/mo locked billed monthly). **Runtime mapping**: `dev-docs/pilot-operations.md` _(private)_ §2–§3, §5–§6.

**Snapshot (2026-08-30)** — *if this ever disagrees with PRD §3.11, **the PRD wins** — flag the drift to Tom; never "fix" it yourself:*

| Plan | Price | Schedule lanes | Voice AI | SMS segs | Enforcement |
|---|---|---|---|---|---|
| **Charter** (12-cap cohort, formerly "Founders") | $0 × 90 days → **$49/mo locked for life** (billed monthly) | 5 | 90 min/mo | 100/mo | no overages in free period; soft after; free period operator-extendable (case by case; not an advertised offer) (GTM v3 D16) |
| **Trial** | $0 × 14 days | 5 | 90 | 100 | **block** (hard cap, no card) |
| **Starter** | **$49/mo** annual · $59/mo month-to-month | 5 | 90 | 100 | **soft** — overage: Voice $0.05/min, SMS $0.05/seg |
| **Teams** | **$149/mo** annual · $179/mo month-to-month | 20 | 300 | 500 | **soft** — same overage rates |

Add-ons: +1 lane $10/mo · +5 lanes pack $40/mo · +100 SMS segs per extra Telnyx number at +$5/mo.

**Unlimited on ALL plans — never gate these**: users, jobs, quotes, invoices, customers, QB syncs, emails, calendar syncs.

**Only three gated/metered features exist**: `schedule_lanes` (block), `voice_ai_minutes` (soft + overage), `outbound_sms_segments` (soft + overage). There is intentionally **no** `quotes_per_month`, job, invoice, or user limit.

## Non-negotiables

1. **Never invent** plan names, prices, allowances, limits, enforcement modes, or overage rates. Every value must trace to PRD §3.11 (product) and GTM v3 §5–§6 (messaging/framing).
2. **Phantom-gate rule**: never design an entitlement gate, paywall branch, or upsell gate for a feature the master marks unlimited. A gate requires BOTH a PRD §3.11 pricing line AND seeded `product_feature` + ppfv rows — a wiring without both is a phantom gate (report it to the Architect).
3. **Marketing-specific**: the public pricing page, `/charter` page, and every plan CTA must match the master exactly — including the Charter framing (90 days free, $49/mo locked for life, 12-spot cap with honest "X spots remaining" display per GTM v3 §6.8) and the D16 rule that an operator extension of the free period is handled case by case and is not an advertised offer. No invented discounts, countdown tactics, tiers, anchor prices, or "limited-time" framing absent from GTM v3 / the PRD. Annual vs month-to-month display follows the master table ($49 annual · $59 monthly; $149 annual · $179 monthly).
4. If work seems to require a value not in the master → **STOP and ask Tom**. The master changes only via Tom-approved PRD edits (Architect-owned); the Architect refreshes this snapshot in the same change — that is how updates reach every mode automatically.
