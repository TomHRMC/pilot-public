/**
 * RoleGate integration tests — layout context
 *
 * Location: apps/web/__tests__/batch_fe_b0/role-gate.integration.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { AuthContext } from "@pilot/ui/auth";
import { RoleGate } from "@pilot/ui/role-gate";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";

function makeContext(role: PilotRole | null): AuthContextValue {
  return {
    user: role
      ? {
          id: "u1",
          email: "a@b.com",
          role,
          tenantId: "t1",
          displayName: "Test",
          accessToken: "tok",
        }
      : null,
    isAuthenticated: role !== null,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

describe("RoleGate integration", () => {
  it("owner user sees all navigation sections", () => {
    render(
      <AuthContext.Provider value={makeContext("owner")}>
        <RoleGate role="owner">
          <nav data-testid="owner-nav">Owner Navigation</nav>
        </RoleGate>
        <nav data-testid="common-nav">Common Navigation</nav>
      </AuthContext.Provider>,
    );
    expect(screen.getByTestId("owner-nav")).toBeTruthy();
    expect(screen.getByTestId("common-nav")).toBeTruthy();
  });

  it("tech user does not see Owner-gated content", () => {
    const { container } = render(
      <AuthContext.Provider value={makeContext("technician")}>
        <RoleGate role="owner">
          <div data-testid="owner-content">Owner Only</div>
        </RoleGate>
        <div data-testid="tech-content">Tech Content</div>
      </AuthContext.Provider>,
    );
    expect(container.querySelector('[data-testid="owner-content"]')).toBeNull();
    expect(screen.getByTestId("tech-content")).toBeTruthy();
  });

  it("hidden owner content is absent from DOM entirely", () => {
    const { container } = render(
      <AuthContext.Provider value={makeContext("technician")}>
        <RoleGate role="owner">
          <div data-testid="owner-only">Secret</div>
        </RoleGate>
      </AuthContext.Provider>,
    );
    expect(container.innerHTML).not.toContain("Secret");
    expect(container.querySelector('[data-testid="owner-only"]')).toBeNull();
  });
});
