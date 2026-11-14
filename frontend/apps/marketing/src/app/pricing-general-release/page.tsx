// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
"use client";

/**
 * Pricing Page — General Release Mode
 * File: src/app/pricing-general-release/page.tsx
 *
 * This file is the General Release variant of /pricing.
 * The React Engineer (MKT-B11-C2) will merge this into the main /pricing/page.tsx
 * behind the useSiteMode() hook switch.
 *
 * In production, /pricing/page.tsx renders this layout when:
 *   useSiteMode() returns "general_release"
 *
 * Design tokens: all styles reference var() tokens from globals.css — no hardcoded hex.
 */

import { useState } from "react";
import Link from "next/link";

const starterFeatures = [
  "5 schedule lanes (parallel job rows)",
  "90 Voice AI minutes/month",
  "100 SMS segments/month",
  "Unlimited users — no per-seat fees",
  "Unlimited jobs, quotes & invoices",
  "Voice-to-quote AI (NEC-aware for electricians)",
  "Real-time job profitability tracking",
  "Smart dispatch board with conflict detection",
  "QuickBooks Online sync (two-way)",
  "Google Calendar sync",
  "Customer SMS + appointment reminders",
  "iOS + Android app — works offline",
  "Stripe payments + invoicing",
  "GPS clock-in/clock-out + photo docs",
];

const teamsFeatures = [
  "20 schedule lanes (parallel job rows)",
  "300 Voice AI minutes/month",
  "500 SMS segments/month",
  "Unlimited users — no per-seat fees",
  "Unlimited jobs, quotes & invoices",
  "Voice-to-quote AI (NEC-aware for electricians)",
  "Real-time job profitability tracking",
  "Smart dispatch board with conflict detection",
  "QuickBooks Online sync (two-way)",
  "Google Calendar sync",
  "Customer SMS + appointment reminders",
  "iOS + Android app — works offline",
  "Stripe payments + invoicing",
  "GPS clock-in/clock-out + photo docs",
  "Priority support",
  "Advanced analytics & reporting",
];

const faqs = [
  {
    q: "Is there a free trial?",
    a: "Yes — 14 days free on your chosen plan (Starter or Teams limits), no credit card required. After 14 days, continue at $59/month (Starter) or $179/month (Teams), or cancel anytime before your trial ends. No surprises.",
  },
  {
    q: "What's a schedule lane?",
    a: "A schedule lane is one parallel job row on your dispatch board. Assign any team member to any job in any lane. Starter includes 5 simultaneous jobs visible at once; Teams includes 20. Most solo operators and small crews work comfortably within 5 lanes.",
  },
  {
    q: "What happens when I use more than my included Voice AI minutes or SMS?",
    a: "Usage beyond the included amounts is billed at usage-based rates. We'll notify you before any overage charges hit. For most contractors working a normal job volume, the included amounts cover everything.",
  },
  {
    q: "Do I pay per user?",
    a: "Never. Both plans include unlimited user accounts. Add apprentices, office staff, or a second truck — no extra charge.",
  },
  {
    q: "Can I switch between Starter and Teams?",
    a: "Yes, anytime. Upgrades take effect immediately. Downgrades take effect at the next billing cycle. You can also change during your trial period.",
  },
  {
    q: "What's the QuickBooks sync like?",
    a: "Two-way, automatic, with built-in conflict resolution. If a customer or invoice changes on both sides, Pilot shows you exactly what changed and lets you pick the right version — no duplicate entries, no mystery data.",
  },
  {
    q: "Does it work on Android?",
    a: "Yes. iOS and Android both. The offline mode works the same on both — data syncs when you're back in signal, whether that's after a basement job or a rural service call.",
  },
  {
    q: "I'm a plumber/HVAC contractor. Is this for me?",
    a: "Electrical is where we're focused right now — the NEC code assistant and default catalog are built around electrical work. Plumbing and HVAC support are coming. If you want to get in early for your trade, reach out.",
  },
];

function CheckIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      className="mt-0.5 shrink-0"
      aria-hidden="true"
    >
      <circle cx="9" cy="9" r="8" fill="var(--margin-50)" />
      <path
        d="M5 9l3 3 5-5"
        stroke="var(--margin-600)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-3 list-none p-0 m-0">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3">
          <CheckIcon />
          <span className="text-sm" style={{ color: "var(--neutral-700)" }}>
            {item}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function PricingGeneralReleasePage() {
  const [annual, setAnnual] = useState(false);
  const [openFaq, setOpenFaq] = useState<string | null>(null);

  const starterMonthly = 59;
  const teamsMonthly = 179;
  const starterAnnual = Math.round(starterMonthly * 0.83); // 17% off = ~$49
  const teamsAnnual = Math.round(teamsMonthly * 0.83); // 17% off = ~$149

  const starterPrice = annual ? starterAnnual : starterMonthly;
  const teamsPrice = annual ? teamsAnnual : teamsMonthly;

  return (
    <>
      {/* Hero */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="pricing-heading"
      >
        <div className="container-marketing text-center">
          <h1
            id="pricing-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            Simple, transparent pricing.
          </h1>
          <p
            className="text-section-subtitle mb-10 max-w-2xl mx-auto"
            style={{ color: "var(--neutral-600)" }}
          >
            Start free for 14 days — no credit card required. Pick the plan that
            fits your crew size.
          </p>

          {/* Annual billing toggle */}
          <div className="flex items-center justify-center gap-4">
            <span
              className="text-sm font-medium"
              style={{
                color: annual ? "var(--neutral-400)" : "var(--neutral-900)",
              }}
            >
              Monthly
            </span>
            <button
              role="switch"
              aria-checked={annual}
              onClick={() => setAnnual(!annual)}
              className="relative inline-flex h-7 w-14 items-center rounded-full transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
              style={{
                background: annual ? "var(--brand-600)" : "var(--neutral-200)",
                outlineColor: "var(--brand-400)",
              }}
              aria-label="Toggle annual billing"
            >
              <span
                className="inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform"
                style={{
                  transform: annual
                    ? "translateX(1.75rem)"
                    : "translateX(0.25rem)",
                }}
              />
            </button>
            <span
              className="flex items-center gap-2 text-sm font-medium"
              style={{
                color: annual ? "var(--neutral-900)" : "var(--neutral-400)",
              }}
            >
              Annually
              <span
                className="px-2 py-0.5 rounded-full text-xs font-semibold"
                style={{
                  background: "var(--margin-50)",
                  color: "var(--margin-600)",
                }}
              >
                Save 17%
              </span>
            </span>
          </div>
        </div>
      </section>

      {/* Pricing cards */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-label="Pricing plans"
      >
        <div className="container-marketing">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Starter card */}
            <div
              className="card-pricing p-8 flex flex-col"
              style={{ boxShadow: "var(--shadow-md)" }}
            >
              <div className="mb-6">
                <h2
                  className="text-xl font-bold mb-1"
                  style={{ color: "var(--neutral-900)" }}
                >
                  Starter
                </h2>
                <p
                  className="text-sm mb-5"
                  style={{ color: "var(--neutral-600)" }}
                >
                  For solo operators and small crews
                </p>

                <div className="flex items-end gap-1 mb-1">
                  <span
                    className="text-section-title font-bold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    ${starterPrice}
                  </span>
                  <span
                    className="text-base mb-2"
                    style={{ color: "var(--neutral-600)" }}
                  >
                    /month
                  </span>
                </div>
                {annual && (
                  <p
                    className="text-xs mb-4"
                    style={{ color: "var(--neutral-500)" }}
                  >
                    Billed as ${starterAnnual * 12}/year
                  </p>
                )}
              </div>

              <Link href="/sign-up" className="btn-primary text-center mb-2">
                Start Free Trial
              </Link>
              <p
                className="text-xs text-center mb-8"
                style={{ color: "var(--neutral-400)" }}
              >
                14-day free trial at Starter limits · No credit card required
              </p>

              <div className="flex-1">
                <FeatureList items={starterFeatures} />
              </div>

              <p
                className="text-xs mt-6"
                style={{ color: "var(--neutral-400)" }}
              >
                Converts to $59/month or cancel anytime before trial ends.
              </p>
            </div>

            {/* Teams card — featured */}
            <div
              className="card-pricing p-8 flex flex-col relative overflow-hidden"
              style={{
                border: "var(--divider-thick) solid var(--brand-600)",
                boxShadow: "var(--shadow-xl)",
              }}
            >
              {/* "Most Popular" badge */}
              <div
                className="absolute top-0 right-0 px-4 py-1.5 text-xs font-semibold text-white"
                style={{
                  background: "var(--brand-600)",
                  borderRadius: "0 1rem 0 0.75rem",
                }}
                aria-label="Most popular plan"
              >
                Most Popular
              </div>

              <div className="mb-6">
                <h2
                  className="text-xl font-bold mb-1"
                  style={{ color: "var(--neutral-900)" }}
                >
                  Teams
                </h2>
                <p
                  className="text-sm mb-5"
                  style={{ color: "var(--neutral-600)" }}
                >
                  For growing multi-crew operations
                </p>

                <div className="flex items-end gap-1 mb-1">
                  <span
                    className="text-section-title font-bold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    ${teamsPrice}
                  </span>
                  <span
                    className="text-base mb-2"
                    style={{ color: "var(--neutral-600)" }}
                  >
                    /month
                  </span>
                </div>
                {annual && (
                  <p
                    className="text-xs mb-4"
                    style={{ color: "var(--neutral-500)" }}
                  >
                    Billed as ${teamsAnnual * 12}/year
                  </p>
                )}
              </div>

              <Link href="/sign-up" className="btn-primary text-center mb-2">
                Start Free Trial
              </Link>
              <p
                className="text-xs text-center mb-8"
                style={{ color: "var(--neutral-400)" }}
              >
                14-day free trial at Teams limits · No credit card required
              </p>

              <div className="flex-1">
                <FeatureList items={teamsFeatures} />
              </div>

              <p
                className="text-xs mt-6"
                style={{ color: "var(--neutral-400)" }}
              >
                Converts to $179/month or cancel anytime before trial ends.
              </p>
            </div>
          </div>

          {/* Schedule Lane explanation callout */}
          <div
            className="mt-10 max-w-4xl mx-auto rounded-xl p-5 flex items-start gap-4"
            style={{
              background: "var(--brand-50)",
              border: "var(--divider-thin) solid var(--brand-100)",
            }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              className="shrink-0 mt-0.5"
              aria-hidden="true"
            >
              <rect
                x="2"
                y="4"
                width="16"
                height="13"
                rx="2"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
              />
              <path
                d="M2 8h16M7 4V2M13 4V2"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <path
                d="M6 12h2M9 12h2M12 12h2"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            <p className="text-sm" style={{ color: "var(--brand-800)" }}>
              <strong style={{ color: "var(--brand-900)" }}>
                What&apos;s a schedule lane?
              </strong>{" "}
              It&apos;s one parallel job row on your dispatch board. Assign any
              team member to any job in any lane. Starter includes 5
              simultaneous lanes; Teams includes 20.
            </p>
          </div>
        </div>
      </section>

      {/* Included-at-a-glance strip */}
      <section
        className="py-12"
        style={{ background: "var(--surface-marketing-alt)" }}
        aria-label="What every plan includes"
      >
        <div className="container-marketing">
          <p
            className="text-sm uppercase tracking-wider text-center mb-6"
            style={{ color: "var(--neutral-400)" }}
          >
            Every plan includes
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            {[
              { icon: "👥", label: "Unlimited users" },
              { icon: "📋", label: "Unlimited jobs" },
              { icon: "🧾", label: "Unlimited invoices" },
              { icon: "📱", label: "Offline mobile" },
              { icon: "🔄", label: "QuickBooks sync" },
              { icon: "📆", label: "Google Calendar sync" },
              { icon: "💳", label: "Stripe payments" },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium"
                style={{
                  background: "var(--white)",
                  color: "var(--neutral-700)",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section
        id="faq"
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-labelledby="faq-heading"
      >
        <div className="container-marketing max-w-3xl mx-auto">
          <h2
            id="faq-heading"
            className="text-section-title text-center mb-12"
            style={{ color: "var(--neutral-900)" }}
          >
            Questions? We&apos;ve got answers.
          </h2>
          <div role="list">
            {faqs.map((faq) => (
              <div key={faq.q} className="faq-item" role="listitem">
                <button
                  className="faq-button"
                  onClick={() => setOpenFaq(openFaq === faq.q ? null : faq.q)}
                  aria-expanded={openFaq === faq.q}
                >
                  <span>{faq.q}</span>
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="none"
                    className="shrink-0"
                    aria-hidden="true"
                    style={{
                      transform:
                        openFaq === faq.q ? "rotate(180deg)" : "rotate(0deg)",
                      transition: "transform 0.2s",
                    }}
                  >
                    <path
                      d="M5 8l5 5 5-5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                {openFaq === faq.q && (
                  <div className="pb-4 pt-1">
                    <p
                      className="text-base"
                      style={{ color: "var(--neutral-600)" }}
                    >
                      {faq.a}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="pricing-cta-heading"
      >
        <div className="container-marketing text-center">
          <h2
            id="pricing-cta-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            Ready to try it on a real job?
          </h2>
          <p
            className="text-body-lg mb-10"
            style={{ color: "var(--neutral-600)" }}
          >
            14 days free. No credit card required. Cancel anytime before your
            trial ends.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/sign-up" className="btn-primary">
              Start Free Trial
            </Link>
            <Link href="/contact" className="btn-secondary">
              Contact Us
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
