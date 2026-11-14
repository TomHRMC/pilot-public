/**
 * usePostLoginRedirect unit tests — web (FE-B2 + C-B11)
 *
 * Location: apps/web/src/hooks/usePostLoginRedirect.test.ts
 *
 * C-B11: operator role now calls GET /api/v1/operator/auth/me and redirects
 * to the server-provided redirect_to. Tests mock apiClient to return
 * platform/tenant variants.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Use vi.hoisted so the mock fn is available when vi.mock is hoisted
const { mockReplace, mockAddNotification, mockSignOut, mockApiGet } =
  vi.hoisted(() => ({
    mockReplace: vi.fn(),
    mockAddNotification: vi.fn(),
    mockSignOut: vi.fn(),
    mockApiGet: vi.fn(),
  }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    signOut: mockSignOut.mockResolvedValue(undefined),
    role: null,
    isAuthenticated: false,
    user: null,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    refreshSession: vi.fn(),
  }),
}));

vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: mockAddNotification,
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
}));

vi.mock("@pilot/shared-api", () => ({
  apiClient: {
    get: mockApiGet,
  },
  isAxiosError: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
  // Default: auth/me returns a tenant user → /dashboard
  mockApiGet.mockResolvedValue({
    data: {
      user_type: "tenant",
      user_id: "uuid-tenant",
      email: "dev@pilot.local",
      first_name: "Dev",
      last_name: "User",
      tenant_id: "uuid-tenant-id",
      role_code: "owner",
      redirect_to: "/dashboard",
    },
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("usePostLoginRedirect (web)", () => {
  it("owner role → calls auth/me, redirects to /dashboard for tenant user", async () => {
    const { result } = renderHook(() => usePostLoginRedirect());
    result.current.redirectForRole("owner");

    await act(async () => {
      await vi.runAllTimersAsync();
      await Promise.resolve();
    });

    expect(mockApiGet).toHaveBeenCalledWith("/api/v1/operator/auth/me");
    expect(mockReplace).toHaveBeenCalledWith("/dashboard");
  });

  it("office_staff role → calls auth/me, redirects to /dashboard for tenant user", async () => {
    const { result } = renderHook(() => usePostLoginRedirect());
    result.current.redirectForRole("office_staff");

    await act(async () => {
      await vi.runAllTimersAsync();
      await Promise.resolve();
    });

    expect(mockApiGet).toHaveBeenCalledWith("/api/v1/operator/auth/me");
    expect(mockReplace).toHaveBeenCalledWith("/dashboard");
  });

  it("operator role → calls auth/me, redirects to /operator/cohort for platform user", async () => {
    mockApiGet.mockResolvedValue({
      data: {
        user_type: "platform",
        user_id: "uuid-platform",
        email: "tom@pilotfortrades.com",
        first_name: "Tom",
        last_name: "Owner",
        platform_role_code: "owner",
        redirect_to: "/operator/cohort",
      },
    });

    const { result } = renderHook(() => usePostLoginRedirect());
    result.current.redirectForRole("accountant");

    await act(async () => {
      await vi.runAllTimersAsync();
      await Promise.resolve();
    });

    expect(mockApiGet).toHaveBeenCalledWith("/api/v1/operator/auth/me");
    expect(mockReplace).toHaveBeenCalledWith("/operator/cohort");
  });

  it("tech role → enqueues info banner and schedules sign-out", async () => {
    const { result } = renderHook(() => usePostLoginRedirect());
    result.current.redirectForRole("technician");

    // No immediate redirect
    expect(mockReplace).not.toHaveBeenCalled();

    // Info banner enqueued
    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({ severity: "info" }),
    );

    // After 5s, signOut + redirect
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    expect(mockSignOut).toHaveBeenCalled();
  });

  it("falls back to role-based map when auth/me fails", async () => {
    mockApiGet.mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => usePostLoginRedirect());
    result.current.redirectForRole("owner");

    await act(async () => {
      await vi.runAllTimersAsync();
      await Promise.resolve();
    });

    expect(mockReplace).toHaveBeenCalledWith("/dashboard");
  });
});

// Import must come after vi.mock calls (hoisted by Vitest)
import { usePostLoginRedirect } from "./usePostLoginRedirect";
