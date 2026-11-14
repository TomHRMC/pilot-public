"use client";

/**
 * useNotificationQueue — cross-platform hook for managing the notification queue.
 *
 * Location: packages/ui/src/notification-banner/useNotificationQueue.ts
 *
 * Must be called inside a <NotificationQueueProvider>.
 * Queue max size: 3 visible notifications (default). Oldest is automatically
 * dismissed when a new notification would exceed the cap (FIFO).
 *
 * Implemented with React Context + useReducer — no external state library
 * required in packages/ui (no Zustand dependency added here).
 */

import { useContext } from "react";
import { NotificationQueueContext } from "./NotificationQueueProvider";
import type { NotificationQueueContextValue } from "./types";

/**
 * useNotificationQueue
 *
 * @throws Error if called outside of <NotificationQueueProvider>
 */
export function useNotificationQueue(): NotificationQueueContextValue {
  const ctx = useContext(NotificationQueueContext);
  console.log("useNotificationQueue called, ctx is:", !!ctx);
  if (!ctx) {
    throw new Error(
      "useNotificationQueue must be called inside a <NotificationQueueProvider>. " +
        "Ensure your app root wraps with <NotificationQueueProvider>.",
    );
  }
  return ctx;
}
