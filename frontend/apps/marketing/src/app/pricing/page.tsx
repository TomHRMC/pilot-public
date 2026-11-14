// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";
import { getSiteMode } from "../../lib/useSiteMode";
import PricingCardsSection from "../../components/PricingCardsSection";

export const metadata: Metadata = {
  title: "Pricing — Pilot for Trades",
  description:
    "Pilot for Trades: Starter at $59/month or Teams at $179/month. 14-day free trial, no credit card required. Voice AI quoting, offline mobile app, QuickBooks sync, and real-time job profitability for solo and small electrical contractors.",
  openGraph: {
    title: "Pricing | Pilot for Trades",
    description:
      "Starter at $59/month · Teams at $179/month. 14-day free trial. Voice AI, offline mobile, QuickBooks sync — everything included.",
    url: "https://pilotfortrades.com/pricing",
  },
};

/* ── Charter Mode data ─────────────────────────────────────────────────── */

const charterFeatures = [
  "Voice-to-quote AI — dictate a scope in 30 seconds",
  "NEC code calculations by voice",
  "iOS + Android app — works offline in basements",
  "GPS clock-in / clock-out + photo documentation",
  "Real-time job profitability tracking (ETC)",
  "Smart dispatch board with conflict detection",
  "Customer quotes, invoicing, and Stripe payments",
  "QuickBooks Online sync",
  "Google Calendar sync",
  "Customer SMS + automated appointment reminders",
  "Unlimited users — no per-seat charges",
  "120 Voice AI minutes + 200 SMS segments/month included",
];

const charterIncludedItems = [
  { icon: "🎙️", label: "120 Voice AI min/mo" },
  { icon: "💬", label: "200 SMS/mo" },
  { icon: "👥", label: "Unlimited users" },
  { icon: "📋", label: "Unlimited jobs" },
  { icon: "📱", label: "Offline mobile" },
  { icon: "🔄", label: "QuickBooks sync" },
];

const charterFaqs = [
  {
    q: "What's included at $49/month?",
    a: "Everything: voice AI quoting, NEC code calculations, offline mobile app, GPS clock-in, photo documentation, real-time job profitability, dispatch board, QuickBooks sync, Google Calendar sync, customer SMS, invoicing, and Stripe payments. 120 Voice AI minutes and 200 SMS segments are included. Unlimited users, unlimited jobs, unlimited invoices.",
  },
  {
    q: "Is there a free trial?",
    a: "We're doing something better than a trial. The first group of electricians who sign up get 90 days free — no credit card — in exchange for using it on real jobs and telling us what we get wrong. After that, you're locked at $49/month for as long as you stay continuously subscribed on the Charter plan. Cancel or upgrade to Teams and the rate is gone for good.",
  },
  {
    q: "What happens when I use more than 120 Voice AI minutes or 200 SMS texts?",
    a: "Usage beyond the included amounts is billed at usage-based rates. We'll notify you before any overage charges hit. For most electricians working a normal volume of jobs, the included amounts cover everything.",
  },
  {
    q: "Do I pay per user?",
    a: "Never. All plans include unlimited user accounts. Add apprentices, office staff, or a second truck — no extra charge.",
  },
  {
    q: "Will the price go up?",
    a: "For Charter Members, no — you're locked at $49/month for as long as you stay continuously subscribed on the Charter plan. If you cancel or upgrade to Teams, the Charter rate is permanently forfeited.",
  },
  {
    q: "Does it work on Android?",
    a: "Yes. iOS and Android both. The offline mode works the same on both — data syncs when you're back in signal, whether that's after a basement job or a rural service call.",
  },
  {
    q: "What's the QuickBooks sync like?",
    a: "Two-way, automatic, with built-in conflict resolution. If a customer or invoice changes on both sides, Pilot shows you exactly what changed and lets you pick the right version — no duplicate entries, no mystery data.",
  },
  {
    q: "I'm a plumber/HVAC contractor. Is this for me?",
    a: "Electrical is where we're focused right now — the NEC code assistant and default catalog are built around electrical work. Plumbing and HVAC support are coming. If you want to get in early for your trade, reach out — we're taking a small number of plumbing and HVAC contractors into the first group.",
  },
];

/* ── General Release data ────────────────────────────────────────────────── */

const generalFaqs = [
  {
    q: "Is there a free trial?",
    a: "Yes — 14 days free on your chosen plan (Starter or Teams limits), no credit card required. After 14 days, continue at $59/month (Starter) or $179/month (Teams), or cancel anytime before the trial ends. No surprises.",
  },
  {
    q: "What's a schedule lane?",
    a: "One parallel job row on your dispatch board. Assign any team member to any job in any lane. Starter includes 5 lanes (ideal for solo and small crews), Teams includes 20 lanes for growing multi-crew operations.",
  },
  {
    q: "Do I pay per user?",
    a: "Never. Both Starter and Teams include unlimited user accounts. Add apprentices, office staff, or multiple trucks — no extra charge per seat.",
  },
  {
    q: "What happens after the trial?",
    a: "After 14 days, you'll be prompted to choose your plan and add a payment method. If you don't add one, your account pauses — nothing is charged automatically.",
  },
  {
    q: "Can I switch plans later?",
    a: "Yes. You can upgrade from Starter to Teams at any time. The price difference is prorated for the remainder of your billing period.",
  },
  {
    q: "What happens if I use more than my included Voice AI minutes or SMS?",
    a: "Usage beyond included amounts is billed at usage-based rates. We notify you before any overage charges. Starter gets 90 minutes and 100 SMS; Teams gets 300 minutes and 500 SMS — enough for most operations.",
  },
  {
    q: "Does it work on Android?",
    a: "Yes. iOS and Android both. Offline mode works the same — data syncs when you're back in signal, whether after a basement job or a rural service call.",
  },
  {
    q: "What's the QuickBooks sync like?",
    a: "Two-way, automatic, with built-in conflict resolution. If a customer or invoice changes on both sides, Pilot shows exactly what changed and lets you pick the right version — no duplicate entries.",
  },
];

/* ── Shared Components ──────────────────────────────────────────────────── */

function FaqSection({ faqs }: { faqs: { q: string; a: string }[] }) {
  return (
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
          Questions? We{"'"}ve got answers.
        </h2>
        <div role="list">
          {faqs.map((faq) => (
            <details key={faq.q} className="faq-item" role="listitem">
              <summary className="faq-button cursor-pointer">
                <span>{faq.q}</span>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  className="shrink-0"
                  aria-hidden="true"
                  style={{ transition: "transform 0.2s" }}
                >
                  <path
                    d="M5 8l5 5 5-5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </summary>
              <div className="pb-4 pt-1">
                <p
                  className="text-base"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {faq.a}
                </p>
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── Charter Mode Pricing Page ─────────────────────────────────────────── */

function PricingPageCharter() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Home",
            item: "https://pilotfortrades.com",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Pricing",
            item: "https://pilotfortrades.com/pricing",
          },
        ],
      },
      {
        "@type": "FAQPage",
        mainEntity: charterFaqs.map((faq) => ({
          "@type": "Question",
          name: faq.q,
          acceptedAnswer: { "@type": "Answer", text: faq.a },
        })),
      },
      {
        "@type": "SoftwareApplication",
        name: "Pilot for Trades",
        applicationCategory: "BusinessApplication",
        operatingSystem: "iOS, Android, Web",
        offers: {
          "@type": "Offer",
          price: "49",
          priceCurrency: "USD",
          priceSpecification: {
            "@type": "UnitPriceSpecification",
            price: "49",
            priceCurrency: "USD",
            unitText: "MONTH",
          },
        },
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero section */}
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
            One price. Everything included.
          </h1>
          <p
            className="text-section-subtitle mb-0"
            style={{ color: "var(--neutral-600)" }}
          >
            $49/month for solo and small electrical contractors — unlimited
            users, voice AI, offline mobile, QuickBooks sync, and real-time job
            profitability.
          </p>
        </div>
      </section>

      {/* Single pricing card section */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-label="Pricing plan"
      >
        <div className="container-marketing">
          {/* Centered single card */}
          <div className="max-w-lg mx-auto card-pricing p-8 flex flex-col">
            <div className="mb-6">
              <h2
                className="text-xl font-bold mb-1"
                style={{ color: "var(--neutral-900)" }}
              >
                Everything Included
              </h2>
              <p
                className="text-sm mb-4"
                style={{ color: "var(--neutral-600)" }}
              >
                For solo and small electrical contractors
              </p>
              <div className="flex items-end gap-1 mb-1">
                <span
                  className="text-section-title font-bold"
                  style={{ color: "var(--neutral-900)" }}
                >
                  $49
                </span>
                <span
                  className="text-base mb-2"
                  style={{ color: "var(--neutral-600)" }}
                >
                  /month
                </span>
              </div>
              <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
                Everything included. Cancel anytime.
              </p>
            </div>

            <div className="flex-1 mb-8">
              <ul className="flex flex-col gap-3 list-none p-0 m-0">
                {charterFeatures.map((item) => (
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
                    <span
                      className="text-sm"
                      style={{ color: "var(--neutral-700)" }}
                    >
                      {item}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <Link href="/charter" className="btn-primary text-center">
              Be one of the first twelve
            </Link>

            <p
              className="text-xs text-center mt-4"
              style={{ color: "var(--neutral-400)" }}
            >
              More plans as we grow — for now, one price for everyone.
            </p>
          </div>

          {/* C-B13 — Charter callout banner */}
          <section
            aria-label="Charter program callout"
            className="max-w-2xl mx-auto mt-8 rounded-xl p-6 flex flex-col gap-4"
            style={{
              background: "var(--brand-50)",
              border: "var(--divider-thin) solid var(--brand-100)",
            }}
          >
            <h3
              className="text-base font-semibold"
              style={{ color: "var(--brand-800)" }}
            >
              Be one of the first twelve
            </h3>
            <p className="text-sm" style={{ color: "var(--brand-800)" }}>
              90 days free, then $49/month locked for as long as you stay.
            </p>
            <Link
              href="/charter"
              className="btn-primary self-start"
              style={{ padding: "0.75rem 1.5rem" }}
            >
              Join the Charter program →
            </Link>
          </section>
        </div>
      </section>

      {/* Included-at-a-glance strip */}
      <section
        className="py-12"
        style={{ background: "var(--surface-marketing-alt)" }}
        aria-label="What's included"
      >
        <div className="container-marketing">
          <div className="flex flex-wrap justify-center gap-6">
            {charterIncludedItems.map((item) => (
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

      <FaqSection faqs={charterFaqs} />

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
            The first group of electricians gets 90 days free, then $49/month
            locked for as long as they stay subscribed.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/charter" className="btn-primary">
              Be one of the first twelve
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

/* ── General Release Pricing Page ───────────────────────────────────────── */

function PricingPageGeneralRelease() {
  // C-B13: Corrected JSON-LD prices — Starter $59/mo, Teams $179/mo (monthly)
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Home",
            item: "https://pilotfortrades.com",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Pricing",
            item: "https://pilotfortrades.com/pricing",
          },
        ],
      },
      {
        "@type": "FAQPage",
        mainEntity: generalFaqs.map((faq) => ({
          "@type": "Question",
          name: faq.q,
          acceptedAnswer: { "@type": "Answer", text: faq.a },
        })),
      },
      {
        "@type": "SoftwareApplication",
        name: "Pilot for Trades",
        applicationCategory: "BusinessApplication",
        operatingSystem: "iOS, Android, Web",
        offers: [
          {
            "@type": "Offer",
            name: "Starter",
            price: "59",
            priceCurrency: "USD",
            priceSpecification: {
              "@type": "UnitPriceSpecification",
              price: "59",
              priceCurrency: "USD",
              unitText: "MONTH",
            },
          },
          {
            "@type": "Offer",
            name: "Teams",
            price: "179",
            priceCurrency: "USD",
            priceSpecification: {
              "@type": "UnitPriceSpecification",
              price: "179",
              priceCurrency: "USD",
              unitText: "MONTH",
            },
          },
        ],
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

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
            className="text-section-subtitle"
            style={{ color: "var(--neutral-600)" }}
          >
            14-day free trial on your chosen plan. No credit card required.
          </p>
        </div>
      </section>

      {/* C-B13: Pricing cards section (client component with toggle) */}
      <PricingCardsSection />

      <FaqSection faqs={generalFaqs} />

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

/* ── Default Export — mode-aware router ─────────────────────────────────── */

export default async function PricingPage() {
  const { isGeneralRelease } = await getSiteMode();
  return isGeneralRelease ? (
    <PricingPageGeneralRelease />
  ) : (
    <PricingPageCharter />
  );
}
