/**
 * SettingsIndexPage — Unit Tests (FE-UI-NAV-S1)
 *
 * Location: apps/web/src/features/settings/components/__tests__/SettingsIndexPage.test.tsx
 *
 * Verifies:
 *   - Personal section always visible
 *   - Workspace section visible to owner/operator (settings.tenant.write)
 *   - Workspace section hidden for tech role
 *   - Notifications card links to /settings/notifications/tenant-defaults
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import "@testing-library/jest-dom";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { SettingsIndexPage } from "../SettingsIndexPage";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => React.createElement("a", { href, className }, children),
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeAuth(
  role: "owner" | "accountant" | "office_staff" | "technician" = "owner",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "mike@example.com",
      role,
      tenantId: "t1",
      displayName: "Mike Johnson",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function renderPage(
  role: "owner" | "accountant" | "office_staff" | "technician" = "owner",
) {
  return render(
    React.createElement(
      AuthContext.Provider,
      { value: makeAuth(role) },
      React.createElement(SettingsIndexPage),
    ),
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("SettingsIndexPage — FE-UI-NAV-S1", () => {
  describe("Personal section", () => {
    it("renders Settings heading", () => {
      renderPage("owner");
      expect(
        screen.getByRole("heading", { name: /settings/i, level: 1 }),
      ).toBeInTheDocument();
    });

    it("renders Personal section for all roles (owner)", () => {
      renderPage("owner");
      expect(screen.getByText("Profile & Account")).toBeInTheDocument();
      expect(screen.getByText("Security")).toBeInTheDocument();
      // Two "Notifications" cards exist for owner (Personal + Workspace) — assert by href
      const personalNotifLink = screen
        .getAllByRole("link")
        .find(
          (l) =>
            l.getAttribute("href") === "/settings/notifications/preferences",
        );
      expect(personalNotifLink).toBeDefined();
    });

    it("renders Personal section for tech role", () => {
      renderPage("technician");
      expect(screen.getByText("Profile & Account")).toBeInTheDocument();
      expect(screen.getByText("Security")).toBeInTheDocument();
      // Personal Notifications card (Workspace hidden for tech, so only one "Notifications")
      const personalNotifLink = screen
        .getAllByRole("link")
        .find(
          (l) =>
            l.getAttribute("href") === "/settings/notifications/preferences",
        );
      expect(personalNotifLink).toBeDefined();
    });

    it("Profile & Account links to /settings/my-account/profile", () => {
      renderPage("owner");
      const link = screen.getByText("Profile & Account").closest("a");
      expect(link).toHaveAttribute("href", "/settings/my-account/profile");
    });
  });

  describe("Workspace section (settings.tenant.write)", () => {
    it("renders Workspace section for owner role", () => {
      renderPage("owner");
      expect(screen.getByText("Team")).toBeInTheDocument();
      expect(screen.getByText("Operations")).toBeInTheDocument();
    });

    it("hides Workspace section for accountant role (read-only set — ADR-0010)", () => {
      renderPage("accountant");
      expect(screen.queryByText("Team")).not.toBeInTheDocument();
    });

    it("hides Workspace section for tech role", () => {
      renderPage("technician");
      expect(screen.queryByText("Team")).not.toBeInTheDocument();
      expect(screen.queryByText("Operations")).not.toBeInTheDocument();
    });

    // PLP-FIX-7: office_staff now sees Team card (gated on users.view) but
    // not Operations/Branding/etc (gated on settings.tenant.write).
    it("office_staff sees Team card but NOT Operations in Workspace", () => {
      renderPage("office_staff");
      expect(screen.getByText("Team")).toBeInTheDocument();
      expect(screen.queryByText("Operations")).not.toBeInTheDocument();
    });

    it("Notifications card in Workspace links to /settings/notifications/tenant-defaults", () => {
      renderPage("owner");
      // Find the Notifications link in Workspace section (not Personal)
      const links = screen.getAllByRole("link");
      const notificationsLink = links.find(
        (l) =>
          l.getAttribute("href") === "/settings/notifications/tenant-defaults",
      );
      expect(notificationsLink).toBeDefined();
    });

    // TS-BUG-1 — Website card (Defect 1 fix: dead-nav bug)
    it("renders Website card for owner role", () => {
      renderPage("owner");
      expect(screen.getByText("Website")).toBeInTheDocument();
    });

    it("Website card links to /settings/website", () => {
      renderPage("owner");
      const link = screen.getByText("Website").closest("a");
      expect(link).toHaveAttribute("href", "/settings/website");
    });

    it("Website card sits in the Workspace section (after Branding, before Voice & AI)", () => {
      renderPage("owner");
      const links = screen.getAllByRole("link");
      const websiteIdx = links.findIndex(
        (l) => l.getAttribute("href") === "/settings/website",
      );
      const brandingIdx = links.findIndex(
        (l) => l.getAttribute("href") === "/settings/communications",
      );
      const voiceIdx = links.findIndex(
        (l) => l.getAttribute("href") === "/settings/voice-ai",
      );
      expect(websiteIdx).toBeGreaterThan(-1);
      expect(brandingIdx).toBeGreaterThan(-1);
      expect(voiceIdx).toBeGreaterThan(-1);
      // Website comes after Branding and before Voice & AI
      expect(websiteIdx).toBeGreaterThan(brandingIdx);
      expect(websiteIdx).toBeLessThan(voiceIdx);
    });

    it("hides Website card for tech role (Workspace section hidden)", () => {
      renderPage("technician");
      expect(screen.queryByText("Website")).not.toBeInTheDocument();
    });

    // PLP — Billing & Subscription card (dead-nav bug, same class as TS-BUG-1 Website card)
    it("renders Billing & Subscription card for owner role", () => {
      renderPage("owner");
      expect(screen.getByText("Billing & Subscription")).toBeInTheDocument();
    });

    it("Billing & Subscription card links to /settings/billing", () => {
      renderPage("owner");
      const link = screen.getByText("Billing & Subscription").closest("a");
      expect(link).toHaveAttribute("href", "/settings/billing");
    });

    it("Billing & Subscription card sits in the Workspace section (after Team, before Operations)", () => {
      renderPage("owner");
      const links = screen.getAllByRole("link");
      const billingIdx = links.findIndex(
        (l) => l.getAttribute("href") === "/settings/billing",
      );
      const teamIdx = links.findIndex(
        (l) => l.getAttribute("href") === "/settings/team",
      );
      const operationsIdx = links.findIndex(
        (l) => l.getAttribute("href") === "/settings/operations",
      );
      expect(billingIdx).toBeGreaterThan(-1);
      expect(teamIdx).toBeGreaterThan(-1);
      expect(operationsIdx).toBeGreaterThan(-1);
      // Billing comes after Team and before Operations
      expect(billingIdx).toBeGreaterThan(teamIdx);
      expect(billingIdx).toBeLessThan(operationsIdx);
    });

    it("hides Billing & Subscription card for accountant role (read-only set — ADR-0010)", () => {
      renderPage("accountant");
      expect(
        screen.queryByText("Billing & Subscription"),
      ).not.toBeInTheDocument();
    });

    it("hides Billing & Subscription card for tech role (Workspace section hidden)", () => {
      renderPage("technician");
      expect(
        screen.queryByText("Billing & Subscription"),
      ).not.toBeInTheDocument();
    });

    it("hides Billing & Subscription card for office_staff role (billing.view gate)", () => {
      renderPage("office_staff");
      expect(
        screen.queryByText("Billing & Subscription"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Integrations & System section", () => {
    it("renders Data & Privacy for all roles (no gate)", () => {
      renderPage("technician");
      expect(screen.getByText("Data & Privacy")).toBeInTheDocument();
    });

    it("hides Integrations for tech role (integrations.manage gate)", () => {
      renderPage("technician");
      // Integrations card is gated by integrations.manage — tech doesn't have it
      expect(screen.queryByText("Integrations")).not.toBeInTheDocument();
    });

    it("shows Integrations for owner role", () => {
      renderPage("owner");
      expect(screen.getByText("Integrations")).toBeInTheDocument();
    });
  });
});
