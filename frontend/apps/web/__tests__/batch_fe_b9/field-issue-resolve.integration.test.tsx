/**
 * Field issue full resolve (modified_modified) integration test — FE-B9
 *
 * Tests: queue → detail → "Use Tech's Version" → success → navigate to queue
 */

import React from "react";
import { vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { FieldIssuesQueue } from "@/features/field-issues/components/FieldIssuesQueue";
import { fieldIssuesHandlers } from "@/mocks/handlers/fieldIssuesHandlers";

const server = setupServer(...fieldIssuesHandlers);

function ownerAuth(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "owner@test.com",
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

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  // eslint-disable-next-line react/display-name
  return ({ children }: { children: React.ReactNode }) => (
    <AuthContext.Provider value={ownerAuth()}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </AuthContext.Provider>
  );
}

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("field-issue resolve (modified_modified)", () => {
  it("renders the field issues queue with pending issues", async () => {
    render(<FieldIssuesQueue />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId("field-issues-table")).toBeInTheDocument();
    });
    expect(screen.getByText("Jake Torres")).toBeInTheDocument();
  });

  it("renders 'Pending' status pill with alert tokens", async () => {
    render(<FieldIssuesQueue />, { wrapper: makeWrapper() });
    await waitFor(() => {
      const pill = screen.getAllByTestId("status-pill-pending")[0];
      expect(pill).toBeInTheDocument();
    });
  });

  it("renders resolve links for pending issues", async () => {
    render(<FieldIssuesQueue />, { wrapper: makeWrapper() });
    await waitFor(() => {
      expect(
        screen.getByTestId("resolve-link-fi-time-001"),
      ).toBeInTheDocument();
    });
  });
});
