/**
 * NotificationBanner (web) — unit tests
 * Location: packages/ui/src/notification-banner/web/NotificationBanner.test.tsx
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { NotificationBanner } from "./NotificationBanner";
import type { NotificationItem } from "../types";

function makeNotification(
  overrides: Partial<NotificationItem> = {},
): NotificationItem {
  return {
    id: "test-1",
    severity: "info",
    title: "Test notification",
    createdAt: new Date(),
    ...overrides,
  };
}

describe("NotificationBanner (web)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders title", () => {
    render(
      <NotificationBanner
        notification={makeNotification({ title: "Quote sent" })}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.getByText("Quote sent")).toBeTruthy();
  });

  it("renders detail when provided", () => {
    render(
      <NotificationBanner
        notification={makeNotification({ detail: "Q-1042 sent to Acme" })}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.getByText("Q-1042 sent to Acme")).toBeTruthy();
  });

  it("has role='alert' when no deepLinkTarget", () => {
    render(
      <NotificationBanner
        notification={makeNotification()}
        onDismiss={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toBeTruthy();
  });

  it("auto-dismisses info severity after 6000ms", () => {
    const onDismiss = vi.fn();
    render(
      <NotificationBanner
        notification={makeNotification({ id: "n1", severity: "info" })}
        onDismiss={onDismiss}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(onDismiss).toHaveBeenCalledWith("n1");
  });

  it("auto-dismisses success severity after 6000ms", () => {
    const onDismiss = vi.fn();
    render(
      <NotificationBanner
        notification={makeNotification({ id: "n2", severity: "success" })}
        onDismiss={onDismiss}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(onDismiss).toHaveBeenCalledWith("n2");
  });

  it("auto-dismisses warning severity after 6000ms", () => {
    const onDismiss = vi.fn();
    render(
      <NotificationBanner
        notification={makeNotification({ id: "n3", severity: "warning" })}
        onDismiss={onDismiss}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(onDismiss).toHaveBeenCalledWith("n3");
  });

  it("auto-dismisses error severity after 12000ms", () => {
    const onDismiss = vi.fn();
    render(
      <NotificationBanner
        notification={makeNotification({ id: "n4", severity: "error" })}
        onDismiss={onDismiss}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(onDismiss).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(onDismiss).toHaveBeenCalledWith("n4");
  });

  it("critical severity does NOT auto-dismiss after 30000ms", () => {
    const onDismiss = vi.fn();
    render(
      <NotificationBanner
        notification={makeNotification({ id: "n5", severity: "critical" })}
        onDismiss={onDismiss}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(30000);
    });
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("calls onDismiss when × button clicked", () => {
    const onDismiss = vi.fn();
    render(
      <NotificationBanner
        notification={makeNotification({ id: "n6" })}
        onDismiss={onDismiss}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalledWith("n6");
  });

  it("calls onNavigate when banner with deepLinkTarget is clicked", () => {
    const onNavigate = vi.fn();
    render(
      <NotificationBanner
        notification={makeNotification({ deepLinkTarget: "/quotes/123" })}
        onDismiss={vi.fn()}
        onNavigate={onNavigate}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /click to view/i }));
    expect(onNavigate).toHaveBeenCalledWith("/quotes/123");
  });

  it("applies dismissAfterMs override", () => {
    const onDismiss = vi.fn();
    render(
      <NotificationBanner
        notification={makeNotification({
          id: "n7",
          severity: "info",
          dismissAfterMs: 2000,
        })}
        onDismiss={onDismiss}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(onDismiss).toHaveBeenCalledWith("n7");
  });
});
