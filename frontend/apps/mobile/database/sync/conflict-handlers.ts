/**
 * Conflict Handlers — Four-class severity routing
 *
 * Location: apps/mobile/database/sync/conflict-handlers.ts
 *
 * Per batch-fe-b7-design.md critical architecture rule #4:
 * "The severity class is the ONLY decision variable."
 *
 * Handler responsibilities:
 *   handleAutoSilent    → auto_apply: silently apply server version; update local DB
 *   handleAutoNotice    → safe_to_apply: apply server version + fire NotificationBanner
 *   handleTechResolvable → requires_review: mark as 'conflict'; open ConflictResolutionScreen
 *   handleOwnerEscalation → escalate_to_owner: create escalation via API; mark as 'conflict'
 *
 * Per §16.6 arch doc and batch-fe-b7-design.md Section A.2.3.
 */

import { Database } from "@nozbe/watermelondb";
import type { SyncConflict } from "./types";
import type { SyncableModel } from "../models/SyncableModel";

type ApiClient = {
  post: (
    url: string,
    data: unknown,
    options?: { headers?: Record<string, string> },
  ) => Promise<{ data: unknown }>;
};

/**
 * auto_apply — Silent server-wins resolution.
 * No user notification. Updates local record with server version.
 */
export async function handleAutoSilent(
  conflict: SyncConflict,
  record: SyncableModel,
  db: Database,
): Promise<void> {
  await db.write(async () => {
    await record.update((r) => {
      const syncable = r as SyncableModel;
      // Apply server field values to local record
      applyServerFields(syncable, conflict.serverVersion);
      syncable.localSyncStatus = "synced";
      syncable.syncError = null;
      syncable.retryCount = 0;
    });
  });

  console.log(
    `[ConflictHandler] auto_apply resolved silently: ${conflict.entityType}/${conflict.entityId}`,
  );
}

/**
 * safe_to_apply — Apply server version + show NotificationBanner.
 * The banner is fired via the sync store, which the NotificationQueueProvider
 * picks up and displays.
 */
export async function handleAutoNotice(
  conflict: SyncConflict,
  record: SyncableModel,
  db: Database,
): Promise<void> {
  await db.write(async () => {
    await record.update((r) => {
      const syncable = r as SyncableModel;
      applyServerFields(syncable, conflict.serverVersion);
      syncable.localSyncStatus = "synced";
      syncable.syncError = null;
      syncable.retryCount = 0;
    });
  });

  // Fire notification via global event (picked up by NotificationQueueProvider)
  // The SyncQueueStore.notifyAutoNotice() call is made from SyncOrchestrator
  // which has access to the notification queue hook context
  if (typeof globalThis !== "undefined" && "pilotNotifySync" in globalThis) {
    const notify = (globalThis as Record<string, unknown>)["pilotNotifySync"];
    if (typeof notify === "function") {
      (notify as (args: { severity: string; message: string }) => void)({
        severity: "info",
        message: `Server update applied to ${conflict.entitySummary}`,
      });
    }
  }

  console.log(
    `[ConflictHandler] safe_to_apply resolved with banner: ${conflict.entityType}/${conflict.entityId}`,
  );
}

/**
 * requires_review — Mark record as 'conflict'; navigate to ConflictResolutionScreen.
 * The orchestrator fires onTechResolvableConflict callback to trigger navigation.
 */
export async function handleTechResolvable(
  conflict: SyncConflict,
  record: SyncableModel,
  db: Database,
): Promise<void> {
  await db.write(async () => {
    await record.update((r) => {
      const syncable = r as SyncableModel;
      syncable.localSyncStatus = "conflict";
      syncable.syncError = `Conflict requires review: ${conflict.id}`;
    });
  });

  console.log(
    `[ConflictHandler] requires_review conflict queued for tech resolution: ${conflict.id}`,
  );
}

/**
 * escalate_to_owner — Create escalation via API; mark record as 'conflict'.
 * Owner receives push notification from the backend.
 * EscalationStatusRow displays the pending escalation to the tech.
 */
export async function handleOwnerEscalation(
  conflict: SyncConflict,
  record: SyncableModel,
  db: Database,
  apiClient: ApiClient,
): Promise<void> {
  // POST escalation to backend — owner gets push notification from BE
  await apiClient.post("/api/v1/mobile-sync/escalations", {
    conflict_id: conflict.id,
    entity_type: conflict.entityType,
    entity_id: conflict.entityId,
    entity_summary: conflict.entitySummary,
    local_version: conflict.localVersion,
    server_version: conflict.serverVersion,
    field_diffs: conflict.fieldDiffs,
  });

  await db.write(async () => {
    await record.update((r) => {
      const syncable = r as SyncableModel;
      syncable.localSyncStatus = "conflict";
      syncable.syncError = `Escalated to owner: ${conflict.id}`;
    });
  });

  console.log(
    `[ConflictHandler] escalate_to_owner: conflict ${conflict.id} sent to owner`,
  );
}

// ─── Internal helpers ──────────────────────────────────────────────────────

/**
 * Applies server-side field values to a local WatermelonDB record.
 * Only applies fields that exist on the local record (no schema violations).
 */
function applyServerFields(
  record: SyncableModel,
  serverVersion: Record<string, unknown>,
): void {
  const raw = (record as unknown as { _raw: Record<string, unknown> })._raw;

  for (const [key, value] of Object.entries(serverVersion)) {
    // Skip sync-control fields — never overwrite from server
    if (
      [
        "sync_status",
        "idempotency_key",
        "sync_error",
        "retry_count",
        "client_capture_at",
        "created_at",
        "id",
      ].includes(key)
    ) {
      continue;
    }

    if (key in raw) {
      raw[key] = value;
    }
  }
}
