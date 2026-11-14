"use client";

import Link from "next/link";
import { useState } from "react";
import PricingToggle, { type BillingInterval } from "./PricingToggle";

/**
 * PricingCardsSection — C-B13 Part B
 *
 * Client component that wraps the PricingToggle + 2-column pricing cards
 * for the General Release pricing page. Manages the billing interval state
 * and displays the correct prices based on the toggle selection.
 *
 * Corrected prices (per Tom, confirmed 2026-08-07):
 *   Starter: $59/mo monthly, $49/mo annual ($588/yr)
 *   Teams:   $179/mo monthly, $149/mo annual ($1,788/yr)
 *
 * @see mkt-c-b13-design-spec.md (private design spec, not in the public snapshot) §2.2, §4.2, §8.2
 */

const PRICES = {
  starter: { monthly: 59, annual: 49, annualTotal: 588 },
  teams: { monthly: 179, annual: 149, annualTotal: 1788 },
} as const;

const starterFeatures = [
  "5 schedule lanes",
  "90 Voice AI min/month",
  "100 SMS segments/month",
  "Unlimited users",
  "Unlimited jobs & quotes",
  "Unlimited invoices",
  "Voice-to-quote AI (NEC-aware)",
  "Real-time job profitability",
  "Smart dispatch board",
  "QuickBooks Online sync",
  "Google Calendar sync",
  "Customer SMS + reminders",
  "iOS + Android, works offline",
  "Stripe payments",
];

const teamsFeatures = [
  "20 schedule lanes",
  "300 Voice AI min/month",
  "500 SMS segments/month",
  "Unlimited users",
  "Unlimited jobs & quotes",
  "Unlimited invoices",
  "Voice-to-quote AI (NEC-aware)",
  "Real-time job profitability",
  "Smart dispatch board",
  "QuickBooks Online sync",
  "Google Calendar sync",
  "Customer SMS + reminders",
  "iOS + Android, works offline",
  "Stripe payments",
  "Priority support",
  "Advanced analytics",
];

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-3 list-none p-0 m-0">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3">
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
          <span className="text-sm" style={{ color: "var(--neutral-700)" }}>
            {item}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function PricingCardsSection() {
  const [billing, setBilling] = useState<BillingInterval>("monthly");

  const starterPrice =
    billing === "monthly" ? PRICES.starter.monthly : PRICES.starter.annual;
  const starterSubtext =
    billing === "monthly"
      ? "or $49/mo billed annually"
      : `billed $${PRICES.starter.annualTotal}/year`;
  const teamsPrice =
    billing === "monthly" ? PRICES.teams.monthly : PRICES.teams.annual;
  const teamsSubtext =
    billing === "monthly"
      ? "or $149/mo billed annually"
      : `billed $${PRICES.teams.annualTotal}/year`;

  return (
    <section
      className="section-padding"
      style={{ background: "var(--white)" }}
      aria-label="Pricing plans"
    >
      <div className="container-marketing">
        <PricingToggle onToggle={setBilling} value={billing} />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Starter card */}
          <div
            className="rounded-2xl p-8 flex flex-col"
            style={{
              border: "var(--divider-thin) solid var(--neutral-200)",
              boxShadow: "var(--shadow-md)",
            }}
          >
            <div className="mb-6">
              <h2
                className="text-xl font-bold mb-1"
                style={{ color: "var(--neutral-900)" }}
              >
                Starter
              </h2>
              <p
                className="text-sm mb-4"
                style={{ color: "var(--neutral-600)" }}
              >
                For solo and small crews
              </p>
              <div className="flex items-end gap-1 mb-1">
                <span
                  className="pricing-price-text text-section-title font-bold"
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
              <p
                className="pricing-price-text text-sm"
                style={{ color: "var(--neutral-500)" }}
              >
                {starterSubtext}
              </p>
            </div>

            <Link href="/sign-up" className="btn-primary text-center mb-2">
              Start Free Trial
            </Link>
            <p
              className="text-xs text-center mb-6"
              style={{ color: "var(--neutral-400)" }}
            >
              14-day free trial · Starter limits · No credit card
            </p>

            <div className="flex-1">
              <FeatureList items={starterFeatures} />
            </div>
          </div>

          {/* Teams card — POPULAR */}
          <div
            className="rounded-2xl p-8 flex flex-col relative"
            style={{
              border: "var(--divider-thick) solid var(--brand-600)",
              boxShadow: "var(--shadow-xl)",
            }}
          >
            {/* Most Popular badge */}
            <div
              className="absolute top-0 right-0 text-xs font-bold px-4 py-2"
              style={{
                background: "var(--brand-600)",
                color: "var(--white)",
                borderRadius: "0 1rem 0 0.75rem",
              }}
              aria-label="Most popular plan"
            >
              ★ Most Popular
            </div>

            <div className="mb-6">
              <h2
                className="text-xl font-bold mb-1"
                style={{ color: "var(--neutral-900)" }}
              >
                Teams
              </h2>
              <p
                className="text-sm mb-4"
                style={{ color: "var(--neutral-600)" }}
              >
                For growing multi-crew ops
              </p>
              <div className="flex items-end gap-1 mb-1">
                <span
                  className="pricing-price-text text-section-title font-bold"
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
              <p
                className="pricing-price-text text-sm"
                style={{ color: "var(--neutral-500)" }}
              >
                {teamsSubtext}
              </p>
            </div>

            <Link href="/sign-up" className="btn-primary text-center mb-2">
              Start Free Trial
            </Link>
            <p
              className="text-xs text-center mb-6"
              style={{ color: "var(--neutral-400)" }}
            >
              14-day free trial · Teams limits · No credit card
            </p>

            <div className="flex-1">
              <FeatureList items={teamsFeatures} />
            </div>
          </div>
        </div>

        {/* Schedule Lane callout banner */}
        <div
          className="max-w-4xl mx-auto mt-10 rounded-xl p-6 flex items-start gap-4"
          style={{
            background: "var(--brand-50)",
            border: "var(--divider-thin) solid var(--brand-100)",
          }}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            className="shrink-0 mt-0.5"
            aria-hidden="true"
          >
            <rect
              x="3"
              y="4"
              width="18"
              height="18"
              rx="2"
              stroke="var(--brand-600)"
              strokeWidth="2"
            />
            <line
              x1="16"
              y1="2"
              x2="16"
              y2="6"
              stroke="var(--brand-600)"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <line
              x1="8"
              y1="2"
              x2="8"
              y2="6"
              stroke="var(--brand-600)"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <line
              x1="3"
              y1="10"
              x2="21"
              y2="10"
              stroke="var(--brand-600)"
              strokeWidth="2"
            />
          </svg>
          <div>
            <p
              className="text-sm font-semibold mb-1"
              style={{ color: "var(--brand-800)" }}
            >
              What{"'"}s a schedule lane?
            </p>
            <p className="text-sm" style={{ color: "var(--brand-800)" }}>
              It{"'"}s one parallel job row on your dispatch board. Assign any
              team member to any job in any lane. No extra charge per lane —
              just choose the tier that fits your crew size.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
