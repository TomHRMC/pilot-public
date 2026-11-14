/**
 * JobDetailScreen unit tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/JobDetailScreen.test.tsx
 *
 * Tests "Mark Complete" button visibility, confirm dialog, and status guards.
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";
import { Alert } from "react-native";
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
const mockChange = jest.fn().mockResolvedValue({});

jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockRouterPush, back: mockRouterBack }),
  useFocusEffect: (cb: () => void) => cb(),
}));

jest.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({ user: { id: MOCK_USER_ID } }),
}));

jest.mock("../../features/offline-sync/hooks/useChangeJobStatus", () => ({
  useChangeJobStatus: () => ({
    change: mockChange,
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

function makeJobServer(statusCode = "scheduled") {
  return setupServer(
    http.get("*/api/v1/jobs/:jobId", () => {
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
      }),
    ),
  );
}

const server = makeJobServer();
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  // Pre-populate cache with status_code for Mark Complete tests
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
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe("JobDetailScreen", () => {
  it("shows 'Mark Job Complete' button when status_code is not completed", async () => {
    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("mark-complete-button")).toBeTruthy();
    });
  });

  it("hides 'Mark Job Complete' when status_code is completed", async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    qc.setQueryData(
      ["tech-jobs-today", MOCK_USER_ID, TODAY],
      [
        {
          id: MOCK_JOB_ID,
          status_code: "completed",
          customer_name: "Acme Electric",
          tenant_id: "tenant-001",
          customer_id: "customer-001",
          site_id: "site-001",
          status_id: "status-completed",
        },
      ],
    );

    const completedWrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: qc }, children);

    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, {
      wrapper: completedWrapper,
    });

    await waitFor(() =>
      expect(screen.queryByTestId("mark-complete-button")).toBeNull(),
    );
  });

  it("shows confirm dialog on 'Mark Job Complete' press", async () => {
    const alertSpy = jest.spyOn(Alert, "alert");

    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, { wrapper });

    await waitFor(() =>
      expect(screen.getByTestId("mark-complete-button")).toBeTruthy(),
    );

    act(() => {
      fireEvent.press(screen.getByTestId("mark-complete-button"));
    });

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith(
        "Mark job complete?",
        expect.any(String),
        expect.any(Array),
      );
    });
  });

  it("calls changeStatus.change() after confirming complete", async () => {
    const alertSpy = jest
      .spyOn(Alert, "alert")
      .mockImplementation((_title, _msg, buttons) => {
        // Simulate pressing the "Complete" button (index 1)
        const completeBtn = buttons?.find((b) => b.text === "Complete");
        if (completeBtn?.onPress) {
          void completeBtn.onPress();
        }
      });

    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, { wrapper });

    await waitFor(() =>
      expect(screen.getByTestId("mark-complete-button")).toBeTruthy(),
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId("mark-complete-button"));
    });

    await waitFor(() => {
      expect(mockChange).toHaveBeenCalledWith(
        expect.objectContaining({
          jobId: MOCK_JOB_ID,
          fromStatus: "scheduled",
          toStatus: "completed",
        }),
      );
    });

    alertSpy.mockRestore();
  });

  it("disables 'Mark Complete' with note when status_code is null (cache miss)", async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    // No cache populated — status_code will be null

    const nullCacheWrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(QueryClientProvider, { client: qc }, children);

    render(<JobDetailScreen jobId={MOCK_JOB_ID} />, {
      wrapper: nullCacheWrapper,
    });

    await waitFor(() =>
      expect(screen.getByTestId("status-cache-note")).toBeTruthy(),
    );

    expect(
      screen.getByTestId("mark-complete-button").props.accessibilityState
        ?.disabled,
    ).toBe(true);
  });
});
