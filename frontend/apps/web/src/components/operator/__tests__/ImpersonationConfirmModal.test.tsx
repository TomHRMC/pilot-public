/**
 * ImpersonationConfirmModal unit tests
 *
 * Location: apps/web/src/components/operator/__tests__/ImpersonationConfirmModal.test.tsx
 *
 * C-B15 Part B: preview block renders, Cancel closes without mutation,
 * confirm fires POST + setImpersonation + location.assign('/dashboard'),
 * 403/409 error messages per spec §5.9.
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
import { ImpersonationConfirmModal } from "../ImpersonationConfirmModal";
import { getImpersonation } from "@pilot/shared-api";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// Stub window.location.assign (jsdom doesn't implement navigation)
const assignMock = vi.fn();
Object.defineProperty(window, "location", {
  value: {
    ...window.location,
    assign: assignMock,
  },
  writable: true,
});

// ── Mock data ────────────────────────────────────────────────────────────────

const mockTenant = {
  tenant_id: "tenant-001",
  name: "Acme Electric",
  is_active: true,
  tier_name: "Charter",
  subscription_status: "trialing",
  created_at: "2026-08-01T00:00:00Z",
};

// ── Server ───────────────────────────────────────────────────────────────────

const server = setupServer(
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

describe("ImpersonationConfirmModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    assignMock.mockClear();
  });

  it("renders preview block with tenant name, tier, and status", () => {
    render(
      <ImpersonationConfirmModal tenant={mockTenant} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByText("View as a tenant")).toBeInTheDocument();
    expect(screen.getAllByText("Acme Electric").length).toBeGreaterThan(0);
    expect(screen.getByText("Charter")).toBeInTheDocument();
    expect(screen.getByText("Trialing")).toBeInTheDocument();
    expect(screen.getByText("Owner (full access)")).toBeInTheDocument();
  });

  it("Cancel closes the modal without firing the mutation", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <ImpersonationConfirmModal tenant={mockTenant} onClose={onClose} />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByText("Cancel"));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(assignMock).not.toHaveBeenCalled();
  });

  it("confirm fires POST start, writes session, and triggers location.assign('/dashboard')", async () => {
    const user = userEvent.setup();
    render(
      <ImpersonationConfirmModal tenant={mockTenant} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    const confirmButton = screen.getByTestId("impersonation-confirm-button");
    await user.click(confirmButton);

    await waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith("/dashboard");
    });

    // Session should be written to sessionStorage
    expect(getImpersonation()).toEqual({
      tenantId: "tenant-001",
      tenantName: "Acme Electric",
    });
  });

  it("403 error shows 'Your role does not permit impersonation.' and modal stays open", async () => {
    server.use(
      http.post("/api/v1/operator/impersonation/start", () =>
        HttpResponse.json(
          { type: "forbidden", title: "Forbidden", status: 403 },
          { status: 403 },
        ),
      ),
    );

    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <ImpersonationConfirmModal tenant={mockTenant} onClose={onClose} />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByTestId("impersonation-confirm-button"));

    await waitFor(() => {
      expect(screen.getByTestId("impersonation-modal-error")).toHaveTextContent(
        "Your role does not permit impersonation.",
      );
    });

    expect(onClose).not.toHaveBeenCalled();
    expect(assignMock).not.toHaveBeenCalled();
  });

  it("409 error shows 'This tenant is inactive and cannot be impersonated.'", async () => {
    server.use(
      http.post("/api/v1/operator/impersonation/start", () =>
        HttpResponse.json(
          { type: "inactive", title: "Inactive", status: 409 },
          { status: 409 },
        ),
      ),
    );

    const user = userEvent.setup();
    render(
      <ImpersonationConfirmModal tenant={mockTenant} onClose={vi.fn()} />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByTestId("impersonation-confirm-button"));

    await waitFor(() => {
      expect(screen.getByTestId("impersonation-modal-error")).toHaveTextContent(
        "This tenant is inactive and cannot be impersonated.",
      );
    });
  });
});
