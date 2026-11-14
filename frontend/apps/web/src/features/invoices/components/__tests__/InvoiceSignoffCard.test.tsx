/**
 * InvoiceSignoffCard unit tests — CE-1 Part C
 *
 * Location: apps/web/src/features/invoices/components/__tests__/InvoiceSignoffCard.test.tsx
 *
 * Tests: populated render, empty state, loading skeleton, error + retry,
 *        superseded line only when count > 0.
 * RULE: Fresh QueryClient per test with retry: false (§14).
 * RULE: MSW setupServer + resetHandlers in afterEach (§15).
 * RULE: Never mock apiClient (§15).
 */

import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InvoiceSignoffCard } from "../InvoiceSignoffCard";

const server = setupServer(
  http.get("/api/v1/invoices/:invoiceId/signoff", ({ params }) => {
    const { invoiceId } = params as { invoiceId: string };

    if (invoiceId === "inv-empty") {
      return HttpResponse.json({ signoff: null, superseded_count: 0 });
    }

    if (invoiceId === "inv-error") {
      return HttpResponse.json(
        { detail: "Internal server error" },
        { status: 500 },
      );
    }

    if (invoiceId === "inv-superseded") {
      return HttpResponse.json({
        signoff: {
          signoff_id: "so-001",
          invoice_id: "inv-superseded",
          signed_by_name: "John Smith",
          signed_at: "2026-08-12T14:30:00Z",
          client_capture_at: null,
          captured_by_user_id: "u-tech-001",
          signature_url: "https://example.com/sig.png",
        },
        superseded_count: 3,
      });
    }

    // Default: populated
    return HttpResponse.json({
      signoff: {
        signoff_id: "so-001",
        invoice_id: invoiceId,
        signed_by_name: "John Smith",
        signed_at: "2026-08-12T14:30:00Z",
        client_capture_at: null,
        captured_by_user_id: "u-tech-001",
        signature_url: "https://example.com/sig.png",
      },
      superseded_count: 0,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

describe("InvoiceSignoffCard", () => {
  it("renders populated state with signer name and signature image", async () => {
    render(<InvoiceSignoffCard invoiceId="inv-001" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByTestId("signoff-signature-img")).toBeInTheDocument();
    });

    expect(screen.getByText("John Smith")).toBeInTheDocument();
    expect(screen.getByTestId("signoff-signature-img")).toHaveAttribute(
      "alt",
      "Customer signature: John Smith",
    );
  });

  it("renders empty state when signoff is null", async () => {
    render(<InvoiceSignoffCard invoiceId="inv-empty" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByText("No signature captured")).toBeInTheDocument();
    });

    expect(
      screen.queryByTestId("signoff-signature-img"),
    ).not.toBeInTheDocument();
  });

  it("renders loading skeleton while fetching", () => {
    render(<InvoiceSignoffCard invoiceId="inv-loading" />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByTestId("signoff-skeleton-img")).toBeInTheDocument();
  });

  it("renders error state with retry on 500", async () => {
    render(<InvoiceSignoffCard invoiceId="inv-error" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByText("Could not load signature")).toBeInTheDocument();
    });
  });

  it("shows superseded count line only when count > 0", async () => {
    const { rerender } = render(<InvoiceSignoffCard invoiceId="inv-001" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByTestId("signoff-signature-img")).toBeInTheDocument();
    });

    // No superseded line when count = 0
    expect(
      screen.queryByTestId("signoff-superseded-count"),
    ).not.toBeInTheDocument();

    // Re-render with superseded invoice
    rerender(<InvoiceSignoffCard invoiceId="inv-superseded" />);

    await waitFor(() => {
      expect(
        screen.getByTestId("signoff-superseded-count"),
      ).toBeInTheDocument();
    });

    expect(screen.getByTestId("signoff-superseded-count")).toHaveTextContent(
      "3 prior signatures replaced.",
    );
  });
});
