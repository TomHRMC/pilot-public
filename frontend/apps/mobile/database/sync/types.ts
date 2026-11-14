/**
 * Sync orchestrator types
 *
 * Location: apps/mobile/database/sync/types.ts
 *
 * Shared type definitions for the SyncOrchestrator, conflict handlers,
 * and sync UI components.
 *
 * Per batch-fe-b7-design.md Section F.4.
 */

export type OfflineEntityType =
  | "time_entry"
  | "expense"
  | "photo"
  | "change_order"
  | "loto_check"
  | "job_status_change"
  | "job_note"
  | "voice_audio"
  | "invoice_signoff";

export type SyncTrigger =
  | "foreground_transition" // App came to foreground
  | "network_online" // OS reported connectivity restored
  | "periodic_check" // 30-second interval while app is active
  | "manual" // User pressed "Sync now"
  | "background"; // Server-initiated silent push (FE-B9 extends)

export type OrchestratorSyncStatus = "idle" | "syncing" | "error" | "paused";

export type SyncState =
  | {
      status: "idle";
      pendingCount: number;
      lastSyncedAt: string | null;
    }
  | {
      status: "syncing";
      pendingCount: number;
      progress: number;
    }
  | {
      status: "error";
      pendingCount: number;
      error: Error;
      lastSyncedAt: string | null;
    }
  | {
      status: "paused";
      pendingCount: number;
      reason: "offline" | "hard_limit_exceeded";
    };

/**
 * Four-class conflict severity from BE-B7b/A40.
 * Drives ALL UI decisions — no other variable should determine conflict display.
 *
 * Per batch-fe-b7-design.md critical architecture rule #4 and arch §16.6.
 */
export type ConflictSeverityClass =
  | "auto_apply" // Silent; no user notification
  | "safe_to_apply" // NotificationBanner from FE-B1
  | "requires_review" // Full-screen ConflictResolutionScreen with DiffView
  | "escalate_to_owner"; // EscalationStatusRow; owner notified

export interface SyncConflict {
  id: string;
  entityType: OfflineEntityType;
  entityId: string;
  entitySummary: string;
  severityClass: ConflictSeverityClass;
  localVersion: Record<string, unknown>;
  serverVersion: Record<string, unknown>;
  fieldDiffs: Array<{
    field_name: string;
    local_value: unknown;
    server_value: unknown;
  }>;
  detectedAt: string;
}

export interface SyncPushResult {
  pushed: number;
  failed: number;
  conflicts: SyncConflict[];
}

export interface SyncPullResult {
  updated: number;
  resolved: number;
}
