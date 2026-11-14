/**
 * Kickback flow integration tests
 *
 * Location: apps/web/__tests__/batch_fe_b5/kickback-flow.integration.test.tsx
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QuoteApprovalActionBar } from "@/features/quote-approval/components/QuoteApprovalActionBar";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

const server = setupServer(
  http.post("/api/v1/quotes/:id/kickback", () =>
    HttpResponse.json({
      id: "q1",
      status: "draft",
      kicked_back_at: new Date().toISOString(),
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function ownerAuth(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "o@t.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return (
    <AuthContext.Provider value={ownerAuth()}>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("Kickback flow integration", () => {
  it("opens KickbackCommentModal when Kick Back is clicked", async () => {
    render(
      <QuoteApprovalActionBar
        quoteId="q1"
        pendingEditCount={0}
        requireApproval
        isApproving={false}
        lineItems={[]}
        onApprove={vi.fn()}
        onApproveWithEdits={vi.fn()}
      />,
      { wrapper },
    );

    fireEvent.click(screen.getByTestId("kickback-btn"));
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeTruthy();
    });
  });

  it("submit disabled when no comment in kickback modal", async () => {
    render(
      <QuoteApprovalActionBar
        quoteId="q1"
        pendingEditCount={0}
        requireApproval
        isApproving={false}
        lineItems={[]}
        onApprove={vi.fn()}
        onApproveWithEdits={vi.fn()}
      />,
      { wrapper },
    );

    fireEvent.click(screen.getByTestId("kickback-btn"));
    await waitFor(() => screen.getByRole("dialog"));
    expect(screen.getByTestId("kickback-submit-btn")).toBeDisabled();
  });

  it("submits kickback with overall comment and closes modal", async () => {
    let kickbackCalled = false;
    server.use(
      http.post("/api/v1/quotes/:id/kickback", () => {
        kickbackCalled = true;
        return HttpResponse.json({
          id: "q1",
          status: "draft",
          kicked_back_at: new Date().toISOString(),
        });
      }),
    );

    render(
      <QuoteApprovalActionBar
        quoteId="q1"
        pendingEditCount={0}
        requireApproval
        isApproving={false}
        lineItems={[]}
        onApprove={vi.fn()}
        onApproveWithEdits={vi.fn()}
      />,
      { wrapper },
    );

    fireEvent.click(screen.getByTestId("kickback-btn"));
    await waitFor(() => screen.getByRole("dialog"));

    fireEvent.change(screen.getByLabelText(/overall comment/i), {
      target: { value: "Labor rate needs revision per current schedule" },
    });

    fireEvent.click(screen.getByTestId("kickback-submit-btn"));
    await waitFor(() => expect(kickbackCalled).toBe(true));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});
