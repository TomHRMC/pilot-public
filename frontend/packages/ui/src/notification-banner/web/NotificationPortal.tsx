"use client";

/**
 * NotificationPortal — Web only
 *
 * Location: packages/ui/src/notification-banner/web/NotificationPortal.tsx
 *
 * Creates the #notification-root DOM node and renders the notification queue
 * via React.createPortal. This component must be rendered in
 * apps/web/src/app/(authed)/layout.tsx so it only appears on authenticated surfaces.
 *
 * Renders the full notification stack (up to maxVisible banners) above all
 * page content including modals.
 */

import React from "react";
import { createPortal } from "react-dom";
import { useNotificationQueue } from "../useNotificationQueue";
import { NotificationBanner } from "./NotificationBanner";

interface NotificationPortalProps {
  onNavigate?: (path: string) => void;
}

/**
 * NotificationPortal (web)
 *
 * Must be rendered inside a <NotificationQueueProvider>.
 *
 * @example
 * // In (authed)/layout.tsx:
 * <NotificationQueueProvider>
 *   <NotificationPortal onNavigate={(path) => router.push(path)} />
 *   {children}
 * </NotificationQueueProvider>
 */
export function NotificationPortal({ onNavigate }: NotificationPortalProps) {
  const { notifications, dismissNotification } = useNotificationQueue();

  if (typeof document === "undefined") return null;
  if (notifications.length === 0) return null;

  // Ensure the portal target exists
  let portalRoot = document.getElementById("notification-root");
  if (!portalRoot) {
    portalRoot = document.createElement("div");
    portalRoot.id = "notification-root";
    document.body.appendChild(portalRoot);
  }

  return createPortal(
    <div
      aria-label="Notifications"
      data-testid="notification-portal"
      style={{
        position: "fixed",
        top: 16,
        right: 16,
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        width: 380,
        maxWidth: "calc(100vw - 32px)",
      }}
    >
      {notifications.map((notification) => (
        <NotificationBanner
          key={notification.id}
          notification={notification}
          onDismiss={dismissNotification}
          onNavigate={onNavigate}
        />
      ))}
    </div>,
    portalRoot,
  );
}
