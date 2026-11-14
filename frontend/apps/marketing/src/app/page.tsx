// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";
import { getSiteMode } from "../lib/useSiteMode";

export const metadata: Metadata = {
  title:
    "Pilot for Trades — AI Voice Quoting & Field Operations for Contractors",
  description:
    "Pilot for Trades: Voice AI quoting and real-time job profitability for solo and small electrical contractors. Know your margin on every job. $49/month, everything included.",
  openGraph: {
    title:
      "Pilot for Trades — AI Voice Quoting & Field Operations for Contractors",
    description:
      "Voice AI quoting and real-time job profitability for solo electricians. $49/month, everything included.",
    url: "https://pilotfortrades.com",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://pilotfortrades.com/#org",
      name: "Pilot for Trades",
      url: "https://pilotfortrades.com",
      logo: "https://pilotfortrades.com/brand/logo-primary.svg",
      contactPoint: {
        "@type": "ContactPoint",
        email: "info@pilotfortrades.com",
        contactType: "customer support",
      },
    },
    {
      "@type": "WebSite",
      "@id": "https://pilotfortrades.com/#website",
      url: "https://pilotfortrades.com",
      name: "Pilot for Trades",
      publisher: { "@id": "https://pilotfortrades.com/#org" },
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
          billingDuration: "P1M",
        },
      },
      description:
        "AI-powered voice quoting, dispatch, invoicing, and profitability tracking for electrical, plumbing, and HVAC contractors.",
    },
  ],
};

export default async function HomePage() {
  const { isGeneralRelease } = await getSiteMode();

  const ctaText = isGeneralRelease
    ? "Start Free Trial"
    : "Be one of the first twelve";
  const ctaHref = isGeneralRelease ? "/sign-up" : "/charter";

  const bottomBodyCopy = isGeneralRelease
    ? "Start your 14-day free trial today. No credit card required. Voice quoting, live margins, and smart dispatch — try it on a real job."
    : "Join contractors who are done with spreadsheet estimates, stale pricing, and flying blind on job profitability. Pilot gives you the tools — voice quoting, live margins, and smart dispatch — in one platform.";

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ── Section 1: Hero ── */}
      <section
        className="hero-gradient hero-padding"
        style={{ paddingTop: "clamp(3.5rem, 5.5vw, 5.5rem)" }}
        aria-labelledby="hero-heading"
      >
        <div className="container-marketing">
          <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
            {/* Text column */}
            <div className="flex-1 max-w-2xl">
              {/* Badge */}
              <div className="inline-block mb-6">
                <span
                  className="text-caption-lg font-medium px-4 py-1 rounded-full"
                  style={{
                    background: "var(--white-15)",
                    color: "var(--white)",
                  }}
                >
                  AI-Powered Field Operations Software
                </span>
              </div>

              <h1
                id="hero-heading"
                className="text-hero mb-6"
                style={{ color: "var(--white)" }}
              >
                Build Quotes by Voice. Know Your Margin on Every Job.
              </h1>

              <p
                className="text-section-subtitle mb-8"
                style={{ color: "var(--white-8)" }}
              >
                The AI-powered platform that handles quoting, dispatch, and
                profitability tracking — so solo electricians can focus on
                billable work, not paperwork at 9 PM.
              </p>

              {/* Trade selector pills */}
              <div
                className="flex flex-wrap gap-2 mb-8"
                role="list"
                aria-label="Supported trades"
              >
                {/* Electrical — active */}
                <span
                  role="listitem"
                  className="px-4 py-1 rounded-full text-sm font-medium cursor-default"
                  style={{
                    background: "var(--white-1)",
                    color: "var(--white)",
                    border: "var(--border-white-20)",
                  }}
                >
                  ⚡ Electrical
                </span>

                {/* Plumbing — muted, Coming Soon */}
                <span
                  role="listitem"
                  className="px-4 py-1 rounded-full text-sm font-medium cursor-default"
                  style={{
                    background: "var(--white-05)",
                    color: "var(--white-55)",
                    border: "var(--border-white-12)",
                  }}
                >
                  💧 Plumbing — Coming Soon
                </span>

                {/* HVAC — muted, Coming Soon */}
                <span
                  role="listitem"
                  className="px-4 py-1 rounded-full text-sm font-medium cursor-default"
                  style={{
                    background: "var(--white-05)",
                    color: "var(--white-55)",
                    border: "var(--border-white-12)",
                  }}
                >
                  ❄️ HVAC — Coming Soon
                </span>
              </div>

              {/* CTA buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Link href={ctaHref} className="btn-primary">
                  {ctaText}
                </Link>
                <Link
                  href="/features#voice-ai"
                  className="text-base font-semibold no-underline flex items-center gap-2"
                  style={{ color: "var(--white-8)" }}
                >
                  See How It Works →
                </Link>
              </div>

              {/* General Release: subtext below CTA buttons */}
              {isGeneralRelease && (
                <p
                  className="mt-3"
                  style={{
                    color: "var(--white-7)",
                    fontSize: "var(--text-caption-lg)",
                    lineHeight: "var(--lh-caption-lg)",
                  }}
                >
                  14-day free trial · No credit card required
                </p>
              )}
            </div>

            {/* Illustration column */}
            <div
              className="flex-1 max-w-lg w-full hidden lg:flex items-center justify-center"
              aria-hidden="true"
            >
              <div
                className="w-full aspect-[4/3] rounded-2xl flex items-center justify-center"
                style={{
                  background: "var(--white-08)",
                  border: "var(--border-white-12)",
                }}
              >
                {/* Hero illustration — mobile voice quoting */}
                <svg
                  viewBox="0 0 400 300"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-full h-full p-8"
                  aria-hidden="true"
                >
                  {/* Phone device */}
                  <rect
                    x="155"
                    y="30"
                    width="90"
                    height="160"
                    rx="14"
                    stroke="var(--brand-200)"
                    strokeWidth="2"
                    fill="var(--white-05)"
                  />
                  <rect
                    x="162"
                    y="42"
                    width="76"
                    height="116"
                    rx="6"
                    fill="var(--white-08)"
                  />

                  {/* Waveform bars inside screen */}
                  <rect
                    x="174"
                    y="88"
                    width="8"
                    height="24"
                    rx="4"
                    fill="var(--brand-600)"
                    opacity="0.8"
                  />
                  <rect
                    x="186"
                    y="78"
                    width="8"
                    height="44"
                    rx="4"
                    fill="var(--brand-600)"
                  />
                  <rect
                    x="198"
                    y="84"
                    width="8"
                    height="32"
                    rx="4"
                    fill="var(--brand-600)"
                    opacity="0.9"
                  />
                  <rect
                    x="210"
                    y="72"
                    width="8"
                    height="56"
                    rx="4"
                    fill="var(--brand-600)"
                  />
                  <rect
                    x="222"
                    y="86"
                    width="8"
                    height="28"
                    rx="4"
                    fill="var(--brand-600)"
                    opacity="0.8"
                  />

                  {/* Mic dot below waveform */}
                  <circle
                    cx="200"
                    cy="140"
                    r="8"
                    stroke="white"
                    strokeWidth="1.5"
                    fill="var(--white-05)"
                  />
                  <circle cx="200" cy="140" r="3" fill="white" opacity="0.7" />

                  {/* Phone home indicator */}
                  <rect
                    x="185"
                    y="178"
                    width="30"
                    height="4"
                    rx="2"
                    fill="var(--brand-200)"
                    opacity="0.5"
                  />

                  {/* Floating card 1 — top right: Quote Ready */}
                  <rect
                    x="265"
                    y="45"
                    width="110"
                    height="52"
                    rx="10"
                    fill="var(--white-1)"
                    stroke="var(--brand-200)"
                    strokeOpacity="0.3"
                    strokeWidth="1"
                  />
                  <text
                    x="275"
                    y="65"
                    fontSize="18"
                    fontWeight="700"
                    fill="white"
                  >
                    $4,250
                  </text>
                  <text x="275" y="83" fontSize="11" fill="white" opacity="0.7">
                    Quote Ready
                  </text>

                  {/* Floating card 2 — bottom left: Job status */}
                  <rect
                    x="25"
                    y="175"
                    width="110"
                    height="52"
                    rx="10"
                    fill="var(--white-1)"
                    stroke="var(--brand-200)"
                    strokeOpacity="0.3"
                    strokeWidth="1"
                  />
                  <text x="35" y="196" fontSize="12" fill="white" opacity="0.7">
                    ⚡ Job #47
                  </text>
                  <text
                    x="35"
                    y="214"
                    fontSize="11"
                    fontWeight="600"
                    fill="white"
                  >
                    In Progress
                  </text>

                  {/* Floating card 3 — bottom right: Margin */}
                  <rect
                    x="265"
                    y="200"
                    width="110"
                    height="52"
                    rx="10"
                    fill="var(--white-1)"
                    stroke="var(--brand-200)"
                    strokeOpacity="0.3"
                    strokeWidth="1"
                  />
                  <text
                    x="275"
                    y="221"
                    fontSize="18"
                    fontWeight="700"
                    fill="var(--brand-200)"
                  >
                    ↑ 34%
                  </text>
                  <text
                    x="275"
                    y="239"
                    fontSize="11"
                    fill="white"
                    opacity="0.7"
                  >
                    Margin
                  </text>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 2: Social Proof Bar ── */}
      <section
        className="py-10"
        style={{
          background: "var(--white)",
          borderBottom: "var(--divider-thin) solid var(--neutral-100)",
        }}
        aria-label="Trust indicators"
      >
        <div className="container-marketing">
          <p
            className="text-sm uppercase tracking-wider text-center mb-8"
            style={{ color: "var(--neutral-400)" }}
          >
            Built for contractors across the trades
          </p>
          <div className="flex flex-wrap items-center justify-center gap-8">
            {[
              { icon: "⚡", label: "Built for the field" },
              { icon: "🔒", label: "Security-first design" },
              { icon: "📱", label: "Mobile-first" },
              { icon: "🎙️", label: "Voice-first AI" },
            ].map((b) => (
              <div key={b.label} className="flex items-center gap-2">
                <span className="text-xl">{b.icon}</span>
                <span
                  className="text-sm font-medium"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {b.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 3: Pain Points ── */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="pain-heading"
      >
        <div className="container-marketing">
          <div className="text-center mb-14">
            <h2
              id="pain-heading"
              className="text-section-title mb-4"
              style={{ color: "var(--neutral-900)" }}
            >
              You Didn&apos;t Start a Business to Do Paperwork Until Midnight
            </h2>
            <p
              className="text-section-subtitle max-w-2xl mx-auto"
              style={{ color: "var(--neutral-600)" }}
            >
              The average contractor spends 15+ hours a week on admin — and
              still doesn&apos;t know if last week&apos;s jobs were profitable.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: (
                  <svg
                    width="40"
                    height="40"
                    viewBox="0 0 40 40"
                    fill="none"
                    aria-hidden="true"
                  >
                    <circle
                      cx="20"
                      cy="20"
                      r="18"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                    />
                    <path
                      d="M20 12v8l4 4"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ),
                stat: "15+ hours/week",
                desc: "Lost to quoting, invoicing, and chasing payments instead of doing billable work.",
              },
              {
                icon: (
                  <svg
                    width="40"
                    height="40"
                    viewBox="0 0 40 40"
                    fill="none"
                    aria-hidden="true"
                  >
                    <rect
                      x="4"
                      y="8"
                      width="32"
                      height="24"
                      rx="3"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                    />
                    <path
                      d="M13 20h14M17 15h6M17 25h6"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                ),
                stat: "Thousands per job",
                desc: "What margin can leak away through stale material pricing, untracked expenses, and underquoted change orders.",
              },
              {
                icon: (
                  <svg
                    width="40"
                    height="40"
                    viewBox="0 0 40 40"
                    fill="none"
                    aria-hidden="true"
                  >
                    <circle
                      cx="20"
                      cy="20"
                      r="18"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                    />
                    <path
                      d="M14 14l12 12M26 14L14 26"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                ),
                stat: "3 weeks late",
                desc: "That's how long it takes most contractors to discover a job lost money. By then, you've quoted 10 more the same way.",
              },
            ].map((item) => (
              <div
                key={item.stat}
                className="bg-white rounded-xl p-8"
                style={{ boxShadow: "var(--shadow-sm)" }}
              >
                <div className="mb-4">{item.icon}</div>
                <p
                  className="text-section-title font-bold mb-2"
                  style={{ color: "var(--brand-600)" }}
                >
                  {item.stat}
                </p>
                <p
                  className="text-body-lg"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 4: Feature Highlights ── */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-labelledby="features-heading"
      >
        <div className="container-marketing">
          <div className="text-center mb-14">
            <h2
              id="features-heading"
              className="text-section-title mb-4"
              style={{ color: "var(--neutral-900)" }}
            >
              Four Tools That Replace a Dozen Apps
            </h2>
            <p
              className="text-section-subtitle max-w-2xl mx-auto"
              style={{ color: "var(--neutral-600)" }}
            >
              Everything you need to run your trade business — quoting,
              dispatch, profitability, and customer comms — in one platform that
              works by voice.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
            {[
              {
                icon: (
                  <svg
                    width="32"
                    height="32"
                    viewBox="0 0 32 32"
                    fill="none"
                    aria-hidden="true"
                  >
                    <rect
                      x="11"
                      y="4"
                      width="10"
                      height="16"
                      rx="5"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                    />
                    <path
                      d="M7 18c0 4.971 4.029 9 9 9s9-4.029 9-9M16 27v3"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                ),
                title: "Voice AI Quoting",
                desc: "Describe the job in plain trade language. Pilot builds the estimate — materials at today's prices, labor at your rates, markup applied — in under 60 seconds. Works on-site, in the truck, or between jobs.",
                href: "/features#voice-ai",
              },
              {
                icon: (
                  <svg
                    width="32"
                    height="32"
                    viewBox="0 0 32 32"
                    fill="none"
                    aria-hidden="true"
                  >
                    <polyline
                      points="4,24 12,14 18,18 26,8"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M26 8h-6M26 8v6"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                ),
                title: "Real-Time Profitability",
                desc: "Track costs against the quoted price as the job happens — not three weeks later when you reconcile invoices. See your margin on every job, every day, from your phone.",
                href: "/features#profitability",
              },
              {
                icon: (
                  <svg
                    width="32"
                    height="32"
                    viewBox="0 0 32 32"
                    fill="none"
                    aria-hidden="true"
                  >
                    <rect
                      x="4"
                      y="6"
                      width="24"
                      height="22"
                      rx="3"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                    />
                    <path
                      d="M10 6V3M22 6V3M4 14h24"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                ),
                title: "Smart Dispatch Board",
                desc: "See your whole week at a glance. Drag to reschedule, detect conflicts before they become callbacks, and route techs with drive-time estimates. Built for seasonal surges and emergency calls.",
                href: "/features#dispatch",
              },
              {
                icon: (
                  <svg
                    width="32"
                    height="32"
                    viewBox="0 0 32 32"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M4 6h18a2 2 0 012 2v14a2 2 0 01-2 2H4V6z"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                    />
                    <path
                      d="M24 10l4 2v8l-4 2"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M9 14h10M9 18h6"
                      stroke="var(--brand-600)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                ),
                title: "Customer Communications",
                desc: "Automated appointment reminders, on-my-way texts, and invoice notifications — all previewed before they send. Your customers stay informed without you picking up the phone.",
                href: "/features#communications",
              },
            ].map((f) => (
              <div
                key={f.title}
                className="p-6 rounded-xl border transition-all"
                style={{
                  background: "var(--neutral-50)",
                  borderColor: "var(--neutral-200)",
                }}
              >
                <div className="mb-4">{f.icon}</div>
                <h3
                  className="text-xl font-semibold mb-2"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {f.title}
                </h3>
                <p
                  className="text-base mb-4"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {f.desc}
                </p>
                <Link
                  href={f.href}
                  className="text-sm font-medium no-underline"
                  style={{ color: "var(--brand-600)" }}
                >
                  Learn more →
                </Link>
              </div>
            ))}
          </div>

          <div className="text-center">
            <Link
              href="/features"
              className="text-base font-semibold no-underline"
              style={{ color: "var(--brand-600)" }}
            >
              See All Features →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Section 5: How It Works ── */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing-alt)" }}
        aria-labelledby="how-heading"
      >
        <div className="container-marketing">
          <div className="text-center mb-14">
            <h2
              id="how-heading"
              className="text-section-title mb-4"
              style={{ color: "var(--neutral-900)" }}
            >
              From Voice to Invoice in Three Steps
            </h2>
            <p
              className="text-section-subtitle"
              style={{ color: "var(--neutral-600)" }}
            >
              No training required. No learning curve. Just talk.
            </p>
          </div>

          <div className="relative">
            {/* Desktop connector line */}
            <div
              className="hidden md:block absolute top-8 left-1/4 right-1/4 h-0.5"
              style={{
                borderTop: "var(--divider-thick) dashed var(--brand-200)",
              }}
              aria-hidden="true"
            />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-10 relative z-10">
              {[
                {
                  num: "1",
                  title: "Speak Your Quote",
                  desc: "Walk the job site and describe what you see. \u201C200-amp panel upgrade, 30 circuits, need a permit pull.\u201D Pilot listens.",
                },
                {
                  num: "2",
                  title: "AI Builds the Estimate",
                  desc: "Pilot calculates materials at current prices, applies your markup, adds labor hours, and generates a professional quote — in under a minute.",
                },
                {
                  num: "3",
                  title: "Send, Schedule & Track",
                  desc: "Send the quote to your customer, schedule the job on your dispatch board, and track profitability in real time from start to invoice.",
                },
              ].map((step) => (
                <div
                  key={step.num}
                  className="flex flex-col items-center text-center"
                >
                  <div
                    className="w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl font-bold mb-6"
                    style={{ background: "var(--brand-600)" }}
                    aria-label={`Step ${step.num}`}
                  >
                    {step.num}
                  </div>
                  <h3
                    className="text-lg font-semibold mb-3"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    {step.title}
                  </h3>
                  <p
                    className="text-base"
                    style={{ color: "var(--neutral-600)" }}
                  >
                    {step.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 6: Trade Callouts ── */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-labelledby="trades-heading"
      >
        <div className="container-marketing">
          <div className="text-center mb-14">
            <h2
              id="trades-heading"
              className="text-section-title mb-4"
              style={{ color: "var(--neutral-900)" }}
            >
              Built for Your Trade
            </h2>
            <p
              className="text-section-subtitle"
              style={{ color: "var(--neutral-600)" }}
            >
              Pilot speaks your language — whether it&apos;s ampacity, pipe
              sizing, or BTU calculations.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            {[
              {
                color: "var(--trade-electrical)",
                emoji: "⚡",
                title: "For Electricians",
                desc: "NEC-aware quoting, voltage drop calculations, panel upgrade templates, and wire sizing — by voice.",
                href: "/trades/electrical",
              },
              {
                color: "var(--trade-plumbing)",
                emoji: "💧",
                title: "For Plumbers",
                desc: "Fixture catalogs, pipe sizing references, real-time material pricing, and emergency dispatch — built in.",
                href: "/trades/plumbing",
              },
              {
                color: "var(--trade-hvac)",
                emoji: "❄️",
                title: "For HVAC Techs",
                desc: "Load calculations, refrigerant pricing, equipment specs, and seasonal scheduling — all from your phone.",
                href: "/trades/hvac",
              },
            ].map((t) => (
              <div
                key={t.title}
                className="rounded-xl overflow-hidden border"
                style={{
                  borderColor: "var(--neutral-200)",
                  background: "var(--white)",
                }}
              >
                {/* Trade accent top bar */}
                <div
                  className="h-1.5"
                  style={{ background: t.color }}
                  aria-hidden="true"
                />
                <div className="p-6">
                  <span className="text-3xl mb-4 block" aria-hidden="true">
                    {t.emoji}
                  </span>
                  <h3
                    className="text-xl font-semibold mb-3"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    {t.title}
                  </h3>
                  <p
                    className="text-base mb-4"
                    style={{ color: "var(--neutral-600)" }}
                  >
                    {t.desc}
                  </p>
                  <Link
                    href={t.href}
                    className="text-sm font-medium no-underline"
                    style={{ color: "var(--brand-600)" }}
                  >
                    Learn More →
                  </Link>
                </div>
              </div>
            ))}
          </div>

          <div className="text-center">
            <Link
              href="/trades/electrical"
              className="text-base font-semibold no-underline"
              style={{ color: "var(--brand-600)" }}
            >
              See How Pilot Works for Your Trade →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Section 7: Testimonials ── */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="testimonials-heading"
      >
        <div className="container-marketing">
          <h2
            id="testimonials-heading"
            className="text-section-title mb-14"
            style={{ color: "var(--neutral-900)" }}
          >
            What Contractors Will Say (placeholder)
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              // PLACEHOLDER COPY — illustrative only. Pilot for Trades was never
              // released; these are not real customers and no customer quotes exist.
              {
                quote:
                  "Testimonial placeholder. Pilot for Trades was never released, so there are no customer quotes.",
                name: "Placeholder 1",
                role: "Testimonial placeholder",
                location: "—",
                trade: "Electrical",
                tradeColor: "var(--trade-electrical)",
              },
              {
                quote:
                  "Testimonial placeholder. Pilot for Trades was never released, so there are no customer quotes.",
                name: "Placeholder 2",
                role: "Testimonial placeholder",
                location: "—",
                trade: "Electrical",
                tradeColor: "var(--trade-electrical)",
              },
              {
                quote:
                  "Testimonial placeholder. Pilot for Trades was never released, so there are no customer quotes.",
                name: "Placeholder 3",
                role: "Testimonial placeholder",
                location: "—",
                trade: "Electrical",
                tradeColor: "var(--trade-electrical)",
              },
            ].map((t) => (
              <figure
                key={t.name}
                className="bg-white rounded-xl p-8"
                style={{ boxShadow: "var(--shadow-sm)" }}
              >
                <div
                  className="text-5xl font-serif mb-4 leading-none"
                  style={{ color: "var(--brand-200)" }}
                  aria-hidden="true"
                >
                  &ldquo;
                </div>
                <blockquote
                  className="text-lg italic mb-6"
                  style={{ color: "var(--neutral-700)" }}
                >
                  {t.quote.replace(/&apos;/g, "'")}
                </blockquote>
                <figcaption>
                  <p
                    className="font-semibold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    {t.name}
                  </p>
                  <p
                    className="text-sm"
                    style={{ color: "var(--neutral-600)" }}
                  >
                    {t.role} · {t.location}
                  </p>
                  <span
                    className="inline-block mt-2 px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{
                      background: `${t.tradeColor}20`,
                      color: t.tradeColor,
                    }}
                  >
                    {t.trade}
                  </span>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 8: Metrics Bar ── */}
      <section className="hero-gradient py-16" aria-label="Product design targets">
        <div className="container-marketing">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { num: "80%", label: "faster quotes (design target)" },
              { num: "95%", label: "pricing accuracy (design target)" },
              { num: "50%", label: "less admin time (design target)" },
            ].map((m, i) => (
              <div
                key={m.label}
                className="text-center"
                style={{
                  borderLeft: i > 0 ? "var(--border-white-15)" : "none",
                }}
              >
                <p
                  className="text-section-title font-bold mb-2"
                  style={{ color: "var(--white)" }}
                >
                  {m.num}
                </p>
                <p className="text-base" style={{ color: "var(--white-8)" }}>
                  {m.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── White separator — prevents adjacent blue sections from merging ── */}
      <div
        className="py-8"
        style={{ background: "var(--white)" }}
        aria-hidden="true"
      />

      {/* ── Section 9: Final CTA Banner ── */}
      <section
        className="section-padding"
        style={{ background: "var(--brand-600)" }}
        aria-labelledby="final-cta-heading"
      >
        <div className="container-marketing text-center">
          <h2
            id="final-cta-heading"
            className="text-section-title font-bold mb-4"
            style={{ color: "var(--white)" }}
          >
            Your Evenings Belong to You. Not Your Estimates.
          </h2>
          <p
            className="text-body-lg mb-10 max-w-2xl mx-auto"
            style={{ color: "var(--white-8)" }}
          >
            {bottomBodyCopy}
          </p>
          <Link href={ctaHref} className="btn-white">
            {ctaText}
          </Link>
        </div>
      </section>
    </>
  );
}
