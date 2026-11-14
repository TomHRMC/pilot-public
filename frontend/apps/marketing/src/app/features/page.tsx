// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { getSiteMode } from "../../lib/useSiteMode";

export const metadata: Metadata = {
  title: "Features — AI Voice Quoting, Dispatch & Profitability",
  description:
    "Voice-driven quoting, real-time profitability tracking, smart dispatch, customer SMS, QuickBooks sync, and offline field ops — all in one platform built for contractors.",
  openGraph: {
    title:
      "Features — AI Voice Quoting, Dispatch & Profitability | Pilot for Trades",
    description:
      "Voice-driven quoting, real-time profitability tracking, smart dispatch, customer SMS, QuickBooks sync, and offline field ops.",
    url: "https://pilotfortrades.com/features",
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
      name: "Features",
      item: "https://pilotfortrades.com/features",
    },
  ],
};

const features = [
  {
    id: "voice-ai",
    badge: "AI-POWERED",
    icon: "🎙️",
    heading: "Talk to Pilot Like You'd Talk to Your Best Apprentice",
    desc: "Describe the job in plain English — or plain electrician, plumber, or HVAC tech. Pilot's Voice AI understands trade-specific terminology, runs calculations in the background, and turns your words into professional estimates. No forms. No typing. No squinting at tiny phone keyboards on a sunny roof.",
    bullets: [
      "Voice-driven quoting: Describe the job, get an estimate.",
      "NEC & code awareness: Automatic voltage drop, conduit fill, and ampacity calculations.",
      "Multi-turn conversations: Add details, change specs, ask questions — Pilot keeps up.",
      "Session continuity: Start a quote in the truck, finish it on-site.",
      "Trade-specific vocabulary: Wire gauges, pipe sizes, refrigerant types — Pilot speaks your language.",
    ],
  },
  {
    id: "quoting",
    badge: "CORE WORKFLOW",
    icon: "📝",
    heading: "Professional Quotes in Minutes, Not Hours",
    desc: "Forget the kitchen-table math at 9 PM. Pilot generates accurate, professional-looking estimates with current material prices, your labor rates, and your markup — all from a voice description or a few taps. Send it to the customer before you leave the driveway.",
    bullets: [
      "Real-time material pricing: Costs update based on current market data.",
      "Three presentation styles: Detailed, summary, or good/better/best.",
      "Template system: Save your most common job types as templates.",
      "Digital acceptance: Customers approve quotes with a tap from their phone.",
      "Automatic markup: Set your margin rules once. Pilot applies them every time.",
      "Quote history: Every version saved.",
    ],
  },
  {
    id: "dispatch",
    badge: "OPERATIONS",
    icon: "📅",
    heading: "Your Whole Week, One Screen",
    desc: "The dispatch board shows every tech, every job, and every gap — at a glance. Drag to reschedule, drop to assign, and let Pilot flag conflicts before they become callbacks. Drive-time estimates and tech availability built right in.",
    bullets: [
      "Drag-and-drop scheduling: Move jobs between techs and time slots with a swipe.",
      "Conflict detection: Double-booked? Pilot catches it before your customer does.",
      "Drive-time estimates: Automatic travel time calculations between job sites.",
      "Tech availability: See who's available, who's on-site, who's headed home.",
      "Calendar sync: Connects to Google Calendar.",
      "Recurring jobs: Set it and forget it for maintenance contracts.",
    ],
  },
  {
    id: "field-ops",
    badge: "IN THE FIELD",
    icon: "🔧",
    heading: "Run Jobs From Your Phone. Even in the Basement.",
    desc: "Everything you need on-site — time tracking, expense logging, photo documentation, and change order management — works on your phone and works offline. No signal? No problem. Pilot syncs when you're back in range.",
    bullets: [
      "Time tracking: Clock in/out per job with GPS verification.",
      "Estimated Time to Complete (ETC): Log remaining time so the office knows when you'll wrap.",
      "Expense capture: Snap a photo of the receipt. Pilot reads it and logs the cost.",
      "Photo documentation: Before/after photos attached to the job record.",
      "GPS check-in: Automatic arrival/departure logging for proof of service.",
      "Change orders: Create a change order on the spot with updated pricing.",
      "LOTO compliance: Lock-out/tag-out checklists built into the job workflow.",
    ],
  },
  {
    id: "profitability",
    badge: "PROFIT ENGINE",
    icon: "📈",
    heading: "Know Your Margin Before the Job Ends",
    desc: "Most contractors don't know if a job was profitable until the invoice is paid — weeks later. Pilot tracks costs in real time: materials, labor, expenses. You see your margin while you can still do something about it.",
    bullets: [
      "Live job costing: Materials + labor + expenses tallied in real time.",
      "Margin tracking: See target margin vs. actual margin — before, during, and after.",
      "ETC projections: Pilot warns you when a job is trending toward a loss.",
      "Profitability alerts: Automated notifications when margins slip.",
      "Job profitability reports: Post-completion breakdown of where the money went.",
      "Portfolio view: See profitability across all active jobs in one dashboard.",
    ],
  },
  {
    id: "communications",
    badge: "CUSTOMER EXPERIENCE",
    icon: "💬",
    heading: "Keep Customers in the Loop Without Lifting a Finger",
    desc: "Automated texts at every stage — appointment reminders, on-my-way notifications, running-late alerts, and invoice follow-ups. Every message is previewed before it sends. Your customers feel informed. You feel professional. Nobody plays phone tag.",
    bullets: [
      "Template system: 13+ pre-built message templates for the entire job lifecycle.",
      "Always preview before send: You approve every message.",
      "Bidirectional SMS: Customers can reply, and you see it in the app.",
      "Voice-to-text replies: Dictate your response while driving.",
      "Customer threading: Full message history per customer, per job.",
      "A2P 10DLC compliant: Registered SMS that actually gets delivered.",
    ],
  },
  {
    id: "invoicing",
    badge: "GET PAID",
    icon: "💳",
    heading: "From Quote to Cash, Faster",
    desc: "Convert any approved quote into an invoice with one tap. Send a payment link your customer can pay from their phone. Stripe handles the processing. Pilot handles the reminders. You handle the next job.",
    bullets: [
      "Quote-to-invoice conversion: One tap turns an approved quote into a ready-to-send invoice.",
      "Payment links: Customers pay online via a secure Stripe-powered payment page.",
      "Automated dunning: Gentle payment reminders on your schedule.",
      "AR dashboard: See who owes what, when it's due, and how long it's outstanding.",
      "Partial payments: Accept deposits, progress payments, and final payments.",
      "Receipt generation: Automatic receipts sent on payment confirmation.",
    ],
  },
  {
    id: "quickbooks",
    badge: "SYNC",
    icon: "🔄",
    heading: "Your QuickBooks Stays. Pilot Handles the Field.",
    desc: "Pilot syncs invoices, payments, and customer records to QuickBooks Online — bidirectionally. Your bookkeeper sees clean data. You never double-enter. And when QuickBooks and Pilot disagree, a simple conflict resolution screen tells you exactly what's different.",
    bullets: [
      "Bi-directional sync: Invoices and payments push to QuickBooks.",
      "Conflict resolution: Side-by-side comparison when data doesn't match.",
      "Invoice push: Approved invoices automatically appear in QuickBooks.",
      "Payment recording: Payments received through Pilot record in QuickBooks.",
      "Sync status dashboard: See what synced, what's pending, what needs attention.",
    ],
  },
  {
    id: "mobile",
    badge: "FIELD-READY",
    icon: "📱",
    heading: "Works in the Basement. Works on the Roof. Works Without Signal.",
    desc: "Built mobile-first for where you actually work — not where you have five bars of LTE. Pilot queues actions when you're offline and syncs automatically when connectivity returns. Start a quote in a basement, and it's saved before you climb the stairs.",
    bullets: [
      "Offline operations: Create quotes, log time, capture photos without internet.",
      "Automatic sync queue: Every action queued locally and pushed when back online.",
      "Background sync: Syncs in the background so you never manually refresh.",
      "Photo upload optimization: Photos compress and upload in batches.",
      "Deferred voice processing: Record voice quotes offline; Pilot processes when you reconnect.",
      "Low-bandwidth mode: Works on LTE.",
    ],
  },
  {
    id: "security",
    badge: "SECURITY",
    icon: "🛡️",
    heading: "Your Data Is Yours. Full Stop.",
    desc: "Multi-tenant isolation means your data is separated from every other contractor on the platform. Two-factor authentication, role-based access, and a full audit trail come standard — not as an enterprise upsell.",
    bullets: [
      "Multi-tenant data isolation: every record is scoped to your business.",
      "Two-factor authentication (MFA): SMS or authenticator app.",
      "Role-based access control (RBAC): Owner, admin, tech, bookkeeper.",
      "Audit trail: key actions logged.",
      "A2P 10DLC compliance: Registered SMS messaging that reaches your customers.",
    ],
  },
  {
    id: "help",
    badge: "SMART SUPPORT",
    icon: "❓",
    heading: "Stuck? Ask Pilot.",
    desc: "An AI assistant that actually knows your app and your trade. Ask how to do something, get a step-by-step answer. Pilot's help system uses RAG trained on our documentation and trade resources.",
    bullets: [
      "RAG-powered search: Ask a question in plain English, get a specific answer.",
      "Contextual help: Pilot knows what screen you're on.",
      "Voice-driven help: Ask by voice, get a spoken response.",
      "Trade reference library: NEC codes, pipe sizing tables, load calculation guides.",
      "Step-by-step walkthroughs: How-to guidance for any workflow.",
    ],
  },
];

/**
 * Maps feature section id to the image filename in public/features/.
 * Note: "communications" id maps to "feature-comms.jpg" (shorter filename).
 */
const FEATURE_IMAGE_MAP: Record<string, string> = {
  "voice-ai": "feature-voice-ai.jpg",
  quoting: "feature-quoting.jpg",
  dispatch: "feature-dispatch.jpg",
  "field-ops": "feature-field-ops.jpg",
  profitability: "feature-profitability.jpg",
  communications: "feature-comms.jpg",
  invoicing: "feature-invoicing.jpg",
  quickbooks: "feature-quickbooks.jpg",
  mobile: "feature-mobile.jpg",
  security: "feature-security.jpg",
  help: "feature-help.jpg",
};

const navLabels = [
  { label: "Voice AI", anchor: "voice-ai" },
  { label: "Quoting", anchor: "quoting" },
  { label: "Dispatch", anchor: "dispatch" },
  { label: "Field Ops", anchor: "field-ops" },
  { label: "Profitability", anchor: "profitability" },
  { label: "Communications", anchor: "communications" },
  { label: "Invoicing", anchor: "invoicing" },
  { label: "QuickBooks", anchor: "quickbooks" },
  { label: "Mobile & Offline", anchor: "mobile" },
  { label: "Security", anchor: "security" },
  { label: "AI Help", anchor: "help" },
];

export default async function FeaturesPage() {
  const { isGeneralRelease } = await getSiteMode();
  const ctaText = isGeneralRelease ? "Start Free Trial" : "Be One of the First";
  const ctaHref = isGeneralRelease ? "/sign-up" : "/charter";
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
        aria-labelledby="features-hero-heading"
      >
        <div className="container-marketing text-center max-w-3xl mx-auto">
          <h1
            id="features-hero-heading"
            className="text-section-title mb-6"
            style={{ color: "var(--neutral-900)" }}
          >
            One Platform. Every Tool Your Trade Business Needs.
          </h1>
          <p
            className="text-section-subtitle mb-8"
            style={{ color: "var(--neutral-600)" }}
          >
            Voice-powered quoting, dispatch, invoicing, profitability tracking,
            and customer communications — built for contractors who work with
            their hands, not a keyboard.
          </p>

          {/* Features overview illustration */}
          <div
            className="flex items-center justify-center mb-14"
            aria-hidden="true"
          >
            <svg
              viewBox="0 0 560 200"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="w-full max-w-2xl"
            >
              {/* Voice AI */}
              <rect
                x="20"
                y="60"
                width="80"
                height="80"
                rx="16"
                fill="var(--brand-50)"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
              />
              <path
                d="M60 85a6 6 0 0 1 6 6v10a6 6 0 0 1-12 0V91a6 6 0 0 1 6-6z"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
                fill="none"
              />
              <path
                d="M50 103v2a10 10 0 0 0 20 0v-2"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
                strokeLinecap="round"
                fill="none"
              />
              <line
                x1="60"
                y1="115"
                x2="60"
                y2="120"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <text
                x="60"
                y="155"
                textAnchor="middle"
                fontSize="11"
                fill="var(--brand-600)"
                fontWeight="600"
              >
                Voice AI
              </text>

              {/* Connector */}
              <line
                x1="100"
                y1="100"
                x2="140"
                y2="100"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />

              {/* Profitability */}
              <rect
                x="140"
                y="60"
                width="80"
                height="80"
                rx="16"
                fill="var(--brand-50)"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
              />
              <polyline
                points="155,120 165,105 175,110 185,90 195,95 205,80"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
              <text
                x="180"
                y="155"
                textAnchor="middle"
                fontSize="11"
                fill="var(--brand-600)"
                fontWeight="600"
              >
                Profitability
              </text>

              {/* Connector */}
              <line
                x1="220"
                y1="100"
                x2="260"
                y2="100"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />

              {/* Dispatch */}
              <rect
                x="260"
                y="60"
                width="80"
                height="80"
                rx="16"
                fill="var(--brand-50)"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
              />
              <rect
                x="272"
                y="76"
                width="56"
                height="42"
                rx="4"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
                fill="none"
              />
              <line
                x1="272"
                y1="86"
                x2="328"
                y2="86"
                stroke="var(--brand-200)"
                strokeWidth="1"
              />
              <rect
                x="278"
                y="92"
                width="12"
                height="12"
                rx="2"
                fill="var(--brand-600)"
                opacity="0.4"
              />
              <rect
                x="294"
                y="92"
                width="12"
                height="12"
                rx="2"
                fill="var(--brand-600)"
                opacity="0.7"
              />
              <rect
                x="310"
                y="92"
                width="12"
                height="12"
                rx="2"
                fill="var(--brand-600)"
                opacity="0.4"
              />
              <text
                x="300"
                y="155"
                textAnchor="middle"
                fontSize="11"
                fill="var(--brand-600)"
                fontWeight="600"
              >
                Dispatch
              </text>

              {/* Connector */}
              <line
                x1="340"
                y1="100"
                x2="380"
                y2="100"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />

              {/* Customer Comms */}
              <rect
                x="380"
                y="60"
                width="80"
                height="80"
                rx="16"
                fill="var(--brand-50)"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
              />
              <path
                d="M392 84h36a4 4 0 0 1 4 4v18a4 4 0 0 1-4 4h-28l-8 8v-8h0a4 4 0 0 1 0-4V88a4 4 0 0 1 4-4z"
                stroke="var(--brand-600)"
                strokeWidth="1.5"
                fill="none"
              />
              <line
                x1="402"
                y1="94"
                x2="418"
                y2="94"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
              />
              <line
                x1="402"
                y1="100"
                x2="422"
                y2="100"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
              />
              <text
                x="420"
                y="155"
                textAnchor="middle"
                fontSize="11"
                fill="var(--brand-600)"
                fontWeight="600"
              >
                Comms
              </text>

              {/* Arrow to QuickBooks */}
              <line
                x1="460"
                y1="100"
                x2="500"
                y2="100"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />
              <rect
                x="500"
                y="60"
                width="40"
                height="80"
                rx="16"
                fill="var(--brand-50)"
                stroke="var(--brand-200)"
                strokeWidth="1.5"
              />
              <text
                x="520"
                y="97"
                textAnchor="middle"
                fontSize="18"
                fill="var(--brand-600)"
              >
                QB
              </text>
              <text
                x="520"
                y="155"
                textAnchor="middle"
                fontSize="11"
                fill="var(--brand-600)"
                fontWeight="600"
              >
                QuickBooks
              </text>
            </svg>
          </div>

          <Link href={ctaHref} className="btn-primary">
            {ctaText}
          </Link>
        </div>
      </section>

      {/* Sticky feature nav */}
      <nav
        className="sticky top-16 z-40 overflow-x-auto"
        style={{
          background: "var(--white)",
          borderBottom: "var(--divider-thin) solid var(--neutral-200)",
        }}
        aria-label="Feature sections"
      >
        <div className="container-marketing">
          <div className="flex gap-1 py-3 min-w-max">
            {navLabels.map((n) => (
              <a
                key={n.anchor}
                href={`#${n.anchor}`}
                className="px-4 py-2 text-sm rounded-full whitespace-nowrap no-underline transition-colors font-medium"
                style={{ color: "var(--neutral-700)" }}
              >
                {n.label}
              </a>
            ))}
          </div>
        </div>
      </nav>

      {/* Feature sections */}
      {features.map((f, idx) => (
        <section
          key={f.id}
          id={f.id}
          className="section-padding"
          style={{
            background:
              idx % 2 === 0 ? "var(--white)" : "var(--surface-marketing)",
          }}
          aria-labelledby={`${f.id}-heading`}
        >
          <div className="container-marketing">
            <div
              className={`flex flex-col ${
                idx % 2 === 0 ? "lg:flex-row" : "lg:flex-row-reverse"
              } gap-12 lg:gap-16 items-center`}
            >
              {/* Content */}
              <div className="flex-1">
                <span
                  className="text-caption-lg font-semibold uppercase tracking-wider mb-3 inline-block"
                  style={{ color: "var(--brand-600)" }}
                >
                  {f.badge}
                </span>
                <h2
                  id={`${f.id}-heading`}
                  className="text-section-title mb-5"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {f.heading}
                </h2>
                <p
                  className="text-body-lg mb-6"
                  style={{ color: "var(--neutral-700)" }}
                >
                  {f.desc}
                </p>
                <ul className="flex flex-col gap-3 list-none p-0 m-0">
                  {f.bullets.map((b) => (
                    <li key={b} className="flex items-start gap-3">
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 20 20"
                        fill="none"
                        className="mt-0.5 shrink-0"
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
                      <span
                        className="text-base"
                        style={{ color: "var(--neutral-700)" }}
                      >
                        {b}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Feature illustration image */}
              <div className="flex-1 w-full max-w-md">
                <div
                  className="w-full aspect-video rounded-2xl overflow-hidden relative"
                  style={{
                    border: "var(--divider-thin) solid var(--neutral-200)",
                  }}
                >
                  <Image
                    src={`/features/${FEATURE_IMAGE_MAP[f.id]}`}
                    alt={`${f.heading} — feature illustration`}
                    fill
                    className="object-cover object-center"
                    sizes="(max-width: 48rem) 100vw, 50vw"
                    loading={idx === 0 ? "eager" : "lazy"}
                  />
                </div>
              </div>
            </div>
          </div>
        </section>
      ))}

      {/* Bottom CTA */}
      <section
        className="section-padding"
        style={{ background: "var(--brand-600)" }}
        aria-labelledby="features-cta-heading"
      >
        <div className="container-marketing text-center">
          <h2
            id="features-cta-heading"
            className="text-section-title font-bold mb-4"
            style={{ color: "var(--white)" }}
          >
            Ready to Transform Your Field Operations?
          </h2>
          <p
            className="text-body-lg mb-10 max-w-2xl mx-auto"
            style={{ color: "var(--white-8)" }}
          >
            Join the Charter program and be among the first contractors to use
            AI-powered voice quoting, real-time profitability tracking, and
            hands-free field ops.
          </p>
          <Link href={ctaHref} className="btn-white">
            {ctaText}
          </Link>
        </div>
      </section>
    </>
  );
}
