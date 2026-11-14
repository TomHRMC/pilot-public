/**
 * TenantSelector unit tests
 *
 * Location: apps/web/src/components/operator/__tests__/TenantSelector.test.tsx
 *
 * C-B15 Part B: renders trigger, opens panel, filters list,
 * accountant → warning (no modal), owner → modal opens.
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
  beforeEach,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { TenantSelector } from "../TenantSelector";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/operator/cohort",
}));

const mockAddNotification = vi.fn();
vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: mockAddNotification,
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
}));

// ── Mock data ────────────────────────────────────────────────────────────────

const mockTenants = {
  tenants: [
    {
      tenant_id: "tenant-001",
      name: "Acme Electric",
      is_active: true,
      tier_name: "Charter",
      subscription_status: "trialing",
      created_at: "2026-08-01T00:00:00Z",
    },
    {
      tenant_id: "tenant-002",
      name: "Bright Spark LLC",
      is_active: true,
      tier_name: "Pro",
      subscription_status: "active",
      created_at: "2026-07-15T00:00:00Z",
    },
  ],
};

// ── Server ───────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/operator/tenants", () => HttpResponse.json(mockTenants)),
  http.post("/api/v1/operator/impersonation/start", () =>
    HttpResponse.json({
      tenant_id: "tenant-001",
      tenant_name: "Acme Electric",
      impersonator_user_id: "uuid-platform",
      role_code: "owner",
      started_at: "2026-08-08T16:00:00Z",
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("TenantSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
  });

  it("renders the trigger button", () => {
    render(<TenantSelector platformRoleCode="owner" />, {
      wrapper: createWrapper(),
    });
    expect(screen.getByTestId("tenant-selector-trigger")).toBeInTheDocument();
  });

  it("opens the dropdown panel on trigger click and shows tenants", async () => {
    const user = userEvent.setup();
    render(<TenantSelector platformRoleCode="owner" />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId("tenant-selector-trigger"));

    await waitFor(() => {
      expect(screen.getByText("Acme Electric")).toBeInTheDocument();
    });
    expect(screen.getByText("Bright Spark LLC")).toBeInTheDocument();
  });

  it("filters the list when searching", async () => {
    const user = userEvent.setup();
    render(<TenantSelector platformRoleCode="owner" />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId("tenant-selector-trigger"));

    await waitFor(() => {
      expect(screen.getByText("Acme Electric")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Search tenants"), "Bright");

    await waitFor(() => {
      expect(screen.queryByText("Acme Electric")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Bright Spark LLC")).toBeInTheDocument();
  });

  it("accountant role → shows warning notification, no modal", async () => {
    const user = userEvent.setup();
    render(<TenantSelector platformRoleCode="accountant" />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId("tenant-selector-trigger"));

    await waitFor(() => {
      expect(screen.getByText("Acme Electric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Acme Electric"));

    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: "warning",
        title: "Your role does not permit impersonation.",
      }),
    );
    // No confirm modal should be open
    expect(
      screen.queryByTestId("impersonation-confirm-modal"),
    ).not.toBeInTheDocument();
  });

  it("owner role → opens confirm modal on tenant select", async () => {
    const user = userEvent.setup();
    render(<TenantSelector platformRoleCode="owner" />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId("tenant-selector-trigger"));

    await waitFor(() => {
      expect(screen.getByText("Acme Electric")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Acme Electric"));

    await waitFor(() => {
      expect(
        screen.getByTestId("impersonation-confirm-modal"),
      ).toBeInTheDocument();
    });
  });
});
