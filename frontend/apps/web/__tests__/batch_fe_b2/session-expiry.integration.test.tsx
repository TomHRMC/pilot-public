/**
 * Session expiry + logout integration tests — FE-B2
 *
 * Location: apps/web/__tests__/batch_fe_b2/session-expiry.integration.test.tsx
 *
 * Tests: auth:session-expired event → banner + redirect; logout → cache clear
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSessionExpiry } from "@/hooks/useSessionExpiry";
import { useLogout } from "@/hooks/useLogout";

const mockReplace = vi.fn();
const mockSignOut = vi.fn();
const mockAddNotification = vi.fn();
const mockClear = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    signOut: mockSignOut,
    role: null,
    isAuthenticated: true,
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

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ clear: mockClear }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockSignOut.mockResolvedValue(undefined);
});

describe("Session expiry + logout integration", () => {
  it("(1) auth:session-expired event → critical banner + signOut + redirect to /login", async () => {
    renderHook(() => useSessionExpiry());

    await act(async () => {
      window.dispatchEvent(new CustomEvent("auth:session-expired"));
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({ severity: "critical" }),
    );
    expect(mockSignOut).toHaveBeenCalled();
    expect(mockReplace).toHaveBeenCalledWith("/login");
  });

  it("(2) logout → TanStack cache cleared → redirect to /login?signedOut=true", async () => {
    const { result } = renderHook(() => useLogout());

    await act(async () => {
      await result.current.logout();
    });

    expect(mockClear).toHaveBeenCalled();
    expect(mockSignOut).toHaveBeenCalled();
    expect(mockReplace).toHaveBeenCalledWith("/login?signedOut=true");
  });
});
