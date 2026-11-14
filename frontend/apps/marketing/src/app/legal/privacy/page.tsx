// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy | Pilot for Trades",
  description:
    "Privacy Policy for Pilot for Trades — learn how we collect, use, and protect your data. Your business data is yours. We don't sell it. Period.",
  openGraph: {
    title: "Privacy Policy | Pilot for Trades",
    description:
      "Privacy Policy for Pilot for Trades — learn how we collect, use, and protect your data.",
    url: "https://pilotfortrades.com/legal/privacy",
  },
};

export default function PrivacyPage() {
  return (
    <section
      className="section-padding"
      style={{ background: "var(--white)" }}
      aria-labelledby="privacy-heading"
    >
      <div className="container-marketing max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <p className="text-sm mb-2" style={{ color: "var(--neutral-500)" }}>
            <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
              Legal
            </Link>{" "}
            / Privacy Policy
          </p>
          <h1
            id="privacy-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            Privacy Policy
          </h1>
          <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
            Effective Date: January 1, 2026 · Last Updated: May 20, 2026
          </p>
        </div>

        {/* Intro */}
        <div className="mb-8" style={{ color: "var(--neutral-700)" }}>
          <p className="text-base leading-relaxed">
            Pilot for Trades (operated by Example Holdings,
            LLC) (&ldquo;Pilot,&rdquo; &ldquo;we,&rdquo;
            &ldquo;us,&rdquo; or &ldquo;our&rdquo;) is committed to protecting
            the privacy of our users and their customers. This Privacy Policy
            describes how we collect, use, store, and share information when you
            use the Pilot for Trades platform, including our website at
            pilotfortrades.com, mobile applications, and related services
            (collectively, the &ldquo;Service&rdquo;).
          </p>
          <p className="mt-3 text-base leading-relaxed">
            By using the Service, you agree to the collection and use of
            information as described in this Privacy Policy.
          </p>
        </div>

        <div
          className="flex flex-col gap-10"
          style={{ color: "var(--neutral-700)" }}
        >
          <LegalSection title="1. Information We Collect">
            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              1.1 Account Information
            </h3>
            <p>
              When you create an account, we collect: name, email address, and
              phone number; business name and trade type (electrical, plumbing,
              HVAC); company size and business address; password (stored in
              hashed form — we never store plaintext passwords).
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              1.2 Business Data
            </h3>
            <p>
              When you use the Service for your business operations, we process:
              quotes and estimates; customer records; job records; financial
              data; photos and documents; and voice data submitted for AI
              quoting (processed for transcription and intent extraction).
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              1.3 Usage Data
            </h3>
            <p>
              We automatically collect: pages and features used; device
              information; IP address and approximate geographic location;
              session duration and feature engagement metrics; error logs and
              crash reports.
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              1.4 Payment Information
            </h3>
            <p>
              Payment processing is handled by Stripe, Inc. Pilot for Trades
              does <strong>not</strong> store your full credit card number, CVV,
              or other sensitive payment credentials. Stripe handles all payment
              data in accordance with PCI DSS Level 1 compliance.
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              1.5 Charter Application and Marketing Data
            </h3>
            <p>
              When you apply to the Charter program or subscribe to
              communications, we collect: email address, trade type and company
              size, signup source and UTM parameters, and newsletter
              subscription preferences.
            </p>
          </LegalSection>

          <LegalSection title="2. How We Use Your Information">
            <p>
              We use collected information for: providing and operating the
              Service; improving and developing new features; sending
              service-related and marketing communications (with your consent);
              and security, fraud prevention, and legal compliance.
            </p>
            <p className="mt-3">
              <strong>We do NOT:</strong> sell your data to third parties, serve
              advertisements based on your business data, or market unrelated
              products without your consent.
            </p>
          </LegalSection>

          <LegalSection title="3. How We Share Your Information">
            <p>
              We do not sell, rent, or trade your personal information. We share
              information only in the following limited circumstances:
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              3.1 Service Providers
            </h3>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr style={{ background: "var(--neutral-100)" }}>
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
                    <th
                      className="text-left p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Data Shared
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Stripe (Stripe, Inc.)
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Payment processing
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Payment method, billing address, invoice amounts
                    </td>
                  </tr>
                  <tr>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Telnyx (Telnyx LLC)
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      SMS message delivery
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Customer phone numbers, message content
                    </td>
                  </tr>
                  <tr>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Amazon Web Services
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Cloud hosting and storage
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      All Service data (encrypted in transit between your devices and the Service; database and file storage encrypted at rest)
                    </td>
                  </tr>
                  <tr>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      SendGrid (Twilio Inc.)
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Transactional email delivery
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Email addresses, email content
                    </td>
                  </tr>
                  <tr>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      OpenAI, L.L.C.
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Help-search embeddings
                    </td>
                    <td
                      className="p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Help search query text
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              3.2 QuickBooks Integration
            </h3>
            <p>
              When you authorize the QuickBooks Online integration, we share
              invoice data, payment records, and customer records with Intuit,
              Inc. as necessary for the synchronization you requested.
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              3.3 Legal Requirements
            </h3>
            <p>
              We may disclose your information if required by law, regulation,
              legal process, or governmental request. We will notify you of such
              requests when legally permitted to do so.
            </p>
          </LegalSection>

          <LegalSection title="4. SMS Data (A2P 10DLC Compliance)">
            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              4.1 SMS Data Collection
            </h3>
            <p>
              When a contractor&apos;s customer provides a phone number and opts
              in to SMS communications, we collect and store: phone number;
              opt-in timestamp; opt-in source; message delivery status; and
              opt-out records.
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              4.2 SMS Data Usage
            </h3>
            <p>
              Phone numbers are used <strong>exclusively</strong> for
              service-related communications initiated by the customer&apos;s
              contractor through the Pilot for Trades platform. These include
              appointment confirmations, job status updates, parts delay
              notifications, invoice and payment notifications, and change-order
              approvals.
            </p>
            <p className="mt-2">
              We <strong>do not</strong> use customer phone numbers for
              marketing, advertising, or promotional purposes.
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              4.3 SMS Data Sharing
            </h3>
            <p>
              We <strong>do not sell, rent, or share</strong> customer phone
              numbers with third parties for marketing purposes. Phone numbers
              are shared only with our SMS carrier (Telnyx) for the sole purpose
              of message delivery.
            </p>
            <p className="mt-2">
              We do not share mobile phone numbers or SMS messaging opt-in data
              with third parties or affiliates for marketing or promotional
              purposes.
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              4.4 SMS Data Retention
            </h3>
            <ul className="list-disc pl-6 mt-2 space-y-1">
              <li>
                SMS opt-in records and message delivery logs are retained for
                the duration of the contractor-customer relationship plus 90
                days.
              </li>
              <li>
                Opt-out records are retained indefinitely to ensure compliance
                with do-not-contact requests.
              </li>
              <li>
                Message content logs are retained for 90 days after delivery,
                then automatically purged.
              </li>
            </ul>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              4.5 SMS Opt-Out
            </h3>
            <p>
              Customers may opt out of SMS communications at any time by
              replying <strong>STOP</strong> to any message, contacting their
              contractor, or emailing{" "}
              <a
                href="mailto:legal@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                legal@pilotfortrades.com
              </a>
              . See our{" "}
              <Link
                href="/legal/sms-terms"
                style={{ color: "var(--brand-600)" }}
              >
                SMS Terms
              </Link>{" "}
              for complete terms.
            </p>
          </LegalSection>

          <LegalSection title="5. Data Security">
            <p>We implement industry-standard security measures including:</p>
            <ul className="list-disc pl-6 mt-3 space-y-1">
              <li>
                <strong>Encryption:</strong> Data encrypted in transit between
                your devices and the Service (TLS 1.2+); the database, file storage and secrets encrypted at
                rest (AES-256)
              </li>
              <li>
                <strong>Access control:</strong> MFA available on all accounts;
                role-based access control (RBAC) limits data access by user role
              </li>
              <li>
                <strong>Infrastructure:</strong> Multi-tenant data isolation;
                DDoS protection via AWS CloudFront (AWS Shield Standard)
              </li>
              <li>
                <strong>Incident response:</strong> We will notify you within 72
                hours of discovering a data breach affecting your personal
                information
              </li>
            </ul>
          </LegalSection>

          <LegalSection title="6. Data Retention">
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr style={{ background: "var(--neutral-100)" }}>
                    <th
                      className="text-left p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Data Type
                    </th>
                    <th
                      className="text-left p-2 border"
                      style={{ borderColor: "var(--neutral-200)" }}
                    >
                      Retention Period
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Active account data", "Duration of active subscription"],
                    [
                      "Closed account data",
                      "30 days after closure (data export window), then permanently deleted",
                    ],
                    [
                      "Voice recordings",
                      "90 days after processing, then automatically purged",
                    ],
                    ["Audit logs", "2 years"],
                    ["Payment records", "7 years (tax/financial regulation)"],
                    ["SMS opt-out records", "Indefinitely (compliance)"],
                  ].map(([type, period]) => (
                    <tr key={type}>
                      <td
                        className="p-2 border"
                        style={{ borderColor: "var(--neutral-200)" }}
                      >
                        {type}
                      </td>
                      <td
                        className="p-2 border"
                        style={{ borderColor: "var(--neutral-200)" }}
                      >
                        {period}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </LegalSection>

          <LegalSection title="7. Your Rights">
            <p>
              You have the following rights regarding your personal information:
            </p>
            <ul className="list-disc pl-6 mt-3 space-y-2">
              <li>
                <strong>Right to access:</strong> Request a copy of the personal
                information we hold about you by contacting{" "}
                <a
                  href="mailto:privacy@pilotfortrades.com"
                  style={{ color: "var(--brand-600)" }}
                >
                  privacy@pilotfortrades.com
                </a>
                .
              </li>
              <li>
                <strong>Right to correction:</strong> Update your account
                information at any time through the Service.
              </li>
              <li>
                <strong>Right to deletion:</strong> Request deletion of your
                account and personal data. We will process deletion requests
                within 30 days.
              </li>
              <li>
                <strong>Right to data portability:</strong> Export your data at
                any time through the Service&apos;s built-in export features
                (CSV, PDF, or JSON).
              </li>
              <li>
                <strong>Right to opt out:</strong> Opt out of non-essential
                communications at any time.
              </li>
            </ul>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              7.1 California Residents (CCPA/CPRA)
            </h3>
            <p>
              California residents have additional rights including the right to
              know, right to delete, and right to opt out of sale. We{" "}
              <strong>do not</strong> sell your personal information. Contact{" "}
              <a
                href="mailto:privacy@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                privacy@pilotfortrades.com
              </a>{" "}
              to exercise these rights.
            </p>

            <h3
              className="font-semibold mt-4 mb-2"
              style={{ color: "var(--neutral-800)" }}
            >
              7.2 EU/EEA Residents (GDPR)
            </h3>
            <p>
              EU/EEA residents have rights under GDPR including access,
              rectification, erasure, restriction, data portability, and
              objection. Contact{" "}
              <a
                href="mailto:privacy@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                privacy@pilotfortrades.com
              </a>{" "}
              for GDPR requests.
            </p>
          </LegalSection>

          <LegalSection title="8. Cookies and Tracking">
            <p>
              <strong>Essential cookies:</strong> Required for the Service to
              function (session management, authentication). Cannot be disabled.
            </p>
            <p className="mt-3">
              <strong>Analytics:</strong> We use Google Analytics 4 (GA4) for
              anonymized usage data. You may opt out using the Google Analytics
              Opt-Out Browser Add-on.
            </p>
            <p className="mt-3">
              <strong>What we don&apos;t use:</strong> We do not use advertising
              cookies, third-party retargeting, or fingerprinting technologies.
            </p>
          </LegalSection>

          <LegalSection title="9. Children's Privacy">
            <p>
              The Service is not directed to individuals under the age of 18. We
              do not knowingly collect personal information from minors. If you
              believe a minor has provided us with personal information, contact
              us at{" "}
              <a
                href="mailto:privacy@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                privacy@pilotfortrades.com
              </a>
              .
            </p>
          </LegalSection>

          <LegalSection title="10. Changes to This Policy">
            <p>
              We may update this Privacy Policy from time to time. Your
              continued use after the effective date constitutes acceptance.
            </p>
          </LegalSection>

          <LegalSection title="11. Contact Information">
            <p>
              <strong>
                Example Holdings, LLC, doing business
                as Pilot for Trades
              </strong>
            </p>
            <p className="mt-2">
              Privacy inquiries:{" "}
              <a
                href="mailto:privacy@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                privacy@pilotfortrades.com
              </a>
            </p>
            <p>
              SMS inquiries:{" "}
              <a
                href="mailto:legal@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                legal@pilotfortrades.com
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
              <Link href="/legal/eula" style={{ color: "var(--brand-600)" }}>
                EULA
              </Link>
              {" · "}
              <Link
                href="/legal/sms-terms"
                style={{ color: "var(--brand-600)" }}
              >
                SMS Terms
              </Link>
              {" · "}
              <Link href="/sms-opt-in" style={{ color: "var(--brand-600)" }}>
                SMS Opt-In Disclosure
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
