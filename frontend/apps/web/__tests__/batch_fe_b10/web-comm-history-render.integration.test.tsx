/**
 * web-comm-history-render — integration test
 *
 * Tests: GET /customers/{id}/communications → flat CommunicationHistoryItem list rendered.
 * POST-BETA: updated to real endpoint + real response shape (not threaded SmsThread[]).
 * Fix 2: updated to mock /customers/:id/threads and new data-testid prefixes (hist-).
 * Design doc G.2
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { CustomerCommsHistoryView } from "../../src/features/customer-comms/components/CustomerCommsHistoryView";

const MOCK_ITEMS = [
  {
    communication_id: "comm-001",
    template_code: "job_dispatch",
    actual_channel: "sms",
    channel_override_flag: false,
    customer_preferred_channel: "sms",
    rendered_message: "Your technician is on the way.",
    rendered_subject: null,
    status: "sent",
    sent_at: "2026-05-26T09:00:00Z",
    sender_user_id: "tech-001",
    job_id: "job-001",
  },
  {
    communication_id: "comm-002",
    template_code: "quote_sent",
    actual_channel: "email",
    channel_override_flag: false,
    customer_preferred_channel: "email",
    rendered_message: "Please review your quote.",
    rendered_subject: "Your Quote from Pilot",
    status: "sent",
    sent_at: "2026-05-26T10:00:00Z",
    sender_user_id: "tech-001",
    job_id: null,
  },
];

const server = setupServer(
  http.get("/api/v1/customers/:customerId/communications", ({ params }) => {
    const { customerId } = params as { customerId: string };
    if (customerId === "customer-empty") {
      return HttpResponse.json({
        customer_id: "customer-empty",
        total: 0,
        page: 1,
        page_size: 50,
        items: [],
      });
    }
    return HttpResponse.json({
      customer_id: customerId,
      total: MOCK_ITEMS.length,
      page: 1,
      page_size: 50,
      items: MOCK_ITEMS,
    });
  }),
  // Fix 2: mock the new threads endpoint so useCustomerSmsThreads resolves cleanly
  http.get("/api/v1/customers/:customerId/threads", () => {
    return HttpResponse.json({ threads: [], total: 0 });
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("web-comm-history-render integration", () => {
  it("renders comm items after successful API call", async () => {
    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("customer-comms-history")).toBeTruthy();
    });

    // data-testid keys are now prefixed with hist- for history items
    expect(screen.getByTestId("comm-item-hist-comm-001")).toBeTruthy();
    expect(screen.getByTestId("comm-item-hist-comm-002")).toBeTruthy();
  });

  it("renders SMS and Email badges", async () => {
    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("SMS")).toBeTruthy();
    });
    expect(screen.getByText("Email")).toBeTruthy();
  });

  it("renders empty state when no items", async () => {
    render(<CustomerCommsHistoryView customerId="customer-empty" />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId("comms-history-empty")).toBeTruthy();
    });
  });
});
