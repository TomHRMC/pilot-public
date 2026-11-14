/**
 * CloseCohortButton unit tests — web (C-B11 Part B)
 *
 * Location: apps/web/src/components/operator/cohort/__tests__/CloseCohortButton.test.tsx
 *
 * Tests: renders button when active, confirmation modal opens.
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { CloseCohortButton } from "../CloseCohortButton";

// Mock notification queue — CloseCohortButton uses useNotificationQueue
vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: vi.fn(),
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
}));

const server = setupServer();

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

describe("CloseCohortButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the Close Cohort button when cohort is active", () => {
    render(<CloseCohortButton cohortIsActive={true} memberCount={3} />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByRole("button", { name: /close charter cohort/i }),
    ).toBeInTheDocument();
  });

  it("renders static badge when cohort is already closed", () => {
    render(<CloseCohortButton cohortIsActive={false} memberCount={3} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Cohort closed")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /close charter cohort/i }),
    ).not.toBeInTheDocument();
  });

  it("opens confirmation modal on click", async () => {
    const user = userEvent.setup();
    render(<CloseCohortButton cohortIsActive={true} memberCount={3} />, {
      wrapper: createWrapper(),
    });

    await user.click(
      screen.getByRole("button", { name: /close charter cohort/i }),
    );

    expect(screen.getByText("Close Charter cohort?")).toBeInTheDocument();
    expect(screen.getByText(/archive the Charter price/i)).toBeInTheDocument();
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Close Cohort" }),
    ).toBeInTheDocument();
  });
});
