/**
 * SettingsSidebar — Integration Tests (BETA-B7)
 *
 * Location: apps/web/__tests__/batch_beta_b7/settings-sidebar.integration.test.tsx
 * Per batch-beta-v1-fixes-b7-design.md §J.2 and §J.6 (settings regression)
 *
 * Tests:
 * 1. Navigate to /settings/operations → sub-items visible
 * 2. Integrations → QuickBooks expanded → depth-2 item visible with deeper indent
 * 3. Sidebar renders without text-caption class on any group label
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";

// Mock next/navigation
const mockPathname = vi.fn(() => "/settings");
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({
    href,
    className,
    children,
    "aria-current": ariaCurrent,
    "data-testid": dataTestId,
    ...rest
  }: {
    href: string;
    className?: string;
    children: React.ReactNode;
    "aria-current"?: React.AriaAttributes["aria-current"];
    "data-testid"?: string;
    [key: string]: unknown;
  }) => (
    <a
      href={href}
      className={className}
      aria-current={ariaCurrent}
      data-testid={dataTestId}
      {...rest}
    >
      {children}
    </a>
  ),
}));

// Mock @pilot/ui
vi.mock("@pilot/ui", () => ({
  SettingsSidebarSearch: () => null,
}));

// PLP-FIX-7: SettingsSidebar now calls useHasPermission which reads AuthContext.
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";

function makeAuthContext(): AuthContextValue {
  const perms = Array.from(ROLE_PERMISSION_MAP.owner) as string[];
  return {
    user: {
      id: "u1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
      accessToken: "tok",
      permissions: perms,
    },
    isAuthenticated: true,
    role: "owner",
    permissions: perms,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
    whenSessionReady: vi.fn().mockResolvedValue(null),
  };
}

function renderWithAuth(ui: React.ReactElement) {
  return render(
    React.createElement(AuthContext.Provider, { value: makeAuthContext() }, ui),
  );
}

import { SettingsSidebar } from "../../src/features/settings/components/SettingsSidebar";

describe("SettingsSidebar — Integration Tests (BETA-B7 §J.2)", () => {
  beforeEach(() => {
    mockPathname.mockReturnValue("/settings");
  });

  it("navigating to /settings/operations shows its sub-items", () => {
    mockPathname.mockReturnValue("/settings/operations");
    renderWithAuth(<SettingsSidebar testID="settings-sidebar" />);

    // Sub-items of Operations should be visible
    expect(screen.getByText("Margin buckets")).toBeInTheDocument();
    expect(screen.getByText("Profitability rules")).toBeInTheDocument();
    expect(screen.getByText("Field operations")).toBeInTheDocument();
  });

  it("Integrations → QuickBooks expanded → depth-2 Auto-expiry visible with deeper indent than QuickBooks", () => {
    mockPathname.mockReturnValue("/settings/integrations/quickbooks");
    renderWithAuth(<SettingsSidebar testID="settings-sidebar" />);

    // Depth-2 item should be visible
    const autoExpiryLink = screen.getByText("Auto-expiry & sync").closest("a");
    const quickBooksLink = screen.getByText("QuickBooks").closest("a");

    expect(autoExpiryLink).toBeInTheDocument();
    expect(quickBooksLink).toBeInTheDocument();

    // Auto-expiry should have pl-10 (deeper indent) vs QuickBooks pl-6
    expect(autoExpiryLink).toHaveClass("pl-10");
    expect(quickBooksLink).toHaveClass("pl-6");
  });

  it("no group label in sidebar has text-caption class", () => {
    mockPathname.mockReturnValue("/settings/operations");
    const { container } = renderWithAuth(
      <SettingsSidebar testID="settings-sidebar" />,
    );

    // Query all elements — none should have text-caption
    const sidebar = container.querySelector('[data-testid="settings-sidebar"]');
    expect(sidebar).toBeInTheDocument();

    const allLinks = sidebar?.querySelectorAll("a") ?? [];
    allLinks.forEach((link) => {
      expect(link.className).not.toContain("text-caption");
    });
  });
});
