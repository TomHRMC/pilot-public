"use client";

/**
 * NotificationQueueProvider — React context provider for the notification queue
 *
 * Location: packages/ui/src/notification-banner/NotificationQueueProvider.tsx
 *
 * Cross-platform (web + mobile). Manages queue state with useReducer.
 * Must wrap the app root — both web (authed)/layout.tsx and mobile _layout.tsx.
 *
 * Queue behaviour:
 *   - Max 3 visible notifications (configurable via maxVisible prop)
 *   - When a 4th is added, oldest is removed (FIFO)
 *   - Critical severity notifications are never auto-dismissed by the provider;
 *     the banner component handles auto-dismiss timing per severity
 */

import React, { createContext, useReducer, useCallback } from "react";
import type {
  NotificationItem,
  NotificationQueueContextValue,
  NotificationQueueProviderProps,
} from "./types";

// ── Context ──────────────────────────────────────────────────────────────────

export const NotificationQueueContext =
  createContext<NotificationQueueContextValue | null>(null);

NotificationQueueContext.displayName = "NotificationQueueContext";

// ── Reducer ──────────────────────────────────────────────────────────────────

type QueueAction =
  | { type: "ADD"; item: NotificationItem; maxVisible: number }
  | { type: "DISMISS"; id: string }
  | { type: "DISMISS_ALL" };

function queueReducer(
  state: NotificationItem[],
  action: QueueAction,
): NotificationItem[] {
  switch (action.type) {
    case "ADD": {
      // Deduplicate: same id replaces existing
      const withoutDup = state.filter((n) => n.id !== action.item.id);
      const next = [...withoutDup, action.item];
      // If over cap, remove oldest (first in array = oldest)
      return next.length > action.maxVisible
        ? next.slice(next.length - action.maxVisible)
        : next;
    }
    case "DISMISS":
      return state.filter((n) => n.id !== action.id);
    case "DISMISS_ALL":
      return [];
    default:
      return state;
  }
}

// ── Provider ─────────────────────────────────────────────────────────────────

/**
 * NotificationQueueProvider
 *
 * @example
 * // In apps/web/src/app/(authed)/layout.tsx:
 * <NotificationQueueProvider>
 *   <NotificationPortal />
 *   {children}
 * </NotificationQueueProvider>
 */
export function NotificationQueueProvider({
  children,
  maxVisible = 3,
}: NotificationQueueProviderProps) {
  const [notifications, dispatch] = useReducer(queueReducer, []);

  const addNotification = useCallback(
    (item: Omit<NotificationItem, "createdAt">) => {
      dispatch({
        type: "ADD",
        item: { ...item, createdAt: new Date() },
        maxVisible,
      });
    },
    [maxVisible],
  );

  const dismissNotification = useCallback((id: string) => {
    dispatch({ type: "DISMISS", id });
  }, []);

  const dismissAll = useCallback(() => {
    dispatch({ type: "DISMISS_ALL" });
  }, []);

  console.log("NotificationQueueProvider rendered");
  return (
    <NotificationQueueContext.Provider
      value={{
        notifications,
        addNotification,
        dismissNotification,
        dismissAll,
      }}
    >
      {children}
    </NotificationQueueContext.Provider>
  );
}
