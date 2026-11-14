/**
 * useRequiresPermission unit tests
 *
 * Location: packages/ui/src/role-gate/useRequiresPermission.test.ts
 */

import { renderHook } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { AuthContext } from "../auth/AuthProvider";
import type { AuthContextValue, PilotRole } from "../auth/types";
import { useRequiresPermission } from "./useRequiresPermission";
import { ROLE_PERMISSION_MAP, type PermissionKey } from "./permissions";

function makeContext(role: PilotRole | null): AuthContextValue {
  const perms = role ? (Array.from(ROLE_PERMISSION_MAP[role]) as string[]) : [];
  return {
    user: role
      ? {
          id: "u1",
          email: "a@b.com",
          role,
          tenantId: "t1",
          displayName: "Test",
          accessToken: "tok",
          permissions: perms,
        }
      : null,
    isAuthenticated: role !== null,
    role,
    permissions: perms,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
    whenSessionReady: vi.fn().mockResolvedValue(null),
  };
}

function wrapperFor(role: PilotRole | null) {
  // eslint-disable-next-line react/display-name
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      AuthContext.Provider,
      { value: makeContext(role) },
      children,
    );
}

describe("useRequiresPermission", () => {
  it("returns true for owner + quotes.approve", () => {
    const { result } = renderHook(
      () => useRequiresPermission("quotes.approve"),
      { wrapper: wrapperFor("owner") },
    );
    expect(result.current).toBe(true);
  });

  it("returns false for tech + quotes.approve", () => {
    const { result } = renderHook(
      () => useRequiresPermission("quotes.approve"),
      { wrapper: wrapperFor("technician") },
    );
    expect(result.current).toBe(false);
  });

  it("owner has all defined permissions", () => {
    const permissions: PermissionKey[] = [
      "quotes.approve",
      "quotes.reject",
      "quotes.kickback",
      "dispatch.move",
      "dispatch.assign",
      "customers.delete",
      "settings.manage",
      "reports.view",
      "comms.send",
      "invoices.approve",
    ];

    const wrapper = wrapperFor("owner");
    for (const perm of permissions) {
      const { result } = renderHook(() => useRequiresPermission(perm), {
        wrapper,
      });
      expect(result.current).toBe(true);
    }
  });

  it("returns false for tech + dispatch.move", () => {
    const { result } = renderHook(
      () => useRequiresPermission("dispatch.move"),
      { wrapper: wrapperFor("technician") },
    );
    expect(result.current).toBe(false);
  });

  // PLP-FIX-7: technician no longer holds comms.send (mirrors prod grants).
  it("returns false for tech + comms.send", () => {
    const { result } = renderHook(() => useRequiresPermission("comms.send"), {
      wrapper: wrapperFor("technician"),
    });
    expect(result.current).toBe(false);
  });
});
