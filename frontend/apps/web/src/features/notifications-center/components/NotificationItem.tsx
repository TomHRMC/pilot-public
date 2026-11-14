"use client";

/**
 * NotificationItem — single notification row
 *
 * Location: apps/web/src/features/notifications-center/components/NotificationItem.tsx
 *
 * Props:
 *   - notification: InAppNotification
 *   - onRead: (id: string) => void
 *   - onNavigate: (target: string) => void
 */

import type { InAppNotification } from "../types";

interface Props {
  notification: InAppNotification;
  onRead: (id: string) => void;
  onNavigate: (target: string) => void;
}

function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const MAX_BODY_LENGTH = 120;

export function NotificationItem({ notification, onRead, onNavigate }: Props) {
  const isUnread = notification.read_at === null;
  const body =
    notification.body.length > MAX_BODY_LENGTH
      ? `${notification.body.slice(0, MAX_BODY_LENGTH)}…`
      : notification.body;

  function handleClick() {
    if (isUnread) onRead(notification.notification_id);
    onNavigate(notification.deep_link_target);
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`w-full text-left px-4 py-3 border-b border-neutral-100 last:border-0 hover:bg-neutral-50 flex items-start gap-3 ${
        isUnread ? "bg-blue-50" : ""
      }`}
      data-testid={`notification-item-${notification.notification_id}`}
    >
      {/* Unread indicator dot */}
      <span className="mt-1.5 shrink-0">
        {isUnread ? (
          <span
            className="block h-2 w-2 rounded-full bg-brand-600"
            aria-label="Unread"
          />
        ) : (
          <span className="block h-2 w-2 rounded-full bg-transparent" />
        )}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-body-sm text-neutral-900">{body}</p>
          {notification.priority === "critical" && (
            <span className="shrink-0 rounded-full bg-red-100 px-1.5 py-0.5 text-caption font-medium text-red-700">
              Critical
            </span>
          )}
        </div>
        <p className="mt-0.5 text-caption text-neutral-400">
          {relativeTime(notification.created_at)}
        </p>
      </div>
    </button>
  );
}
