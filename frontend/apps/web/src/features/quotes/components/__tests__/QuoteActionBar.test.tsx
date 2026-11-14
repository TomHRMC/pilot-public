/**
 * QuoteActionBar unit tests — FE-B19
 *
 * Location: apps/web/src/features/quotes/components/__tests__/QuoteActionBar.test.tsx
 *
 * Platform: Web (Vitest + @testing-library/react)
 *
 * RBAC visibility rules tested:
 *   - draft + owner: shows "Send to Customer", NOT "Submit for Approval"
 *   - draft + tech: shows "Submit for Approval", NOT "Send to Customer"
 *   - accepted + owner: shows "Convert to Job"
 *   - non-draft, non-accepted: renders nothing
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { QuoteActionBar } from "../QuoteActionBar";

// Mock mutations — test only RBAC visibility, not mutation behavior
vi.mock("../../hooks/useSubmitForApproval", () => ({
  useSubmitForApproval: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("../../hooks/useConvertQuote", () => ({
  useConvertQuote: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("../../hooks/useGeneratePublicLink", () => ({
  useGeneratePublicLink: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// ---------------------------------------------------------------------------
// Auth context helper — uses AuthContext.Provider (RoleGate reads AuthContext)
// ---------------------------------------------------------------------------
function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role,
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function createWrapper(
  role: "owner" | "office_staff" | "technician" | "accountant",
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={makeContext(role)}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </AuthContext.Provider>
    );
  }
  return TestWrapper;
}

const BASE_PROPS = {
  quoteId: "q-00000001-0000-0000-0000-000000000001",
  customerEmail: "mike@smithelectrical.example.com",
  customerName: "Smith Electrical",
  quoteVersionId: "qv-00000001-0000-0000-0000-000000000001",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("QuoteActionBar — RBAC visibility", () => {
  it("draft + owner: shows Send to Customer button", () => {
    render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="draft"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("owner") },
    );
    expect(
      screen.getByRole("button", { name: /send to customer/i }),
    ).toBeInTheDocument();
  });

  it("draft + owner: does NOT show Submit for Approval button", () => {
    render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="draft"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("owner") },
    );
    expect(
      screen.queryByRole("button", { name: /submit for approval/i }),
    ).toBeNull();
  });

  it("draft + tech: shows Submit for Approval button", () => {
    render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="draft"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("technician") },
    );
    expect(
      screen.getByRole("button", { name: /submit for approval/i }),
    ).toBeInTheDocument();
  });

  it("draft + tech: does NOT show Send to Customer button", () => {
    render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="draft"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("technician") },
    );
    expect(
      screen.queryByRole("button", { name: /send to customer/i }),
    ).toBeNull();
  });

  it("accepted + owner: shows Convert to Job button", () => {
    render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="sent"
        customerAcceptedAt="2026-06-01T00:00:00Z"
      />,
      { wrapper: createWrapper("owner") },
    );
    expect(
      screen.getByRole("button", { name: /convert to job/i }),
    ).toBeInTheDocument();
  });

  it("sent (not accepted) + owner: renders nothing", () => {
    const { container } = render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="sent"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("owner") },
    );
    // Component returns null for non-draft, non-accepted
    expect(container.firstChild).toBeNull();
  });

  it("pending_approval status: renders nothing", () => {
    const { container } = render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="pending_approval"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("owner") },
    );
    expect(container.firstChild).toBeNull();
  });

  it("converted status: renders nothing", () => {
    const { container } = render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="converted"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("owner") },
    );
    expect(container.firstChild).toBeNull();
  });

  // UI-FIX-1B: approved status tests
  it("approved + owner: renders Send to Customer button", () => {
    render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="approved"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("owner") },
    );
    expect(
      screen.getByRole("button", { name: /send to customer/i }),
    ).toBeInTheDocument();
  });

  it("approved + owner: action bar is NOT null (guard did not fire)", () => {
    render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="approved"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("owner") },
    );
    // Guard did not fire — "Send to Customer" is visible (owner has quotes.edit)
    expect(
      screen.getByRole("button", { name: /send to customer/i }),
    ).toBeInTheDocument();
  });

  it("approved + tech: renders nothing (no quotes.edit permission)", () => {
    render(
      <QuoteActionBar
        {...BASE_PROPS}
        status="approved"
        customerAcceptedAt={null}
      />,
      { wrapper: createWrapper("technician") },
    );
    // RoleGate blocks the button — the action bar renders (guard passes for approved),
    // but the Send to Customer button inside is hidden — tech does not have quotes.edit
    expect(
      screen.queryByRole("button", { name: /send to customer/i }),
    ).toBeNull();
  });
});
