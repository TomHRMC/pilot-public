/**
 * Notification Preferences Page — FE-B12 / UI-FIX-2C
 *
 * Location: apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx
 *
 * Route: /settings/notifications/preferences
 *
 * Renders the full 8×3 notification preference matrix for the logged-in user.
 * Owner can also switch to /settings/notifications/tenant-defaults for team-level prefs.
 * Also displays recent in-app notification history below the matrix (UI-FIX-2C).
 */

"use client";

import React from "react";
import Link from "next/link";
import { NotificationPreferenceMatrix } from "@pilot/ui";
import { useNotificationPreferences } from "../../../../../features/notification-preferences/hooks/useNotificationPreferences";
import { useRecentInAppNotifications } from "../../../../../features/notification-preferences/hooks/useRecentInAppNotifications";

export default function NotificationPreferencesPage() {
  const {
    preferences,
    categories,
    isLoading,
    isError,
    isPending,
    onCellChange,
    onCellRevert,
    onRowRevert,
    onMuteAllPush,
    onMuteAllEmail,
    onResetAll,
  } = useNotificationPreferences();

  const {
    notifications: recentNotifications,
    isLoading: notifsLoading,
    markAllRead,
    isMarkingRead,
  } = useRecentInAppNotifications();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
        Failed to load notification preferences. Please refresh the page.
      </div>
    );
  }

  const unreadCount = recentNotifications.filter((n) => !n.isRead).length;

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <div>
        <h1 className="text-h2 font-semibold text-neutral-900">
          Notification preferences
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Choose how you&apos;d like to be notified about activity in Pilot.
        </p>
      </div>

      <NotificationPreferenceMatrix
        preferences={preferences}
        categories={categories}
        onCellChange={onCellChange}
        onCellRevert={onCellRevert}
        onRowRevert={onRowRevert}
        onMuteAllPush={onMuteAllPush}
        onMuteAllEmail={onMuteAllEmail}
        onResetAll={onResetAll}
        isPending={isPending}
        testID="notification-preference-matrix"
      />

      {/* Recent In-App Notifications — UI-FIX-2C */}
      <div className="mt-2" data-testid="recent-inapp-notifications-section">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-neutral-900">
            Recent notifications
            {unreadCount > 0 && (
              <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-brand-100 text-brand-700">
                {unreadCount} unread
              </span>
            )}
          </h2>
          {unreadCount > 0 && (
            <button
              onClick={() => void markAllRead()}
              disabled={isMarkingRead}
              className="text-xs text-brand-600 hover:underline disabled:opacity-50"
            >
              Mark all read
            </button>
          )}
        </div>

        {notifsLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin h-5 w-5 rounded-full border-2 border-brand-600 border-t-transparent" />
          </div>
        ) : recentNotifications.length === 0 ? (
          <div className="rounded-md border border-neutral-200 p-8 text-center">
            <p className="text-sm text-neutral-500">No recent notifications.</p>
          </div>
        ) : (
          <div className="rounded-md border border-neutral-200 overflow-hidden">
            {recentNotifications.map((notif, idx) => (
              <div
                key={notif.notificationId}
                className={`flex gap-3 px-4 py-3 ${idx < recentNotifications.length - 1 ? "border-b border-neutral-100" : ""} ${!notif.isRead ? "bg-brand-50" : "bg-white"}`}
              >
                <div
                  className={`mt-1 h-2 w-2 rounded-full shrink-0 ${!notif.isRead ? "bg-brand-500" : "bg-neutral-200"}`}
                />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-neutral-900">
                    {notif.title}
                  </p>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    {notif.body}
                  </p>
                  <p className="text-xs text-neutral-400 mt-1">
                    {new Date(notif.createdAt).toLocaleString()}
                  </p>
                </div>
                {notif.deepLinkHref && (
                  <Link
                    href={notif.deepLinkHref}
                    className="ml-auto text-xs text-brand-600 hover:underline shrink-0 self-center"
                  >
                    View →
                  </Link>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
