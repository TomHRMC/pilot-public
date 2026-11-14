/**
 * FE-B28 — JobsPage TanStack Table migration integration test
 *
 * Location: apps/web/src/__tests__/batch_fe_b28/jobs_table_migration.integration.test.tsx
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { setupServer } from "msw/node";
import { handlers } from "../../mocks/handlers/index";
import { JobsPage } from "@/features/jobs/components/JobsPage";

vi.mock("next/navigation", () => ({
  usePathname: () => "/jobs",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuthContext(): AuthContextValue {
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

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <AuthContext.Provider value={makeAuthContext()}>
      <QueryClientProvider client={qc}>
        <JobsPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("JobsPage — FE-B28 TanStack Table migration", () => {
  it("renders without crashing", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Jobs")).toBeInTheDocument();
    });
  });

  it("renders correct column headers", async () => {
    renderPage();
    await waitFor(() => {
      // "Customer", "Status", "Scheduled" may appear in both filter pills AND column headers
      // Use getAllByText — at least one match confirms the header is rendered.
      expect(screen.getAllByText("Customer").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Status").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Scheduled").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Actions").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders job data from MSW fixture", async () => {
    renderPage();
    await waitFor(() => {
      // MSW jobs.ts fixture has "Johnson Electrical"
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });
  });

  it("renders sort indicator on sortable headers", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });
    const sortIndicators = screen.getAllByText("↕");
    expect(sortIndicators.length).toBeGreaterThanOrEqual(1);
  });

  it("status filter pills render", async () => {
    renderPage();
    await waitFor(() => {
      // "All" pill uniquely exists as a filter button (not in data rows)
      const allPills = screen.getAllByText("All");
      expect(allPills.length).toBeGreaterThanOrEqual(1);
      // "Completed" may appear in both filter pills and data badges — use getAllByText
      const completedEls = screen.getAllByText("Completed");
      expect(completedEls.length).toBeGreaterThanOrEqual(1);
    });
  });
});
