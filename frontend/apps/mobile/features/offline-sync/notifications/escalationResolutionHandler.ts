/**
 * escalationResolutionHandler — push notification handler for escalation_resolved
 *
 * Location: apps/mobile/features/offline-sync/notifications/escalationResolutionHandler.ts
 *
 * Established FE-B9. Handles silent push type `escalation_resolved`.
 * Called by the Expo Notifications background handler.
 *
 * Flow (design doc Decision 6):
 *   1. Silent push received → call SyncOrchestrator.pull()
 *   2. WatermelonDB transitions escalation record to terminal state
 *   3. Invalidate TanStack Query cache for field-issues list
 *   4. Return so the native system can dismiss the push silently
 *
 * FE-B9 does NOT build push notification permission request UI (FE-B13 scope).
 */

import type { QueryClient } from "@tanstack/react-query";
import type { SyncOrchestrator } from "../../../database/sync/orchestrator";

export interface EscalationResolutionPushPayload {
  type: "escalation_resolved";
  issue_id: string;
  resolution:
    | "resolved_in_favor_of_tech"
    | "resolved_in_favor_of_server"
    | "resolved_with_action";
  job_id?: string;
}

/**
 * Handle a silent `escalation_resolved` push notification.
 *
 * @param payload - The push notification data body
 * @param orchestrator - SyncOrchestrator instance (manages WatermelonDB pull)
 * @param queryClient - TanStack Query client for cache invalidation
 */
export async function handleEscalationResolutionPush(
  payload: EscalationResolutionPushPayload,
  orchestrator: SyncOrchestrator,
  queryClient: QueryClient,
): Promise<void> {
  if (payload.type !== "escalation_resolved") {
    // Not our notification type — ignore
    return;
  }

  try {
    // Step 1: Pull from server — updates WatermelonDB escalation record to terminal state
    await orchestrator.pull();

    // Step 2: Invalidate TanStack Query cache for field-issues list
    // This triggers re-render of SyncQueueItem with terminal state via EscalationResolutionOutcome
    queryClient.invalidateQueries({ queryKey: ["field-issues-summary"] });
    queryClient.invalidateQueries({ queryKey: ["field-issues"] });
  } catch (err) {
    // Log error but do not throw — silent push handlers must not crash
    console.error(
      "[escalationResolutionHandler] Failed to process escalation_resolved push:",
      err,
    );
  }
}

/**
 * Register the escalation resolution handler with Expo Notifications.
 * Call this in app/_layout.tsx or app startup.
 *
 * @example
 * import * as Notifications from 'expo-notifications';
 * import { registerEscalationResolutionHandler } from './escalationResolutionHandler';
 * registerEscalationResolutionHandler(orchestrator, queryClient);
 */
export function registerEscalationResolutionHandler(
  orchestrator: SyncOrchestrator,
  queryClient: QueryClient,
): void {
  // Import lazily to avoid circular deps at module init time
  // The actual Expo Notifications import happens at runtime
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const Notifications = require("expo-notifications") as {
    addNotificationReceivedListener: (
      listener: (notification: {
        request: { content: { data: Record<string, unknown> } };
      }) => void,
    ) => { remove: () => void };
  };

  Notifications.addNotificationReceivedListener((notification) => {
    const data = notification.request.content.data;
    if (data.type === "escalation_resolved") {
      void handleEscalationResolutionPush(
        data as unknown as EscalationResolutionPushPayload,
        orchestrator,
        queryClient,
      );
    }
  });
}
