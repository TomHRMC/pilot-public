/**
 * useAuth unit tests
 *
 * Location: packages/ui/src/auth/useAuth.test.ts
 */

import { renderHook } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { AuthContext } from "./AuthProvider";
import { useAuth } from "./useAuth";
import type { AuthContextValue, PilotUser } from "./types";

const mockOwner: PilotUser = {
  id: "user-1",
  email: "owner@test.com",
  role: "owner",
  tenantId: "tenant-1",
  displayName: "Test Owner",
  accessToken: "token-123",
  permissions: ["*"],
};

const mockContextValue: AuthContextValue = {
  user: mockOwner,
  isAuthenticated: true,
  role: "owner",
  permissions: ["*"],
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("new-token"),
  whenSessionReady: vi.fn().mockResolvedValue(mockOwner),
};

describe("useAuth", () => {
  it("returns null user when not authenticated", () => {
    const unauthContext: AuthContextValue = {
      ...mockContextValue,
      user: null,
      isAuthenticated: false,
      role: null,
    };

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        AuthContext.Provider,
        { value: unauthContext },
        children,
      );

    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.role).toBeNull();
  });

  it("returns correct PilotUser after mock sign-in", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        AuthContext.Provider,
        { value: mockContextValue },
        children,
      );

    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.user).toEqual(mockOwner);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.role).toBe("owner");
  });

  it("signOut clears context user", async () => {
    const signOutMock = vi.fn().mockResolvedValue(undefined);
    const context: AuthContextValue = {
      ...mockContextValue,
      signOut: signOutMock,
    };

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(AuthContext.Provider, { value: context }, children);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await result.current.signOut();
    expect(signOutMock).toHaveBeenCalledOnce();
  });

  it("throws when used outside AuthProvider", () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => renderHook(() => useAuth())).toThrow(
      "[useAuth] must be used inside <AuthProvider>",
    );

    consoleSpy.mockRestore();
  });

  it("refreshSession calls through to context", async () => {
    const wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        AuthContext.Provider,
        { value: mockContextValue },
        children,
      );

    const { result } = renderHook(() => useAuth(), { wrapper });

    const token = await result.current.refreshSession();
    expect(token).toBe("new-token");
  });
});
