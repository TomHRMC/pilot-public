/**
 * RoleGate unit tests
 *
 * Location: packages/ui/src/role-gate/RoleGate.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { AuthContext } from "../auth/AuthProvider";
import type { AuthContextValue, PilotRole } from "../auth/types";
import { ROLE_PERMISSION_MAP } from "./permissions";
import { RoleGate } from "./RoleGate";

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

function AuthWrapper({
  role,
  children,
}: {
  role: PilotRole | null;
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      {children}
    </AuthContext.Provider>
  );
}

describe("RoleGate", () => {
  it("renders children when user role matches", () => {
    render(
      <AuthWrapper role="owner">
        <RoleGate role="owner">
          <span>owner content</span>
        </RoleGate>
      </AuthWrapper>,
    );
    expect(screen.getByText("owner content")).toBeTruthy();
  });

  it("returns null (no DOM node) when role does not match", () => {
    const { container } = render(
      <AuthWrapper role="technician">
        <RoleGate role="owner">
          <span>owner content</span>
        </RoleGate>
      </AuthWrapper>,
    );
    expect(container.textContent).toBe("");
  });

  it("renders if user has ANY role in an array", () => {
    render(
      <AuthWrapper role="office_staff">
        <RoleGate role={["owner", "office_staff"]}>
          <span>multi-role content</span>
        </RoleGate>
      </AuthWrapper>,
    );
    expect(screen.getByText("multi-role content")).toBeTruthy();
  });

  it("operator role has access to owner-level content", () => {
    render(
      <AuthWrapper role="accountant">
        <RoleGate role={["owner", "accountant"]}>
          <span>operator sees this</span>
        </RoleGate>
      </AuthWrapper>,
    );
    expect(screen.getByText("operator sees this")).toBeTruthy();
  });

  it("returns null when user is not authenticated (role is null)", () => {
    const { container } = render(
      <AuthWrapper role={null}>
        <RoleGate role="owner">
          <span>owner content</span>
        </RoleGate>
      </AuthWrapper>,
    );
    expect(container.textContent).toBe("");
  });

  it("hidden content truly absent from DOM (not display:none)", () => {
    const { container } = render(
      <AuthWrapper role="technician">
        <RoleGate role="owner">
          <span data-testid="hidden">owner content</span>
        </RoleGate>
      </AuthWrapper>,
    );
    // Must be absent from DOM entirely, not hidden via CSS
    expect(container.querySelector('[data-testid="hidden"]')).toBeNull();
  });
});
