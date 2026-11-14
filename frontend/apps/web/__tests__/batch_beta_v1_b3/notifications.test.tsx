/**
 * Notifications integration tests — BETA-B3
 *
 * Location: apps/web/__tests__/batch_beta_v1_b3/notifications.test.tsx
 *
 * Tests the /notifications page: list renders, unread badge, mark-read interaction.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { NotificationsPage } from "../../src/features/notifications-center/components/NotificationsPage";

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

describe("/notifications integration", () => {
  beforeEach(() => {
    vi.mocked(useInAppNotifications).mockReset();
    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: MOCK_NOTIFICATIONS,
      unreadCount: 1,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead: vi.fn().mockResolvedValue(undefined),
      markAllRead: vi.fn().mockResolvedValue(undefined),
    });
  });

  it("list renders notification bodies", () => {
    render(<NotificationsPage />);
    expect(screen.getByText("Your quote Q-001 was approved")).toBeTruthy();
    expect(screen.getByText("Invoice INV-001 payment received")).toBeTruthy();
  });

  it("unread badge shows correct count", () => {
    render(<NotificationsPage />);
    expect(screen.getByText("1 unread")).toBeTruthy();
  });

  it("mark-read triggered on clicking unread notification", () => {
    const markRead = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useInAppNotifications).mockReturnValue({
      notifications: MOCK_NOTIFICATIONS,
      unreadCount: 1,
      isConnected: true,
      isBellOpen: false,
      openBell: vi.fn(),
      closeBell: vi.fn(),
      markRead,
      markAllRead: vi.fn().mockResolvedValue(undefined),
    });

    render(<NotificationsPage />);
    fireEvent.click(screen.getByText("Your quote Q-001 was approved"));
    expect(markRead).toHaveBeenCalledWith("n-001");
  });

  it("empty state when no notifications", () => {
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
  });
});
