/**
 * ManualPaymentPanel unit tests — STRIPE-CONNECT-1-C
 *
 * Location: apps/web/src/features/public-invoice/__tests__/ManualPaymentPanel.test.tsx
 *
 * 4 field-presence cases (both / phone-only / email-only / both-null fallback line);
 * tel: / mailto: hrefs; aria-label="Payment instructions"; heading present; no Pay CTA inside.
 *
 * Pure presentational — no MSW, no QueryClient needed.
 */

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

import { ManualPaymentPanel } from "../ManualPaymentPanel";

describe("ManualPaymentPanel", () => {
  it("both phone + email present — renders heading, body, both links, divider", () => {
    render(
      <ManualPaymentPanel
        tenantName="Lang Electric"
        tenantPhone="(804) 555-0142"
        tenantEmail="billing@example.com"
      />,
    );

    // Section a11y label
    expect(screen.getByLabelText("Payment instructions")).toBeInTheDocument();

    // Heading
    expect(screen.getByText("How to pay this invoice")).toBeInTheDocument();

    // Body copy with tenant name
    expect(
      screen.getByText(/Contact Lang Electric to arrange payment/),
    ).toBeInTheDocument();

    // Phone link
    const phoneLink = screen.getByTestId("manual-payment-phone-link");
    expect(phoneLink).toBeInTheDocument();
    expect(phoneLink).toHaveAttribute("href", "tel:(804) 555-0142");
    expect(phoneLink).toHaveTextContent("(804) 555-0142");

    // Email link
    const emailLink = screen.getByTestId("manual-payment-email-link");
    expect(emailLink).toBeInTheDocument();
    expect(emailLink).toHaveAttribute("href", "mailto:billing@example.com");
    expect(emailLink).toHaveTextContent("billing@example.com");

    // Labels
    expect(screen.getByText("Phone")).toBeInTheDocument();
    expect(screen.getByText("Email")).toBeInTheDocument();

    // No Pay CTA inside the panel
    expect(screen.queryByTestId("pay-invoice-button")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("pay-remaining-button"),
    ).not.toBeInTheDocument();

    // No Stripe caption
    expect(screen.queryByText(/powered by stripe/i)).not.toBeInTheDocument();
  });

  it("phone only — renders single phone block, no email block", () => {
    render(
      <ManualPaymentPanel
        tenantName="Acme Electric"
        tenantPhone="(555) 123-4567"
        tenantEmail={null}
      />,
    );

    expect(screen.getByTestId("manual-payment-phone-link")).toBeInTheDocument();
    expect(
      screen.queryByTestId("manual-payment-email-link"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Phone")).toBeInTheDocument();
    expect(screen.queryByText("Email")).not.toBeInTheDocument();
  });

  it("email only — renders single email block, no phone block", () => {
    render(
      <ManualPaymentPanel
        tenantName="Acme Electric"
        tenantPhone={null}
        tenantEmail="hello@acme.example.com"
      />,
    );

    expect(screen.getByTestId("manual-payment-email-link")).toBeInTheDocument();
    expect(
      screen.queryByTestId("manual-payment-phone-link"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.queryByText("Phone")).not.toBeInTheDocument();
  });

  it("both null — renders fallback line, no contact links, no divider", () => {
    render(
      <ManualPaymentPanel
        tenantName="Acme Electric"
        tenantPhone={null}
        tenantEmail={null}
      />,
    );

    // Heading + body still present
    expect(screen.getByText("How to pay this invoice")).toBeInTheDocument();
    expect(
      screen.getByText(/Contact Acme Electric to arrange payment/),
    ).toBeInTheDocument();

    // Fallback line
    expect(
      screen.getByText(/Please reach out to Acme Electric to arrange payment/),
    ).toBeInTheDocument();

    // No contact links
    expect(
      screen.queryByTestId("manual-payment-phone-link"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("manual-payment-email-link"),
    ).not.toBeInTheDocument();
  });
});
