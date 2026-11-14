// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import ApplicationForm from "../../components/forms/ApplicationForm";

export const metadata: Metadata = {
  title: "Careers — Build the Future of Trades Software",
  description:
    "Join Pilot for Trades — we're building AI-powered, voice-first software for electricians, plumbers & HVAC contractors. Remote-first, high autonomy, founder access.",
  openGraph: {
    title: "Careers — Build the Future of Trades Software | Pilot for Trades",
    description:
      "Join Pilot for Trades. Remote-first, high autonomy, AI-assisted development, direct founder access.",
    url: "https://pilotfortrades.com/careers",
  },
};

const values = [
  {
    emoji: "🔨",
    title: "Builders First",
    desc: "We don't theorize about solutions — we ship them. Bias toward action. If you built it, you own it.",
  },
  {
    emoji: "🪜",
    title: "Field-Tested Thinking",
    desc: "Every feature decision starts with \"does this work for a contractor on a ladder?\" If you haven't talked to a customer this week, you're guessing.",
  },
  {
    emoji: "🚀",
    title: "Ship Fast, Fix Fast",
    desc: "Speed beats perfection. We ship, measure, learn, and iterate. Mistakes are fine. Slow is not.",
  },
  {
    emoji: "🪟",
    title: "Radical Transparency",
    desc: "Open roadmap. Public metrics. Honest standups. If something's broken, we say so. If something's hard, we say that too.",
  },
];

// PLACEHOLDER COPY — Pilot for Trades was never released and is not hiring.
// The original launch-draft role listings were removed from this public snapshot.
const openRoles: { title: string; desc: string; details: string[] }[] = [
  {
    title: "No open roles",
    desc: "Placeholder copy from a launch that never happened. Pilot for Trades was never released and is not hiring.",
    details: [],
  },
];

export default function CareersPage() {
  return (
    <>
      {/* Hero */}
      <section
        className="hero-gradient py-20"
        style={{ paddingBlock: "5rem" }}
        aria-labelledby="careers-heading"
      >
        <div className="container-marketing text-center max-w-3xl mx-auto">
          <h1
            id="careers-heading"
            className="text-section-title mb-6"
            style={{ color: "var(--white)" }}
          >
            Build the Future of Trades Software
          </h1>
          <p
            className="text-section-subtitle"
            style={{ color: "var(--white-8)" }}
          >
            800,000 trade businesses in the US still run on spreadsheets and
            sticky notes. We&apos;re changing that with AI — and we&apos;re
            looking for people who want to help.
          </p>
        </div>
      </section>

      {/* Who we're building for */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-labelledby="problem-heading"
      >
        <div className="container-marketing max-w-3xl mx-auto">
          <h2
            id="problem-heading"
            className="text-section-title mb-8"
            style={{ color: "var(--neutral-900)" }}
          >
            The Problem We&apos;re Solving
          </h2>
          <div className="flex flex-col gap-4">
            <p className="text-body-lg" style={{ color: "var(--neutral-700)" }}>
              Electricians, plumbers, and HVAC techs are the backbone of every
              building you&apos;ve ever walked into. They work 10-hour days
              on-site, then go home and spend another 3 hours on admin — quoting
              jobs, chasing invoices, updating schedules.
            </p>
            <p className="text-body-lg" style={{ color: "var(--neutral-700)" }}>
              The software that exists was built for enterprise operations with
              200+ employees. The solo contractor with a van and a dream?
              Nobody&apos;s building for them. Until now.
            </p>
            <p className="text-body-lg" style={{ color: "var(--neutral-700)" }}>
              Pilot for Trades is AI-first, voice-first software that handles
              the business side so contractors can focus on their craft.
              We&apos;re starting with electrical contractors and expanding to
              plumbing and HVAC.
            </p>
          </div>
        </div>
      </section>

      {/* Culture & values */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="values-heading"
      >
        <div className="container-marketing">
          <h2
            id="values-heading"
            className="text-section-title text-center mb-14"
            style={{ color: "var(--neutral-900)" }}
          >
            What We Care About
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
            {values.map((v) => (
              <div key={v.title} className="card-marketing p-6 text-center">
                <span className="text-4xl block mb-4" aria-hidden="true">
                  {v.emoji}
                </span>
                <h3
                  className="text-lg font-semibold mb-3"
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

      {/* What it's like */}
      <section
        className="py-16"
        style={{ background: "var(--white)" }}
        aria-labelledby="culture-heading"
      >
        <div className="container-marketing max-w-3xl mx-auto">
          <h2
            id="culture-heading"
            className="text-section-title mb-8"
            style={{ color: "var(--neutral-900)" }}
          >
            The Honest Version
          </h2>
          <p
            className="text-body-lg mb-6"
            style={{ color: "var(--neutral-700)" }}
          >
            We&apos;re a solo-founder company at pre-launch. Here&apos;s what
            that means:
          </p>
          <ul className="flex flex-col gap-4 list-none p-0 m-0">
            {[
              {
                label: "Fully remote.",
                desc: "Work from anywhere with good internet.",
              },
              {
                label: "AI-assisted development.",
                desc: "We use AI copilots extensively — for code, content, and customer research. If that excites you, you'll fit right in.",
              },
              {
                label: "High autonomy.",
                desc: "No layers of approval. You'll have direct access to the founder and direct impact on the product.",
              },
              {
                label: "No corporate theater.",
                desc: 'No mandatory fun, no 45-minute standups, no "alignment syncs." Ship things and go live your life.',
              },
            ].map((item) => (
              <li key={item.label} className="flex items-start gap-3">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  className="mt-1 shrink-0"
                  aria-hidden="true"
                >
                  <circle cx="10" cy="10" r="9" fill="var(--brand-50)" />
                  <path
                    d="M6 10l3 3 5-5"
                    stroke="var(--brand-600)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <p
                  className="text-body-lg"
                  style={{ color: "var(--neutral-700)" }}
                >
                  <strong style={{ color: "var(--neutral-900)" }}>
                    {item.label}
                  </strong>{" "}
                  {item.desc}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Open Roles */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing-alt)" }}
        aria-labelledby="openroles-heading"
      >
        <div className="container-marketing max-w-4xl mx-auto">
          <h2
            id="openroles-heading"
            className="text-section-title mb-6"
            style={{ color: "var(--neutral-900)" }}
          >
            Open Roles
          </h2>
          <p
            className="text-body-lg mb-12"
            style={{ color: "var(--neutral-700)" }}
          >
            Placeholder section from the launch draft. Pilot for Trades was
            never released, and there are no open roles.
          </p>

          {/* Role cards — detail bullets, no Apply Now buttons */}
          <div className="flex flex-col gap-6">
            {openRoles.map((role) => (
              <div
                key={role.title}
                className="rounded-xl p-6"
                style={{
                  background: "var(--white)",
                  border: "var(--divider-thin) solid var(--neutral-200)",
                }}
              >
                <h3
                  className="text-xl font-semibold mb-2"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {role.title}
                </h3>
                <p
                  className="text-base mb-4"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {role.desc}
                </p>
                <ul className="flex flex-col gap-1 list-none p-0 m-0">
                  {role.details.map((detail, i) => (
                    <li
                      key={i}
                      className="text-sm"
                      style={{ color: "var(--neutral-600)" }}
                      dangerouslySetInnerHTML={{
                        __html: detail.replace(
                          /\*\*(.+?)\*\*/g,
                          '<strong style="color: var(--neutral-800)">$1</strong>',
                        ),
                      }}
                    />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Application Form */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="apply-heading"
      >
        <div className="container-marketing max-w-2xl mx-auto">
          <h2
            id="apply-heading"
            className="text-section-title mb-3"
            style={{ color: "var(--neutral-900)" }}
          >
            Apply Now
          </h2>
          <p
            className="text-body-lg mb-8"
            style={{ color: "var(--neutral-600)" }}
          >
            Tell us who you are and why this matters to you. We review every
            application personally.
          </p>
          <ApplicationForm />
        </div>
      </section>
    </>
  );
}
