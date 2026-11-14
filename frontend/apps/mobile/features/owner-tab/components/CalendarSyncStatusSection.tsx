/**
 * CalendarSyncStatusSection — wires useCalendarStatus to CalendarSyncStatusRow
 *
 * Location: apps/mobile/features/owner-tab/components/CalendarSyncStatusSection.tsx
 *
 * Placed below the QuickBooks sync row on the Owner tab.
 * Deep-link URLs come from config constants (not hardcoded).
 *
 * Pattern ref: design doc batch-fe-b8-design.md §A.3, §D.7
 */

import React from "react";
import { CalendarSyncStatusRow } from "@pilot/ui";
import {
  useCalendarStatus,
  CALENDAR_RESOLVE_WEB_URL,
  CALENDAR_SETTINGS_WEB_URL,
} from "../hooks/useCalendarStatus";

export function CalendarSyncStatusSection() {
  const { data: status, isLoading } = useCalendarStatus();

  // Use error/reconnect URL if reconnect needed, otherwise use resolve URL
  const resolveWebUrl =
    status?.requiresReconnect || status?.connectionStatus === "error"
      ? CALENDAR_SETTINGS_WEB_URL
      : CALENDAR_RESOLVE_WEB_URL;

  return (
    <CalendarSyncStatusRow
      status={status}
      isLoading={isLoading}
      resolveWebUrl={resolveWebUrl}
      testID="owner-tab-calendar-sync-row"
    />
  );
}
