/**
 * CustomerForm unit tests — FE-B18
 *
 * Location: apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CustomerForm } from "../CustomerForm";
import type { CustomerFormValues } from "../CustomerForm";

describe("CustomerForm", () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    isSubmitting: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(<CustomerForm {...defaultProps} />);
    expect(screen.getByText(/display name/i)).toBeTruthy();
  });

  it("shows person fields (first/last name) when type = person", () => {
    render(
      <CustomerForm {...defaultProps} initialValues={{ type: "person" }} />,
    );
    expect(screen.getByLabelText(/first name/i)).toBeTruthy();
    expect(screen.getByLabelText(/last name/i)).toBeTruthy();
    expect(screen.queryByLabelText(/company name/i)).toBeNull();
  });

  it("shows company fields when type = company", () => {
    render(
      <CustomerForm {...defaultProps} initialValues={{ type: "company" }} />,
    );
    expect(screen.getByLabelText(/company name/i)).toBeTruthy();
    expect(screen.queryByLabelText(/first name/i)).toBeNull();
    expect(screen.queryByLabelText(/last name/i)).toBeNull();
  });

  it("switches from person to company when radio toggled", () => {
    render(<CustomerForm {...defaultProps} />);
    // Default is person — company radio should switch it
    fireEvent.click(screen.getByRole("radio", { name: /company/i }));
    expect(screen.getByLabelText(/company name/i)).toBeTruthy();
    expect(screen.queryByLabelText(/first name/i)).toBeNull();
  });

  it("submit button is disabled if display_name is empty", () => {
    render(<CustomerForm {...defaultProps} />);
    const submit = screen.getByTestId("customer-form-submit");
    expect((submit as HTMLButtonElement).disabled).toBe(true);
  });

  it("submit button enabled when display_name is filled", () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Alice Smith" },
    });
    const submit = screen.getByTestId("customer-form-submit");
    expect((submit as HTMLButtonElement).disabled).toBe(false);
  });

  it("submit calls onSubmit with correct data shape for person type", () => {
    const onSubmit = vi.fn();
    render(
      <CustomerForm
        {...defaultProps}
        onSubmit={onSubmit}
        initialValues={{ type: "person" }}
      />,
    );

    fireEvent.change(screen.getByLabelText(/first name/i), {
      target: { value: "Alice" },
    });
    fireEvent.change(screen.getByLabelText(/last name/i), {
      target: { value: "Smith" },
    });
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Alice Smith" },
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "alice@example.com" },
    });

    fireEvent.click(screen.getByTestId("customer-form-submit"));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining<Partial<CustomerFormValues>>({
        type: "person",
        display_name: "Alice Smith",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
      }),
    );
  });

  it("submit calls onSubmit with correct data shape for company type", () => {
    const onSubmit = vi.fn();
    render(
      <CustomerForm
        {...defaultProps}
        onSubmit={onSubmit}
        initialValues={{ type: "company" }}
      />,
    );

    fireEvent.change(screen.getByLabelText(/company name/i), {
      target: { value: "Acme Corp" },
    });
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Acme Corp" },
    });

    fireEvent.click(screen.getByTestId("customer-form-submit"));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining<Partial<CustomerFormValues>>({
        type: "company",
        display_name: "Acme Corp",
        company_name: "Acme Corp",
        first_name: null,
        last_name: null,
      }),
    );
  });

  it("cancel calls onCancel", () => {
    const onCancel = vi.fn();
    render(<CustomerForm {...defaultProps} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("uses custom submitLabel when provided", () => {
    render(<CustomerForm {...defaultProps} submitLabel="Add Customer" />);
    expect(screen.getByTestId("customer-form-submit").textContent).toContain(
      "Add Customer",
    );
  });

  it("shows submitting text when isSubmitting = true", () => {
    render(<CustomerForm {...defaultProps} isSubmitting />);
    expect(screen.getByTestId("customer-form-submit").textContent).toContain(
      "Saving",
    );
  });

  it("pre-fills initialValues correctly", () => {
    render(
      <CustomerForm
        {...defaultProps}
        initialValues={{
          type: "person",
          display_name: "Pre Filled",
          first_name: "Pre",
          last_name: "Filled",
          email: "pre@filled.com",
        }}
      />,
    );
    expect(
      (screen.getByLabelText(/display name/i) as HTMLInputElement).value,
    ).toBe("Pre Filled");
    expect(
      (screen.getByLabelText(/first name/i) as HTMLInputElement).value,
    ).toBe("Pre");
    expect(
      (screen.getByLabelText(/last name/i) as HTMLInputElement).value,
    ).toBe("Filled");
  });

  // ── DLC-1: SMS attestation checkbox tests ────────────────────────────────────

  it("attestation checkbox does NOT appear when mobile_phone is empty", () => {
    render(<CustomerForm {...defaultProps} />);
    // mobile_phone is empty by default → checkbox should not render
    expect(screen.queryByTestId("sms-attestation-checkbox")).toBeNull();
  });

  it("attestation checkbox appears when mobile_phone has a value", async () => {
    render(<CustomerForm {...defaultProps} />);
    // Type a phone number
    fireEvent.change(screen.getByLabelText(/mobile phone/i), {
      target: { value: "+13035550001" },
    });
    await waitFor(() => {
      expect(screen.getByTestId("sms-attestation-checkbox")).toBeTruthy();
    });
  });

  it("submit is blocked when phone present but attestation unchecked", async () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Smith Electric" },
    });
    fireEvent.change(screen.getByLabelText(/mobile phone/i), {
      target: { value: "+13035550001" },
    });
    // Checkbox is unchecked by default
    await waitFor(() => {
      const submit = screen.getByTestId(
        "customer-form-submit",
      ) as HTMLButtonElement;
      expect(submit.disabled).toBe(true);
    });
  });

  it("submit is enabled when phone present AND attestation checked", async () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Smith Electric" },
    });
    fireEvent.change(screen.getByLabelText(/mobile phone/i), {
      target: { value: "+13035550001" },
    });
    await waitFor(() => screen.getByTestId("sms-attestation-checkbox"));
    fireEvent.click(screen.getByTestId("sms-attestation-checkbox"));

    const submit = screen.getByTestId(
      "customer-form-submit",
    ) as HTMLButtonElement;
    expect(submit.disabled).toBe(false);
  });

  it("onSubmit includes sms_attestation_checked=true when checkbox checked", async () => {
    const onSubmit = vi.fn();
    render(<CustomerForm {...defaultProps} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Smith" },
    });
    fireEvent.change(screen.getByLabelText(/mobile phone/i), {
      target: { value: "+13035550001" },
    });
    await waitFor(() => screen.getByTestId("sms-attestation-checkbox"));
    fireEvent.click(screen.getByTestId("sms-attestation-checkbox"));
    fireEvent.click(screen.getByTestId("customer-form-submit"));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ sms_attestation_checked: true }),
    );
  });

  // ── DLC-B2: Consumer SMS consent disclosure tests ─────────────────────────────

  it("disclosure renders when a phone number is entered", async () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/mobile phone/i), {
      target: { value: "+13035550001" },
    });
    await waitFor(() => {
      const disclosure = screen.getByTestId("customer-sms-consent-disclosure");
      expect(disclosure).toBeTruthy();
      expect(disclosure.textContent).toContain("Msg & data rates may apply");
      expect(disclosure.textContent).toContain("Reply STOP");
    });
  });

  it("disclosure is hidden when no phone number", () => {
    render(<CustomerForm {...defaultProps} />);
    // mobile_phone is empty by default → disclosure should not render
    expect(screen.queryByTestId("customer-sms-consent-disclosure")).toBeNull();
  });

  it("privacy policy link points to the correct URL", async () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/mobile phone/i), {
      target: { value: "+13035550001" },
    });
    await waitFor(() => screen.getByTestId("customer-sms-consent-disclosure"));
    const link = screen
      .getByTestId("customer-sms-consent-disclosure")
      .querySelector("a");
    expect(link).toBeTruthy();
    expect(link!.getAttribute("href")).toBe(
      "https://www.pilotfortrades.com/legal/privacy",
    );
  });

  // ── PLP-FIX-4 Issue 10: email validation + phone E.164 ──────────────────────

  it("invalid email shows inline error and blocks submit", () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Test Customer" },
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "not-an-email" },
    });
    // Inline error should appear
    expect(screen.getByText("Enter a valid email address.")).toBeTruthy();
    // Email input should have aria-invalid
    const emailInput = screen.getByLabelText(/email/i);
    expect(emailInput).toHaveAttribute("aria-invalid", "true");
    // Submit should be disabled
    const submit = screen.getByTestId(
      "customer-form-submit",
    ) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("valid email does not show error and allows submit", () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Test Customer" },
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "valid@example.com" },
    });
    // No inline error
    expect(screen.queryByText("Enter a valid email address.")).toBeNull();
    // Submit should be enabled
    const submit = screen.getByTestId(
      "customer-form-submit",
    ) as HTMLButtonElement;
    expect(submit.disabled).toBe(false);
  });

  it("phone typed as digits displays formatted mask", () => {
    render(<CustomerForm {...defaultProps} />);
    const phoneInput = screen.getByTestId(
      "customer-mobile-phone",
    ) as HTMLInputElement;
    fireEvent.change(phoneInput, { target: { value: "5551234567" } });
    expect(phoneInput.value).toBe("(555) 123-4567");
  });

  it("phone submits E.164 in onSubmit payload", async () => {
    const onSubmit = vi.fn();
    render(<CustomerForm {...defaultProps} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Smith" },
    });
    fireEvent.change(screen.getByTestId("customer-mobile-phone"), {
      target: { value: "5551234567" },
    });
    await waitFor(() => screen.getByTestId("sms-attestation-checkbox"));
    fireEvent.click(screen.getByTestId("sms-attestation-checkbox"));
    fireEvent.click(screen.getByTestId("customer-form-submit"));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ mobile_phone: "+15551234567" }),
    );
  });

  it("DLC-1 gate still blocks when phone present + attestation unchecked", async () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Smith Electric" },
    });
    fireEvent.change(screen.getByTestId("customer-mobile-phone"), {
      target: { value: "5551234567" },
    });
    await waitFor(() => screen.getByTestId("sms-attestation-checkbox"));
    const submit = screen.getByTestId(
      "customer-form-submit",
    ) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });
});
