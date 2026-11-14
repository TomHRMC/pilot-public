/**
 * useSessionExpiry unit tests — web (FE-B2)
 *
 * Location: apps/web/src/hooks/useSessionExpiry.test.ts
 *
 * 3 tests per design doc §I.1
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSessionExpiry } from "./useSessionExpiry";

const mockReplace = vi.fn();
const mockSignOut = vi.fn();
const mockAddNotification = vi.fn();

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

beforeEach(() => {
  vi.clearAllMocks();
  mockSignOut.mockResolvedValue(undefined);
});

describe("useSessionExpiry (web)", () => {
  it("subscribes to auth:session-expired on mount", () => {
    const addEventListenerSpy = vi.spyOn(window, "addEventListener");
    renderHook(() => useSessionExpiry());
    expect(addEventListenerSpy).toHaveBeenCalledWith(
      "auth:session-expired",
      expect.any(Function),
    );
    addEventListenerSpy.mockRestore();
  });

  it("unsubscribes on unmount", () => {
    const removeEventListenerSpy = vi.spyOn(window, "removeEventListener");
    const { unmount } = renderHook(() => useSessionExpiry());
    unmount();
    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      "auth:session-expired",
      expect.any(Function),
    );
    removeEventListenerSpy.mockRestore();
  });

  it("dispatching event enqueues critical banner and calls signOut", async () => {
    renderHook(() => useSessionExpiry());

    await act(async () => {
      window.dispatchEvent(new CustomEvent("auth:session-expired"));
      // Allow microtasks to flush
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({ severity: "critical" }),
    );
    expect(mockSignOut).toHaveBeenCalled();
  });
});
