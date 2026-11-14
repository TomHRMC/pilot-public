/**
 * NotificationQueueProvider — unit tests
 * Location: packages/ui/src/notification-banner/NotificationQueueProvider.test.tsx
 */

import { describe, it, expect } from "vitest";
import { render, screen, renderHook, act } from "@testing-library/react";
import React from "react";
import { NotificationQueueProvider } from "./NotificationQueueProvider";
import { useNotificationQueue } from "./useNotificationQueue";

function QueueWrapper({ children }: { children: React.ReactNode }) {
  return <NotificationQueueProvider>{children}</NotificationQueueProvider>;
}

function QueueWrapperMax2({ children }: { children: React.ReactNode }) {
  return (
    <NotificationQueueProvider maxVisible={2}>
      {children}
    </NotificationQueueProvider>
  );
}

describe("NotificationQueueProvider", () => {
  it("provides context value to children via useNotificationQueue", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: QueueWrapper,
    });
    expect(result.current.notifications).toBeDefined();
    expect(typeof result.current.addNotification).toBe("function");
    expect(typeof result.current.dismissNotification).toBe("function");
    expect(typeof result.current.dismissAll).toBe("function");
  });

  it("maxVisible prop controls cap to 2", () => {
    const { result } = renderHook(() => useNotificationQueue(), {
      wrapper: QueueWrapperMax2,
    });
    act(() => {
      result.current.addNotification({ id: "1", severity: "info", title: "A" });
      result.current.addNotification({ id: "2", severity: "info", title: "B" });
      result.current.addNotification({ id: "3", severity: "info", title: "C" });
    });
    expect(result.current.notifications).toHaveLength(2);
    expect(
      result.current.notifications.find((n) => n.id === "1"),
    ).toBeUndefined();
  });

  it("children render inside the provider", () => {
    render(
      <NotificationQueueProvider>
        <span data-testid="child">child content</span>
      </NotificationQueueProvider>,
    );
    expect(screen.getByTestId("child")).toBeTruthy();
  });
});
