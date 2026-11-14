/**
 * SmsConsentDisclosure unit tests — SIGNUP-C
 *
 * Location: apps/web/src/features/signup/components/__tests__/SmsConsentDisclosure.test.tsx
 *
 * Verifies the disclosure block renders all 7 required 10DLC CTA elements
 * (the TCR consent screenshot content) + the Privacy Policy link.
 */

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  SmsConsentDisclosure,
  SMS_CONSENT_DISCLOSURE_TEXT,
} from "../SmsConsentDisclosure";

describe("SmsConsentDisclosure", () => {
  it("renders the disclosure block with the required data-testid", () => {
    render(<SmsConsentDisclosure />);
    expect(
      screen.getByTestId("signup-sms-consent-disclosure"),
    ).toBeInTheDocument();
  });

  it("renders the program name 'Pilot for Trades'", () => {
    render(<SmsConsentDisclosure />);
    expect(screen.getByText(/Pilot for Trades/i)).toBeInTheDocument();
  });

  it("renders the message types 'account, billing, security, and support messages'", () => {
    render(<SmsConsentDisclosure />);
    expect(
      screen.getByText(/account, billing, security, and support messages/i),
    ).toBeInTheDocument();
  });

  it("renders 'Message frequency varies'", () => {
    render(<SmsConsentDisclosure />);
    expect(screen.getByText(/Message frequency varies/i)).toBeInTheDocument();
  });

  it("renders 'Msg & data rates may apply'", () => {
    render(<SmsConsentDisclosure />);
    expect(screen.getByText(/Msg & data rates may apply/i)).toBeInTheDocument();
  });

  it("renders 'Reply HELP for help, STOP to opt out'", () => {
    render(<SmsConsentDisclosure />);
    expect(
      screen.getByText(/Reply HELP for help, STOP to opt out/i),
    ).toBeInTheDocument();
  });

  it("renders the no-sharing statement", () => {
    render(<SmsConsentDisclosure />);
    expect(
      screen.getByText(
        /Mobile information will not be shared with third parties or used for marketing purposes/i,
      ),
    ).toBeInTheDocument();
  });

  it("renders a Privacy Policy link pointing to the correct URL", () => {
    render(<SmsConsentDisclosure />);
    const link = screen.getByRole("link", {
      name: /Privacy Policy/i,
    });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute(
      "href",
      "https://www.pilotfortrades.com/legal/privacy",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("exports the canonical disclosure text constant containing all required elements", () => {
    // The constant is the single source of truth for the SHA-256 hash.
    expect(SMS_CONSENT_DISCLOSURE_TEXT).toContain("Pilot for Trades");
    expect(SMS_CONSENT_DISCLOSURE_TEXT).toContain(
      "account, billing, security, and support messages",
    );
    expect(SMS_CONSENT_DISCLOSURE_TEXT).toContain("Message frequency varies");
    expect(SMS_CONSENT_DISCLOSURE_TEXT).toContain("Msg & data rates may apply");
    expect(SMS_CONSENT_DISCLOSURE_TEXT).toContain(
      "Reply HELP for help, STOP to opt out",
    );
    expect(SMS_CONSENT_DISCLOSURE_TEXT).toContain("Privacy Policy");
    expect(SMS_CONSENT_DISCLOSURE_TEXT).toContain(
      "Mobile information will not be shared with third parties or used for marketing purposes",
    );
  });
});
