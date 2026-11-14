/**
 * notify.ts — FE-B11
 *
 * Convenience helpers for settings notifications.
 * NotificationItem requires id + title + severity (not message/text).
 */

import type { NotificationQueueContextValue } from "@pilot/ui";

type AddNotification = NotificationQueueContextValue["addNotification"];

let _counter = 0;
function nextId(prefix: string) {
  return `${prefix}-${++_counter}-${Date.now()}`;
}

export function notifyReverted(addNotification: AddNotification) {
  addNotification({
    id: nextId("settings-reverted"),
    title: "Reverted to default.",
    severity: "success",
  });
}

export function notifySaved(addNotification: AddNotification, label?: string) {
  addNotification({
    id: nextId("settings-saved"),
    title: label ? `${label} saved.` : "Setting saved.",
    severity: "success",
  });
}

export function notifyError(addNotification: AddNotification, detail: string) {
  addNotification({
    id: nextId("settings-error"),
    title: "Couldn't save — try again.",
    detail,
    severity: "error",
  });
}
