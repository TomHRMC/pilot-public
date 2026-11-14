/**
 * Jobs tab integration tests (MOB-B1)
 *
 * Location: apps/mobile/__tests__/batch_mob_b1/jobs-tab.integration.test.tsx
 *
 * Tests JobsTabScreen end-to-end with MSW-intercepted API calls.
 * Mocks useAuth (user.id) and useRouter (navigation assertions).
 */

import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  JOB_TODAY_1,
  JOB_TODAY_2,
  JOB_UPCOMING_1,
  JOB_UNSCHEDULED,
  MOCK_TECH_ID,
} from "../../mocks/handlers/jobsHandlers";
import type { JobListItem } from "../../features/jobs/job-types";
import { JobsTabScreen } from "../../features/jobs/components/JobsTabScreen";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockRouterPush = jest.fn();

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: {
      id: MOCK_TECH_ID,
      email: "tech@test.com",
      role: "technician",
      tenantId: "tenant-001",
      displayName: "Test Tech",
      accessToken: "token",
    },
    isAuthenticated: true,
    role: "technician",
    signIn: jest.fn(),
    confirmMfaChallenge: jest.fn(),
    signOut: jest.fn(),
    refreshSession: jest.fn(),
  }),
}));

// ── Test server ───────────────────────────────────────────────────────────────

const TODAY = new Date().toISOString().slice(0, 10);

// Default: fixture with today + upcoming + unscheduled jobs
// Backend returns PaginatedJobListResponse { items, total, limit, offset }
const server = setupServer(
  http.get("*/api/v1/jobs/", () => {
    const items = [JOB_TODAY_1, JOB_TODAY_2, JOB_UPCOMING_1, JOB_UNSCHEDULED];
    return HttpResponse.json({
      items,
      total: items.length,
      limit: 50,
      offset: 0,
    });
  }),
  // Quotes handler for pendingQuoteCount
  // Backend returns PaginatedQuoteListResponse { items, total, limit, offset }
  http.get("*/api/v1/quotes", () => {
    const items = [
      {
        id: "q-001",
        quote_number: "Q-001",
        status: "pending_approval",
        customer_name: "Acme",
        total_cents: 50000,
        submitted_at: null,
        has_owner_edits: false,
        quote_version_id: "v-001",
      },
      {
        id: "q-002",
        quote_number: "Q-002",
        status: "approved",
        customer_name: "Smith",
        total_cents: 25000,
        submitted_at: null,
        has_owner_edits: false,
        quote_version_id: "v-002",
      },
    ];
    return HttpResponse.json({
      items,
      total: items.length,
      limit: 50,
      offset: 0,
    });
  }),
);

let qc: QueryClient;

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  qc?.clear();
  mockRouterPush.mockClear();
});
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("JobsTabScreen integration", () => {
  it("renders TODAY section with 2 job cards when API returns today jobs", async () => {
    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("today-section-header")).toBeTruthy();
    });

    expect(screen.getByTestId(`today-job-${JOB_TODAY_1.id}`)).toBeTruthy();
    expect(screen.getByTestId(`today-job-${JOB_TODAY_2.id}`)).toBeTruthy();
    expect(screen.getByText("Acme Electric")).toBeTruthy();
    expect(screen.getByText("Smith Residence")).toBeTruthy();
  });

  it("renders UPCOMING section with 1 upcoming job", async () => {
    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("upcoming-section-header")).toBeTruthy();
    });

    expect(
      screen.getByTestId(`upcoming-job-${JOB_UPCOMING_1.id}`),
    ).toBeTruthy();
    expect(screen.getByText("Jones Commercial")).toBeTruthy();
  });

  it("does NOT render unscheduled jobs in either section", async () => {
    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(
        screen.queryByTestId(`today-job-${JOB_UNSCHEDULED.id}`),
      ).toBeNull();
    });
    expect(
      screen.queryByTestId(`upcoming-job-${JOB_UNSCHEDULED.id}`),
    ).toBeNull();
  });

  it("renders My Quotes entry with pending count badge", async () => {
    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("my-quotes-entry-row")).toBeTruthy();
    });

    // 1 pending_approval quote in fixture
    expect(screen.getByTestId("my-quotes-badge")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("renders empty Today state when no today jobs returned", async () => {
    server.use(
      http.get("*/api/v1/jobs/", () => {
        return HttpResponse.json({
          items: [JOB_UPCOMING_1],
          total: 1,
          limit: 50,
          offset: 0,
        });
      }),
    );

    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("today-empty-state")).toBeTruthy();
    });

    expect(screen.getByText("No jobs scheduled for today")).toBeTruthy();
  });

  it("renders empty Upcoming state when no upcoming jobs returned", async () => {
    server.use(
      http.get("*/api/v1/jobs/", () => {
        return HttpResponse.json({
          items: [JOB_TODAY_1],
          total: 1,
          limit: 50,
          offset: 0,
        });
      }),
    );

    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("upcoming-empty-state")).toBeTruthy();
    });

    expect(screen.getByText("No upcoming jobs this week")).toBeTruthy();
  });

  it("renders error state with Try again button when API returns 500", async () => {
    server.use(
      http.get("*/api/v1/jobs/", () => {
        return HttpResponse.json({ detail: "server error" }, { status: 500 });
      }),
    );

    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("jobs-retry-button")).toBeTruthy();
    });

    expect(screen.getByText("Failed to load jobs")).toBeTruthy();
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("tapping a job card calls router.push with the correct job path", async () => {
    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId(`today-job-${JOB_TODAY_1.id}`)).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId(`today-job-${JOB_TODAY_1.id}`));
    expect(mockRouterPush).toHaveBeenCalledWith(`/jobs/${JOB_TODAY_1.id}`);
  });

  it("tapping My Quotes row calls router.push to the quotes pending route", async () => {
    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("my-quotes-entry-row")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("my-quotes-entry-row"));
    expect(mockRouterPush).toHaveBeenCalledWith(
      "/(tabs)/(home)/quotes/pending",
    );
  });

  it("UPCOMING section collapses and expands when header is pressed", async () => {
    render(<JobsTabScreen />, { wrapper });

    await waitFor(() => {
      expect(
        screen.getByTestId(`upcoming-job-${JOB_UPCOMING_1.id}`),
      ).toBeTruthy();
    });

    // Collapse
    fireEvent.press(screen.getByTestId("upcoming-section-header"));
    await waitFor(() => {
      expect(
        screen.queryByTestId(`upcoming-job-${JOB_UPCOMING_1.id}`),
      ).toBeNull();
    });

    // Expand
    fireEvent.press(screen.getByTestId("upcoming-section-header"));
    await waitFor(() => {
      expect(
        screen.getByTestId(`upcoming-job-${JOB_UPCOMING_1.id}`),
      ).toBeTruthy();
    });
  });
});
