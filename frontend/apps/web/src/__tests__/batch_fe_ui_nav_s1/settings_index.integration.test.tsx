/**
 * Settings Index — Integration Tests (FE-UI-NAV-S1)
 *
 * Location: apps/web/src/__tests__/batch_fe_ui_nav_s1/settings_index.integration.test.tsx
 *
 * Tests that the SettingsIndexPage renders correctly for different roles
 * and that navigation links are correct.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { SettingsIndexPage } from "@/features/settings/components/SettingsIndexPage";

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
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(
        AuthContext.Provider,
        { value: makeAuth(role) },
        React.createElement(SettingsIndexPage),
      ),
    ),
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Settings Index Integration — FE-UI-NAV-S1", () => {
  it("renders /settings route without 404 (Settings heading visible)", () => {
    renderPage("owner");
    expect(
      screen.getByRole("heading", { level: 1, name: /settings/i }),
    ).toBeInTheDocument();
  });

  it("owner sees Personal section (Profile & Account + Security)", () => {
    renderPage("owner");
    expect(screen.getByText("Profile & Account")).toBeInTheDocument();
    expect(screen.getByText("Security")).toBeInTheDocument();
  });

  it("owner sees Workspace section (Team, Operations, Branding, Voice)", () => {
    renderPage("owner");
    expect(screen.getByText("Team")).toBeInTheDocument();
    expect(screen.getByText("Operations")).toBeInTheDocument();
    expect(screen.getByText("Branding")).toBeInTheDocument();
    expect(screen.getByText("Voice & AI")).toBeInTheDocument();
  });

  it("tech role sees only Personal section — Workspace hidden", () => {
    renderPage("technician");
    expect(screen.getByText("Profile & Account")).toBeInTheDocument();
    expect(screen.getByText("Security")).toBeInTheDocument();
    // Workspace items not in DOM
    expect(screen.queryByText("Team")).not.toBeInTheDocument();
    expect(screen.queryByText("Operations")).not.toBeInTheDocument();
  });

  it("Personal Notifications card links to /settings/notifications/preferences for all roles", () => {
    renderPage("technician");
    const links = screen.getAllByRole("link");
    const personalNotifLink = links.find(
      (l) => l.getAttribute("href") === "/settings/notifications/preferences",
    );
    expect(personalNotifLink).toBeDefined();
    expect(personalNotifLink).toHaveTextContent(/notifications/i);
  });

  it("Notifications card in Workspace section links to /settings/notifications/tenant-defaults", () => {
    renderPage("owner");
    const links = screen.getAllByRole("link");
    const tenantDefaultsLink = links.find(
      (l) =>
        l.getAttribute("href") === "/settings/notifications/tenant-defaults",
    );
    expect(tenantDefaultsLink).toBeDefined();
    expect(tenantDefaultsLink).toHaveTextContent(/notifications/i);
  });

  // PLP-FIX-7: office_staff now sees Team card (gated on users.view) but
  // not Operations (gated on settings.tenant.write).
  it("office_staff sees Team card but NOT Operations (no settings.tenant.write)", () => {
    renderPage("office_staff");
    expect(screen.getByText("Team")).toBeInTheDocument();
    expect(screen.queryByText("Operations")).not.toBeInTheDocument();
  });

  it("Data & Privacy visible to tech role (no RBAC gate)", () => {
    renderPage("technician");
    expect(screen.getByText("Data & Privacy")).toBeInTheDocument();
  });
});
