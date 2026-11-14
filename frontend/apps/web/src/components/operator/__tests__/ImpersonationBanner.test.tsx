/**
 * ImpersonationBanner unit tests
 *
 * Location: apps/web/src/components/operator/__tests__/ImpersonationBanner.test.tsx
 *
 * C-B15 Part B: renders "Viewing as:" + tenant name,
 * Exit fires POST end + clearImpersonation + location.assign('/operator/cohort').
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
import { ImpersonationBanner } from "../ImpersonationBanner";
import { setImpersonation, getImpersonation } from "@pilot/shared-api";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

// Stub window.location.assign
const assignMock = vi.fn();
Object.defineProperty(window, "location", {
  value: {
    ...window.location,
    assign: assignMock,
  },
  writable: true,
});

// ── Server ───────────────────────────────────────────────────────────────────

const server = setupServer(
  http.post("/api/v1/operator/impersonation/end", () =>
    HttpResponse.json({ ended: true }),
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

describe("ImpersonationBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    assignMock.mockClear();
  });

  it("renders nothing when no impersonation session is active", () => {
    const { container } = render(<ImpersonationBanner />, {
      wrapper: createWrapper(),
    });
    expect(container.firstChild).toBeNull();
  });

  it("renders 'Viewing as:' + tenant name when session is active", () => {
    setImpersonation({ tenantId: "tenant-001", tenantName: "Acme Electric" });

    render(<ImpersonationBanner />, { wrapper: createWrapper() });

    expect(screen.getByTestId("impersonation-banner")).toBeInTheDocument();
    expect(screen.getByText(/Viewing as:/i)).toBeInTheDocument();
    expect(screen.getByText("Acme Electric")).toBeInTheDocument();
  });

  it("Exit fires POST end, clears session, and triggers location.assign('/operator/cohort')", async () => {
    const user = userEvent.setup();
    setImpersonation({ tenantId: "tenant-001", tenantName: "Acme Electric" });

    render(<ImpersonationBanner />, { wrapper: createWrapper() });

    const exitButton = screen.getByTestId("impersonation-exit-button");
    await user.click(exitButton);

    await waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith("/operator/cohort");
    });

    // Session should be cleared
    expect(getImpersonation()).toBeNull();
  });

  it("Exit clears session even if the end mutation fails", async () => {
    server.use(
      http.post("/api/v1/operator/impersonation/end", () =>
        HttpResponse.json({ error: "server error" }, { status: 500 }),
      ),
    );

    const user = userEvent.setup();
    setImpersonation({ tenantId: "tenant-001", tenantName: "Acme Electric" });

    render(<ImpersonationBanner />, { wrapper: createWrapper() });

    const exitButton = screen.getByTestId("impersonation-exit-button");
    await user.click(exitButton);

    await waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith("/operator/cohort");
    });

    // Session should still be cleared (defensive — spec §8.4)
    expect(getImpersonation()).toBeNull();
  });
});
