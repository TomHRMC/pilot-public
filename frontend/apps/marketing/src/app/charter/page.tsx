// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getSiteMode } from "../../lib/useSiteMode";
import CharterApplicationForm from "../../components/forms/CharterApplicationForm";
import CharterAvailabilityBadge from "../../components/CharterAvailabilityBadge";

export const metadata: Metadata = {
  title: "Be one of the first twelve — Charter for Pilot for Trades",
  description:
    "Twelve electrical contractors get 90 days free, concierge onboarding, and a $49/month rate locked for as long as they stay subscribed. No card at signup. Each signup is reviewed personally by our team.",
  openGraph: {
    title: "Be one of the first twelve | Pilot for Trades",
    description:
      "90 days free. Then $49/month locked for as long as you stay. Our team does the setup personally — not a waitlist, a real conversation.",
    url: "https://pilotfortrades.com/charter",
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
      name: "Charter",
      item: "https://pilotfortrades.com/charter",
    },
  ],
};

const whatYouGet = [
  {
    icon: "🆓",
    title: "90 days free, no card required.",
    desc: "Full Starter capability — quoting, dispatch, invoicing, QuickBooks sync, voice AI. No credit card collected at signup. The only out-of-pocket cost is carrier registration fees if you want to text customers, and that's passed through at cost.",
  },
  {
    icon: "🔒",
    title: "$49/month locked for as long as you stay.",
    desc: "When the free period ends, you move to $49/month — locked at that rate for as long as you stay continuously subscribed. Cancel and the rate is gone for good. Upgrade to Teams and it's gone too. One-way door, stated up front.",
  },
  {
    icon: "🛠️",
    title: "We'll set it up for you.",
    desc: "Send us your customer list however you've got it — spreadsheet, QuickBooks, a shoebox of invoices. We'll load it in, build out your price book with your rates and markups, and set your tax rates. Usually takes us an afternoon. You show up to an account that already has your business in it.",
  },
  {
    icon: "📞",
    title: "Direct line to our team.",
    desc: "Direct number, not a support queue. Your requests go to the top of the build queue. That's the real offer — not the free months, but a direct line to the team building the product.",
  },
];

const theAsk = [
  {
    lead: "Use it on real jobs.",
    detail: "Not test data — actual customers, actual quotes, actual invoices.",
  },
  {
    lead: "Answer us when we ask.",
    detail:
      "We'll text or email now and then, usually one question, usually about something you did that day. A reply within a day or so is all we need.",
  },
  {
    lead: "Hit the feedback button when something's broken or confusing.",
    detail: "Takes ten seconds. Don't be polite about it.",
  },
  {
    lead: "One phone call near the end.",
    detail: "About 30 minutes, whenever works for you.",
  },
];

const exitGuarantee = ["Customers", "Jobs", "Quotes", "Invoices", "Payments"];

export default async function CharterPage() {
  // In General Release mode, redirect to /sign-up to avoid SEO/bookmark breakage
  const { isGeneralRelease } = await getSiteMode();
  if (isGeneralRelease) {
    redirect("/sign-up");
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero — two-column desktop layout */}
      <section
        className="hero-gradient hero-padding"
        aria-labelledby="charter-heading"
      >
        <div className="container-marketing">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start max-w-6xl mx-auto">
            {/* LEFT COLUMN — headline, bio, offer, ask */}
            <div>
              <h1
                id="charter-heading"
                className="text-hero mb-6"
                style={{ color: "var(--white)", lineHeight: "var(--lh-hero)" }}
              >
                Twelve spots. We{"'"}re filling them now.
              </h1>

              {/* C-B13 — Charter availability badge (client component) */}
              <CharterAvailabilityBadge />

              {/* Bio callout */}
              <div
                className="mb-6 pl-4 border-l-4"
                style={{ borderColor: "var(--white-4)" }}
              >
                <p
                  className="text-base leading-relaxed italic"
                  style={{ color: "var(--white-7)" }}
                >
                  Pilot was designed from the ground up by an electrical
                  engineer with fifteen years in electrical and controls
                  engineering — before a single line of software was written. We
                  know the work well enough to know we don{"'"}t know your
                  business. That{"'"}s why the Charter program exists.
                </p>
              </div>

              {/* Core offer */}
              <p
                className="mb-6"
                style={{
                  color: "var(--white-85)",
                  fontSize: "var(--text-body-lg)",
                  lineHeight: "var(--lh-body-lg)",
                }}
              >
                We{"'"}re looking for twelve electricians to run their actual
                business on it for ninety days. Free. We{"'"}ll set it up with
                you — your customers, your price book, your rates — so you{"'"}
                re running from day one, not configuring.{" "}
                <strong style={{ color: "var(--white)" }}>
                  After ninety days it{"'"}s forty-nine a month and that price
                  never goes up for you, as long as you stay on.
                </strong>
              </p>

              {/* The only cost */}
              <p
                className="mb-8"
                style={{
                  color: "var(--white-7)",
                  fontSize: "var(--text-body-lg)",
                  lineHeight: "var(--lh-body-lg)",
                }}
              >
                The only thing it costs you in the meantime is the phone carrier
                fees if you want to text customers — that{"'"}s about thirty
                bucks and it goes straight to the carrier. We don{"'"}t touch
                it.
              </p>

              {/* Honest ask — scannable list */}
              <div className="mb-8">
                <p
                  className="text-sm font-semibold uppercase tracking-wide mb-3"
                  style={{ color: "var(--white-5)" }}
                >
                  What we need from you
                </p>
                <ul className="flex flex-col gap-3 list-none p-0 m-0">
                  {theAsk.map((item) => (
                    <li key={item.lead} className="flex items-start gap-3">
                      <span
                        className="mt-1 shrink-0 text-sm"
                        style={{ color: "var(--white-4)" }}
                        aria-hidden="true"
                      >
                        →
                      </span>
                      <span
                        style={{
                          color: "var(--white-85)",
                          fontSize: "var(--text-body-lg)",
                          lineHeight: "var(--lh-body-lg)",
                        }}
                      >
                        <strong style={{ color: "var(--white)" }}>
                          {item.lead}
                        </strong>{" "}
                        {item.detail}
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="text-sm mt-4" style={{ color: "var(--white-5)" }}>
                  That{"'"}s it. No surveys, no scheduled meetings, no
                  paperwork.
                </p>
              </div>

              {/* Note on scarcity */}
              <p className="text-sm" style={{ color: "var(--white-5)" }}>
                Twelve is what we can do properly. We are a small team, and past
                that we{"'"}d be doing a bad job for everybody.
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
                <CharterApplicationForm source="charter_page" />
              </div>
              <p
                className="text-center text-sm mt-4"
                style={{ color: "var(--white-4)" }}
              >
                Each signup is reviewed personally by our team. No credit card
                required.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* What You Get */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-labelledby="what-you-get-heading"
      >
        <div className="container-marketing">
          <h2
            id="what-you-get-heading"
            className="text-section-title text-center mb-14"
            style={{ color: "var(--neutral-900)" }}
          >
            What You Get
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {whatYouGet.map((item) => (
              <div
                key={item.title}
                className="flex items-start gap-4 p-6 rounded-xl"
                style={{
                  background: "var(--surface-marketing)",
                  border: "var(--divider-thin) solid var(--neutral-200)",
                }}
              >
                <span className="text-3xl shrink-0" aria-hidden="true">
                  {item.icon}
                </span>
                <div>
                  <h3
                    className="text-lg font-semibold mb-1"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    {item.title}
                  </h3>
                  <p
                    className="text-base"
                    style={{ color: "var(--neutral-600)" }}
                  >
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Exit Guarantee */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="exit-heading"
      >
        <div className="container-marketing max-w-2xl mx-auto text-center">
          <h2
            id="exit-heading"
            className="text-section-title mb-6"
            style={{ color: "var(--neutral-900)" }}
          >
            If it doesn{"'"}t work out, we{"'"}ll help you leave.
          </h2>
          <p
            className="text-body-lg mb-8"
            style={{ color: "var(--neutral-600)" }}
          >
            Tell us and we{"'"}ll export everything as clean spreadsheets, and
            we{"'"}ll help you get it into whatever you{"'"}re moving to. No
            arguing, no retention pitch, no thirty-day notice. There{"'"}s an
            export button in the app; you don{"'"}t have to ask us. Your data is
            yours.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {exitGuarantee.map((item) => (
              <span
                key={item}
                className="inline-block px-4 py-2 rounded-full text-sm font-medium"
                style={{
                  background: "var(--white)",
                  color: "var(--neutral-700)",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Trust strip */}
      <section className="py-8" style={{ background: "var(--white)" }}>
        <div className="container-marketing text-center">
          <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
            No credit card required. Each signup is reviewed personally by our
            team.
          </p>
        </div>
      </section>
    </>
  );
}
