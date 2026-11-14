// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
// EARLY TIER CONCEPT — superseded by /pricing ($59/$179 monthly, $49/$149 billed
// annually, unlimited users). Not linked from the site; disallowed in robots.ts.
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Pricing Preview (In Development)",
  description:
    "Feature-differentiated pricing comparison for Pilot for Trades — in development. Current live pricing is at /pricing.",
  robots: { index: false, follow: false },
};

/* ─── Feature comparison matrix data ────────────────── */

interface MatrixFeature {
  name: string;
  starter: string | boolean;
  professional: string | boolean;
  enterprise: string | boolean;
}

interface MatrixCategory {
  name: string;
  features: MatrixFeature[];
}

const matrixData: MatrixCategory[] = [
  {
    name: "Voice AI",
    features: [
      {
        name: "Voice AI Quoting",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Multi-turn Conversations",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "NEC Code References",
        starter: true,
        professional: true,
        enterprise: true,
      },
    ],
  },
  {
    name: "Quoting",
    features: [
      {
        name: "Quote Creation",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Real-Time Material Pricing",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Template Library",
        starter: "10 templates",
        professional: "Unlimited",
        enterprise: "Unlimited",
      },
      {
        name: "Digital Acceptance",
        starter: true,
        professional: true,
        enterprise: true,
      },
    ],
  },
  {
    name: "Dispatch",
    features: [
      {
        name: "Dispatch Board",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Calendar Sync",
        starter: "1 calendar",
        professional: "Multi-calendar",
        enterprise: "Multi-calendar",
      },
      {
        name: "Drive Time Routing",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Conflict Detection",
        starter: true,
        professional: true,
        enterprise: true,
      },
    ],
  },
  {
    name: "Communications",
    features: [
      {
        name: "Customer SMS",
        starter: "100/mo",
        professional: "500/mo",
        enterprise: "Unlimited",
      },
      {
        name: "Email Notifications",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Voice-to-Text Replies",
        starter: true,
        professional: true,
        enterprise: true,
      },
    ],
  },
  {
    name: "Integrations",
    features: [
      {
        name: "QuickBooks Online Sync",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Stripe Payments",
        starter: true,
        professional: true,
        enterprise: true,
      },
    ],
  },
  {
    name: "Support",
    features: [
      {
        name: "In-App AI Help",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Email Support",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Priority Support",
        starter: false,
        professional: true,
        enterprise: true,
      },
      {
        name: "Dedicated Onboarding",
        starter: false,
        professional: false,
        enterprise: true,
      },
    ],
  },
  {
    name: "Team",
    features: [
      {
        name: "Users Included",
        starter: "Up to 5",
        professional: "Up to 15",
        enterprise: "50+",
      },
      {
        name: "Role-Based Permissions",
        starter: true,
        professional: true,
        enterprise: true,
      },
      {
        name: "Multi-Location",
        starter: false,
        professional: true,
        enterprise: true,
      },
    ],
  },
];

/* ─── Cell value renderer ────────────────────────────── */

function CellValue({ value }: { value: string | boolean }) {
  if (value === true) {
    return (
      <span
        className="inline-flex items-center justify-center"
        aria-label="Included"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" fill="var(--margin-50)" />
          <path
            d="M7 12l3.5 3.5L17 9"
            stroke="var(--margin-600)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    );
  }
  if (value === false) {
    return (
      <span
        className="inline-flex items-center justify-center"
        aria-label="Not included"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M5 12h14"
            stroke="var(--neutral-300)"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </span>
    );
  }
  return (
    <span
      className="text-sm font-medium"
      style={{ color: "var(--neutral-700)" }}
    >
      {value}
    </span>
  );
}

/* ─── FeatureList (reused from pricing page) ─────────── */

const starterFeatures = [
  "Voice AI Quoting",
  "Real-Time Profitability Tracking",
  "Smart Dispatch Board",
  "Customer SMS (100 messages/mo)",
  "Invoicing & Stripe Payments",
  "QuickBooks Online Sync",
  "Mobile + Offline Mode",
  "AI Help System",
];

const professionalFeatures = [
  "Everything in Starter",
  "500 SMS messages/mo",
  "Multi-calendar sync",
  "Priority support",
  "Advanced reporting",
  "Custom quote templates",
];

const enterpriseFeatures = [
  "Everything in Professional",
  "Unlimited SMS",
  "Custom onboarding",
  "Dedicated account manager",
  "SLA guarantee",
  "Custom integrations",
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

/* ─── Page ───────────────────────────────────────────── */

export default function PricingPreviewPage() {
  return (
    <>
      {/* Dev banner */}
      <div
        className="sticky top-16 z-30 border-b text-sm font-medium text-center py-3 px-4"
        style={{
          background: "var(--alert-50)",
          borderColor: "var(--alert-400)",
          color: "var(--neutral-800)",
        }}
      >
        ⚠️ This page is in development. Pricing and feature breakdown are not
        final.{" "}
        <Link
          href="/pricing"
          style={{ color: "var(--brand-600)", textDecoration: "underline" }}
        >
          See current live pricing →
        </Link>
      </div>

      {/* Hero zone */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="pricing-preview-heading"
      >
        <div className="container-marketing text-center">
          <h1
            id="pricing-preview-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            Pricing Preview
          </h1>
          <p
            className="text-section-subtitle mb-8 max-w-2xl mx-auto"
            style={{ color: "var(--neutral-600)" }}
          >
            Feature-differentiated pricing — in development. Current live
            pricing at{" "}
            <Link href="/pricing" style={{ color: "var(--brand-600)" }}>
              /pricing
            </Link>
            .
          </p>
          <div
            className="max-w-2xl mx-auto rounded-xl p-6 text-left"
            style={{
              border: "var(--divider-thin) solid var(--brand-200)",
              background: "var(--brand-50)",
            }}
          >
            <p className="text-base" style={{ color: "var(--neutral-800)" }}>
              <strong>The math is simple.</strong> Pilot saves 15+ hours/week —
              that&apos;s $750+ at $50/hour. It prevents $1,500–$4,000 in losses
              per job from underquoting. The tool pays for itself before your
              first invoice.
            </p>
          </div>
        </div>
      </section>

      {/* Pricing cards */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-label="Pricing tiers"
      >
        <div className="container-marketing">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Starter */}
            <div className="card-pricing p-8 flex flex-col">
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
                  For solo and small-team contractors
                </p>
                <div className="flex items-end gap-1 mb-1">
                  <span
                    className="text-section-title font-bold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    $149
                  </span>
                  <span
                    className="text-base mb-2"
                    style={{ color: "var(--neutral-600)" }}
                  >
                    /month
                  </span>
                </div>
                <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
                  Up to 5 users
                </p>
              </div>
              <div className="flex-1 mb-8">
                <FeatureList items={starterFeatures} />
              </div>
              <Link href="/charter" className="btn-primary text-center">
                Be One of the First
              </Link>
            </div>

            {/* Professional (featured) */}
            <div
              className="card-pricing p-8 flex flex-col relative"
              style={{
                outline: "var(--outline-thick) solid var(--brand-600)",
                outlineOffset: "var(--divider-thin-neg)",
              }}
            >
              <div
                className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-semibold"
                style={{
                  background: "var(--brand-600)",
                  color: "var(--white)",
                }}
              >
                Most Popular
              </div>
              <div className="mb-6 pt-2">
                <h2
                  className="text-xl font-bold mb-1"
                  style={{ color: "var(--neutral-900)" }}
                >
                  Professional
                </h2>
                <p
                  className="text-sm mb-4"
                  style={{ color: "var(--neutral-600)" }}
                >
                  For growing teams ready to scale
                </p>
                <div className="flex items-end gap-1 mb-1">
                  <span
                    className="text-section-title font-bold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    Coming Soon
                  </span>
                </div>
                <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
                  Up to 15 users
                </p>
              </div>
              <div className="flex-1 mb-8">
                <FeatureList items={professionalFeatures} />
              </div>
              <Link href="/charter" className="btn-primary text-center">
                Be One of the First
              </Link>
            </div>

            {/* Enterprise */}
            <div className="card-pricing p-8 flex flex-col">
              <div className="mb-6">
                <h2
                  className="text-xl font-bold mb-1"
                  style={{ color: "var(--neutral-900)" }}
                >
                  Enterprise
                </h2>
                <p
                  className="text-sm mb-4"
                  style={{ color: "var(--neutral-600)" }}
                >
                  For large operations with custom needs
                </p>
                <div className="flex items-end gap-1 mb-1">
                  <span
                    className="text-section-title font-bold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    Custom
                  </span>
                </div>
                <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
                  50+ users
                </p>
              </div>
              <div className="flex-1 mb-8">
                <FeatureList items={enterpriseFeatures} />
              </div>
              <Link href="/contact" className="btn-secondary text-center">
                Contact Us
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Comparison Matrix */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="matrix-heading"
      >
        <div className="container-marketing">
          <h2
            id="matrix-heading"
            className="text-section-title text-center mb-12"
            style={{ color: "var(--neutral-900)" }}
          >
            Full Feature Comparison
          </h2>

          <div
            className="overflow-x-auto rounded-2xl"
            style={{
              border: "var(--divider-thin) solid var(--neutral-200)",
              boxShadow: "var(--shadow-md)",
            }}
          >
            <table
              className="w-full border-collapse"
              style={{ minWidth: "var(--width-xl)" }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom:
                      "var(--divider-thin) solid var(--neutral-200)",
                  }}
                >
                  <th
                    className="text-left py-6 px-6 text-sm font-semibold sticky left-0 z-10"
                    style={{
                      background: "var(--neutral-50)",
                      color: "var(--neutral-700)",
                      minWidth: "var(--width-lg)",
                    }}
                  >
                    Feature
                  </th>
                  <th
                    className="text-center py-6 px-4 text-sm font-semibold"
                    style={{
                      background: "var(--neutral-50)",
                      color: "var(--neutral-700)",
                      minWidth: "var(--width-sm)",
                    }}
                  >
                    <div>Starter</div>
                    <div
                      className="text-base font-bold"
                      style={{ color: "var(--neutral-900)" }}
                    >
                      $149/mo
                    </div>
                  </th>
                  <th
                    className="text-center py-6 px-4 text-sm font-semibold relative"
                    style={{
                      background: "var(--brand-50)",
                      color: "var(--neutral-700)",
                      outline: "var(--outline-thick) solid var(--brand-500)",
                      minWidth: "var(--width-md)",
                    }}
                  >
                    <div
                      className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-xs font-semibold"
                      style={{
                        background: "var(--brand-600)",
                        color: "var(--white)",
                      }}
                    >
                      Most Popular
                    </div>
                    <div>Professional</div>
                    <div
                      className="text-base font-bold"
                      style={{ color: "var(--neutral-900)" }}
                    >
                      TBD/mo
                    </div>
                  </th>
                  <th
                    className="text-center py-6 px-4 text-sm font-semibold"
                    style={{
                      background: "var(--neutral-50)",
                      color: "var(--neutral-700)",
                      minWidth: "var(--width-sm)",
                    }}
                  >
                    <div>Enterprise</div>
                    <div
                      className="text-base font-bold"
                      style={{ color: "var(--neutral-900)" }}
                    >
                      Custom
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {matrixData.map((category) => (
                  <>
                    {/* Category row */}
                    <tr
                      key={`cat-${category.name}`}
                      style={{ background: "var(--neutral-50)" }}
                    >
                      <td
                        colSpan={4}
                        className="py-3 px-6 text-xs font-semibold uppercase tracking-wider"
                        style={{ color: "var(--neutral-500)" }}
                      >
                        {category.name}
                      </td>
                    </tr>

                    {/* Feature rows */}
                    {category.features.map((feat) => (
                      <tr
                        key={feat.name}
                        style={{
                          borderBottom:
                            "var(--divider-thin) solid var(--neutral-100)",
                          background: "var(--white)",
                        }}
                        className="hover:bg-neutral-50 transition-colors"
                      >
                        <td
                          className="py-4 px-6 text-sm sticky left-0 z-10"
                          style={{
                            color: "var(--neutral-700)",
                            background: "var(--white)",
                          }}
                        >
                          {feat.name}
                        </td>
                        <td className="py-4 px-4 text-center">
                          <CellValue value={feat.starter} />
                        </td>
                        <td
                          className="py-4 px-4 text-center"
                          style={{ background: "var(--brand-600-03)" }}
                        >
                          <CellValue value={feat.professional} />
                        </td>
                        <td className="py-4 px-4 text-center">
                          <CellValue value={feat.enterprise} />
                        </td>
                      </tr>
                    ))}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section
        className="section-padding"
        style={{ background: "var(--brand-600)" }}
        aria-labelledby="pricing-preview-cta"
      >
        <div className="container-marketing text-center max-w-2xl mx-auto">
          <h2
            id="pricing-preview-cta"
            className="text-section-title mb-4"
            style={{ color: "var(--white)" }}
          >
            Ready to get started?
          </h2>
          <p className="text-body-lg mb-8" style={{ color: "var(--white-82)" }}>
            Start with the Starter plan — 14-day free trial, no credit card
            required.
          </p>
          <Link href="/charter" className="btn-white">
            Be One of the First
          </Link>
        </div>
      </section>
    </>
  );
}
