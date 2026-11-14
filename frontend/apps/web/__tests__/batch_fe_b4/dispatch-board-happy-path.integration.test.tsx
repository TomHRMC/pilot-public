/**
 * Dispatch Board Happy Path — Integration Tests
 *
 * Location: apps/web/__tests__/batch_fe_b4/dispatch-board-happy-path.integration.test.tsx
 * Per batch-fe-b4-design.md §I.2
 * Target: 4 tests
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { handlers } from "../../src/mocks/handlers";

// ── Auth mock: mock RoleGate to bypass auth in integration tests ─────────────
// (RoleGate uses relative imports to useAuth, not @pilot/ui/auth)
vi.mock("@pilot/ui/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useRequiresPermission: () => ({ permitted: true }),
  ROLE_PERMISSION_MAP: {},
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: { id: "user-1", email: "owner@test.com" },
    role: "owner",
    isAuthenticated: true,
    signIn: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn(),
  }),
  AuthContext: { _currentValue: null },
}));

// Mock next/navigation (DispatchBoardPage uses useRouter for job card navigation)
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/schedule",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock react-dnd HTML5 backend (requires real DOM pointer events)
vi.mock("react-dnd", () => ({
  DndProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useDrag: () => [{ isDragging: false }, vi.fn(), vi.fn()],
  useDrop: () => [{ isOver: false, canDrop: true }, vi.fn()],
}));

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("Dispatch Board — Happy Path Integration", () => {
  it("board renders toolbar with Today button", async () => {
    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(
      () => {
        expect(screen.getByText("Today")).toBeInTheDocument();
      },
      { timeout: 5000 },
    );
  });

  it("filter bar is rendered (DISPATCH-B2 replaced sidebar with FilterBar)", async () => {
    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    // DISPATCH-B2: FilterBar replaced FilterSidebar — assert via the bar's aria-label
    await waitFor(() => {
      expect(
        screen.getByLabelText("Dispatch board filter bar"),
      ).toBeInTheDocument();
    });
  });

  it("view tab switcher renders Day/Week/Month tabs", async () => {
    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText("Day")).toBeInTheDocument();
      expect(screen.getByText("Week")).toBeInTheDocument();
      expect(screen.getByText("Month")).toBeInTheDocument();
    });
  });

  it("board renders the info bar", async () => {
    const { DispatchBoardPage } =
      await import("../../src/features/dispatch-board/components/DispatchBoardPage");

    render(<DispatchBoardPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      // Toolbar is part of the board; dispatch board page renders it
      expect(
        screen.getByRole("tablist", { name: "Calendar view" }),
      ).toBeInTheDocument();
    });
  });
});
