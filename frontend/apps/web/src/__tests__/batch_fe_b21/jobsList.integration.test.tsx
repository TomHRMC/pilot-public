/**
 * FE-B21 Integration — Jobs List
 *
 * Location: apps/web/src/__tests__/batch_fe_b21/jobsList.integration.test.tsx
 *
 * Tests:
 * 1. /jobs renders job list from MSW
 * 2. Status filter pills render + filter client-side
 * 3. Each job row has a "View" link to /jobs/[id]
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { jobsHandlers } from "@/mocks/handlers/jobs";
import { JobsPage } from "@/features/jobs/components/JobsPage";

// Mock next/navigation — required for Link components
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/jobs",
  useSearchParams: () => new URLSearchParams(),
}));

// Per-test MSW server
const server = setupServer(...jobsHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant" = "owner",
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

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function Wrapper({
  role = "owner",
  children,
}: {
  role?: "owner" | "office_staff" | "technician" | "accountant";
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("JobsPage integration", () => {
  it("renders job list from MSW handlers", async () => {
    render(<JobsPage />, {
      wrapper: ({ children }) => <Wrapper>{children}</Wrapper>,
    });

    // Wait for MSW data to load
    await waitFor(() => {
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });

    expect(screen.getByText("Smith Residence")).toBeInTheDocument();
    expect(screen.getByText("Martinez Properties")).toBeInTheDocument();
  });

  it("status filter dropdown renders (UI-FIX-1C: pills replaced with select)", async () => {
    render(<JobsPage />, {
      wrapper: ({ children }) => <Wrapper>{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });

    // UI-FIX-1C: status filter is now a <select> dropdown, not pills
    const statusSelect = screen.getByLabelText("Filter by status");
    expect(statusSelect).toBeInTheDocument();
  });

  it("selecting 'completed' and clicking Search triggers server-side filter", async () => {
    render(<JobsPage />, {
      wrapper: ({ children }) => <Wrapper>{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });

    // UI-FIX-1C: select status dropdown and click Search
    const statusSelect = screen.getByLabelText("Filter by status");
    fireEvent.change(statusSelect, { target: { value: "completed" } });
    const searchBtn = screen.getByTestId("job-search-btn");
    fireEvent.click(searchBtn);

    // MSW handler applies status filter — completed jobs visible
    await waitFor(() => {
      expect(screen.getByText("Martinez Properties")).toBeInTheDocument();
    });
  });

  it("each job row has a View link to /jobs/[id]", async () => {
    render(<JobsPage />, {
      wrapper: ({ children }) => <Wrapper>{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByText("Johnson Electrical")).toBeInTheDocument();
    });

    // Get all "View" links and verify one points to job-1
    const viewLinks = screen.getAllByRole("link", { name: /view/i });
    expect(viewLinks.length).toBeGreaterThan(0);

    const job1Link = viewLinks.find(
      (link) => link.getAttribute("href") === "/jobs/job-1",
    );
    expect(job1Link).toBeTruthy();
  });

  it("completed jobs show '→ Invoice' link for owner", async () => {
    render(<JobsPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByText("Martinez Properties")).toBeInTheDocument();
    });

    // Martinez is "completed" — invoice link should be visible for owner
    expect(screen.getByRole("link", { name: /invoice/i })).toBeInTheDocument();
  });

  it("completed jobs do NOT show '→ Invoice' link for tech", async () => {
    render(<JobsPage />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });

    await waitFor(() => {
      expect(screen.getByText("Martinez Properties")).toBeInTheDocument();
    });

    // Tech should not see invoice conversion link
    expect(screen.queryByRole("link", { name: /invoice/i })).toBeNull();
  });
});
