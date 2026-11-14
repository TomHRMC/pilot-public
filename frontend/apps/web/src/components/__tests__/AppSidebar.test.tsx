/**
 * AppSidebar — Unit Tests (UI-FIX-2E / FE-UI-NAV-S1)
 *
 * Location: apps/web/src/components/__tests__/AppSidebar.test.tsx
 *
 * Tests:
 *   - Expanded state: icons + labels visible
 *   - Collapsed state: labels hidden, toggle button changes aria-label
 *   - localStorage key pilot.sidebar.collapsed persists state
 *   - Nav order: Dashboard, Schedule, Customers, Quotes, Jobs, Invoices, Comms, Catalog, Reports
 *   - Toggle: pill «/» button at top-right (FE-UI-NAV-S1 — no text label)
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { AppSidebar } from "../AppSidebar";

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

// ─── Mocks ────────────────────────────────────────────────────────────────────
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

// ─── Helper ───────────────────────────────────────────────────────────────────
const ownerAuth: AuthContextValue = {
  user: {
    id: "u1",
    email: "owner@example.com",
    role: "owner",
    tenantId: "t1",
    displayName: "Owner User",
    accessToken: "tok",
    // PLP-FIX-9: owner has wildcard in prod; tests need explicit permissions
    // for the server-authoritative gating path (useHasPermission).
    permissions: ["*"],
  },
  isAuthenticated: true,
  role: "owner",
  permissions: ["*"],
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
};

function renderSidebar(authValue = ownerAuth) {
  return render(
    React.createElement(
      AuthContext.Provider,
      { value: authValue },
      React.createElement(AppSidebar),
    ),
  );
}

beforeEach(() => {
  localStorageMock.clear();
});

// ─── Tests ────────────────────────────────────────────────────────────────────
describe("AppSidebar — UI-FIX-2E", () => {
  describe("Expanded state (default)", () => {
    it("renders all 9 nav labels when expanded", () => {
      renderSidebar();
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
      expect(screen.getByText("Schedule")).toBeInTheDocument();
      expect(screen.getByText("Customers")).toBeInTheDocument();
      expect(screen.getByText("Quotes")).toBeInTheDocument();
      expect(screen.getByText("Jobs")).toBeInTheDocument();
      expect(screen.getByText("Invoices")).toBeInTheDocument();
      expect(screen.getByText("Comms")).toBeInTheDocument();
      expect(screen.getByText("Catalog")).toBeInTheDocument();
      expect(screen.getByText("Reports")).toBeInTheDocument();
    });

    it("renders Collapse navigation pill toggle button when expanded (FE-UI-NAV-S1)", () => {
      renderSidebar();
      // FE-UI-NAV-S1: pill toggle uses aria-label only (no text label)
      expect(
        screen.getByRole("button", { name: /collapse navigation/i }),
      ).toBeInTheDocument();
    });

    it("does NOT render 'Collapse' text label (FE-UI-NAV-S1: pill toggle has no text)", () => {
      renderSidebar();
      // FE-UI-NAV-S1: bottom Collapse text button was removed; pill has aria-label only
      expect(screen.queryByText("Collapse")).not.toBeInTheDocument();
    });
  });

  describe("Collapse / expand toggle", () => {
    it("hides nav labels and shows Expand button after clicking pill toggle", () => {
      renderSidebar();
      const toggleBtn = screen.getByRole("button", {
        name: /collapse navigation/i,
      });
      fireEvent.click(toggleBtn);
      // After collapse, nav labels should be gone
      expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
      // Expand button should appear (aria-label changes)
      expect(
        screen.getByRole("button", { name: /expand navigation/i }),
      ).toBeInTheDocument();
    });

    it("persists collapsed state to localStorage key pilot.sidebar.collapsed", () => {
      renderSidebar();
      const toggleBtn = screen.getByRole("button", {
        name: /collapse navigation/i,
      });
      fireEvent.click(toggleBtn);
      expect(localStorageMock.getItem("pilot.sidebar.collapsed")).toBe("true");
    });

    it("reads expanded state from localStorage on mount", () => {
      localStorageMock.setItem("pilot.sidebar.collapsed", "false");
      renderSidebar();
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /collapse navigation/i }),
      ).toBeInTheDocument();
    });

    it("reads collapsed state from localStorage on mount — shows Expand button", () => {
      localStorageMock.setItem("pilot.sidebar.collapsed", "true");
      renderSidebar();
      expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /expand navigation/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Active state", () => {
    it("Dashboard link has aria-current=page when pathname is /dashboard", () => {
      renderSidebar();
      const link = screen.getByText("Dashboard").closest("a");
      expect(link).toHaveAttribute("aria-current", "page");
    });
  });

  describe("RBAC", () => {
    it("tech role does NOT see Reports", () => {
      // PLP-FIX-9: tech auth must use technician permissions, not owner's wildcard
      const techPerms = Array.from(ROLE_PERMISSION_MAP.technician) as string[];
      const techAuth: AuthContextValue = {
        ...ownerAuth,
        user: {
          ...ownerAuth.user!,
          role: "technician",
          permissions: techPerms,
        },
        role: "technician",
        permissions: techPerms,
      };
      renderSidebar(techAuth);
      expect(screen.queryByText("Reports")).not.toBeInTheDocument();
    });

    it("owner role sees Catalog", () => {
      renderSidebar();
      expect(screen.getByText("Catalog")).toBeInTheDocument();
    });
  });

  describe("Removed nav items", () => {
    it("does NOT render Operations nav item", () => {
      renderSidebar();
      expect(screen.queryByText("Operations")).not.toBeInTheDocument();
    });

    it("does NOT render Sync nav item", () => {
      renderSidebar();
      expect(screen.queryByText("Sync")).not.toBeInTheDocument();
    });

    it("does NOT render Notifications nav item", () => {
      renderSidebar();
      expect(screen.queryByText("Notifications")).not.toBeInTheDocument();
    });

    it("does NOT render Settings nav item", () => {
      renderSidebar();
      expect(screen.queryByText("Settings")).not.toBeInTheDocument();
    });
  });
});
