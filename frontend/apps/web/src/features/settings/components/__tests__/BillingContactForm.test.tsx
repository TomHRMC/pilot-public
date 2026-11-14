/**
 * BillingContactForm unit tests — STRIPE-CONNECT-1-C (B5)
 *
 * Location: apps/web/src/features/settings/components/__tests__/BillingContactForm.test.tsx
 *
 * - Invalid email shows a non-color-only error (text message, not just red border)
 * - Submit fires PATCH with correct payload + Idempotency-Key header (MSW request capture)
 * - Empty inputs send null
 *
 * TanStack Query test setup: fresh QueryClient per test with retry: false;
 * MSW setupServer with server.resetHandlers() in afterEach; never mock apiClient.
 */

import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import "@testing-library/jest-dom";

import { BillingContactForm } from "../BillingContactForm";
import { billingPaymentContactHandlers } from "../../../../mocks/handlers/billingPaymentContactHandlers";

// ── MSW ──────────────────────────────────────────────────────────────────────

const server = setupServer(...billingPaymentContactHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

function renderForm() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      React.createElement(BillingContactForm),
    ),
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("BillingContactForm", () => {
  it("hydrates inputs from the GET handler", async () => {
    renderForm();

    const phoneInput = await screen.findByTestId("billing-contact-phone-input");
    const emailInput = screen.getByTestId("billing-contact-email-input");

    await waitFor(() => {
      expect(phoneInput).toHaveValue("(804) 555-0142");
    });
    expect(emailInput).toHaveValue("billing@example.com");
  });

  it("invalid email shows a non-color-only error message", async () => {
    renderForm();

    const emailInput = await screen.findByTestId("billing-contact-email-input");

    // Enter an invalid email and blur to trigger validation
    fireEvent.change(emailInput, { target: { value: "not-an-email" } });
    fireEvent.blur(emailInput);

    // Submit to trigger resolver
    fireEvent.click(screen.getByTestId("billing-contact-save-button"));

    await waitFor(() => {
      const errorEl = screen.queryByTestId("billing-contact-email-error");
      expect(errorEl).toBeInTheDocument();
      expect(errorEl?.textContent).toBeTruthy();
    });

    // The error is communicated by text, not color alone (aria-invalid + describedby)
    expect(emailInput).toHaveAttribute("aria-invalid", "true");
  });

  it("submit fires PATCH with correct payload + Idempotency-Key header", async () => {
    let capturedRequest: {
      url: string;
      method: string;
      body: unknown;
      headers: Headers;
    } | null = null;

    server.use(
      http.patch(
        "/api/v1/settings/billing/payment-contact",
        async ({ request }) => {
          const body = (await request.json()) as unknown;
          capturedRequest = {
            url: request.url,
            method: request.method,
            body,
            headers: request.headers,
          };
          return HttpResponse.json({
            billing_contact_phone: (body as Record<string, unknown>)
              .billing_contact_phone,
            billing_contact_email: (body as Record<string, unknown>)
              .billing_contact_email,
          });
        },
      ),
    );

    renderForm();

    // Wait for hydration
    const phoneInput = await screen.findByTestId("billing-contact-phone-input");

    // Change the phone value — PhoneInput normalizes to E.164 (PLP-FIX-4)
    fireEvent.change(phoneInput, { target: { value: "(555) 999-0000" } });

    // Submit
    fireEvent.click(screen.getByTestId("billing-contact-save-button"));

    await waitFor(() => {
      expect(capturedRequest).not.toBeNull();
    });

    expect(capturedRequest!.method).toBe("PATCH");
    expect(capturedRequest!.url).toContain(
      "/api/v1/settings/billing/payment-contact",
    );

    // Payload: both keys present, email unchanged (carried forward), phone as E.164
    const body = capturedRequest!.body as Record<string, unknown>;
    expect(body.billing_contact_phone).toBe("+15559990000");
    expect(body.billing_contact_email).toBe("billing@example.com");

    // Idempotency-Key header present
    const idempotencyKey = capturedRequest!.headers.get("Idempotency-Key");
    expect(idempotencyKey).toBeTruthy();
  });

  it("empty inputs send null (clears the field)", async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.get("/api/v1/settings/billing/payment-contact", () =>
        HttpResponse.json({
          billing_contact_phone: "(804) 555-0142",
          billing_contact_email: "billing@example.com",
        }),
      ),
      http.patch(
        "/api/v1/settings/billing/payment-contact",
        async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({
            billing_contact_phone: null,
            billing_contact_email: null,
          });
        },
      ),
    );

    renderForm();

    const phoneInput = await screen.findByTestId("billing-contact-phone-input");
    const emailInput = screen.getByTestId("billing-contact-email-input");

    // Clear both fields
    fireEvent.change(phoneInput, { target: { value: "" } });
    fireEvent.change(emailInput, { target: { value: "" } });

    fireEvent.click(screen.getByTestId("billing-contact-save-button"));

    await waitFor(() => {
      expect(capturedBody).not.toBeNull();
    });

    expect(capturedBody!.billing_contact_phone).toBeNull();
    expect(capturedBody!.billing_contact_email).toBeNull();
  });

  it("empty-state nudge shown when both values are null on load", async () => {
    server.use(
      http.get("/api/v1/settings/billing/payment-contact", () =>
        HttpResponse.json({
          billing_contact_phone: null,
          billing_contact_email: null,
        }),
      ),
    );

    renderForm();

    await waitFor(() => {
      expect(
        screen.getByText(
          /Add a billing contact so customers can reach you to arrange payment/,
        ),
      ).toBeInTheDocument();
    });
  });
});
