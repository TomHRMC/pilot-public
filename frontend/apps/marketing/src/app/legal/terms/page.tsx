// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service | Pilot for Trades",
  description:
    "Terms of Service for Pilot for Trades — AI-powered field operations software for trade contractors. Read our terms governing use of the platform.",
  openGraph: {
    title: "Terms of Service | Pilot for Trades",
    description:
      "Terms of Service for Pilot for Trades — AI-powered field operations software for trade contractors.",
    url: "https://pilotfortrades.com/legal/terms",
  },
};

export default function TermsPage() {
  return (
    <section
      className="section-padding"
      style={{ background: "var(--white)" }}
      aria-labelledby="terms-heading"
    >
      <div className="container-marketing max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <p className="text-sm mb-2" style={{ color: "var(--neutral-500)" }}>
            <Link href="/legal/terms" style={{ color: "var(--brand-600)" }}>
              Legal
            </Link>{" "}
            / Terms of Service
          </p>
          <h1
            id="terms-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            Terms of Service
          </h1>
          <p className="text-sm" style={{ color: "var(--neutral-500)" }}>
            Effective Date: January 1, 2026 · Last Updated: August 7, 2026
          </p>
        </div>

        {/* Intro */}
        <div className="mb-8" style={{ color: "var(--neutral-700)" }}>
          <p className="text-base leading-relaxed">
            These Terms of Service (&ldquo;Terms&rdquo;) constitute a legally
            binding agreement between you and Example Holdings,
            LLC, doing business as Pilot for Trades
            (&ldquo;Company,&rdquo; &ldquo;we,&rdquo; &ldquo;us,&rdquo; or
            &ldquo;our&rdquo;). They govern your access to and use of the Pilot
            for Trades platform, including our website at pilotfortrades.com,
            mobile applications, and related services (collectively, the
            &ldquo;Service&rdquo;). By accessing or using the Service, you agree
            to be bound by these Terms. If you do not agree to these Terms, do
            not use the Service.
          </p>
        </div>

        {/* Sections */}
        <div
          className="flex flex-col gap-10"
          style={{ color: "var(--neutral-700)" }}
        >
          <LegalSection title="1. Acceptance of Terms">
            <p>
              By creating an account, accessing the Service, or using any
              feature of the Pilot for Trades platform, you acknowledge that you
              have read, understood, and agree to be bound by these Terms and
              our{" "}
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
              </Link>
              .
            </p>
            <p className="mt-3">
              <strong>Eligibility:</strong> You must be at least 18 years of age
              and have the legal authority to enter into these Terms on behalf
              of yourself or a business entity.
            </p>
            <p className="mt-3">
              <strong>Modifications:</strong> We may update these Terms from
              time to time. Your continued use of the Service after the
              effective date constitutes your acceptance.
            </p>
          </LegalSection>

          <LegalSection title="2. Description of Service">
            <p>
              Pilot for Trades is a software-as-a-service (SaaS) platform
              designed for trade contractors — including electricians, plumbers,
              and HVAC technicians — that provides:
            </p>
            <ul className="list-disc pl-6 mt-3 space-y-1">
              <li>
                AI-powered voice quoting and estimating with real-time material
                pricing
              </li>
              <li>
                Dispatch and scheduling management with route optimization
              </li>
              <li>Customer communications via SMS and email</li>
              <li>
                Invoicing and payment processing via integrated payment
                providers
              </li>
              <li>
                Real-time job profitability tracking and financial reporting
              </li>
              <li>
                QuickBooks Online integration for bidirectional accounting sync
              </li>
              <li>
                Offline-capable mobile operations with automatic synchronization
              </li>
              <li>AI-powered help and trade reference system</li>
            </ul>
            <p className="mt-3">
              <strong>Beta features:</strong> During beta or early access
              periods, certain features may be designated as &ldquo;Beta&rdquo;
              or &ldquo;Preview.&rdquo; These features are provided as-is and
              may be modified or removed without notice.
            </p>
          </LegalSection>

          <LegalSection title="3. User Accounts and Registration">
            <p>
              <strong>Account creation:</strong> To use the Service, you must
              create an account by providing accurate, current, and complete
              information, including your name, email address, business name,
              and trade type.
            </p>
            <p className="mt-3">
              <strong>Account security:</strong> You are responsible for
              maintaining the confidentiality of your account credentials.
              Notify us immediately at{" "}
              <a
                href="mailto:security@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                security@pilotfortrades.com
              </a>{" "}
              if you become aware of any unauthorized access to your account.
            </p>
            <p className="mt-3">
              <strong>Multi-tenant architecture:</strong> The Service operates
              on a multi-tenant architecture with strict data isolation between
              customer accounts. Your data is scoped to your account in the
              application layer and is not visible to other customers.
            </p>
          </LegalSection>

          <LegalSection title="4. Subscription and Payment Terms">
            <p>
              <strong>Subscription plans:</strong> The Service is offered under
              subscription plans as described on our{" "}
              <Link href="/pricing" style={{ color: "var(--brand-600)" }}>
                Pricing page
              </Link>
              .
            </p>
            <p className="mt-3">
              <strong>Billing:</strong> Subscriptions are billed monthly or
              annually. Payment is processed automatically via Stripe, Inc.
              Pilot for Trades does not store your full credit card number.
            </p>
            <p className="mt-3">
              <strong>Refund policy:</strong> If you cancel within the first 30
              days of your initial paid subscription, you are eligible for a
              full refund. After 30 days, subscriptions are non-refundable for
              the current billing period.
            </p>
            <p className="mt-3">
              <strong>Price changes:</strong> We may change pricing with at
              least 30 days&apos; written notice. Changes take effect at the
              start of your next billing cycle.
            </p>
          </LegalSection>

          {/* D22 — Charter Rate Clause */}
          <LegalSection title="Charter Rate">
            <p>
              <strong>Charter Rate.</strong> Charter members receive a locked
              monthly rate of $49/month for as long as they remain continuously
              subscribed. This rate is locked at signup and does not change as
              long as the subscription remains active. Canceling the
              subscription or upgrading to the Teams plan permanently forfeits
              the Charter rate — it cannot be reinstated, even if the customer
              later returns to the Starter plan.
            </p>
          </LegalSection>

          <LegalSection title="5. Acceptable Use">
            <p>
              You agree to use the Service only for lawful purposes related to
              operating your trade contracting business. You agree NOT to:
            </p>
            <ul className="list-disc pl-6 mt-3 space-y-1">
              <li>
                Use the Service for any illegal purpose or in violation of any
                applicable law
              </li>
              <li>Reverse engineer, decompile, or disassemble the Service</li>
              <li>
                Attempt to gain unauthorized access to the Service or other
                users&apos; accounts
              </li>
              <li>
                Use the SMS communication features for marketing without proper
                consumer consent as required by TCPA
              </li>
              <li>Share your account credentials with unauthorized users</li>
              <li>
                Scrape, crawl, or use automated means to access the Service
                beyond the provided APIs
              </li>
              <li>
                Resell, sublicense, or redistribute access to the Service
                without written authorization
              </li>
            </ul>
            <p className="mt-3">
              <strong>SMS compliance:</strong> When using the Service&apos;s
              customer communication features, you are responsible for ensuring
              that your customers have provided proper opt-in consent. See our{" "}
              <Link
                href="/legal/sms-terms"
                style={{ color: "var(--brand-600)" }}
              >
                SMS Terms
              </Link>{" "}
              for details.
            </p>
          </LegalSection>

          <LegalSection title="6. Intellectual Property">
            <p>
              <strong>Pilot&apos;s ownership:</strong> The Service, including
              all software, algorithms, AI models, user interface designs,
              documentation, branding, and trademarks, is owned by Pilot for
              Trades and its licensors.
            </p>
            <p className="mt-3">
              <strong>Your data ownership:</strong> You retain full ownership of
              all business data you enter into the Service, including customer
              records, quotes, invoices, job records, financial data, and
              communications.
            </p>
            <p className="mt-3">
              <strong>AI-generated content:</strong> Estimates, calculations,
              and suggestions generated by the Service&apos;s AI features are
              provided as tools to assist your professional judgment. You retain
              ownership of the final versions of documents you create using the
              Service.
            </p>
          </LegalSection>

          <LegalSection title="7. User Data and Privacy">
            <p>
              Your use of the Service is also governed by our{" "}
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
              </Link>
              , which describes how we collect, use, store, and protect your
              information.
            </p>
            <p className="mt-3">
              <strong>Data portability:</strong> You may export your data at any
              time through the Service&apos;s export features in standard
              formats (CSV, PDF, or JSON).
            </p>
            <p className="mt-3">
              <strong>Data deletion:</strong> You may request deletion of your
              account and associated data by contacting{" "}
              <a
                href="mailto:legal@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                legal@pilotfortrades.com
              </a>
              . We will delete your data within 30 days, except where retention
              is required by law.
            </p>
            <p className="mt-3">
              <strong>SMS data:</strong> See our{" "}
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
              </Link>{" "}
              §4 and{" "}
              <Link
                href="/legal/sms-terms"
                style={{ color: "var(--brand-600)" }}
              >
                SMS Terms
              </Link>{" "}
              for specific SMS data handling practices.
            </p>
          </LegalSection>

          <LegalSection title="8. Third-Party Integrations">
            <p>
              The Service integrates with third-party services including
              QuickBooks Online (Intuit), Stripe (payments), Telnyx (SMS), and
              Google Calendar. Your use of these integrations
              is subject to those services&apos; respective terms. Pilot for
              Trades is not responsible for the availability, performance, or
              practices of third-party services.
            </p>
          </LegalSection>

          {/* D24 — 10DLC Carrier Fees Pass-Through Disclosure */}
          <LegalSection title="10DLC Carrier Fees">
            <p>
              <strong>10DLC Carrier Fees.</strong> Carrier registration fees for
              10DLC (10-digit long code) messaging are passed through at cost.
              Pilot for Trades does not mark up, add margins to, or profit from
              carrier registration fees. These fees are set by the carrier
              (T-Mobile, AT&T, Verizon) and may change without notice. The
              customer is responsible for all carrier fees associated with their
              10DLC messaging registration.
            </p>
          </LegalSection>

          <LegalSection title="9. Service Availability">
            <p>
              <strong>Availability target:</strong> We target 99.9% uptime for
              cloud-hosted features, measured monthly, excluding scheduled
              maintenance windows.
            </p>
            <p className="mt-3">
              <strong>Offline functionality:</strong> The Service&apos;s mobile
              application is designed to operate in an offline mode. Offline
              data synchronizes automatically when connectivity is restored.
            </p>
            <p className="mt-3">
              <strong>Service modifications:</strong> We may add, modify, or
              remove features. We will not remove core features (quoting,
              dispatch, invoicing, profitability tracking) without at least 90
              days&apos; notice.
            </p>
          </LegalSection>

          <LegalSection title="10. Limitation of Liability">
            <p className="uppercase text-sm leading-relaxed">
              THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS
              AVAILABLE&rdquo; WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
              IMPLIED.
            </p>
            <p className="mt-3 uppercase text-sm leading-relaxed">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, PILOT FOR TRADES&apos;
              TOTAL AGGREGATE LIABILITY SHALL NOT EXCEED THE AMOUNT YOU PAID TO
              PILOT FOR TRADES IN THE TWELVE (12) MONTHS IMMEDIATELY PRECEDING
              THE EVENT GIVING RISE TO THE CLAIM.
            </p>
            <p className="mt-3 uppercase text-sm leading-relaxed">
              IN NO EVENT SHALL PILOT FOR TRADES BE LIABLE FOR ANY INDIRECT,
              INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING
              LOSS OF PROFITS, LOSS OF REVENUE, OR LOSS OF DATA.
            </p>
            <p className="mt-3">
              Without limiting the foregoing, Pilot for Trades is not liable for
              business decisions made in reliance on AI-generated estimates,
              inaccuracies in code compliance references, or losses from
              material pricing data that does not reflect actual supplier costs.
            </p>
          </LegalSection>

          <LegalSection title="11. Indemnification">
            <p>
              You agree to indemnify, defend, and hold harmless Pilot for
              Trades, its officers, directors, employees, and agents from any
              claims, damages, losses, and expenses (including reasonable
              attorneys&apos; fees) arising out of or related to: your use of
              the Service; your violation of these Terms; your violation of any
              applicable law; or your business operations.
            </p>
            <p className="mt-3">
              <strong>Professional responsibility:</strong> You acknowledge that
              the Service is a tool to assist your professional work and does
              not replace your professional judgment, licensing obligations, or
              responsibility for code compliance.
            </p>
          </LegalSection>

          <LegalSection title="12. Termination">
            <p>
              <strong>Termination by you:</strong> You may cancel your
              subscription at any time through your account settings or by
              contacting{" "}
              <a
                href="mailto:support@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                support@pilotfortrades.com
              </a>
              . Cancellation takes effect at the end of your current billing
              period.
            </p>
            <p className="mt-3">
              <strong>Effect of termination:</strong> Upon termination, your
              access to the Service will be revoked. You will have 30 days to
              export your data. After the 30-day data export window, your data
              will be permanently deleted from our systems.
            </p>
          </LegalSection>

          <LegalSection title="13. Dispute Resolution">
            <p>
              <strong>Governing law:</strong> These Terms are governed by the
              laws of the State of Colorado, without regard to its conflict of
              law principles.
            </p>
            <p className="mt-3">
              <strong>Informal resolution:</strong> Before filing any formal
              dispute, contact us at{" "}
              <a
                href="mailto:legal@pilotfortrades.com"
                style={{ color: "var(--brand-600)" }}
              >
                legal@pilotfortrades.com
              </a>{" "}
              to attempt informal resolution within 30 days.
            </p>
            <p className="mt-3">
              <strong>Arbitration:</strong> If informal resolution fails,
              disputes shall be resolved by binding arbitration administered by
              the AAA under its Commercial Arbitration Rules.
            </p>
            <p className="mt-3 uppercase text-sm leading-relaxed">
              CLASS ACTION WAIVER: YOU AGREE THAT ANY DISPUTE RESOLUTION
              PROCEEDINGS WILL BE CONDUCTED ONLY ON AN INDIVIDUAL BASIS AND NOT
              IN A CLASS, CONSOLIDATED, OR REPRESENTATIVE ACTION.
            </p>
          </LegalSection>

          <LegalSection title="14. General Provisions">
            <p>
              These Terms, together with the{" "}
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
              </Link>
              ,{" "}
              <Link href="/legal/eula" style={{ color: "var(--brand-600)" }}>
                EULA
              </Link>
              , and{" "}
              <Link
                href="/legal/sms-terms"
                style={{ color: "var(--brand-600)" }}
              >
                SMS Terms
              </Link>
              , constitute the entire agreement between you and Pilot for Trades
              regarding the Service.
            </p>
            <p className="mt-3">
              If any provision is held invalid or unenforceable, the remaining
              provisions remain in full force. You may not assign your rights
              without our prior written consent.
            </p>
          </LegalSection>

          <LegalSection title="15. Contact Information">
            <p>
              <strong>
                Example Holdings, LLC, doing business
                as Pilot for Trades
              </strong>
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
              <Link href="/legal/privacy" style={{ color: "var(--brand-600)" }}>
                Privacy Policy
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
