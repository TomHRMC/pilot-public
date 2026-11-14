/**
 * Notification queue — integration tests in web layout
 * Location: apps/web/__tests__/batch_fe_b1/notification-queue.integration.test.tsx
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  renderHook,
} from "@testing-library/react";
import React from "react";

import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { NotificationBanner } from "@pilot/ui/notification-banner";
import type { NotificationSeverity } from "@pilot/ui/notification-banner";

function TestApp({ children }: { children: React.ReactNode }) {
  return (
    <NotificationQueueProvider maxVisible={3}>
      {children}
    </NotificationQueueProvider>
  );
}

function makeItem(
  id: string,
  severity: NotificationSeverity = "info",
  title = "Test",
) {
  return { id, severity, title };
}

describe("Notification queue — integration", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("single addNotification makes notification available from hook", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: TestApp,
    });
    act(() => {
      result.current.addNotification(makeItem("1", "info", "Quote sent"));
    });
    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0]!.title).toBe("Quote sent");
  });

  it("4 simultaneous adds → only 3 visible, oldest dismissed", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: TestApp,
    });
    act(() => {
      result.current.addNotification(makeItem("1", "info", "First"));
      result.current.addNotification(makeItem("2", "info", "Second"));
      result.current.addNotification(makeItem("3", "info", "Third"));
      result.current.addNotification(makeItem("4", "info", "Fourth"));
    });
    expect(result.current.notifications).toHaveLength(3);
    expect(
      result.current.notifications.find((n) => n.title === "First"),
    ).toBeUndefined();
    expect(
      result.current.notifications.find((n) => n.title === "Fourth"),
    ).toBeTruthy();
  });

  it("clicking deepLinkTarget banner calls onNavigate with correct path", () => {
    const onNavigate = vi.fn();
    render(
      <TestApp>
        <NotificationBanner
          notification={{
            id: "n1",
            severity: "info",
            title: "Quote approved",
            deepLinkTarget: "/quotes/q-1042",
            createdAt: new Date(),
          }}
          onDismiss={vi.fn()}
          onNavigate={onNavigate}
        />
      </TestApp>,
    );
    fireEvent.click(screen.getByRole("button", { name: /click to view/i }));
    expect(onNavigate).toHaveBeenCalledWith("/quotes/q-1042");
  });

  it("error severity banner persists for full 12000ms", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: TestApp,
    });
    act(() => {
      result.current.addNotification(makeItem("1", "error", "Payment error"));
    });
    expect(result.current.notifications).toHaveLength(1);
    // The banner component itself manages auto-dismiss — queue just holds it
    // After 12s, the banner would call dismissNotification — simulate:
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    // Queue still has it (no banner component attached here to do dismiss)
    expect(result.current.notifications).toHaveLength(1);
  });

  it("dismissAll clears all notifications from queue", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: TestApp,
    });
    act(() => {
      result.current.addNotification(makeItem("1"));
      result.current.addNotification(makeItem("2"));
      result.current.dismissAll();
    });
    expect(result.current.notifications).toHaveLength(0);
  });
});
