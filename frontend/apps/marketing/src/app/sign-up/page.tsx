// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import CharterApplicationForm from "../../components/CharterApplicationForm";

export const metadata: Metadata = {
  title: "Start Your Free Trial — Pilot for Trades",
  description:
    "14-day free trial. No credit card required. Start using Voice AI quoting, dispatch, and QuickBooks sync for your electrical contracting business today.",
  openGraph: {
    title: "Start Your Free Trial | Pilot for Trades",
    description: "14 days free. No credit card. Cancel anytime.",
    url: "https://pilotfortrades.com/sign-up",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
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
      name: "Start Your Free Trial",
      item: "https://pilotfortrades.com/sign-up",
    },
  ],
};

const includedCards = [
  {
    icon: "🆓",
    title: "14 days free at your chosen plan's limits",
    desc: "Full access on Starter (5 lanes) or Teams (20 lanes) — no credit card needed to start.",
  },
  {
    icon: "⚡",
    title: "Full access to every core feature",
    desc: "Voice AI quoting, dispatch board, invoicing, QuickBooks sync, and offline mobile — everything included.",
  },
  {
    icon: "🔒",
    title: "No credit card until your trial ends",
    desc: "If you choose to stay, continue at $49/month (Starter) or $149/month (Teams), billed annually. Cancel anytime before trial ends.",
  },
];

export default function SignUpPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero — two-column desktop layout, matches /charter pattern */}
      <section
        className="hero-gradient hero-padding"
        aria-labelledby="sign-up-heading"
      >
        <div className="container-marketing">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start max-w-6xl mx-auto">
            {/* LEFT COLUMN — headline and what's included */}
            <div>
              <h1
                id="sign-up-heading"
                className="text-hero mb-4"
                style={{ color: "var(--white)", lineHeight: "var(--lh-hero)" }}
              >
                Start Your Free Trial
              </h1>

              <p
                className="text-section-subtitle mb-10"
                style={{ color: "var(--white-8)" }}
              >
                14 days free. No credit card required. Cancel anytime.
              </p>

              {/* What's included cards */}
              <div className="flex flex-col gap-4 mb-8">
                {includedCards.map((card) => (
                  <div
                    key={card.icon}
                    className="flex items-start gap-4 rounded-xl p-5"
                    style={{
                      background: "var(--white-08)",
                      border: "var(--border-white-12)",
                    }}
                  >
                    <span
                      className="text-2xl shrink-0 mt-0.5"
                      aria-hidden="true"
                    >
                      {card.icon}
                    </span>
                    <div>
                      <p
                        className="text-base font-semibold mb-1"
                        style={{ color: "var(--white)" }}
                      >
                        {card.title}
                      </p>
                      <p
                        className="text-sm"
                        style={{ color: "var(--white-7)" }}
                      >
                        {card.desc}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pricing reminder */}
              <p
                className="text-caption-lg"
                style={{
                  color: "var(--white-5)",
                  fontSize: "var(--text-caption-lg)",
                  lineHeight: "var(--lh-caption-lg)",
                }}
              >
                After 14 days, continue at $59/month (Starter) or $179/month
                (Teams), or $49/$149 billed annually. Cancel anytime before trial ends.
              </p>
            </div>

            {/* RIGHT COLUMN — form card + trust line */}
            <div className="lg:sticky lg:top-8">
              <div
                className="rounded-2xl p-8"
                style={{
                  background: "var(--white)",
                  boxShadow: "var(--shadow-2xl)",
                }}
              >
                {/* CharterApplicationForm keeps its own button label; source prop tags the signup origin */}
                <CharterApplicationForm source="sign_up_page" />
              </div>
              <p
                className="text-center text-sm mt-4"
                style={{ color: "var(--white-4)" }}
              >
                No credit card required. Cancel anytime.
              </p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
