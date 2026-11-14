/**
 * NotificationBell unit tests — FE-B23
 *
 * Location: apps/web/src/features/notifications-center/components/__tests__/NotificationBell.test.tsx
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationBell } from "../NotificationBell";
import { useNotificationBellStore } from "../../store/notificationBellStore";
import type { InAppNotification } from "../../types";

// Mutable list — swapped per-test; never mutate the array directly
let _notifData: InAppNotification[] = [];

vi.mock("../../hooks/useInAppNotifications", () => ({
  // Arrow function captures the mutable reference — updates per test
  useInAppNotifications: () => ({ data: _notifData, isLoading: false }),
}));

vi.mock("../../hooks/useNotificationSse", () => ({
  useNotificationSse: vi.fn(() => ({ isConnected: false })),
}));

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeQc()}>{children}</QueryClientProvider>
  );
}

const makeNotif = (
  id: string,
  readAt: string | null = null,
): InAppNotification => ({
  notification_id: id,
  category_id: "cat",
  body: `Message ${id}`,
  deep_link_target: "/",
  priority: "standard",
  created_at: new Date().toISOString(),
  read_at: readAt,
});

describe("NotificationBell", () => {
  beforeEach(() => {
    _notifData = [];
    useNotificationBellStore.setState({ unreadCount: 0, drawerOpen: false });
  });

  it("renders bell icon", () => {
    render(<NotificationBell />, { wrapper: Wrapper });
    expect(screen.getByTestId("notification-bell")).toBeInTheDocument();
  });

  it("shows no badge when there are no unread notifications", () => {
    _notifData = [makeNotif("n1", new Date().toISOString())]; // all read
    render(<NotificationBell />, { wrapper: Wrapper });
    expect(screen.queryByTestId("notification-badge")).not.toBeInTheDocument();
  });

  it("shows badge with count when unread notifications exist", () => {
    // 3 unread notifications — useEffect will set unreadCount = 3
    _notifData = [makeNotif("n1"), makeNotif("n2"), makeNotif("n3")];
    render(<NotificationBell />, { wrapper: Wrapper });
    expect(screen.getByTestId("notification-badge")).toBeInTheDocument();
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("3");
  });

  it("opens drawer when bell is clicked", () => {
    render(<NotificationBell />, { wrapper: Wrapper });
    fireEvent.click(screen.getByTestId("notification-bell"));
    expect(useNotificationBellStore.getState().drawerOpen).toBe(true);
  });
});
