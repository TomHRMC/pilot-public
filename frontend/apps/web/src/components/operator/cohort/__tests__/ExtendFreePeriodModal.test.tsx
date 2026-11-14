/**
 * ExtendFreePeriodModal unit tests — web (C-B11 Part B)
 *
 * Location: apps/web/src/components/operator/cohort/__tests__/ExtendFreePeriodModal.test.tsx
 *
 * Tests: renders form, validation blocks empty reason, submit fires mutation.
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { ExtendFreePeriodModal } from "../ExtendFreePeriodModal";
import type { CohortMember } from "../CohortMemberRow";

const mockMember: CohortMember = {
  tenant_id: "tenant-001",
  business_name: "Acme Electric",
  charter_member_number: 1,
  free_period_ends_at: "2026-11-04T00:00:00Z",
  days_remaining: 90,
  stripe_status: "trialing",
  has_payment_method: false,
  messaging_status: "not_started",
  customer_count: 3,
  invoice_count: 2,
  days_since_last_job: 5,
  last_contact: null,
  alert_level: "none",
};

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

describe("ExtendFreePeriodModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the form with current end date and fields", () => {
    render(<ExtendFreePeriodModal member={mockMember} onClose={vi.fn()} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Current free period ends")).toBeInTheDocument();
    // Date may render as "November 4, 2026" or "November 3, 2026" depending
    // on the test runner timezone — match by month to stay resilient.
    expect(screen.getByText(/November \d, 2026/)).toBeInTheDocument();
    expect(screen.getByLabelText(/new end date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/reason/i)).toBeInTheDocument();
    expect(screen.getByText("Preview")).toBeInTheDocument();
    expect(screen.getByText("None (silent extension)")).toBeInTheDocument();
  });

  it("validation blocks submit when reason is too short", async () => {
    const user = userEvent.setup();
    render(<ExtendFreePeriodModal member={mockMember} onClose={vi.fn()} />, {
      wrapper: createWrapper(),
    });

    // Enter a date but a short reason
    await user.type(screen.getByLabelText(/new end date/i), "2026-12-04");
    await user.type(screen.getByLabelText(/reason/i), "short");

    const submitButton = screen.getByRole("button", {
      name: /extend free period/i,
    });
    expect(submitButton).toBeDisabled();
  });

  it("submit fires the extend mutation with correct payload", async () => {
    const user = userEvent.setup();
    let capturedBody: unknown = null;
    server.use(
      http.post(
        "/api/v1/operator/cohort/:tenantId/extend",
        async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            tenant_id: "tenant-001",
            previous_free_period_ends_at: "2026-11-04T00:00:00Z",
            new_free_period_ends_at: "2026-12-04T00:00:00Z",
            stripe_subscription_id: "sub_mock_001",
            stripe_trial_end_updated: true,
          });
        },
      ),
    );

    const onClose = vi.fn();
    render(<ExtendFreePeriodModal member={mockMember} onClose={onClose} />, {
      wrapper: createWrapper(),
    });

    await user.type(screen.getByLabelText(/new end date/i), "2026-12-04");
    await user.type(
      screen.getByLabelText(/reason/i),
      "Customer needs more time to evaluate",
    );

    const submitButton = screen.getByRole("button", {
      name: /extend free period/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(capturedBody).toEqual({
        new_free_period_ends_at: "2026-12-04T00:00:00Z",
        override_reason: "Customer needs more time to evaluate",
      });
    });
  });
});
