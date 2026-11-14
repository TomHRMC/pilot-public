// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { getSiteMode } from "../../lib/useSiteMode";

export const metadata: Metadata = {
  title: "About — Our Mission to Transform the Trades",
  description:
    "Pilot for Trades is building AI-powered, voice-first software for electricians, plumbers & HVAC techs. Learn our founder story, product philosophy, and what's next.",
  openGraph: {
    title: "About — Our Mission to Transform the Trades | Pilot for Trades",
    description:
      "Pilot for Trades is building AI-powered, voice-first software for electricians, plumbers & HVAC techs.",
    url: "https://pilotfortrades.com/about",
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
      name: "About",
      item: "https://pilotfortrades.com/about",
    },
  ],
};

export default async function AboutPage() {
  const { isGeneralRelease } = await getSiteMode();
  const ctaText = isGeneralRelease ? "Start Free Trial" : "Be One of the First";
  const ctaHref = isGeneralRelease ? "/sign-up" : "/charter";
  const ctaBodyCopy = isGeneralRelease
    ? "Join contractors running tighter operations with Pilot."
    : "Join the Charter program. Your feedback doesn\u2019t just matter \u2014 it drives what we build next.";
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
        aria-labelledby="about-heading"
      >
        <div className="container-marketing text-center max-w-3xl mx-auto">
          <h1
            id="about-heading"
            className="text-section-title mb-6"
            style={{ color: "var(--neutral-900)" }}
          >
            AI-Powered Tools That Understand Your Craft
          </h1>
          <p
            className="text-section-subtitle"
            style={{ color: "var(--neutral-600)" }}
          >
            We believe every tradesperson deserves software that works as hard
            as they do — voice-first, field-ready, and built by someone who gets
            it.
          </p>
        </div>
      </section>

      {/* Founder story */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-labelledby="founder-heading"
      >
        <div className="container-marketing">
          <div className="flex flex-col lg:flex-row gap-12 lg:gap-16 items-center max-w-5xl mx-auto">
            {/* Photo placeholder */}
            <div className="shrink-0" aria-hidden="true">
              <div
                className="w-56 h-56 rounded-2xl overflow-hidden relative"
                style={{
                  border: "var(--divider-thick) solid var(--brand-200)",
                }}
              >
                <Image
                  src="/about-hero.jpg"
                  alt="Pilot for Trades — built at the intersection of craft and technology"
                  fill
                  className="object-cover object-center"
                  sizes="14rem"
                  priority
                />
              </div>
            </div>

            {/* Text */}
            <div>
              <h2
                id="founder-heading"
                className="text-section-title mb-6"
                style={{ color: "var(--neutral-900)" }}
              >
                Why Pilot Exists
              </h2>
              <div className="flex flex-col gap-4">
                <p
                  className="text-body-lg"
                  style={{ color: "var(--neutral-700)" }}
                >
                  Pilot for Trades started with a simple observation: the people
                  who build and fix everything we depend on — our power, our
                  water, our heat — are running their businesses on
                  spreadsheets, sticky notes, and prayer.
                </p>
                <p
                  className="text-body-lg"
                  style={{ color: "var(--neutral-700)" }}
                >
                  I&apos;m Tom Lang, the founder of Pilot. I&apos;ve seen contractors
                  lose money not because they&apos;re bad
                  at their trade, but because the tools they&apos;re forced to
                  use were built for office workers. The existing software is
                  either too expensive, too complicated, or too far removed from
                  the job site to be useful.
                </p>
                <p
                  className="text-body-lg"
                  style={{ color: "var(--neutral-700)" }}
                >
                  So we built something different. Pilot is AI-first and
                  voice-first because that&apos;s how contractors actually work
                  — with their hands full, on a ladder, in a crawl space. You
                  shouldn&apos;t need a clean desk and a keyboard to run your
                  business.
                </p>
                <p
                  className="text-body-lg"
                  style={{ color: "var(--neutral-700)" }}
                >
                  We&apos;re building this in public, one feature at a time,
                  with direct input from the contractors who use it. You&apos;re
                  helping shape what this becomes.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Product philosophy */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="philosophy-heading"
      >
        <div className="container-marketing">
          <h2
            id="philosophy-heading"
            className="text-section-title text-center mb-14"
            style={{ color: "var(--neutral-900)" }}
          >
            How We Build
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {[
              {
                icon: "🎙️",
                title: "Voice-First",
                desc: 'Every feature starts with the question: "Can a contractor use this with dirty hands?" If it needs a keyboard, we go back to the drawing board.',
              },
              {
                icon: "📵",
                title: "Offline-Capable",
                desc: "Basements, crawl spaces, rural job sites — your app should work where you work. Pilot syncs when it can, but never stops you when it can't.",
              },
              {
                icon: "🔧",
                title: "Built for the Field",
                desc: "Not a repurposed office tool. Not a scaled-down enterprise suite. Purpose-built for contractors with 1–15 employees who spend their day on-site.",
              },
            ].map((v) => (
              <div key={v.title} className="card-marketing p-8 text-center">
                <span className="text-4xl block mb-4" aria-hidden="true">
                  {v.icon}
                </span>
                <h3
                  className="text-xl font-semibold mb-3"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {v.title}
                </h3>
                <p
                  className="text-base"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {v.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology note */}
      <section
        className="py-16"
        style={{ background: "var(--white)" }}
        aria-labelledby="tech-heading"
      >
        <div className="container-marketing max-w-3xl mx-auto text-center">
          <h2
            id="tech-heading"
            className="text-section-title mb-6"
            style={{ color: "var(--neutral-900)" }}
          >
            Security-First. Solo-Friendly.
          </h2>
          <p
            className="text-body-lg mb-4"
            style={{ color: "var(--neutral-700)" }}
          >
            Pilot runs on AWS with TLS in transit and an encrypted database. Your voice
            data is processed on our own servers — it never touches a
            third-party AI service. Every contractor&apos;s data is scoped by
            tenant in the application layer, so one business can&apos;t see
            another&apos;s records.
          </p>
          <p
            className="text-body-lg font-semibold"
            style={{ color: "var(--neutral-900)" }}
          >
            Your data is yours. Period.
          </p>
        </div>
      </section>

      {/* Roadmap */}
      <section
        className="py-16"
        style={{ background: "var(--surface-marketing-alt)" }}
        aria-labelledby="roadmap-heading"
      >
        <div className="container-marketing max-w-4xl mx-auto">
          <h2
            id="roadmap-heading"
            className="text-section-title text-center mb-12"
            style={{ color: "var(--neutral-900)" }}
          >
            Where We&apos;re Going
          </h2>
          <div className="flex flex-col md:flex-row gap-6">
            {[
              {
                phase: "✅ Now",
                label: "MVP: Electrical",
                desc: "Voice quoting, dispatch, invoicing, profitability, QuickBooks sync — all optimized for electrical contractors.",
                active: true,
              },
              {
                phase: "🔜 Next",
                label: "Phase 2: Plumbing & HVAC",
                desc: "Same powerful platform, adapted for plumbing and HVAC workflows with trade-specific AI vocabulary.",
                active: false,
              },
              {
                phase: "🔮 Future",
                label: "Multi-Trade Teams",
                desc: "Shops that run electrical and plumbing? We'll handle that. One platform for the whole operation.",
                active: false,
              },
            ].map((item) => (
              <div
                key={item.label}
                className="flex-1 rounded-xl p-6"
                style={{
                  background: item.active ? "var(--brand-50)" : "var(--white)",
                  border: item.active
                    ? "var(--divider-thick) solid var(--brand-200)"
                    : "var(--divider-thin) solid var(--neutral-200)",
                }}
              >
                <p
                  className="text-sm font-medium mb-2"
                  style={{ color: "var(--neutral-500)" }}
                >
                  {item.phase}
                </p>
                <h3
                  className="text-lg font-bold mb-3"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {item.label}
                </h3>
                <p
                  className="text-base"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
          <p
            className="text-sm text-center mt-8"
            style={{ color: "var(--neutral-500)" }}
          >
            We share our roadmap because transparency builds trust. If a feature
            matters to you,{" "}
            <Link
              href="/contact"
              className="no-underline font-medium"
              style={{ color: "var(--brand-600)" }}
            >
              tell us
            </Link>
            .
          </p>
        </div>
      </section>

      {/* CTA */}
      <section
        className="section-padding"
        style={{ background: "var(--brand-600)" }}
        aria-labelledby="about-cta-heading"
      >
        <div className="container-marketing text-center">
          <h2
            id="about-cta-heading"
            className="text-section-title font-bold mb-4"
            style={{ color: "var(--white)" }}
          >
            Want to Help Build the Future of Trades Software?
          </h2>
          <p
            className="text-body-lg mb-10 max-w-2xl mx-auto"
            style={{ color: "var(--white-8)" }}
          >
            {ctaBodyCopy}
          </p>
          <Link href={ctaHref} className="btn-white">
            {ctaText}
          </Link>
        </div>
      </section>
    </>
  );
}
