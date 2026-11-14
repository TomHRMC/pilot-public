// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";
import ContactForm from "../../components/ContactForm";
import { getSiteMode } from "../../lib/useSiteMode";

export const metadata: Metadata = {
  title: "Contact Us — Support & Sales",
  description:
    "Have a question about Pilot for Trades? Reach us at info@pilotfortrades.com or use our contact form. We respond within 24 hours.",
  openGraph: {
    title: "Contact Us — Support & Sales | Pilot for Trades",
    description:
      "Have a question about Pilot for Trades? We respond within 24 hours. No bots. No ticket queues.",
    url: "https://pilotfortrades.com/contact",
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
      name: "Contact",
      item: "https://pilotfortrades.com/contact",
    },
  ],
};

export default async function ContactPage() {
  const { isGeneralRelease } = await getSiteMode();
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
        aria-labelledby="contact-heading"
      >
        <div className="container-marketing text-center max-w-2xl mx-auto">
          <h1
            id="contact-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            Let&apos;s Talk
          </h1>
          <p
            className="text-section-subtitle"
            style={{ color: "var(--neutral-600)" }}
          >
            Whether you&apos;re curious about features, pricing, or just want to
            say hey — we respond within 24 hours. No bots. No ticket queues. A
            real person reads every message.
          </p>
        </div>
      </section>

      {/* Contact cards + form */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-label="Contact options and form"
      >
        <div className="container-marketing">
          <div className="flex flex-col lg:flex-row gap-12 lg:gap-16 max-w-5xl mx-auto">
            {/* Left: contact info cards (static — no event handlers) */}
            <div className="flex flex-col gap-6 lg:w-80 shrink-0">
              <div
                className="rounded-xl p-6"
                style={{
                  background: "var(--surface-marketing)",
                  border: "var(--divider-thin) solid var(--neutral-200)",
                }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl" aria-hidden="true">
                    ✉️
                  </span>
                  <h2
                    className="text-lg font-semibold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    Email us
                  </h2>
                </div>
                <a
                  href="mailto:info@pilotfortrades.com"
                  className="text-base font-medium no-underline"
                  style={{ color: "var(--brand-600)" }}
                >
                  info@pilotfortrades.com
                </a>
                <p
                  className="text-sm mt-1"
                  style={{ color: "var(--neutral-600)" }}
                >
                  We respond within 24 hours, usually faster.
                </p>
              </div>

              <div
                className="rounded-xl p-6"
                style={{
                  background: "var(--surface-marketing)",
                  border: "var(--divider-thin) solid var(--neutral-200)",
                }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl" aria-hidden="true">
                    ❓
                  </span>
                  <h2
                    className="text-lg font-semibold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    Check the FAQ
                  </h2>
                </div>
                <p
                  className="text-base mb-3"
                  style={{ color: "var(--neutral-600)" }}
                >
                  Many common questions are answered on our Pricing FAQ.
                </p>
                <Link
                  href="/pricing#faq"
                  className="text-sm font-medium no-underline"
                  style={{ color: "var(--brand-600)" }}
                >
                  View FAQ →
                </Link>
              </div>

              <div
                className="rounded-xl p-6"
                style={{
                  background: "var(--surface-marketing)",
                  border: "var(--divider-thin) solid var(--neutral-200)",
                }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl" aria-hidden="true">
                    👥
                  </span>
                  <h2
                    className="text-lg font-semibold"
                    style={{ color: "var(--neutral-900)" }}
                  >
                    {isGeneralRelease
                      ? "Start your free trial"
                      : "Join the Charter program"}
                  </h2>
                </div>
                <p
                  className="text-base mb-3"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {isGeneralRelease
                    ? "Ready to try it on a real job? 14 days free, no credit card required."
                    : "Not ready to talk? Be one of the first and we\u2019ll reach out when it\u2019s your turn."}
                </p>
                <Link
                  href={isGeneralRelease ? "/sign-up" : "/charter"}
                  className="text-sm font-medium no-underline"
                  style={{ color: "var(--brand-600)" }}
                >
                  {isGeneralRelease
                    ? "Start Free Trial →"
                    : "Be One of the First →"}
                </Link>
              </div>
            </div>

            {/* Right: contact form (client component) */}
            <div className="flex-1">
              <h2
                className="text-xl font-bold mb-6"
                style={{ color: "var(--neutral-900)" }}
              >
                Send a message
              </h2>
              <ContactForm />
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
