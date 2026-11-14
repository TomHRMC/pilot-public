/**
 * EmailBrandingPreview Tests — FE-B14
 *
 * Location: packages/ui/src/email-branding-preview/EmailBrandingPreview.test.tsx
 *
 * Tests for the fleshed EmailBrandingPreview component (from FE-B1 skeleton).
 * Backward compatibility: FE-B1 minimal props usage still works.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmailBrandingPreview } from "./EmailBrandingPreview";
import type { TenantBranding } from "./types";

const MOCK_BRANDING: TenantBranding = {
  primaryColorHex: "#E05A2B",
  logoUrl: "https://cdn.example.com/logos/acme.png",
  senderName: "Acme Electric LLC",
  replyToEmail: "hello@acme-electric.example.com",
};

describe("EmailBrandingPreview", () => {
  // ─── FE-B1 backward compatibility ──────────────────────────────────────────

  it("renders shimmer skeleton when branding is null (FE-B1 regression)", () => {
    render(<EmailBrandingPreview branding={null} />);
    expect(screen.getByTestId("preview-skeleton")).toBeInTheDocument();
  });

  it("renders without crash with FE-B1 minimal props (branding only)", () => {
    const { container } = render(
      <EmailBrandingPreview branding={MOCK_BRANDING} />,
    );
    expect(
      container.querySelector("[data-testid='email-branding-preview']"),
    ).toBeInTheDocument();
  });

  // ─── FE-B14 fleshed behavior ───────────────────────────────────────────────

  it("renders shimmer skeleton when isLoading is true even if previewHtml is present", () => {
    render(
      <EmailBrandingPreview
        branding={MOCK_BRANDING}
        previewHtml="<html><body>Preview</body></html>"
        isLoading={true}
      />,
    );
    expect(screen.getByTestId("preview-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("preview-iframe")).not.toBeInTheDocument();
  });

  it("renders iframe srcDoc with previewHtml when provided and not loading", () => {
    const html = "<html><body><h1>Preview</h1></body></html>";
    render(
      <EmailBrandingPreview
        branding={MOCK_BRANDING}
        previewHtml={html}
        isLoading={false}
      />,
    );
    const iframe = screen.getByTestId("preview-iframe") as HTMLIFrameElement;
    expect(iframe).toBeInTheDocument();
    expect(iframe.getAttribute("srcdoc")).toBe(html);
  });

  it("iframe has sandbox='allow-same-origin' (security guard)", () => {
    render(
      <EmailBrandingPreview
        branding={MOCK_BRANDING}
        previewHtml="<html><body>test</body></html>"
      />,
    );
    const iframe = screen.getByTestId("preview-iframe");
    expect(iframe.getAttribute("sandbox")).toBe("allow-same-origin");
  });

  it("renders placeholder when branding is provided but previewHtml is undefined", () => {
    render(<EmailBrandingPreview branding={MOCK_BRANDING} />);
    expect(screen.getByTestId("preview-placeholder")).toBeInTheDocument();
    expect(screen.queryByTestId("preview-iframe")).not.toBeInTheDocument();
  });

  it("shows template name in the header when branding is provided", () => {
    render(
      <EmailBrandingPreview
        branding={MOCK_BRANDING}
        templateKey="invoice_sent"
      />,
    );
    expect(screen.getByText("Invoice sent")).toBeInTheDocument();
  });

  it("shows customer-facing badge for customer-facing templates", () => {
    render(
      <EmailBrandingPreview
        branding={MOCK_BRANDING}
        templateKey="quote_sent"
      />,
    );
    expect(screen.getByText("Customer-facing")).toBeInTheDocument();
  });

  it("shows logo image with alt text when logoUrl is provided", () => {
    render(<EmailBrandingPreview branding={MOCK_BRANDING} />);
    const logo = screen.getByTestId("preview-logo");
    expect(logo).toHaveAttribute("src", MOCK_BRANDING.logoUrl);
    expect(logo).toHaveAttribute("alt", `${MOCK_BRANDING.senderName} logo`);
  });

  it("does not render a logo when logoUrl is null", () => {
    const brandingNoLogo: TenantBranding = { ...MOCK_BRANDING, logoUrl: null };
    render(<EmailBrandingPreview branding={brandingNoLogo} />);
    expect(screen.queryByTestId("preview-logo")).not.toBeInTheDocument();
  });

  it("applies previewWidth style to the container", () => {
    render(
      <EmailBrandingPreview branding={MOCK_BRANDING} previewWidth={800} />,
    );
    const container = screen.getByTestId("email-branding-preview");
    expect(container).toHaveStyle({ width: "800px" });
  });
});
