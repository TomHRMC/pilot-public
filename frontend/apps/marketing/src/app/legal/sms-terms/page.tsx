// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "SMS Terms & Conditions",
  description:
    "SMS messaging terms for Pilot for Trades customer communications. Learn about message types, frequency, opt-out instructions, and your privacy rights.",
  openGraph: {
    title: "SMS Terms & Conditions | Pilot for Trades",
    url: "https://pilotfortrades.com/legal/sms-terms",
  },
};

export default function SmsTermsPage() {
  return (
    <section
      className="section-padding"
      style={{ background: "var(--white)" }}
      aria-labelledby="sms-terms-heading"
    >
      <div className="container-marketing max-w-3xl mx-auto">
        <div className="mb-10">
          <p className="text-sm mb-2" style={{ color: "var(--neutral-500)" }}>
            <Link href="/legal/sms-terms" style={{ color: "var(--brand-600)" }}>
              SMS Terms &amp; Conditions
            </Link>
          </p>
          <h1
            id="sms-terms-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            SMS Terms &amp; Conditions
          </h1>
          <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
            Effective Date: January 1, 2026 · Last Updated: May 20, 2026
          </p>
        </div>

        <div
          className="flex flex-col gap-10"
          style={{ color: "var(--neutral-700)" }}
        >
          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              1. Program Name
            </h2>
            <p
              className="text-base leading-relaxed font-medium"
              style={{ color: "var(--neutral-900)" }}
            >
              Pilot for Trades Customer Messaging Service
            </p>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              2. Program Description
            </h2>
            <p className="text-base leading-relaxed">
              Pilot for Trades enables trade contractors (electricians,
              plumbers, HVAC technicians) to send service-related text messages
              to their customers via SMS. These messages are transactional and
              customer-care in nature — they help you stay informed about your
              service appointments, job status, and billing.
            </p>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              3. Message Types
            </h2>
            <p className="text-base mb-4">
              When your contractor uses Pilot for Trades, you may receive the
              following types of SMS messages:
            </p>
            <ul className="flex flex-col gap-2 list-none p-0 m-0">
              {[
                [
                  "Appointment confirmations",
                  "Confirming your scheduled service date and time.",
                ],
                [
                  "Appointment reminders",
                  "Reminders before your upcoming service visit.",
                ],
                [
                  "On-my-way notifications",
                  "Letting you know your technician is en route with an estimated arrival time.",
                ],
                [
                  "Running-late notifications",
                  "Alerting you if your technician is delayed and providing an updated ETA.",
                ],
                [
                  "Arrival confirmations",
                  "Confirming your technician has arrived at the job site.",
                ],
                [
                  "Job-complete notifications",
                  "Letting you know the work has been finished.",
                ],
                [
                  "Parts-delay updates",
                  "Informing you of any delays caused by parts availability.",
                ],
                [
                  "Invoice sent notifications",
                  "Alerting you that an invoice has been sent for your review.",
                ],
                [
                  "Payment received confirmations",
                  "Confirming that your payment has been received.",
                ],
                [
                  "Payment reminders",
                  "Friendly reminders about outstanding invoices.",
                ],
                [
                  "Change-order approvals",
                  "Requesting your approval for changes to the original scope of work.",
                ],
                [
                  "Quote notifications",
                  "Notifying you that a new quote has been prepared for your review.",
                ],
                [
                  "General service updates",
                  "Other service-related communications from your contractor.",
                ],
              ].map(([label, desc]) => (
                <li key={label} className="flex items-start gap-3">
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 18 18"
                    fill="none"
                    className="mt-0.5 shrink-0"
                    aria-hidden="true"
                  >
                    <circle cx="9" cy="9" r="8" fill="var(--brand-50)" />
                    <path
                      d="M5 9l3 3 5-5"
                      stroke="var(--brand-600)"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="text-base">
                    <strong>{label}</strong> — {desc}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              4. Message Frequency
            </h2>
            <p className="text-base leading-relaxed">
              Message frequency varies based on your service appointment
              schedule. You may receive{" "}
              <strong>1–5 messages per service appointment</strong>. Ongoing
              messaging frequency depends on your contractor&apos;s
              communication preferences and the services you receive.
            </p>
            <p className="text-base leading-relaxed mt-3">
              You will not receive marketing, promotional, or advertising
              messages through this program. All messages are service-related.
            </p>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              5. Opt-In / Consent
            </h2>
            <p className="text-base leading-relaxed">
              By providing your phone number to a Pilot for Trades contractor,
              you consent to receive service-related SMS messages from that
              contractor via the Pilot for Trades platform.
            </p>
            <p className="text-base leading-relaxed mt-3">
              You can opt in to receive SMS messages when:
            </p>
            <ul className="flex flex-col gap-2 mt-3 list-none p-0 m-0 ml-4">
              {[
                [
                  "Scheduling a service",
                  "You provide your phone number and agree to receive text updates during the booking process.",
                ],
                [
                  "Providing contact information",
                  "You share your phone number with your contractor and consent to text communications.",
                ],
                [
                  "Requesting service updates",
                  "You ask your contractor to send you text notifications about your job.",
                ],
              ].map(([label, desc]) => (
                <li key={label} className="flex items-start gap-3">
                  <span
                    className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: "var(--brand-600)" }}
                    aria-hidden="true"
                  />
                  <span className="text-base">
                    <strong>{label}</strong> — {desc}
                  </span>
                </li>
              ))}
            </ul>
            <p className="text-base leading-relaxed mt-3">
              Your contractor records your consent in the Pilot for Trades
              platform, including the date, time, and source of your opt-in.
            </p>
            <p className="text-base leading-relaxed mt-3">
              Consent to receive SMS messages is not a condition of purchasing
              any services from your contractor.
            </p>
          </div>

          <div
            className="rounded-xl p-6"
            style={{
              background: "var(--margin-50)",
              border: "var(--divider-thin) solid var(--margin-400)",
            }}
          >
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              6. Opt-Out / STOP
            </h2>
            <p
              className="text-base leading-relaxed font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              You can opt out at any time.
            </p>
            <p className="text-base leading-relaxed">
              To stop receiving SMS messages from Pilot for Trades, reply{" "}
              <strong>STOP</strong> to any message you receive. You will receive
              a single confirmation message:
            </p>
            <blockquote
              className="mt-3 p-4 rounded-lg text-sm italic"
              style={{
                background: "var(--white)",
                border: "var(--divider-thin) solid var(--margin-200)",
              }}
            >
              &ldquo;You&apos;ve been unsubscribed from Pilot for Trades
              messages. You will not receive any more texts. Reply START to
              re-subscribe.&rdquo;
            </blockquote>
            <p className="text-base leading-relaxed mt-3">
              After opting out, no further messages will be sent to your phone
              number unless you choose to re-subscribe. You can also contact
              your contractor directly or email us at{" "}
              <a
                href="mailto:support@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                support@pilotfortrades.com
              </a>
              .
            </p>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              7. HELP
            </h2>
            <p className="text-base leading-relaxed">
              For help with SMS messages from Pilot for Trades:
            </p>
            <ul className="mt-3 flex flex-col gap-2 list-none p-0 m-0">
              <li className="text-base">
                <strong>Reply HELP</strong> to any message you receive.
              </li>
              <li className="text-base">
                <strong>Email:</strong>{" "}
                <a
                  href="mailto:support@pilotfortrades.com"
                  style={{ color: "var(--brand-600)" }}
                >
                  support@pilotfortrades.com
                </a>
              </li>
            </ul>
            <p className="text-base leading-relaxed mt-3">
              You will receive a response message:
            </p>
            <blockquote
              className="mt-3 p-4 rounded-lg text-sm italic"
              style={{
                background: "var(--neutral-50)",
                border: "var(--divider-thin) solid var(--neutral-200)",
              }}
            >
              &ldquo;Pilot for Trades SMS Help: For support, visit
              pilotfortrades.com/contact or email support@pilotfortrades.com. To
              opt out, reply STOP.&rdquo;
            </blockquote>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              8. Cost Disclosure
            </h2>
            <p className="text-base leading-relaxed">
              <strong>Message and data rates may apply.</strong> Pilot for
              Trades does not charge consumers for receiving SMS messages, but
              standard carrier messaging rates may apply depending on your
              mobile plan. Check with your wireless carrier for details about
              your text messaging plan.
            </p>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              9. Carrier Disclaimer
            </h2>
            <p className="text-base leading-relaxed">
              Carriers (AT&amp;T, T-Mobile, Verizon, and others) are not liable
              for delayed or undelivered messages. Message delivery is subject
              to effective transmission by your wireless carrier. Pilot for
              Trades is not responsible for messages that are not delivered due
              to carrier network issues, device incompatibility, or other
              factors outside our control.
            </p>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              10. Privacy
            </h2>
            <p className="text-base leading-relaxed">
              Your phone number and messaging data are handled in accordance
              with our{" "}
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
              </Link>
              .
            </p>
            <ul className="flex flex-col gap-2 mt-3 list-none p-0 m-0 ml-4">
              {[
                "We collect and store your phone number, opt-in consent records, and message delivery status.",
                "Your phone number is used exclusively for service-related communications initiated by your contractor.",
                "We do not sell, rent, or share your phone number with third parties for marketing purposes.",
                "Phone numbers are shared only with our SMS delivery partner (Telnyx) for the sole purpose of message delivery.",
                "SMS opt-in records and message delivery logs are retained for the duration of the contractor-customer relationship plus 90 days.",
                "Opt-out records are retained indefinitely to ensure compliance.",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span
                    className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: "var(--brand-600)" }}
                    aria-hidden="true"
                  />
                  <span className="text-base">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              11. Supported Carriers
            </h2>
            <p className="text-base leading-relaxed mb-3">
              Major US carriers are supported, including but not limited to:
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                "AT&T",
                "T-Mobile",
                "Verizon",
                "US Cellular",
                "Sprint (T-Mobile)",
                "Cricket Wireless",
                "MetroPCS",
                "Boost Mobile",
                "Mint Mobile",
                "Google Fi",
                "Visible",
              ].map((carrier) => (
                <span
                  key={carrier}
                  className="px-3 py-1 rounded-full text-sm"
                  style={{
                    background: "var(--neutral-100)",
                    color: "var(--neutral-700)",
                  }}
                >
                  {carrier}
                </span>
              ))}
            </div>
            <p className="text-sm mt-3" style={{ color: "var(--neutral-500)" }}>
              Carrier support and message deliverability may vary. Not all
              carriers support all message types.
            </p>
          </div>

          <div>
            <h2
              className="text-xl font-semibold mb-3"
              style={{ color: "var(--neutral-900)" }}
            >
              12. Contact Information
            </h2>
            <p className="text-base leading-relaxed">
              <strong>Pilot for Trades</strong>
              <br />
              Email:{" "}
              <a
                href="mailto:support@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                support@pilotfortrades.com
              </a>
              <br />
              Website:{" "}
              <a
                href="https://pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                pilotfortrades.com
              </a>
            </p>
            <p className="text-base leading-relaxed mt-3">
              If you have any questions about these SMS Terms &amp; Conditions,
              please contact us at{" "}
              <a
                href="mailto:support@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                support@pilotfortrades.com
              </a>
              .
            </p>
          </div>

          <div
            className="pt-6"
            style={{
              borderTop: "var(--divider-thin) solid var(--neutral-200)",
            }}
          >
            <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
              See also:{" "}
              <Link href="/sms-opt-in" style={{ color: "var(--brand-600)" }}>
                SMS Opt-In Disclosure
              </Link>{" "}
              ·{" "}
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
              </Link>{" "}
              ·{" "}
              <Link href="/legal/terms" style={{ color: "var(--brand-600)" }}>
                Terms of Service
              </Link>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
