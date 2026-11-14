// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "End User License Agreement (EULA) | Pilot for Trades",
  description:
    "End User License Agreement for Pilot for Trades mobile and web applications. Understand your rights and obligations when using our software.",
  openGraph: {
    title: "End User License Agreement (EULA) | Pilot for Trades",
    description:
      "End User License Agreement for Pilot for Trades mobile and web applications.",
    url: "https://pilotfortrades.com/legal/eula",
  },
};

export default function EulaPage() {
  return (
    <section
      className="section-padding"
      style={{ background: "var(--white)" }}
      aria-labelledby="eula-heading"
    >
      <div className="container-marketing max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <p className="text-sm mb-2" style={{ color: "var(--neutral-500)" }}>
            <Link href="/legal/eula" style={{ color: "var(--brand-600)" }}>
              Legal
            </Link>{" "}
            / End User License Agreement
          </p>
          <h1
            id="eula-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            End User License Agreement
          </h1>
          <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
            Effective Date: January 1, 2026 · Last Updated: May 20, 2026
          </p>
        </div>

        {/* Intro */}
        <div className="mb-8" style={{ color: "var(--neutral-700)" }}>
          <p className="text-base leading-relaxed">
            This End User License Agreement (&ldquo;EULA&rdquo;) is a legal
            agreement between you (either an individual or a single business
            entity) and Pilot for Trades (&ldquo;Pilot,&rdquo; &ldquo;we,&rdquo;
            &ldquo;us,&rdquo; or &ldquo;our&rdquo;) governing your use of the
            Pilot for Trades software application, including any associated
            media, documentation, and internet-based services (collectively, the
            &ldquo;Application&rdquo;).
          </p>
          <p className="mt-3 text-base leading-relaxed">
            By installing, accessing, or using the Application, you agree to be
            bound by the terms of this EULA. If you do not agree, do not install
            or use the Application.
          </p>
        </div>

        <div
          className="flex flex-col gap-10"
          style={{ color: "var(--neutral-700)" }}
        >
          <LegalSection title="1. License Grant">
            <p>
              Subject to your compliance with this EULA and the{" "}
              <Link href="/legal/terms" style={{ color: "var(--brand-600)" }}>
                Terms of Service
              </Link>
              , Pilot for Trades grants you a limited, non-exclusive,
              non-transferable, revocable license to:
            </p>
            <ul className="list-disc pl-6 mt-3 space-y-1">
              <li>
                Install and use the Application on devices owned or controlled
                by you or your authorized employees, up to the user limit
                specified by your subscription plan
              </li>
              <li>
                Access and use the web-based version of the Application via
                supported browsers
              </li>
              <li>
                Use the Application for your internal business operations as a
                trade contractor
              </li>
            </ul>
            <p className="mt-3">
              <strong>License contingency:</strong> This license is contingent
              upon maintaining an active, paid subscription. If your
              subscription lapses or is terminated, this license is
              automatically revoked.
            </p>
          </LegalSection>

          <LegalSection title="2. License Restrictions">
            <p>You agree NOT to:</p>
            <ul className="list-disc pl-6 mt-3 space-y-1">
              <li>
                Reverse engineer, decompile, or disassemble the Application
              </li>
              <li>
                Modify, adapt, or create derivative works based on the
                Application
              </li>
              <li>
                Redistribute, rent, lease, or lend the Application to third
                parties
              </li>
              <li>
                Circumvent any security measures, access controls, or licensing
                mechanisms
              </li>
              <li>
                Use the Application for competitive analysis or to build a
                competing product
              </li>
              <li>
                Use automated tools (bots, scrapers) to access the Application
                beyond the provided APIs
              </li>
              <li>
                Remove or alter any proprietary notices, labels, or marks on the
                Application
              </li>
            </ul>
          </LegalSection>

          <LegalSection title="3. Intellectual Property">
            <p>
              <strong>Pilot&apos;s ownership:</strong> The Application,
              including all software code, algorithms, AI models, user interface
              designs, and associated intellectual property, is the exclusive
              property of Pilot for Trades. This EULA does not transfer any
              ownership interest in the Application to you.
            </p>
            <p className="mt-3">
              <strong>AI-generated content:</strong> Quotes, estimates,
              calculations, and suggestions generated by the Application&apos;s
              AI features are produced using your input data and Pilot&apos;s AI
              models. You own the final versions of documents (quotes, invoices,
              estimates) you create. Pilot and its licensors retain ownership of
              the underlying AI models, algorithms, and processing logic.
            </p>
            <p className="mt-3">
              <strong>Voice recordings:</strong> Voice recordings submitted to
              the Application are processed for transcription and intent
              extraction. Recordings are retained for 90 days for AI accuracy
              improvement, then automatically purged. You may request immediate
              deletion at any time.
            </p>
            <p className="mt-3">
              <strong>Feedback:</strong> If you provide feedback, feature
              requests, or suggestions, you grant Pilot for Trades a perpetual,
              irrevocable, royalty-free license to use such feedback for product
              improvement.
            </p>
          </LegalSection>

          <LegalSection title="4. User Data Ownership">
            <p>
              <strong>Your data:</strong> You retain full ownership of all
              business data you enter into the Application, including customer
              records, quotes, invoices, job records, photos, documents,
              financial data, and communication records.
            </p>
            <p className="mt-3">
              <strong>Limited processing license:</strong> By using the
              Application, you grant Pilot for Trades a limited, non-exclusive
              license to process, store, transmit, and display your data solely
              for the purpose of providing the Service. This license terminates
              when you delete your data or close your account.
            </p>
            <p className="mt-3">
              <strong>Data export:</strong> You may export your data at any time
              using the Application&apos;s built-in export features (CSV, PDF,
              JSON). Upon account termination, you have 30 days to export your
              data before it is permanently deleted.
            </p>
          </LegalSection>

          <LegalSection title="5. Subscription and Payments">
            <p>
              Use of the Application requires an active subscription as
              described in the{" "}
              <Link href="/legal/terms" style={{ color: "var(--brand-600)" }}>
                Terms of Service
              </Link>{" "}
              §4. The license granted by this EULA is contingent upon
              maintaining a paid subscription in good standing.
            </p>
            <p className="mt-3">
              <strong>Effect of non-payment:</strong> If subscription payment
              fails and is not resolved: (1) account suspended for 14 days; (2)
              if unresolved, account terminated; (3) 30-day window to export
              data; (4) data permanently deleted after export window.
            </p>
          </LegalSection>

          <LegalSection title="6. Updates and Modifications">
            <p>
              Pilot for Trades may update the Application at any time to add
              features, improve performance, fix bugs, or comply with legal
              requirements.
            </p>
            <p className="mt-3">
              <strong>Feature changes notice:</strong>
            </p>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>
                Core features (quoting, dispatch, invoicing, profitability
                tracking): 90 days&apos; notice before removal
              </li>
              <li>Secondary features: 30 days&apos; notice</li>
              <li>
                Bug fixes and security updates: may be applied without prior
                notice
              </li>
            </ul>
          </LegalSection>

          <LegalSection title="7. Third-Party Components">
            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              7.1 Open-Source Software
            </h3>
            <p>
              The Application includes open-source software components licensed
              under various licenses (MIT, Apache 2.0, BSD, etc.). A complete
              list is available upon request at{" "}
              <a
                href="mailto:legal@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                legal@pilotfortrades.com
              </a>
              .
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              7.2 Third-Party Services
            </h3>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr style={{ background: "var(--neutral-100)" }}>
                    <th
                      className="text-left p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Service
                    </th>
                    <th
                      className="text-left p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Provider
                    </th>
                    <th
                      className="text-left p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Purpose
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    [
                      "QuickBooks Online",
                      "Intuit, Inc.",
                      "Accounting synchronization",
                    ],
                    ["Stripe", "Stripe, Inc.", "Payment processing"],
                    ["Telnyx", "Telnyx LLC", "SMS message delivery"],
                    [
                      "Google Calendar",
                      "Google LLC",
                      "Calendar synchronization",
                    ],
                  ].map(([service, provider, purpose]) => (
                    <tr key={service}>
                      <td
                        className="p-2 border"
                        style={{ borderColor: "var(--neutral-200)" }}
                      >
                        {service}
                      </td>
                      <td
                        className="p-2 border"
                        style={{ borderColor: "var(--neutral-200)" }}
                      >
                        {provider}
                      </td>
                      <td
                        className="p-2 border"
                        style={{ borderColor: "var(--neutral-200)" }}
                      >
                        {purpose}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </LegalSection>

          <LegalSection title="8. Disclaimer of Warranties">
            <p className="uppercase text-sm leading-relaxed">
              THE APPLICATION IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS
              AVAILABLE&rdquo; WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
              IMPLIED.
            </p>
            <p className="mt-3">
              Pilot for Trades specifically disclaims any warranty of: AI
              accuracy (no warranty that AI-generated estimates, quotes, or
              calculations are accurate or complete); code compliance (no
              warranty that NEC, UPC, or other code references are current or
              applicable to your jurisdiction — you are responsible for
              verifying code compliance); material pricing (pricing is a
              reference and should be verified with your distributor); and
              uninterrupted operation.
            </p>
            <p className="mt-3 uppercase text-sm leading-relaxed font-semibold">
              THE APPLICATION IS A TOOL TO ASSIST YOUR PROFESSIONAL WORK. IT
              DOES NOT REPLACE YOUR PROFESSIONAL JUDGMENT, TRADE LICENSING, OR
              RESPONSIBILITY TO YOUR CUSTOMERS.
            </p>
          </LegalSection>

          <LegalSection title="9. Limitation of Liability">
            <p className="uppercase text-sm leading-relaxed">
              TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, PILOT FOR
              TRADES&apos; TOTAL AGGREGATE LIABILITY FOR ALL CLAIMS ARISING OUT
              OF OR RELATED TO THIS EULA SHALL NOT EXCEED THE TOTAL AMOUNT YOU
              PAID TO PILOT FOR TRADES IN THE TWELVE (12) MONTHS IMMEDIATELY
              PRECEDING THE EVENT GIVING RISE TO THE CLAIM.
            </p>
            <p className="mt-3 uppercase text-sm leading-relaxed">
              IN NO EVENT SHALL PILOT FOR TRADES BE LIABLE FOR ANY INDIRECT,
              INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING
              LOSS OF PROFITS, REVENUE, DATA, OR BUSINESS INTERRUPTION.
            </p>
          </LegalSection>

          <LegalSection title="10. Termination">
            <p>
              <strong>Termination by you:</strong> You may terminate this EULA
              at any time by uninstalling the Application, canceling your
              subscription, or requesting account deletion.
            </p>
            <p className="mt-3">
              <strong>Effect of termination:</strong> Your license to use the
              Application is immediately revoked. You must uninstall the
              Application from all devices. You have 30 days to export your
              data, after which it will be permanently deleted.
            </p>
          </LegalSection>

          <LegalSection title="11. Governing Law and Dispute Resolution">
            <p>
              This EULA is governed by the laws of the State of Colorado,
              without regard to its conflict of law principles. Disputes are
              subject to the dispute resolution provisions in the{" "}
              <Link href="/legal/terms" style={{ color: "var(--brand-600)" }}>
                Terms of Service
              </Link>{" "}
              §13, including the binding arbitration clause and class action
              waiver.
            </p>
          </LegalSection>

          <LegalSection title="12. General Provisions">
            <p>
              This EULA, together with the{" "}
              <Link href="/legal/terms" style={{ color: "var(--brand-600)" }}>
                Terms of Service
              </Link>
              ,{" "}
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
              </Link>
              , and{" "}
              <Link
                href="/legal/sms-terms"
                style={{ color: "var(--brand-600)" }}
              >
                SMS Terms
              </Link>
              , constitutes the entire agreement between you and Pilot for
              Trades regarding your use of the Application. In the event of a
              conflict between this EULA and the Terms of Service, the Terms of
              Service shall control.
            </p>
          </LegalSection>

          <LegalSection title="13. Contact Information">
            <p>
              <strong>Pilot for Trades</strong>
            </p>
            <p className="mt-2">
              Legal inquiries:{" "}
              <a
                href="mailto:legal@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                legal@pilotfortrades.com
              </a>
            </p>
            <p>
              Support:{" "}
              <a
                href="mailto:support@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                support@pilotfortrades.com
              </a>
            </p>
            <p>
              Website:{" "}
              <Link href="/" style={{ color: "var(--brand-600)" }}>
                pilotfortrades.com
              </Link>
            </p>
          </LegalSection>

          {/* Footer links */}
          <div
            className="pt-6"
            style={{
              borderTop: "var(--divider-thin) solid var(--neutral-200)",
            }}
          >
            <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
              Related:{" "}
              <Link href="/legal/terms" style={{ color: "var(--brand-600)" }}>
                Terms of Service
              </Link>
              {" · "}
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
              </Link>
              {" · "}
              <Link
                href="/legal/sms-terms"
                style={{ color: "var(--brand-600)" }}
              >
                SMS Terms
              </Link>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function LegalSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h2
        className="text-xl font-semibold mb-3"
        style={{ color: "var(--neutral-900)" }}
      >
        {title}
      </h2>
      <div className="text-base leading-relaxed">{children}</div>
    </div>
  );
}
