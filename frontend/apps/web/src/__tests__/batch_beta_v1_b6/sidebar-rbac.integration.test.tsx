/**
 * BETA-B6: Sidebar RBAC integration test
 *
 * Location: apps/web/src/__tests__/batch_beta_v1_b6/sidebar-rbac.integration.test.tsx
 *
 * UI-FIX-2E: Updated to reflect new nav items:
 *   - 9 items total: Dashboard, Schedule, Customers, Quotes, Jobs, Invoices,
 *     Comms, Catalog (catalog.view), Reports (reports.view)
 *   - Removed: Operations, Sync, Notifications, Settings
 *
 * RBAC rules:
 *   - Reports: requires reports.view (owner / office_staff / operator; NOT tech)
 *   - Catalog: requires catalog.view (all roles except those lacking it)
 *   - All other 7 items: visible to all authenticated roles
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { AppSidebar } from "../../components/AppSidebar";

// ─── localStorage mock ────────────────────────────────────────────────────────
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

// ─── Next.js navigation mock ─────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) =>
    React.createElement("a", { href, ...rest }, children),
}));

// ─── Auth context helpers ─────────────────────────────────────────────────────
function makeAuthValue(role: PilotRole): AuthContextValue {
  // PLP-FIX-7: derive permissions from ROLE_PERMISSION_MAP so the
  // server-authoritative gating path works in tests.
  const perms = Array.from(ROLE_PERMISSION_MAP[role]) as string[];
  return {
    user: {
      id: "u1",
      email: "test@example.com",
      role,
      tenantId: "t1",
      displayName: "Test User",
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
    whenSessionReady: vi.fn().mockResolvedValue(null),
  };
}

function renderSidebarAs(role: PilotRole) {
  return render(
    React.createElement(
      AuthContext.Provider,
      { value: makeAuthValue(role) },
      React.createElement(AppSidebar),
    ),
  );
}

beforeEach(() => {
  localStorageMock.clear();
});

// ─── Tests ────────────────────────────────────────────────────────────────────
describe("AppSidebar RBAC — UI-FIX-2E new nav items", () => {
  // ── Reports RBAC ──────────────────────────────────────────────────────────
  it("owner sees Reports (has reports.view)", () => {
    renderSidebarAs("owner");
    expect(screen.getByText("Reports")).toBeInTheDocument();
  });

  it("operator sees Reports (has reports.view)", () => {
    renderSidebarAs("accountant");
    expect(screen.getByText("Reports")).toBeInTheDocument();
  });

  it("office_staff sees Reports (has reports.view)", () => {
    renderSidebarAs("office_staff");
    expect(screen.getByText("Reports")).toBeInTheDocument();
  });

  it("tech does NOT see Reports (lacks reports.view)", () => {
    renderSidebarAs("technician");
    expect(screen.queryByText("Reports")).not.toBeInTheDocument();
  });

  // ── Catalog RBAC ──────────────────────────────────────────────────────────
  it("owner sees Catalog (has catalog.view)", () => {
    renderSidebarAs("owner");
    expect(screen.getByText("Catalog")).toBeInTheDocument();
  });

  it("tech sees Catalog (has catalog.view)", () => {
    renderSidebarAs("technician");
    expect(screen.getByText("Catalog")).toBeInTheDocument();
  });

  // ── Removed items — must NOT appear ──────────────────────────────────────
  it("owner does NOT see Operations in sidebar (moved to settings only)", () => {
    renderSidebarAs("owner");
    expect(screen.queryByText("Operations")).not.toBeInTheDocument();
  });

  it("owner does NOT see Sync in sidebar", () => {
    renderSidebarAs("owner");
    expect(screen.queryByText("Sync")).not.toBeInTheDocument();
  });

  it("owner does NOT see Notifications nav item (now a settings sub-page)", () => {
    renderSidebarAs("owner");
    expect(screen.queryByText("Notifications")).not.toBeInTheDocument();
  });

  it("owner does NOT see Settings nav item (now a header gear icon)", () => {
    renderSidebarAs("owner");
    expect(screen.queryByText("Settings")).not.toBeInTheDocument();
  });

  // PLP-FIX-7/PLP-FIX-9: Nav items are now permission-gated (server-authoritative).
  // Technician lacks schedule.manage, quotes.view, invoices.view, communications.view
  // → those items are hidden. Office_staff now HAS communications.view → Comms visible.
  it("owner sees all 9 nav items", () => {
    renderSidebarAs("owner");
    const expected = [
      "Dashboard",
      "Schedule",
      "Customers",
      "Quotes",
      "Jobs",
      "Invoices",
      "Comms",
      "Catalog",
      "Reports",
    ];
    for (const label of expected) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("office_staff sees Dashboard, Schedule, Customers, Quotes, Jobs, Invoices, Comms, Catalog, Reports (PLP-FIX-9: comms granted)", () => {
    const { unmount } = renderSidebarAs("office_staff");
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Schedule")).toBeInTheDocument();
    expect(screen.getByText("Customers")).toBeInTheDocument();
    expect(screen.getByText("Quotes")).toBeInTheDocument();
    expect(screen.getByText("Jobs")).toBeInTheDocument();
    expect(screen.getByText("Invoices")).toBeInTheDocument();
    // PLP-FIX-9 (INV-D-5): office_staff now holds communications.view → Comms visible
    expect(screen.getByText("Comms")).toBeInTheDocument();
    expect(screen.getByText("Catalog")).toBeInTheDocument();
    expect(screen.getByText("Reports")).toBeInTheDocument();
    unmount();
  });

  it("technician sees Dashboard, Customers, Jobs, Catalog but NOT Schedule, Quotes, Invoices, Comms, Reports", () => {
    const { unmount } = renderSidebarAs("technician");
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Customers")).toBeInTheDocument();
    expect(screen.getByText("Jobs")).toBeInTheDocument();
    expect(screen.getByText("Catalog")).toBeInTheDocument();
    // technician lacks these permissions in prod grants
    expect(screen.queryByText("Schedule")).not.toBeInTheDocument();
    expect(screen.queryByText("Quotes")).not.toBeInTheDocument();
    expect(screen.queryByText("Invoices")).not.toBeInTheDocument();
    expect(screen.queryByText("Comms")).not.toBeInTheDocument();
    expect(screen.queryByText("Reports")).not.toBeInTheDocument();
    unmount();
  });

  // ── Toggle button ──────────────────────────────────────────────────────────
  it("renders a Collapse navigation button when expanded (default state)", () => {
    renderSidebarAs("owner");
    expect(
      screen.getByRole("button", { name: /collapse navigation/i }),
    ).toBeInTheDocument();
  });
});
