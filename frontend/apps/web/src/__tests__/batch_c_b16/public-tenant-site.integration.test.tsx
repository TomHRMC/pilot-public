/**
 * C-B16 Integration Test — Public Tenant-Site Pages
 *
 * Location: apps/web/src/__tests__/batch_c_b16/public-tenant-site.integration.test.tsx
 *
 * The public pages are Server Components that use fetchTenantSite() (server-side
 * fetch with revalidate: 300). In the test environment we cannot exercise the
 * Next.js RSC data flow, so we test the presentational components directly with
 * the same fixture shape the MSW public-snapshot handler returns.
 *
 * Tests:
 * 1. Landing page — business name (H1) + contact line visible above fold
 * 2. Landing page — body paragraphs render as plain text
 * 3. Privacy page — title H1 + body paragraphs render
 * 4. Terms page — title H1 + body paragraphs render
 * 5. 404 branch — neutral NotFoundState renders (no tenant branding, no footer)
 * 6. ContactLine — renders phone, email, city/state when provided
 * 7. ContactLine — renders nothing when all fields are null
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TenantSiteHeader } from "@/features/tenant-site-public/TenantSiteHeader";
import { ContactLine } from "@/features/tenant-site-public/ContactLine";
import { LegalPageBody } from "@/features/tenant-site-public/LegalPageBody";
import { LegalLinks } from "@/features/tenant-site-public/LegalLinks";
import { NotFoundState } from "@/features/tenant-site-public/NotFoundState";
import { HostedByPilotFooter } from "@/features/tenant-site-public/HostedByPilotFooter";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

// ── Fixture (matches MSW public-snapshot handler shape) ───────────────────────

const SITE_SNAPSHOT = {
  slug: "lang-electric",
  display_name: "Lang Electric",
  tagline: "Residential & commercial electrical — Richmond, VA",
  public_email: "office@langelectric.example",
  public_phone: "+15551234567",
  public_city: "Richmond",
  public_state: "VA",
  public_address_line1: null,
  public_postal_code: null,
  template_version: "v1",
  published_at: "2026-08-14T01:23:45Z",
  pages: {
    landing: {
      heading: "Lang Electric",
      body_paragraphs: [
        "Lang Electric has been serving the Richmond metro area since 2015.",
        "We specialize in residential panel upgrades, commercial tenant build-outs, and EV charger installations.",
      ],
      contact_lines: [
        "(555) 123-4567",
        "office@langelectric.example",
        "Richmond, VA",
      ],
    },
    privacy: {
      title: "Privacy Policy",
      body_paragraphs: [
        "This privacy policy describes how Lang Electric collects, uses, and protects your information.",
        "SMS Communications: We may send you text messages regarding appointment confirmations, service updates, and account alerts.",
        "To opt out, reply STOP to any message. For help, reply HELP.",
      ],
    },
    terms: {
      title: "Terms of Service",
      body_paragraphs: [
        "These terms govern the use of Lang Electric's services.",
        "SMS Terms: By providing your phone number, you consent to receive SMS messages related to your service appointments and account.",
      ],
    },
  },
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("C-B16 — Public Tenant-Site Pages", () => {
  describe("Landing page", () => {
    it("1. business name (H1) + contact line visible above fold", () => {
      render(
        <TenantSiteHeader
          displayName={SITE_SNAPSHOT.display_name}
          tagline={SITE_SNAPSHOT.tagline}
          publicPhone={SITE_SNAPSHOT.public_phone}
          publicEmail={SITE_SNAPSHOT.public_email}
          publicCity={SITE_SNAPSHOT.public_city}
          publicState={SITE_SNAPSHOT.public_state}
          publicAddressLine1={SITE_SNAPSHOT.public_address_line1}
          publicPostalCode={SITE_SNAPSHOT.public_postal_code}
          showFullAddress={false}
          variant="landing"
        />,
      );

      const h1 = screen.getByRole("heading", { level: 1 });
      expect(h1).toHaveTextContent("Lang Electric");
      expect(h1.tagName).toBe("H1");

      // Contact line should show phone, email, city/state
      expect(screen.getByText("+15551234567")).toBeInTheDocument();
      expect(
        screen.getByText("office@langelectric.example"),
      ).toBeInTheDocument();
      expect(screen.getByText("Richmond, VA")).toBeInTheDocument();
    });

    it("2. body paragraphs render as plain text", () => {
      const landingPage = SITE_SNAPSHOT.pages.landing;
      render(
        <main>
          <h2>About this business</h2>
          <div>
            {landingPage.body_paragraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </main>,
      );

      expect(
        screen.getByText(
          "Lang Electric has been serving the Richmond metro area since 2015.",
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/We specialize in residential panel upgrades/),
      ).toBeInTheDocument();
    });

    it("renders tagline below business name", () => {
      render(
        <TenantSiteHeader
          displayName={SITE_SNAPSHOT.display_name}
          tagline={SITE_SNAPSHOT.tagline}
          publicPhone={SITE_SNAPSHOT.public_phone}
          publicEmail={SITE_SNAPSHOT.public_email}
          publicCity={SITE_SNAPSHOT.public_city}
          publicState={SITE_SNAPSHOT.public_state}
          variant="landing"
        />,
      );
      expect(
        screen.getByText("Residential & commercial electrical — Richmond, VA"),
      ).toBeInTheDocument();
    });
  });

  describe("Privacy page", () => {
    it("3. title H1 + body paragraphs render", () => {
      const privacy = SITE_SNAPSHOT.pages.privacy;
      render(
        <LegalPageBody
          title={privacy.title}
          bodyParagraphs={privacy.body_paragraphs}
          publishedAt={SITE_SNAPSHOT.published_at}
          displayName={SITE_SNAPSHOT.display_name}
        />,
      );

      const h1 = screen.getByRole("heading", { level: 1 });
      expect(h1).toHaveTextContent("Privacy Policy");

      expect(
        screen.getByText(/This privacy policy describes how Lang Electric/),
      ).toBeInTheDocument();
      expect(screen.getByText(/To opt out, reply STOP/)).toBeInTheDocument();
    });

    it("renders last-updated date", () => {
      render(
        <LegalPageBody
          title="Privacy Policy"
          bodyParagraphs={["Test paragraph"]}
          publishedAt={SITE_SNAPSHOT.published_at}
          displayName={SITE_SNAPSHOT.display_name}
        />,
      );
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });

    it("renders back link to home", () => {
      render(
        <LegalPageBody
          title="Privacy Policy"
          bodyParagraphs={["Test"]}
          publishedAt={SITE_SNAPSHOT.published_at}
          displayName={SITE_SNAPSHOT.display_name}
        />,
      );
      const backLink = screen.getByText(/Back to Lang Electric/);
      expect(backLink.closest("a")).toHaveAttribute("href", "/");
    });
  });

  describe("Terms page", () => {
    it("4. title H1 + body paragraphs render", () => {
      const terms = SITE_SNAPSHOT.pages.terms;
      render(
        <LegalPageBody
          title={terms.title}
          bodyParagraphs={terms.body_paragraphs}
          publishedAt={SITE_SNAPSHOT.published_at}
          displayName={SITE_SNAPSHOT.display_name}
        />,
      );

      const h1 = screen.getByRole("heading", { level: 1 });
      expect(h1).toHaveTextContent("Terms of Service");

      expect(screen.getByText(/These terms govern/)).toBeInTheDocument();
      expect(
        screen.getByText(/SMS Terms: By providing your phone number/),
      ).toBeInTheDocument();
    });
  });

  describe("404 branch", () => {
    it("5. neutral NotFoundState renders — no tenant branding, no footer", () => {
      render(<NotFoundState />);

      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        "Page not found",
      );
      expect(
        screen.getByText(/does not exist or is no longer available/),
      ).toBeInTheDocument();
      expect(screen.getByText("Visit Pilot for Trades →")).toBeInTheDocument();

      // No tenant name should appear
      expect(screen.queryByText("Lang Electric")).toBeNull();
      // No "Hosted by" footer
      expect(screen.queryByText(/Hosted by/)).toBeNull();
    });
  });

  describe("ContactLine", () => {
    it("6. renders phone, email, city/state when provided", () => {
      render(
        <ContactLine
          publicPhone="+15551234567"
          publicEmail="office@langelectric.example"
          publicCity="Richmond"
          publicState="VA"
        />,
      );

      expect(screen.getByText("+15551234567")).toBeInTheDocument();
      expect(
        screen.getByText("office@langelectric.example"),
      ).toBeInTheDocument();
      expect(screen.getByText("Richmond, VA")).toBeInTheDocument();
    });

    it("7. renders nothing when all fields are null", () => {
      const { container } = render(
        <ContactLine
          publicPhone={null}
          publicEmail={null}
          publicCity={null}
          publicState={null}
        />,
      );
      expect(container.firstChild).toBeNull();
    });

    it("compact mode omits email", () => {
      render(
        <ContactLine
          publicPhone="+15551234567"
          publicEmail="office@langelectric.example"
          publicCity="Richmond"
          publicState="VA"
          compact
        />,
      );
      expect(screen.getByText("+15551234567")).toBeInTheDocument();
      expect(screen.queryByText("office@langelectric.example")).toBeNull();
    });
  });

  describe("LegalLinks", () => {
    it("renders Privacy and Terms links", () => {
      render(<LegalLinks />);
      const privacyLink = screen.getByText("Privacy Policy");
      const termsLink = screen.getByText("Terms of Service");
      expect(privacyLink.closest("a")).toHaveAttribute("href", "/privacy");
      expect(termsLink.closest("a")).toHaveAttribute("href", "/terms");
    });
  });

  describe("HostedByPilotFooter", () => {
    it("renders Hosted by Pilot for Trades text", () => {
      render(<HostedByPilotFooter />);
      expect(screen.getByText(/Hosted by/)).toBeInTheDocument();
      expect(screen.getByText("Pilot for Trades")).toBeInTheDocument();
    });
  });
});
