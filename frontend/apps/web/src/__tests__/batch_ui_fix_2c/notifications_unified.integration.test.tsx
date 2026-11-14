/**
 * UI-FIX-2C Integration Tests — Notifications Unified Page
 *
 * Location: apps/web/src/__tests__/batch_ui_fix_2c/notifications_unified.integration.test.tsx
 *
 * Coverage:
 * 1. Unified preferences page renders without crashing
 * 2. NotificationPreferenceMatrix is present (testID="notification-preference-matrix")
 * 3. Recent in-app notifications section renders when there is data
 * 4. Recent notifications section shows "No recent notifications." when list is empty
 * 5. Unread count badge renders when there are unread notifications
 * 6. Mark all read button renders when there are unread notifications
 * 7. Redirect pages call redirect() to /settings/notifications/preferences
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import "@testing-library/jest-dom";

// ── Hoist mocks so vi.mock() factories can reference them ───────────────────
const { mockRedirect } = vi.hoisted(() => ({
  mockRedirect: vi.fn(),
}));

// ── next/navigation mock ────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/notifications/preferences",
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  redirect: mockRedirect,
}));

// ── next/link mock ──────────────────────────────────────────────────────────
vi.mock("next/link", () => ({
  default: ({
    href,
    className,
    children,
    ...rest
  }: {
    href: string;
    className?: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} className={className} {...rest}>
      {children}
    </a>
  ),
}));

// ── useNotificationPreferences mock ────────────────────────────────────────
vi.mock(
  "@/features/notification-preferences/hooks/useNotificationPreferences",
  () => ({
    useNotificationPreferences: () => ({
      preferences: [],
      categories: [],
      isLoading: false,
      isError: false,
      isPending: false,
      onCellChange: vi.fn(),
      onCellRevert: vi.fn(),
      onRowRevert: vi.fn(),
      onMuteAllPush: vi.fn(),
      onMuteAllEmail: vi.fn(),
      onResetAll: vi.fn(),
    }),
  }),
);

// ── useRecentInAppNotifications mock ────────────────────────────────────────
const mockMarkAllRead = vi.fn().mockResolvedValue(undefined);

// Mutable state — individual tests override via vi.doMock or module-level variables
let mockNotifications: Array<{
  notificationId: string;
  category: string;
  title: string;
  body: string;
  isRead: boolean;
  createdAt: string;
  deepLinkHref: string | null;
}> = [];
let mockNotifsLoading = false;

vi.mock(
  "@/features/notification-preferences/hooks/useRecentInAppNotifications",
  () => ({
    useRecentInAppNotifications: () => ({
      notifications: mockNotifications,
      isLoading: mockNotifsLoading,
      isError: false,
      markAllRead: mockMarkAllRead,
      isMarkingRead: false,
    }),
  }),
);

// ── @pilot/ui mock ──────────────────────────────────────────────────────────
vi.mock("@pilot/ui", () => ({
  NotificationPreferenceMatrix: ({ testID }: { testID?: string }) =>
    React.createElement(
      "div",
      { "data-testid": testID ?? "notification-preference-matrix" },
      "Mock Matrix",
    ),
}));

// ── Import components after mocks ───────────────────────────────────────────
import NotificationPreferencesPage from "@/app/(authed)/settings/notifications/preferences/page";
import NotificationEmailPage from "@/app/(authed)/settings/notifications/email/page";
import NotificationSmsPage from "@/app/(authed)/settings/notifications/sms/page";
import NotificationInAppPage from "@/app/(authed)/settings/notifications/in-app/page";

// ── Fixtures ────────────────────────────────────────────────────────────────
const MOCK_NOTIFICATIONS = [
  {
    notificationId: "notif-001",
    category: "job_status",
    title: "Job completed",
    body: "Technician Mike marked the job as complete.",
    isRead: false,
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    deepLinkHref: "/jobs/job-1042",
  },
  {
    notificationId: "notif-002",
    category: "quote_approved",
    title: "Quote approved",
    body: "Customer approved the quote.",
    isRead: true,
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    deepLinkHref: null,
  },
];

// ── Tests ───────────────────────────────────────────────────────────────────

describe("NotificationPreferencesPage — unified page (UI-FIX-2C)", () => {
  beforeEach(() => {
    mockNotifications = [];
    mockNotifsLoading = false;
    mockRedirect.mockClear();
    mockMarkAllRead.mockClear();
  });

  it("renders without crashing", () => {
    render(<NotificationPreferencesPage />);
    expect(screen.getByText("Notification preferences")).toBeInTheDocument();
  });

  it("renders NotificationPreferenceMatrix with correct testID", () => {
    render(<NotificationPreferencesPage />);
    expect(
      screen.getByTestId("notification-preference-matrix"),
    ).toBeInTheDocument();
  });

  it("renders the recent in-app notifications section container", () => {
    render(<NotificationPreferencesPage />);
    expect(
      screen.getByTestId("recent-inapp-notifications-section"),
    ).toBeInTheDocument();
  });

  it("shows 'No recent notifications.' when list is empty", () => {
    mockNotifications = [];
    render(<NotificationPreferencesPage />);
    expect(screen.getByText("No recent notifications.")).toBeInTheDocument();
  });

  it("renders notification items when data is present", () => {
    mockNotifications = [...MOCK_NOTIFICATIONS];
    render(<NotificationPreferencesPage />);
    expect(screen.getByText("Job completed")).toBeInTheDocument();
    expect(screen.getByText("Quote approved")).toBeInTheDocument();
  });

  it("renders notification body text", () => {
    mockNotifications = [...MOCK_NOTIFICATIONS];
    render(<NotificationPreferencesPage />);
    expect(
      screen.getByText("Technician Mike marked the job as complete."),
    ).toBeInTheDocument();
  });

  it("renders unread count badge when there are unread notifications", () => {
    mockNotifications = [...MOCK_NOTIFICATIONS]; // 1 unread (notif-001)
    render(<NotificationPreferencesPage />);
    expect(screen.getByText("1 unread")).toBeInTheDocument();
  });

  it("renders 'Mark all read' button when there are unread notifications", () => {
    mockNotifications = [...MOCK_NOTIFICATIONS];
    render(<NotificationPreferencesPage />);
    expect(
      screen.getByRole("button", { name: /mark all read/i }),
    ).toBeInTheDocument();
  });

  it("does NOT render unread badge when all notifications are read", () => {
    mockNotifications = MOCK_NOTIFICATIONS.map((n) => ({ ...n, isRead: true }));
    render(<NotificationPreferencesPage />);
    expect(screen.queryByText(/unread/)).not.toBeInTheDocument();
  });

  it("renders deep-link 'View →' for notifications that have deepLinkHref", () => {
    mockNotifications = [...MOCK_NOTIFICATIONS];
    render(<NotificationPreferencesPage />);
    // notif-001 has deepLinkHref, notif-002 does not
    const viewLinks = screen.getAllByText("View →");
    expect(viewLinks).toHaveLength(1);
  });

  it("renders a loading spinner when notifications are loading", () => {
    mockNotifsLoading = true;
    mockNotifications = [];
    const { container } = render(<NotificationPreferencesPage />);
    const spinner = container.querySelector(".animate-spin");
    expect(spinner).toBeTruthy();
  });
});

describe("Notification redirect pages — UI-FIX-2C", () => {
  beforeEach(() => {
    mockRedirect.mockClear();
  });

  it("NotificationEmailPage calls redirect to /settings/notifications/preferences", () => {
    // redirect() returns never — call as function, don't render as JSX
    try {
      NotificationEmailPage();
    } catch {
      /* redirect throws */
    }
    expect(mockRedirect).toHaveBeenCalledWith(
      "/settings/notifications/preferences",
    );
  });

  it("NotificationSmsPage calls redirect to /settings/notifications/preferences", () => {
    try {
      NotificationSmsPage();
    } catch {
      /* redirect throws */
    }
    expect(mockRedirect).toHaveBeenCalledWith(
      "/settings/notifications/preferences",
    );
  });

  it("NotificationInAppPage calls redirect to /settings/notifications/preferences", () => {
    try {
      NotificationInAppPage();
    } catch {
      /* redirect throws */
    }
    expect(mockRedirect).toHaveBeenCalledWith(
      "/settings/notifications/preferences",
    );
  });
});
