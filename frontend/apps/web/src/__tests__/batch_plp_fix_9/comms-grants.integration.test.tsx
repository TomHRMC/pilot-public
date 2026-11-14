/**
 * PLP-FIX-9 Integration — Comms grants (INV-D-5)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_9/comms-grants.integration.test.tsx
 *
 * Tests:
 * - As office_staff (post-grant): Comms nav item visible, customer Comms tab visible
 * - As accountant/technician: Comms nav hidden, customer Comms tab hidden
 * - Messages widget hidden for technician, visible for office_staff
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { AppSidebar } from "@/components/AppSidebar";
import { RecentCustomerMessagesWidget } from "@/features/dashboard/components/RecentCustomerMessagesWidget";
import { CustomerDetailTabs } from "@/app/(authed)/customers/[id]/_components/CustomerDetailTabs";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/dashboard",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

vi.mock("@/features/dashboard/hooks/useRecentCustomerMessages", () => ({
  useRecentCustomerMessages: () => ({
    messages: [],
    isLoading: false,
    isError: false,
  }),
}));

// localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAuth(role: PilotRole): AuthContextValue {
  const perms = Array.from(ROLE_PERMISSION_MAP[role]) as string[];
  return {
    user: {
      id: "u1",
      email: `${role}@pilot-dev.example.com`,
      role,
      tenantId: "t1",
      displayName: role,
      accessToken: "tok",
      permissions: perms,
    },
    isAuthenticated: true,
    role,
    permissions: perms,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
    whenSessionReady: vi.fn(),
  };
}

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderWithAuth(ui: React.ReactElement, role: PilotRole) {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>{ui}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-9 — comms grants (INV-D-5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  describe("AppSidebar Comms nav item", () => {
    it("office_staff sees Comms nav (communications.view granted)", () => {
      renderWithAuth(<AppSidebar />, "office_staff");
      expect(screen.getByText("Comms")).toBeInTheDocument();
    });

    it("accountant does NOT see Comms nav (lacks communications.view)", () => {
      renderWithAuth(<AppSidebar />, "accountant");
      expect(screen.queryByText("Comms")).not.toBeInTheDocument();
    });

    it("technician does NOT see Comms nav (lacks communications.view)", () => {
      renderWithAuth(<AppSidebar />, "technician");
      expect(screen.queryByText("Comms")).not.toBeInTheDocument();
    });
  });

  describe("RecentCustomerMessagesWidget", () => {
    it("office_staff sees the widget (communications.view granted)", () => {
      renderWithAuth(<RecentCustomerMessagesWidget />, "office_staff");
      expect(screen.getByTestId("recent-messages-widget")).toBeInTheDocument();
    });

    it("technician does NOT see the widget (hidden, not error)", () => {
      renderWithAuth(<RecentCustomerMessagesWidget />, "technician");
      expect(
        screen.queryByTestId("recent-messages-widget"),
      ).not.toBeInTheDocument();
    });
  });

  describe("CustomerDetailTabs Comms tab", () => {
    it("office_staff sees Comms tab (communications.view granted)", () => {
      renderWithAuth(<CustomerDetailTabs customerId="c1" />, "office_staff");
      expect(screen.getByText("Comms")).toBeInTheDocument();
    });

    it("accountant does NOT see Comms tab (lacks communications.view)", () => {
      renderWithAuth(<CustomerDetailTabs customerId="c1" />, "accountant");
      expect(screen.queryByText("Comms")).not.toBeInTheDocument();
    });
  });
});
