/**
 * Role-based redirect integration tests — FE-B2 + C-B11
 *
 * Location: apps/web/__tests__/batch_fe_b2/login-rbac.integration.test.tsx
 *
 * Tests: owner/office_staff → /dashboard; tech → blocked + info banner
 *
 * C-B11: redirectForRole now calls GET /api/v1/operator/auth/me to determine
 * user_type before redirecting. Tests mock apiClient to return a tenant user
 * (redirect_to=/dashboard) and await the async resolution.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

const { mockReplace, mockAddNotification, mockSignOut, mockApiGet } =
  vi.hoisted(() => ({
    mockReplace: vi.fn(),
    mockAddNotification: vi.fn(),
    mockSignOut: vi.fn(),
    mockApiGet: vi.fn(),
  }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    signOut: mockSignOut,
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
  mockSignOut.mockResolvedValue(undefined);
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

describe("Role-based redirect integration (web)", () => {
  it("(1) owner → /dashboard", async () => {
    const { result } = renderHook(() => usePostLoginRedirect());
    result.current.redirectForRole("owner");

    await act(async () => {
      await vi.runAllTimersAsync();
      await Promise.resolve();
    });

    expect(mockApiGet).toHaveBeenCalledWith("/api/v1/operator/auth/me");
    expect(mockReplace).toHaveBeenCalledWith("/dashboard");
  });

  it("(2) tech → info banner + scheduled signOut + redirect to /login", async () => {
    const { result } = renderHook(() => usePostLoginRedirect());
    result.current.redirectForRole("technician");

    expect(mockReplace).not.toHaveBeenCalled();
    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: "info",
      }),
    );

    // Advance 5 seconds — signOut should be called
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });

    expect(mockSignOut).toHaveBeenCalled();
  });

  it("(3) office_staff → /dashboard", async () => {
    const { result } = renderHook(() => usePostLoginRedirect());
    result.current.redirectForRole("office_staff");

    await act(async () => {
      await vi.runAllTimersAsync();
      await Promise.resolve();
    });

    expect(mockApiGet).toHaveBeenCalledWith("/api/v1/operator/auth/me");
    expect(mockReplace).toHaveBeenCalledWith("/dashboard");
  });
});

// Import must come after vi.mock calls (hoisted by Vitest)
import { usePostLoginRedirect } from "@/hooks/usePostLoginRedirect";
