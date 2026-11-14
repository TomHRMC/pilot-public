/**
 * SettingsGearIcon — Unit Tests (UI-FIX-2E)
 *
 * Location: apps/web/src/components/__tests__/SettingsGearIcon.test.tsx
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import "@testing-library/jest-dom";
import { SettingsGearIcon } from "../SettingsGearIcon";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/dashboard"),
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
}));

describe("SettingsGearIcon — UI-FIX-2E", () => {
  it("renders a Settings button", () => {
    render(<SettingsGearIcon />);
    expect(
      screen.getByRole("button", { name: /settings/i }),
    ).toBeInTheDocument();
  });

  it("is NOT active when pathname is /dashboard (text-neutral-500 class)", () => {
    render(<SettingsGearIcon />);
    const btn = screen.getByRole("button", { name: /settings/i });
    expect(btn.className).toContain("text-neutral-500");
    expect(btn.className).not.toContain("text-brand-600");
  });

  it("is active when pathname starts with /settings (text-brand-600 class)", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/settings/team");
    render(<SettingsGearIcon />);
    const btn = screen.getByRole("button", { name: /settings/i });
    expect(btn.className).toContain("text-brand-600");
    expect(btn.className).not.toContain("text-neutral-500");
  });

  it("navigates to /settings on click", () => {
    mockPush.mockClear();
    render(<SettingsGearIcon />);
    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    expect(mockPush).toHaveBeenCalledWith("/settings");
  });

  it("has aria-current=page when active", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/settings/security");
    render(<SettingsGearIcon />);
    const btn = screen.getByRole("button", { name: /settings/i });
    expect(btn).toHaveAttribute("aria-current", "page");
  });

  it("does NOT have aria-current when not on settings", async () => {
    const { usePathname } = await import("next/navigation");
    vi.mocked(usePathname).mockReturnValue("/dashboard");
    render(<SettingsGearIcon />);
    const btn = screen.getByRole("button", { name: /settings/i });
    expect(btn).not.toHaveAttribute("aria-current");
  });
});
