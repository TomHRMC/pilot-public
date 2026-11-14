/**
 * NotificationsPage unit tests — BETA-B3
 *
 * Location: apps/web/src/features/notifications-center/components/__tests__/NotificationsPage.test.tsx
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { NotificationsPage } from "../NotificationsPage";

// Mock the useInAppNotifications hook
vi.mock("@pilot/ui", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@pilot/ui")>();
  return {
    ...actual,
    useInAppNotifications: vi.fn(),
  };
});

import { useInAppNotifications } from "@pilot/ui";

const MOCK_NOTIFICATIONS = [
  {
    notification_id: "n-001",
    category_id: "cat-001",
    body: "Your quote Q-001 was approved",
    deep_link_target: "/quotes/q-001",
    priority: "critical" as const,
    created_at: new Date("2024-01-15T10:00:00Z").toISOString(),
    read_at: null,
  },
  {
    notification_id: "n-002",
    category_id: "cat-002",
    body: "Invoice INV-001 payment received",
    deep_link_target: "/invoices/inv-001",
    priority: "standard" as const,
    created_at: new Date("2024-01-14T09:00:00Z").toISOString(),
    read_at: new Date("2024-01-14T10:00:00Z").toISOString(),
  },
];

describe("NotificationsPage", () => {
  beforeEach(() => {
    vi.mocked(useInAppNotifications).mockReset();
  });

  it("renders notification list", () => {
    const markRead = vi.fn();
    const markAllRead = vi.fn();

    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: MOCK_NOTIFICATIONS,
      unreadCount: 1,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead,
      markAllRead,
    });

    render(<NotificationsPage />);
    expect(screen.getByText("Your quote Q-001 was approved")).toBeTruthy();
    expect(screen.getByText("Invoice INV-001 payment received")).toBeTruthy();
  });

  it("renders unread count badge when unread notifications exist", () => {
    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: MOCK_NOTIFICATIONS,
      unreadCount: 1,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead: vi.fn(),
      markAllRead: vi.fn(),
    });

    render(<NotificationsPage />);
    expect(screen.getByText("1 unread")).toBeTruthy();
  });

  it("renders Mark all read button when unread notifications exist", () => {
    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: MOCK_NOTIFICATIONS,
      unreadCount: 1,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead: vi.fn(),
      markAllRead: vi.fn(),
    });

    render(<NotificationsPage />);
    expect(screen.getByRole("button", { name: /mark all read/i })).toBeTruthy();
  });

  it("clicking Mark all read calls markAllRead", () => {
    const markAllRead = vi.fn().mockResolvedValue(undefined);

    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: MOCK_NOTIFICATIONS,
      unreadCount: 1,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead: vi.fn(),
      markAllRead,
    });

    render(<NotificationsPage />);
    fireEvent.click(screen.getByRole("button", { name: /mark all read/i }));
    expect(markAllRead).toHaveBeenCalledOnce();
  });

  it("clicking a notification calls markRead with the notification_id", () => {
    const markRead = vi.fn().mockResolvedValue(undefined);

    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: MOCK_NOTIFICATIONS,
      unreadCount: 1,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead,
      markAllRead: vi.fn(),
    });

    render(<NotificationsPage />);
    fireEvent.click(screen.getByText("Your quote Q-001 was approved"));
    expect(markRead).toHaveBeenCalledWith("n-001");
  });

  it("renders empty state when no notifications", () => {
    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: [],
      unreadCount: 0,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead: vi.fn(),
      markAllRead: vi.fn(),
    });

    render(<NotificationsPage />);
    expect(screen.getByText(/no notifications/i)).toBeTruthy();
    expect(screen.getByText(/you're all caught up/i)).toBeTruthy();
  });

  it("does NOT render Mark all read button when all notifications are read", () => {
    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: MOCK_NOTIFICATIONS,
      unreadCount: 0,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead: vi.fn(),
      markAllRead: vi.fn(),
    });

    render(<NotificationsPage />);
    expect(screen.queryByRole("button", { name: /mark all read/i })).toBeNull();
  });
});
