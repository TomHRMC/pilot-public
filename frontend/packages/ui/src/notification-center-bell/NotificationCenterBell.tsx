/**
 * NotificationCenterBell — Shared web + mobile component
 *
 * Location: packages/ui/src/notification-center-bell/NotificationCenterBell.tsx
 *
 * Renders: bell icon + unread badge + slides-in drawer (web) / bottom sheet (mobile).
 *
 * ⚠️ INTERFACE LOCKED after FE-B12 ships — FE-B13 embeds this in onboarding confirmation.
 *
 * Design doc Section H token audit:
 * - Unread badge (1–9): bg-brand-500 text-white
 * - Unread badge (10+): bg-brand-700 text-white
 * - SSE disconnected indicator: alert-300 (amber dot)
 */

"use client";

import React, { useRef, useEffect } from "react";
import { Platform } from "react-native";
import type { NotificationCenterBellProps, InAppNotification } from "./types";

const isWeb = Platform.OS === "web";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const past = new Date(isoString).getTime();
  const diffMs = now - past;
  const diffMinutes = Math.floor(diffMs / 60_000);
  if (diffMinutes < 1) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

// ─── Bell Icon ────────────────────────────────────────────────────────────────

function BellIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`w-5 h-5 ${className}`}
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── Unread Badge ─────────────────────────────────────────────────────────────

function UnreadBadge({ count }: { count: number }) {
  if (count === 0) return null;
  // Design doc Section H: 1-9 → brand-500; 10+ → brand-700
  const bgClass = count >= 10 ? "bg-brand-700" : "bg-brand-500";
  return (
    <span
      className={`absolute -top-1 -right-1 flex items-center justify-center min-w-[16px] h-4 rounded-full ${bgClass} text-white text-[10px] font-bold px-1 leading-none`}
      aria-hidden="true"
    >
      {count >= 100 ? "99+" : count}
    </span>
  );
}

// ─── Notification Item ────────────────────────────────────────────────────────

function NotificationItem({
  notification,
  onMarkRead,
  onNavigate,
}: {
  notification: InAppNotification;
  onMarkRead: (id: string) => Promise<void>;
  onNavigate: (target: string) => void;
}) {
  const isUnread = !notification.read_at;

  const handleClick = async () => {
    if (isUnread) {
      await onMarkRead(notification.notification_id);
    }
    onNavigate(notification.deep_link_target);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-neutral-50 focus:outline-none focus:bg-neutral-50 transition-colors border-b border-neutral-100 last:border-b-0 ${
        isUnread ? "bg-brand-50/30" : ""
      }`}
      data-testid={`notification-item-${notification.notification_id}`}
    >
      {/* Unread dot */}
      <div className="mt-1.5 flex-shrink-0">
        {isUnread ? (
          <div
            className="w-2 h-2 rounded-full bg-brand-500"
            aria-label="Unread"
          />
        ) : (
          <div className="w-2 h-2" aria-hidden="true" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <p
          className={`text-sm leading-snug ${isUnread ? "font-medium text-neutral-900" : "text-neutral-700"}`}
        >
          {notification.body}
        </p>
        <p className="mt-0.5 text-xs text-neutral-400">
          {formatRelativeTime(notification.created_at)}
        </p>
      </div>
    </button>
  );
}

// ─── Notification Drawer (web) ────────────────────────────────────────────────

function NotificationDrawer({
  isOpen,
  notifications,
  unreadCount,
  isConnected,
  onMarkRead,
  onMarkAllRead,
  onNavigate,
  onClose,
  testID,
}: {
  isOpen: boolean;
  notifications: InAppNotification[];
  unreadCount: number;
  isConnected: boolean;
  onMarkRead: (id: string) => Promise<void>;
  onMarkAllRead: () => Promise<void>;
  onNavigate: (target: string) => void;
  onClose: () => void;
  testID?: string;
}) {
  const drawerRef = useRef<HTMLElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isOpen, onClose]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <aside
      ref={drawerRef}
      data-testid={testID ?? "notification-center-drawer"}
      aria-label="Notifications"
      className="absolute right-0 top-full mt-2 w-96 max-h-[35rem] bg-white rounded-xl shadow-xl border border-neutral-200 z-50 flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-neutral-900">
            Notifications
          </h2>
          {/* SSE connection indicator */}
          {!isConnected && (
            <span
              className="w-2 h-2 rounded-full bg-alert-300"
              title="Notification stream disconnected — reconnecting..."
              data-testid="sse-disconnected-indicator"
            />
          )}
        </div>
        {unreadCount > 0 && (
          <button
            type="button"
            onClick={onMarkAllRead}
            className="text-xs text-brand-600 hover:text-brand-800 focus:outline-none focus:underline"
            data-testid="mark-all-read"
          >
            Mark all read
          </button>
        )}
      </div>

      {/* Notification list */}
      <div
        className="flex-1 overflow-y-auto"
        role="list"
        aria-label="Notification list"
      >
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <BellIcon className="text-neutral-300 mb-3 w-8 h-8" />
            <p className="text-sm text-neutral-400">No notifications yet</p>
          </div>
        ) : (
          notifications.map((n) => (
            <NotificationItem
              key={n.notification_id}
              notification={n}
              onMarkRead={onMarkRead}
              onNavigate={(target) => {
                onNavigate(target);
                onClose();
              }}
            />
          ))
        )}
      </div>
    </aside>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

/**
 * NotificationCenterBell
 *
 * Renders the bell button + unread badge. On click, shows notification drawer.
 * Compose with useInAppNotifications to supply all props.
 *
 * @example
 * const notifs = useInAppNotifications();
 * <NotificationCenterBell
 *   notifications={notifs.notifications}
 *   unreadCount={notifs.unreadCount}
 *   isConnected={notifs.isConnected}
 *   onMarkRead={notifs.markRead}
 *   onMarkAllRead={notifs.markAllRead}
 *   onNotificationNavigate={router.push}
 * />
 */
export function NotificationCenterBell({
  notifications,
  unreadCount,
  isConnected,
  onMarkRead,
  onMarkAllRead,
  onNotificationNavigate,
  testID,
}: NotificationCenterBellProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  if (!isWeb) {
    // Mobile: minimal placeholder — full mobile bottom sheet in mobile variant
    return null;
  }

  return (
    <div
      className="relative"
      data-testid={testID ?? "notification-center-bell"}
    >
      <button
        type="button"
        onClick={() => setIsOpen((o) => !o)}
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="relative p-2 rounded-md text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 transition-colors"
        data-testid="notification-bell-button"
      >
        <BellIcon />
        <UnreadBadge count={unreadCount} />
      </button>

      <NotificationDrawer
        isOpen={isOpen}
        notifications={notifications}
        unreadCount={unreadCount}
        isConnected={isConnected}
        onMarkRead={onMarkRead}
        onMarkAllRead={onMarkAllRead}
        onNavigate={onNotificationNavigate}
        onClose={() => setIsOpen(false)}
        testID="notification-center-drawer"
      />
    </div>
  );
}
