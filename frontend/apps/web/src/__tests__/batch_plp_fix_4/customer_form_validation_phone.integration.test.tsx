/**
 * PLP-FIX-4 Integration: Customer form validation + phone E.164
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_4/customer_form_validation_phone.integration.test.tsx
 *
 * Verifies:
 *  1. Invalid email blocks submit + shows inline error
 *  2. Valid email passes
 *  3. Phone typed as digits displays mask + submits E.164
 *  4. DLC-1 attestation gate intact
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CustomerForm } from "../../features/customers/components/CustomerForm";

describe("PLP-FIX-4 — Customer form validation + phone E.164", () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    isSubmitting: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("invalid email blocks submit and shows inline error", () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Test Customer" },
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "not-valid" },
    });

    // Inline error visible
    expect(
      screen.getByText("Enter a valid email address."),
    ).toBeInTheDocument();
    // aria-invalid on email input
    expect(screen.getByLabelText(/email/i)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    // Submit disabled
    const submit = screen.getByTestId(
      "customer-form-submit",
    ) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("valid email allows submit", () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Test Customer" },
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "valid@example.com" },
    });

    expect(screen.queryByText("Enter a valid email address.")).toBeNull();

    const submit = screen.getByTestId(
      "customer-form-submit",
    ) as HTMLButtonElement;
    expect(submit.disabled).toBe(false);
  });

  it("phone typed as 5551234567 displays (555) 123-4567 and submits E.164", async () => {
    const onSubmit = vi.fn();
    render(<CustomerForm {...defaultProps} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Smith" },
    });
    const phoneInput = screen.getByTestId("customer-mobile-phone");
    fireEvent.change(phoneInput, { target: { value: "5551234567" } });

    // Display mask
    expect((phoneInput as HTMLInputElement).value).toBe("(555) 123-4567");

    // Check attestation box appears
    await waitFor(() =>
      expect(
        screen.getByTestId("sms-attestation-checkbox"),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("sms-attestation-checkbox"));
    fireEvent.click(screen.getByTestId("customer-form-submit"));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        mobile_phone: "+15551234567",
      }),
    );
  });

  it("DLC-1 attestation gate blocks submit when phone present + unchecked", async () => {
    render(<CustomerForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/display name/i), {
      target: { value: "Smith Electric" },
    });
    fireEvent.change(screen.getByTestId("customer-mobile-phone"), {
      target: { value: "5551234567" },
    });

    await waitFor(() =>
      expect(
        screen.getByTestId("sms-attestation-checkbox"),
      ).toBeInTheDocument(),
    );

    const submit = screen.getByTestId(
      "customer-form-submit",
    ) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });
});
