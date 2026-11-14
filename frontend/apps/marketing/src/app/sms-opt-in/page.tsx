// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "SMS Opt-In Disclosure — What You're Signing Up For",
  description:
    "Learn what SMS messages you'll receive from your contractor through Pilot for Trades, how to opt out, and how your information is protected.",
  openGraph: {
    title: "SMS Opt-In Disclosure | Pilot for Trades",
    url: "https://pilotfortrades.com/sms-opt-in",
  },
};

export default function SmsOptInPage() {
  return (
    <>
      {/* Hero */}
      <section
        className="section-padding"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="sms-optin-heading"
      >
        <div className="container-marketing max-w-3xl mx-auto text-center">
          <h1
            id="sms-optin-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            SMS Text Message Disclosure
          </h1>
          <p
            className="text-section-subtitle"
            style={{ color: "var(--neutral-600)" }}
          >
            This page explains what happens when your contractor sends you text
            messages through Pilot for Trades.
          </p>
        </div>
      </section>

      {/* Content */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-label="SMS disclosure content"
      >
        <div className="container-marketing max-w-3xl mx-auto">
          <div
            className="flex flex-col gap-10"
            style={{ color: "var(--neutral-700)" }}
          >
            {/* 1 */}
            <div
              className="rounded-xl p-6"
              style={{
                background: "var(--brand-50)",
                border: "var(--divider-thin) solid var(--brand-200)",
              }}
            >
              <h2
                className="text-xl font-semibold mb-4"
                style={{ color: "var(--neutral-900)" }}
              >
                1. What You&apos;re Signing Up For
              </h2>
              <p className="text-base leading-relaxed mb-4">
                When you provide your phone number to a contractor who uses
                Pilot for Trades, you may receive service-related text messages
                including:
              </p>
              <ul className="flex flex-col gap-2 list-none p-0 m-0">
                {[
                  [
                    "Appointment confirmations and reminders",
                    "So you know when to expect your technician.",
                  ],
                  [
                    "Estimated arrival times",
                    '"Your electrician is 20 minutes away."',
                  ],
                  [
                    "Job status updates",
                    "Running late, arrived, work complete.",
                  ],
                  [
                    "Invoice and payment notifications",
                    "When an invoice is ready or a payment is received.",
                  ],
                  [
                    "Change-order requests",
                    "If the scope of work changes and your approval is needed.",
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
                      <circle cx="9" cy="9" r="8" fill="var(--brand-100)" />
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
              <p
                className="text-base leading-relaxed mt-4 font-medium"
                style={{ color: "var(--neutral-900)" }}
              >
                All messages are service-related. You will{" "}
                <strong>never</strong> receive marketing, advertising, or
                promotional texts through this program.
              </p>
            </div>

            {/* 2 */}
            <div>
              <h2
                className="text-xl font-semibold mb-4"
                style={{ color: "var(--neutral-900)" }}
              >
                2. How Opt-In Works
              </h2>
              <p className="text-base leading-relaxed mb-4">
                You opt in to receive SMS messages when:
              </p>
              <ol className="flex flex-col gap-3 list-none p-0 m-0">
                {[
                  "You provide your phone number to your contractor and agree to receive text updates — verbally, in writing, or through a digital form.",
                  'You request service notifications during the scheduling process — for example, "Text me when you\'re on the way."',
                  "Your contractor adds your contact information to the Pilot for Trades platform with your verbal or written consent.",
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-4">
                    <span
                      className="w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
                      style={{
                        background: "var(--brand-600)",
                        color: "var(--white)",
                      }}
                    >
                      {String.fromCharCode(97 + i)}
                    </span>
                    <span className="text-base pt-0.5">{item}</span>
                  </li>
                ))}
              </ol>
              <p className="text-base leading-relaxed mt-4">
                Your contractor records your opt-in consent in the Pilot for
                Trades platform, including the timestamp and source of your
                consent. Consent to receive messages is not required to receive
                services.
              </p>
            </div>

            {/* 3 */}
            <div>
              <h2
                className="text-xl font-semibold mb-3"
                style={{ color: "var(--neutral-900)" }}
              >
                3. Message Frequency
              </h2>
              <p className="text-base leading-relaxed">
                You may receive{" "}
                <strong>1–5 messages per service appointment</strong>. Message
                frequency varies based on your service schedule and the types of
                updates your contractor sends. You won&apos;t receive more than
                necessary.
              </p>
            </div>

            {/* 4 — Opt-out highlighted */}
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
                4. Opt-Out Instructions
              </h2>
              <p className="text-base leading-relaxed">
                <strong>Reply STOP</strong> to any message to unsubscribe. You
                will receive a single confirmation message and no further texts
                will be sent.
              </p>
              <p className="text-base leading-relaxed mt-3">
                You can re-opt-in at any time by contacting your contractor and
                asking to be added back to text notifications, or by replying{" "}
                <strong>START</strong> to the last number that messaged you.
              </p>
            </div>

            {/* 5 */}
            <div>
              <h2
                className="text-xl font-semibold mb-3"
                style={{ color: "var(--neutral-900)" }}
              >
                5. Help
              </h2>
              <p className="text-base leading-relaxed">
                <strong>Reply HELP</strong> to any message for assistance, or
                email{" "}
                <a
                  href="mailto:support@pilotfortrades.com"
                  style={{ color: "var(--brand-600)" }}
                >
                  support@pilotfortrades.com
                </a>
                .
              </p>
              <p className="text-base leading-relaxed mt-2">
                We&apos;ll respond with instructions on how to manage your
                messaging preferences.
              </p>
            </div>

            {/* 6 */}
            <div>
              <h2
                className="text-xl font-semibold mb-3"
                style={{ color: "var(--neutral-900)" }}
              >
                6. Cost
              </h2>
              <p className="text-base leading-relaxed">
                <strong>Message and data rates may apply.</strong> Pilot for
                Trades does not charge you for receiving messages, but your
                wireless carrier may charge standard messaging rates based on
                your plan.
              </p>
            </div>

            {/* 7 */}
            <div>
              <h2
                className="text-xl font-semibold mb-3"
                style={{ color: "var(--neutral-900)" }}
              >
                7. Privacy
              </h2>
              <p className="text-base leading-relaxed mb-3">
                Your information is protected under our{" "}
                <Link
                  href="/legal/privacy"
                  style={{ color: "var(--brand-600)" }}
                >
                  Privacy Policy
                </Link>
                .
              </p>
              <ul className="flex flex-col gap-2 list-none p-0 m-0">
                {[
                  "We do not sell your phone number or share it for marketing purposes.",
                  "Your number is used only for service-related messages initiated by your contractor.",
                  "We share your number only with our SMS delivery partner (Telnyx) to deliver messages.",
                  "You can request deletion of your data by emailing support@pilotfortrades.com.",
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

            {/* 8 */}
            <div>
              <h2
                className="text-xl font-semibold mb-3"
                style={{ color: "var(--neutral-900)" }}
              >
                8. Contact
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
                Questions about SMS messages? Email us at{" "}
                <a
                  href="mailto:support@pilotfortrades.com"
                  style={{ color: "var(--brand-600)" }}
                >
                  support@pilotfortrades.com
                </a>{" "}
                and we&apos;ll help.
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
                <Link
                  href="/legal/sms-terms"
                  style={{ color: "var(--brand-600)" }}
                >
                  SMS Terms &amp; Conditions
                </Link>{" "}
                ·{" "}
                <Link
                  href="/legal/privacy"
                  style={{ color: "var(--brand-600)" }}
                >
                  Privacy Policy
                </Link>
              </p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
