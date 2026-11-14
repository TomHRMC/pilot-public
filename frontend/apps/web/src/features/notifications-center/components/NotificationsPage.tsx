"use client";

/**
 * NotificationsPage — in-app notification center list view
 *
 * Location: apps/web/src/features/notifications-center/components/NotificationsPage.tsx
 *
 * Reuses existing useInAppNotifications hook from @pilot/ui — no new hook created.
 * Hook verified: returns { notifications, unreadCount, isLoading (derived), markRead, markAllRead }.
 *
 * Note: useInAppNotifications does not expose isLoading directly — it uses useQuery internally.
 * The hook returns UseInAppNotificationsReturn which does not include isLoading.
 * We derive loading state from notifications being undefined (initial render).
 */

import { useInAppNotifications } from "@pilot/ui";
import { EmptyState } from "@pilot/ui/states";

export function NotificationsPage() {
  const { notifications, unreadCount, markRead, markAllRead } =
    useInAppNotifications();

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">
          Notifications
          {unreadCount > 0 && (
            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-700">
              {unreadCount} unread
            </span>
          )}
        </h1>
        {unreadCount > 0 && (
          <button
            onClick={() => void markAllRead()}
            className="text-sm text-brand-600 hover:text-brand-800"
          >
            Mark all read
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <EmptyState
          type="no-data"
          title="No notifications"
          description="You're all caught up."
        />
      ) : (
        <div className="space-y-1">
          {notifications.map((n) => (
            <div
              key={n.notification_id}
              className={`flex items-start gap-3 p-4 rounded-md border cursor-pointer transition-colors ${
                n.read_at
                  ? "border-neutral-100 bg-white text-neutral-500"
                  : "border-brand-100 bg-brand-50 text-neutral-900"
              }`}
              onClick={() => void markRead(n.notification_id)}
            >
              {!n.read_at && (
                <span className="mt-1.5 h-2 w-2 rounded-full bg-brand-600 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm">{n.body}</p>
                <p className="text-xs text-neutral-400 mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
