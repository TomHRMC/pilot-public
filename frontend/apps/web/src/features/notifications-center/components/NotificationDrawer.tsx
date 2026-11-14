"use client";

/**
 * NotificationDrawer — slide-in notification panel
 *
 * Location: apps/web/src/features/notifications-center/components/NotificationDrawer.tsx
 *
 * Shows last 50 notifications. Closes on backdrop or "×" button.
 * "Mark all read" fires useMarkNotificationsRead.
 */

import { useRouter } from "next/navigation";
import { useInAppNotifications } from "../hooks/useInAppNotifications";
import { useMarkNotificationsRead } from "../hooks/useMarkNotificationsRead";
import { useNotificationBellStore } from "../store/notificationBellStore";
import { NotificationItem } from "./NotificationItem";

export function NotificationDrawer() {
  const drawerOpen = useNotificationBellStore((s) => s.drawerOpen);
  const setDrawerOpen = useNotificationBellStore((s) => s.setDrawerOpen);
  const setUnreadCount = useNotificationBellStore((s) => s.setUnreadCount);

  const { data: notifications = [] } = useInAppNotifications();
  const markRead = useMarkNotificationsRead();
  const router = useRouter();

  if (!drawerOpen) return null;

  function handleMarkAllRead() {
    markRead.mutate(
      {},
      {
        onSuccess: () => {
          setUnreadCount(0);
        },
      },
    );
  }

  function handleRead(notificationId: string) {
    markRead.mutate({ notification_ids: [notificationId] });
  }

  function handleNavigate(target: string) {
    setDrawerOpen(false);
    void router.push(target);
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20"
        onClick={() => setDrawerOpen(false)}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        className="fixed right-0 top-0 z-50 flex h-full w-80 flex-col bg-white shadow-xl"
        aria-label="Notifications"
        data-testid="notification-drawer"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
          <h2 className="text-h3 text-neutral-900">Notifications</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleMarkAllRead}
              disabled={markRead.isPending}
              className="text-caption text-brand-600 hover:underline disabled:opacity-50"
              data-testid="mark-all-read-btn"
            >
              Mark all read
            </button>
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="p-1 text-neutral-400 hover:text-neutral-600"
              aria-label="Close notifications"
              data-testid="close-drawer-btn"
            >
              ×
            </button>
          </div>
        </div>

        {/* Notification list */}
        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <p className="px-4 py-8 text-center text-body text-neutral-400">
              No notifications yet
            </p>
          ) : (
            notifications.map((n) => (
              <NotificationItem
                key={n.notification_id}
                notification={n}
                onRead={handleRead}
                onNavigate={handleNavigate}
              />
            ))
          )}
        </div>
      </aside>
    </>
  );
}
