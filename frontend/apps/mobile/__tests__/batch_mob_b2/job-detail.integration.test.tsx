/**
 * Job Detail integration tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/job-detail.integration.test.tsx
 *
 * Tests JobDetailScreen end-to-end with MSW-intercepted API calls.
 * Verifies: header render, all 9 sections present, navigation, error state, loading state.
 */

import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  act,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { JobDetailScreen } from "../../features/jobs/components/JobDetailScreen";

const MOCK_USER_ID = "tech-user-001";
const MOCK_JOB_ID = "job-today-001";
const TODAY = new Date().toISOString().slice(0, 10);

// ── Mocks ──────────────────────────────────────────────────────────────────────

const mockRouterPush = jest.fn();
const mockRouterBack = jest.fn();

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockRouterPush, back: mockRouterBack }),
  useFocusEffect: (cb: () => void) => cb(),
}));

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({ user: { id: MOCK_USER_ID } }),
}));

jest.mock("../../features/offline-sync/hooks/useChangeJobStatus", () => ({
  useChangeJobStatus: () => ({
    change: jest.fn(),
    isPending: false,
    error: null,
  }),
}));
jest.mock("../../features/offline-sync/hooks/useCreateTimeEntry", () => ({
  useCreateTimeEntry: () => ({
    create: jest.fn(),
    isPending: false,
    error: null,
  }),
}));
jest.mock("../../features/offline-sync/hooks/useCreateExpense", () => ({
  useCreateExpense: () => ({
    create: jest.fn(),
    isPending: false,
    error: null,
  }),
}));
jest.mock("../../features/offline-sync/hooks/useCreateJobNote", () => ({
  useCreateJobNote: () => ({
    create: jest.fn(),
    isPending: false,
    error: null,
  }),
}));
jest.mock("../../features/offline-sync/hooks/useConfirmLoto", () => ({
  useConfirmLoto: () => ({ confirm: jest.fn(), isPending: false, error: null }),
}));
jest.mock("../../features/offline-sync/hooks/useCreateChangeOrder", () => ({
  useCreateChangeOrder: () => ({
    create: jest.fn(),
    isPending: false,
    error: null,
  }),
}));
jest.mock("../../features/offline-sync/hooks/useCreatePhoto", () => ({
  useCreatePhoto: () => ({ create: jest.fn(), isPending: false, error: null }),
}));

jest.mock("../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({
      create: jest.fn(),
      query: jest
        .fn()
        .mockReturnValue({ fetch: jest.fn().mockResolvedValue([]) }),
    }),
  },
}));

jest.mock("@nozbe/watermelondb", () => ({
  Q: { where: jest.fn(), oneOf: jest.fn() },
}));

// ── Server ─────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/jobs/:jobId", ({ params }) => {
    return HttpResponse.json({
      id: params["jobId"],
      tenant_id: "tenant-001",
      customer_id: "customer-001",
      site_id: "site-001",
      status_id: "status-scheduled",
      scheduled_start_at: `${TODAY}T09:00:00Z`,
      scheduled_end_at: `${TODAY}T12:00:00Z`,
      estimated_duration_minutes: 180,
    });
  }),
  http.get("*/api/v1/jobs/:jobId/time-entries", () => HttpResponse.json([])),
  http.get("*/api/v1/jobs/:jobId/expenses", () => HttpResponse.json([])),
  http.get("*/api/v1/jobs/:jobId/notes", () =>
    HttpResponse.json({ detail: "not found" }, { status: 404 }),
  ),
  http.get("*/api/v1/jobs/:jobId/loto-confirmations", () =>
    HttpResponse.json([]),
  ),
  http.get("*/api/v1/jobs/:jobId/change-orders", () => HttpResponse.json([])),
  http.get("*/api/v1/jobs/:jobId/projected-margin", () =>
    HttpResponse.json({
      margin_percent: 38,
      quoted_hours: 3,
      actual_hours: 2.5,
      cost_delta_cents: 4200,
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

function wrapper({
  children,
  withCache = true,
}: {
  children: React.ReactNode;
  withCache?: boolean;
}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (withCache) {
    qc.setQueryData(
      ["tech-jobs-today", MOCK_USER_ID, TODAY],
      [
        {
          id: MOCK_JOB_ID,
          status_code: "scheduled",
          customer_name: "Acme Electric",
          tenant_id: "tenant-001",
          customer_id: "customer-001",
          site_id: "site-001",
          status_id: "status-scheduled",
        },
      ],
    );
  }
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe("Job Detail integration", () => {
  it("shows loading indicator before MSW responds", async () => {
    // Use a delayed handler
    server.use(
      http.get("*/api/v1/jobs/:jobId", async () => {
        await new Promise((r) => setTimeout(r, 200));
        return HttpResponse.json({
          id: MOCK_JOB_ID,
          tenant_id: "tenant-001",
          customer_id: "customer-001",
          site_id: "site-001",
          status_id: "status-scheduled",
          scheduled_start_at: `${TODAY}T09:00:00Z`,
          scheduled_end_at: `${TODAY}T12:00:00Z`,
          estimated_duration_minutes: 180,
        });
      }),
    );

    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, {
      wrapper: ({ children }) => wrapper({ children, withCache: true }),
    });

    expect(screen.getByTestId("job-detail-loading")).toBeTruthy();
  });

  it("renders header with customer_name and status pill from cache", async () => {
    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, {
      wrapper: ({ children }) => wrapper({ children, withCache: true }),
    });

    await waitFor(() =>
      expect(screen.getByTestId("job-detail-screen")).toBeTruthy(),
    );

    expect(screen.getByTestId("customer-name")).toBeTruthy();
    expect(screen.getByText("Acme Electric")).toBeTruthy();
    expect(screen.getByTestId("status-pill")).toBeTruthy();
  });

  it("renders all 9 sections in the scrollable area", async () => {
    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, {
      wrapper: ({ children }) => wrapper({ children, withCache: true }),
    });

    await waitFor(() =>
      expect(screen.getByTestId("job-detail-screen")).toBeTruthy(),
    );

    expect(screen.getByTestId("section-clock-in-out")).toBeTruthy();
    expect(screen.getByTestId("section-loto")).toBeTruthy();
    expect(screen.getByTestId("section-projected-margin")).toBeTruthy();
    expect(screen.getByTestId("section-expenses")).toBeTruthy();
    expect(screen.getByTestId("section-change-orders")).toBeTruthy();
    expect(screen.getByTestId("section-job-notes")).toBeTruthy();
    expect(screen.getByTestId("section-photos")).toBeTruthy();
    expect(screen.getByTestId("message-customer-button")).toBeTruthy();
    expect(screen.getByTestId("mark-complete-section")).toBeTruthy();
  });

  it("navigates to comms on 'Message Customer' press", async () => {
    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, {
      wrapper: ({ children }) => wrapper({ children, withCache: true }),
    });

    await waitFor(() =>
      expect(screen.getByTestId("message-customer-button")).toBeTruthy(),
    );

    act(() => {
      fireEvent.press(screen.getByTestId("message-customer-button"));
    });

    await waitFor(() => {
      expect(mockRouterPush).toHaveBeenCalledWith(
        expect.stringContaining(`/jobs/${MOCK_JOB_ID}/comms`),
      );
    });
  });

  it("shows error state when GET /api/v1/jobs/{id} returns 500", async () => {
    server.use(
      http.get("*/api/v1/jobs/:jobId", () => {
        return HttpResponse.json({ detail: "error" }, { status: 500 });
      }),
    );

    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, {
      wrapper: ({ children }) => wrapper({ children, withCache: true }),
    });

    await waitFor(() =>
      expect(screen.getByTestId("job-detail-error")).toBeTruthy(),
    );

    expect(screen.getByTestId("retry-button")).toBeTruthy();
  });

  it("renders date range in header", async () => {
    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, {
      wrapper: ({ children }) => wrapper({ children, withCache: true }),
    });

    await waitFor(() => expect(screen.getByTestId("date-range")).toBeTruthy());
  });
});
