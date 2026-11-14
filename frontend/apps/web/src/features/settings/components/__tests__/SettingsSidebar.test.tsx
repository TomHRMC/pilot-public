/**
 * SettingsSidebar — Unit Tests (UI-FIX-2E update)
 *
 * Location: apps/web/src/features/settings/components/__tests__/SettingsSidebar.test.tsx
 *
 * UI-FIX-2E changes:
 *   - My Account group removed
 *   - Billing item removed
 *   - "Communications" → "Branding"
 *   - "Security & MFA" → "Security"
 *   - New order: Team, Operations, Notifications, Sync & Storage, Integrations,
 *     Branding, Voice & AI, Security, Data & Privacy
 *
 * Original BETA-B7 typography tests retained (depth classes, active state, etc.)
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";

// Mock next/navigation
const mockPathname = vi.fn(() => "/settings/operations");
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
    ...rest
  }: {
    href: string;
    className?: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} className={className} {...rest}>
      {children}
    </a>
  ),
}));

// Mock @pilot/ui
vi.mock("@pilot/ui", () => ({
  SettingsSidebarSearch: () => null,
}));

// PLP-FIX-7: SettingsSidebar now calls useHasPermission which reads AuthContext.
// Wrap renders in an AuthContext provider with owner permissions.
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

import { SettingsSidebar } from "../SettingsSidebar";

// ── UI-FIX-2E: Removed items must NOT appear ───────────────────────────────
describe("SettingsSidebar — UI-FIX-2E removed items", () => {
  it("does NOT render My Account group", () => {
    mockPathname.mockReturnValue("/settings/team");
    renderWithAuth(<SettingsSidebar />);
    expect(screen.queryByText("My Account")).not.toBeInTheDocument();
  });

  it("does NOT render Profile sub-item", () => {
    mockPathname.mockReturnValue("/settings/team");
    renderWithAuth(<SettingsSidebar />);
    // Profile link under My Account should be gone
    const profileLinks = screen.queryAllByText("Profile");
    expect(profileLinks).toHaveLength(0);
  });

  it("does NOT render Billing standalone item", () => {
    mockPathname.mockReturnValue("/settings/team");
    renderWithAuth(<SettingsSidebar />);
    // No depth-0 Billing item
    const navEl = screen.getByRole("navigation", {
      name: /settings navigation/i,
    });
    const items = within(navEl).queryAllByText("Billing");
    // Billing as a top-level nav link should not be present
    expect(
      items.filter((el) =>
        el.closest("a")?.className.includes("text-sm font-semibold"),
      ),
    ).toHaveLength(0);
  });

  it("does NOT render Communications label (now Branding)", () => {
    mockPathname.mockReturnValue("/settings/communications");
    renderWithAuth(<SettingsSidebar />);
    expect(screen.queryByText("Communications")).not.toBeInTheDocument();
  });

  it("does NOT render Security & MFA label (now Security)", () => {
    mockPathname.mockReturnValue("/settings/security");
    renderWithAuth(<SettingsSidebar />);
    expect(screen.queryByText("Security & MFA")).not.toBeInTheDocument();
  });
});

// ── UI-FIX-2E: New labels must be present ─────────────────────────────────
describe("SettingsSidebar — UI-FIX-2E new labels", () => {
  it("renders Branding (formerly Communications)", () => {
    mockPathname.mockReturnValue("/settings/team");
    renderWithAuth(<SettingsSidebar />);
    expect(screen.getByText("Branding")).toBeInTheDocument();
  });

  it("renders Security (formerly Security & MFA)", () => {
    mockPathname.mockReturnValue("/settings/team");
    renderWithAuth(<SettingsSidebar />);
    expect(screen.getByText("Security")).toBeInTheDocument();
  });

  it("renders all 10 top-level items in correct order", () => {
    mockPathname.mockReturnValue("/settings/team");
    renderWithAuth(<SettingsSidebar />);
    const navEl = screen.getByRole("navigation", {
      name: /settings navigation/i,
    });
    const topLinks = within(navEl).getAllByRole("link");
    // Extract depth-0 links (those with text-sm class)
    const depth0Labels = topLinks
      .filter((el) => el.className.includes("text-sm"))
      .map((el) => el.textContent?.trim());
    expect(depth0Labels).toEqual([
      "Team",
      "Operations",
      "Notifications",
      "Sync & Storage",
      "Integrations",
      "Branding",
      "Website",
      "Voice & AI",
      "Security",
      "Data & Privacy",
    ]);
  });
});

// ── BETA-B7 Typography Hierarchy (retained from original) ──────────────────
describe("SettingsSidebar — Typography Hierarchy (BETA-B7 §J.1)", () => {
  it("depth-0 group labels have text-sm class", () => {
    mockPathname.mockReturnValue("/settings/operations");
    renderWithAuth(<SettingsSidebar />);
    const operationsLink = screen.getByText("Operations").closest("a");
    expect(operationsLink).toHaveClass("text-sm");
  });

  it("depth-0 group labels have font-semibold class", () => {
    mockPathname.mockReturnValue("/settings/operations");
    renderWithAuth(<SettingsSidebar />);
    const operationsLink = screen.getByText("Operations").closest("a");
    expect(operationsLink).toHaveClass("font-semibold");
  });

  it("depth-0 group labels do NOT have text-caption class", () => {
    mockPathname.mockReturnValue("/settings/operations");
    renderWithAuth(<SettingsSidebar />);
    const operationsLink = screen.getByText("Operations").closest("a");
    expect(operationsLink?.className ?? "").not.toContain("text-caption");
  });

  it("depth-1 sub-items have text-xs class", () => {
    mockPathname.mockReturnValue("/settings/operations");
    renderWithAuth(<SettingsSidebar />);
    const marginBucketsLink = screen.getByText("Margin buckets").closest("a");
    expect(marginBucketsLink).toHaveClass("text-xs");
  });

  it("depth-1 sub-items have pl-6 indent", () => {
    mockPathname.mockReturnValue("/settings/operations");
    renderWithAuth(<SettingsSidebar />);
    const marginBucketsLink = screen.getByText("Margin buckets").closest("a");
    expect(marginBucketsLink).toHaveClass("pl-6");
  });

  it("depth-2 sub-sub-items have pl-10 indent", () => {
    mockPathname.mockReturnValue("/settings/integrations/quickbooks");
    renderWithAuth(<SettingsSidebar />);
    const autoExpiryLink = screen.getByText("Auto-expiry & sync").closest("a");
    expect(autoExpiryLink).toHaveClass("pl-10");
  });

  it("depth-2 sub-sub-items have text-neutral-500 color", () => {
    mockPathname.mockReturnValue("/settings/integrations/quickbooks");
    renderWithAuth(<SettingsSidebar />);
    const autoExpiryLink = screen.getByText("Auto-expiry & sync").closest("a");
    expect(autoExpiryLink).toHaveClass("text-neutral-500");
  });

  it("active item still has bg-brand-50 and text-brand-700 regardless of depth", () => {
    mockPathname.mockReturnValue("/settings/operations/margin-buckets");
    renderWithAuth(<SettingsSidebar />);
    const activeLink = screen.getByText("Margin buckets").closest("a");
    expect(activeLink).toHaveClass("bg-brand-50");
    expect(activeLink).toHaveClass("text-brand-700");
  });

  it("ancestor group label is visible when child is active", () => {
    mockPathname.mockReturnValue("/settings/operations/margin-buckets");
    renderWithAuth(<SettingsSidebar />);
    expect(screen.getByText("Operations")).toBeInTheDocument();
  });
});
