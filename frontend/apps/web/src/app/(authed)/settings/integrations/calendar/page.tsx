/**
 * CalendarIntegrationSettingsPage — /settings/integrations/calendar
 *
 * Route: /settings/integrations/calendar
 * Auth: Required (via (authed) layout)
 * Role Gate: owner/operator
 *
 * Page sections (in order):
 *   1. CalendarConnectionStatusCard + InFlightSyncIndicator surface="calendar"
 *   2. CalendarConflictQueue (anchor: #conflicts; ?scroll=conflicts → scrollIntoView on mount)
 *   3. CalendarSyncActivityLog (collapsible)
 *   4. CalendarAutoExpirySettings
 *
 * Pattern ref: design doc batch-fe-b8-design.md §A.4, §D.1
 */

"use client";

import React, { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  RoleGate,
  InFlightSyncIndicator,
  useInFlightSyncStatus,
} from "@pilot/ui";
import { CalendarConnectionStatusCard } from "@/features/calendar-conflict/components/CalendarConnectionStatusCard";
import { CalendarConflictQueue } from "@/features/calendar-conflict/components/CalendarConflictQueue";
import { CalendarSyncActivityLog } from "@/features/calendar-conflict/components/CalendarSyncActivityLog";
import { CalendarAutoExpirySettings } from "@/features/calendar-conflict/components/CalendarAutoExpirySettings";
import { useCalendarStatus } from "@/features/calendar-conflict/hooks/useCalendarStatus";

export default function CalendarIntegrationSettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: calendarStatus, isLoading } = useCalendarStatus();

  // FE-B15: unified sync status from BE-B15 (replaces local connectionStatus mapping)
  const syncStatus = useInFlightSyncStatus("calendar");

  // ?scroll=conflicts → scroll to #conflicts anchor on mount
  useEffect(() => {
    if (searchParams.get("scroll") === "conflicts") {
      const el = document.getElementById("conflicts");
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      }
    }
  }, [searchParams]);

  const handleReconnect = () => {
    // Redirect to the Google OAuth reconnect flow
    // In MVP this navigates to the OAuth initiation endpoint
    window.location.href = "/api/v1/integrations/calendar/connect";
  };

  const handleManualSync = () => {
    // Trigger manual sync via API — fire and forget
    void fetch("/api/v1/integrations/calendar/sync", { method: "POST" });
  };

  // FE-B15 click-to-detail — Decision 4
  const handleResolve = () => {
    router.push("/settings/integrations/calendar/conflicts");
  };

  return (
    <RoleGate role={["owner", "accountant"]}>
      <main
        className="mx-auto max-w-3xl space-y-8 p-6"
        data-testid="calendar-settings-page"
      >
        {/* Page heading */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-h2 font-medium text-neutral-900">
              Calendar Sync
            </h1>
            <p className="mt-1 text-body text-neutral-600">
              Manage your calendar integration and resolve sync conflicts.
            </p>
          </div>

          {/* InFlightSyncIndicator surface="calendar" — FE-B15: wired to useInFlightSyncStatus */}
          <InFlightSyncIndicator
            surface="calendar"
            state={syncStatus.state}
            pendingCount={syncStatus.pendingCount}
            pendingItems={syncStatus.pendingItems}
            lastSyncedAt={syncStatus.lastSyncedAt}
            nextSyncAt={syncStatus.nextSyncAt}
            amberThreshold={syncStatus.amberThreshold}
            manualTriggerSupported={syncStatus.manualTriggerSupported}
            onManualSync={
              syncStatus.manualTriggerSupported ? handleManualSync : undefined
            }
            onResolve={handleResolve}
            compact={true}
          />
        </div>

        {/* Section 1: Connection status */}
        <section aria-label="Calendar connection status">
          <CalendarConnectionStatusCard
            status={calendarStatus}
            isLoading={isLoading}
            onReconnect={handleReconnect}
          />
        </section>

        {/* Section 2: Conflict queue (anchored #conflicts) */}
        <CalendarConflictQueue
          autoExpireDays={30} // TODO: fetch from tenant settings
        />

        {/* Section 3: Activity log (collapsible) */}
        <CalendarSyncActivityLog />

        {/* Section 4: Auto-expiry settings */}
        <CalendarAutoExpirySettings />
      </main>
    </RoleGate>
  );
}
