/**
 * useNotificationQueue — unit tests
 * Location: packages/ui/src/notification-banner/useNotificationQueue.test.ts
 */

import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { NotificationQueueProvider } from "./NotificationQueueProvider";
import { useNotificationQueue } from "./useNotificationQueue";

function makeWrapper(maxVisible = 3) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      NotificationQueueProvider,
      { maxVisible },
      children,
    );
  }
  return Wrapper;
}

function makeItem(id: string, title = "Test") {
  return { id, severity: "info" as const, title };
}

describe("useNotificationQueue", () => {
  it("throws when called outside NotificationQueueProvider", () => {
    expect(() => renderHook(() => useNotificationQueue())).toThrow(
      "useNotificationQueue must be called inside a <NotificationQueueProvider>",
    );
  });

  it("starts with empty queue", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: makeWrapper(),
    });
    expect(result.current.notifications).toHaveLength(0);
  });

  it("addNotification adds to queue", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.addNotification(makeItem("1"));
    });
    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0]!.id).toBe("1");
  });

  it("addNotification with same id replaces existing (dedup)", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.addNotification(makeItem("1", "Original"));
      result.current.addNotification(makeItem("1", "Updated"));
    });
    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0]!.title).toBe("Updated");
  });

  it("respects maxVisible=3 cap — adding 4th dismisses oldest", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: makeWrapper(3),
    });
    act(() => {
      result.current.addNotification(makeItem("1", "First"));
      result.current.addNotification(makeItem("2", "Second"));
      result.current.addNotification(makeItem("3", "Third"));
      result.current.addNotification(makeItem("4", "Fourth"));
    });
    expect(result.current.notifications).toHaveLength(3);
    expect(
      result.current.notifications.find((n) => n.id === "1"),
    ).toBeUndefined();
    expect(result.current.notifications.find((n) => n.id === "4")).toBeTruthy();
  });

  it("dismissNotification removes by id", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.addNotification(makeItem("1"));
      result.current.addNotification(makeItem("2"));
    });
    act(() => {
      result.current.dismissNotification("1");
    });
    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0]!.id).toBe("2");
  });

  it("dismissAll clears all notifications", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.addNotification(makeItem("1"));
      result.current.addNotification(makeItem("2"));
    });
    act(() => {
      result.current.dismissAll();
    });
    expect(result.current.notifications).toHaveLength(0);
  });

  it("queue persists across re-renders", () => {
    const { result, rerender } = renderHook(() => useNotificationQueue(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.addNotification(makeItem("1"));
    });
    rerender();
    expect(result.current.notifications).toHaveLength(1);
  });
});
