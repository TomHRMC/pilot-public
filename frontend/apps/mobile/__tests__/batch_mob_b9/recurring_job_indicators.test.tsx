/**
 * recurring_job_indicators — MOB-B9 integration tests
 *
 * Location: apps/mobile/__tests__/batch_mob_b9/recurring_job_indicators.test.tsx
 *
 * Tests recurring ↻ badge on JobCardRow and "Part of recurring series" banner
 * on JobDetailScreen.
 *
 * Rules applied:
 *   - Expo Router mocked (Rule 16 — every screen test)
 *   - WatermelonDB mocked (Rule 16 — every test touching DB)
 *   - .toBeTruthy() / .toBeNull() — no toBeInTheDocument() (Rule 17 — mobile)
 *   - retry: false on QueryClient (Rule 14)
 */

import React from "react";
import { render, screen } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

// ── useJobDetail mock ─────────────────────────────────────────────────────────

import type { JobDetailData } from "../../features/jobs/hooks/useJobDetail";

// ── Imports ───────────────────────────────────────────────────────────────────

import { JobCardRow } from "../../features/jobs/components/JobCardRow";
import { JobDetailScreen } from "../../features/jobs/components/JobDetailScreen";
import type { JobListItem } from "../../features/jobs/job-types";

// ── Expo Router mock (required for all screen tests) ───────────────────────────

const mockPush = jest.fn();
const mockBack = jest.fn();

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack, replace: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: mockPush, back: mockBack },
  Link: ({ children }: { children: React.ReactNode }) => children,
  // useFocusEffect is called by ProjectedMarginSection inside JobDetailScreen
  useFocusEffect: jest.fn((cb: () => void) => cb()),
}));

// ── WatermelonDB mock (required for all tests touching DB) ────────────────────

jest.mock("../../database", () => ({
  database: {
    write: jest.fn((fn: () => unknown) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn: (r: Record<string, unknown>) => void) => {
        const record = { id: "mock-id", localSyncStatus: "pending" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));

// ── Auth mock ─────────────────────────────────────────────────────────────────

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({ user: { id: "tech-user-001" } }),
}));

// ── MSW server (replaces banned apiClient mock) ──────────────────────────────
// Covers the LOTO policy query inside JobDetailScreen (useLotoPolicy hook
// calls GET /api/v1/settings/loto-policy). Returns an empty/default policy
// so the component renders without error.

const server = setupServer(
  http.get("*/api/v1/settings/loto-policy", () =>
    HttpResponse.json({
      loto_required: false,
      loto_steps: [],
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const mockUseJobDetail = jest.fn();

jest.mock("../../features/jobs/hooks/useJobDetail", () => ({
  useJobDetail: (...args: unknown[]) => mockUseJobDetail(...args),
}));

// ── useChangeJobStatus mock ───────────────────────────────────────────────────

jest.mock("../../features/offline-sync/hooks/useChangeJobStatus", () => ({
  useChangeJobStatus: () => ({ change: jest.fn(), isPending: false }),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeJobListItem(overrides: Partial<JobListItem> = {}): JobListItem {
  return {
    id: "job-card-001",
    tenant_id: "tenant-001",
    customer_id: "cust-001",
    site_id: "site-001",
    status_id: "status-scheduled",
    status_code: "scheduled",
    customer_name: "Acme Electric",
    scheduled_start_at: "2026-08-01T09:00:00Z",
    scheduled_end_at: "2026-08-01T12:00:00Z",
    estimated_duration_minutes: 180,
    ...overrides,
  };
}

function makeJobDetailData(
  overrides: Partial<{ recurrence_rule_id: string | null }> = {},
): JobDetailData {
  return {
    job: {
      id: "job-detail-001",
      tenant_id: "tenant-001",
      customer_id: "cust-001",
      site_id: "site-001",
      status_id: "status-scheduled",
      scheduled_start_at: "2026-08-01T09:00:00Z",
      scheduled_end_at: "2026-08-01T12:00:00Z",
      estimated_duration_minutes: 180,
      recurrence_rule_id: overrides.recurrence_rule_id ?? null,
    },
    timeEntries: [],
    status_code: "scheduled",
    customer_name: "Acme Electric",
    activeTimeEntry: null,
  };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderWithQueryClient(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>{ui}</QueryClientProvider>,
  );
}

// ── Cleanup ───────────────────────────────────────────────────────────────────

beforeEach(() => {
  mockPush.mockClear();
  mockBack.mockClear();
  mockUseJobDetail.mockReset();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("MOB-B9 — Recurring Job Indicators", () => {
  // ── JobCardRow badge ───────────────────────────────────────────────────────

  it("test_recurring_badge_visible_on_card_with_rule", () => {
    render(
      <JobCardRow
        job={makeJobListItem({ recurrence_rule_id: "rule-001" })}
        onPress={() => {}}
      />,
    );
    expect(screen.getByTestId("recurring-badge")).toBeTruthy();
  });

  it("test_recurring_badge_absent_on_card_without_rule", () => {
    render(
      <JobCardRow
        job={makeJobListItem({ recurrence_rule_id: null })}
        onPress={() => {}}
      />,
    );
    expect(screen.queryByTestId("recurring-badge")).toBeNull();
  });

  // ── JobDetailScreen banner ─────────────────────────────────────────────────

  it("test_recurring_banner_visible_on_detail_with_rule", () => {
    mockUseJobDetail.mockReturnValue({
      data: makeJobDetailData({ recurrence_rule_id: "rule-001" }),
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    renderWithQueryClient(<JobDetailScreen jobId="job-detail-001" />);

    expect(screen.getByTestId("recurring-series-banner")).toBeTruthy();
    expect(screen.getByText(/recurring series/i)).toBeTruthy();
  });

  it("test_recurring_banner_absent_on_detail_without_rule", () => {
    mockUseJobDetail.mockReturnValue({
      data: makeJobDetailData({ recurrence_rule_id: null }),
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    renderWithQueryClient(<JobDetailScreen jobId="job-detail-001" />);

    expect(screen.queryByTestId("recurring-series-banner")).toBeNull();
  });

  it("test_recurring_banner_shows_manage_text", () => {
    mockUseJobDetail.mockReturnValue({
      data: makeJobDetailData({ recurrence_rule_id: "rule-001" }),
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    renderWithQueryClient(<JobDetailScreen jobId="job-detail-001" />);

    expect(screen.getByText(/Manage/i)).toBeTruthy();
  });
});
