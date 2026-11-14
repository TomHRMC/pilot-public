"use client";

/**
 * NotificationBell — header bell icon with badge + SSE connection
 *
 * Location: apps/web/src/features/notifications-center/components/NotificationBell.tsx
 *
 * - Bell icon in app header
 * - Badge shows unread count when > 0
 * - Opens NotificationDrawer on click
 * - Syncs initial unread count from useInAppNotifications
 * - Maintains SSE connection via useNotificationSse
 */

import { useEffect } from "react";
import { useInAppNotifications } from "../hooks/useInAppNotifications";
import { useNotificationSse } from "../hooks/useNotificationSse";
import { useNotificationBellStore } from "../store/notificationBellStore";

export function NotificationBell() {
  const { data: notifications = [] } = useInAppNotifications();
  const { isConnected } = useNotificationSse();
  const unreadCount = useNotificationBellStore((s) => s.unreadCount);
  const setUnreadCount = useNotificationBellStore((s) => s.setUnreadCount);
  const toggleDrawer = useNotificationBellStore((s) => s.toggleDrawer);

  // Sync initial unread count from data
  useEffect(() => {
    const count = notifications.filter((n) => n.read_at === null).length;
    setUnreadCount(count);
  }, [notifications, setUnreadCount]);

  return (
    <button
      type="button"
      onClick={toggleDrawer}
      className="relative p-2 text-neutral-500 hover:text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2 rounded-md"
      aria-label={
        unreadCount > 0
          ? `Notifications — ${unreadCount} unread`
          : "Notifications"
      }
      data-testid="notification-bell"
    >
      {/* Bell icon (SVG) */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>

      {/* Unread badge */}
      {unreadCount > 0 && (
        <span
          className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-0.5 text-caption font-bold text-white"
          data-testid="notification-badge"
        >
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}

      {/* SSE connectivity dot (subtle — green when connected) */}
      {isConnected && (
        <span
          className="absolute bottom-1 right-1 block h-1.5 w-1.5 rounded-full bg-green-400"
          aria-hidden="true"
        />
      )}
    </button>
  );
}
