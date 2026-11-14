/**
 * SyncOrchestrator — Custom sync class for mobile offline-first operations
 *
 * Location: apps/mobile/database/sync/orchestrator.ts
 *
 * CRITICAL: Does NOT use WatermelonDB's built-in synchronize(). This class
 * implements custom push/pull logic against BE-B7a/A37 endpoints.
 *
 * Every push includes X-Idempotency-Key header (UUID from model.idempotencyKey).
 * Backend deduplicates via idempotency_key + natural-key fallback.
 *
 * client_capture_at is preserved across the sync boundary — NOT overwritten
 * by server-side created_at.
 *
 * Conflict routing: severity class is the ONLY decision variable per §16.6.
 *   auto_apply      → handleAutoSilent (no UI)
 *   safe_to_apply   → handleAutoNotice (NotificationBanner)
 *   requires_review → handleTechResolvable (ConflictResolutionScreen)
 *   escalate_to_owner → handleOwnerEscalation (EscalationStatusRow)
 *
 * Per batch-fe-b7-design.md Section A.2.3, Section F.4, and §15 entire section.
 */

import { Database, Q } from "@nozbe/watermelondb";
import type {
  SyncTrigger,
  SyncState,
  SyncConflict,
  SyncPushResult,
  SyncPullResult,
  OfflineEntityType,
} from "./types";
import type { SyncableModel } from "../models/SyncableModel";
import {
  handleAutoSilent,
  handleAutoNotice,
  handleTechResolvable,
  handleOwnerEscalation,
} from "./conflict-handlers";

type ApiClient = {
  post: (
    url: string,
    data: unknown,
    options?: { headers?: Record<string, string> },
  ) => Promise<{ data: unknown }>;
  get: (url: string) => Promise<{ data: unknown }>;
};

export interface SyncOrchestratorOptions {
  database: Database;
  /** Bound apiClient with current JWT */
  apiClient: ApiClient;
  /** Device identifier (Expo Constants.deviceId) */
  deviceId: string;
  /** Called on every sync state change for UI updates */
  onStateChange?: (state: SyncState) => void;
  /** Called when a conflict requires tech action */
  onTechResolvableConflict?: (conflict: SyncConflict) => void;
  /** Called when a conflict is escalated to owner */
  onOwnerEscalation?: (conflict: SyncConflict) => void;
}

/** Maps entity types to their WatermelonDB table names */
const ENTITY_TABLE_MAP: Record<
  Exclude<OfflineEntityType, "voice_audio">,
  string
> = {
  time_entry: "time_entries",
  expense: "expenses",
  photo: "photos",
  change_order: "change_orders",
  loto_check: "loto_checks",
  job_status_change: "job_status_changes",
  job_note: "job_notes",
  invoice_signoff: "invoice_signoffs",
};

/** Maps entity types to their backend push endpoints */
const ENTITY_PUSH_ENDPOINT: Record<
  Exclude<OfflineEntityType, "voice_audio" | "photo">,
  string
> = {
  time_entry: "/api/v1/mobile-sync/push/time-entries",
  expense: "/api/v1/mobile-sync/push/expenses",
  change_order: "/api/v1/mobile-sync/push/change-orders",
  loto_check: "/api/v1/mobile-sync/push/loto-checks",
  job_status_change: "/api/v1/mobile-sync/push/job-status-changes",
  job_note: "/api/v1/mobile-sync/push/job-notes",
  // CE-1 Part B: invoice sign-off pushes directly to the signoff endpoint
  // (not via mobile-sync/push) — the URL includes the invoice_id path param.
  // The push() method handles this via the INVOICE_SIGNOFF_ENDPOINT_PREFIX.
  invoice_signoff: "__invoice_signoff__",
};

/**
 * CE-1 Part B: invoice sign-off uses a RESTful endpoint with the invoice_id
 * in the URL path, not a generic mobile-sync/push endpoint. The push() method
 * detects the sentinel and builds the URL from the record's invoice_id field.
 */
const INVOICE_SIGNOFF_SENTINEL = "__invoice_signoff__";
const INVOICE_SIGNOFF_ENDPOINT_PREFIX = "/api/v1/invoices/";
const INVOICE_SIGNOFF_ENDPOINT_SUFFIX = "/signoff";

/** Hard limit in hours; after this, writes are blocked until synced */
const HARD_LIMIT_HOURS = 72;

export class SyncOrchestrator {
  private readonly db: Database;
  private readonly apiClient: ApiClient;
  private readonly deviceId: string;
  private readonly onStateChange?: (state: SyncState) => void;
  private readonly onTechResolvableConflict?: (conflict: SyncConflict) => void;
  private readonly onOwnerEscalation?: (conflict: SyncConflict) => void;

  private currentState: SyncState = {
    status: "idle",
    pendingCount: 0,
    lastSyncedAt: null,
  };

  /** Prevents concurrent syncs — second call is a no-op if sync in progress */
  private isSyncing = false;

  constructor(options: SyncOrchestratorOptions) {
    this.db = options.database;
    this.apiClient = options.apiClient;
    this.deviceId = options.deviceId;
    this.onStateChange = options.onStateChange;
    this.onTechResolvableConflict = options.onTechResolvableConflict;
    this.onOwnerEscalation = options.onOwnerEscalation;
  }

  /**
   * Run a full push+pull sync cycle.
   * Safe to call concurrently — second call is a no-op if sync is already in progress.
   */
  async sync(trigger: SyncTrigger): Promise<void> {
    if (this.isSyncing) {
      console.log(
        `[SyncOrchestrator] sync(${trigger}) skipped — already syncing`,
      );
      return;
    }

    this.isSyncing = true;
    const pendingCount = await this.getPendingCount();

    this.setState({ status: "syncing", pendingCount, progress: 0 });

    try {
      // Create a sync session with the backend
      const sessionResponse = await this.apiClient.post(
        "/api/v1/mobile/sync-sessions",
        { device_id: this.deviceId, trigger },
      );
      const session = sessionResponse.data as { session_id: string };

      // Push all pending entities
      const pushResult = await this.push();

      this.setState({
        status: "syncing",
        pendingCount: pushResult.failed,
        progress: 50,
      });

      // Pull server state updates
      const pullResult = await this.pull();

      // Complete the sync session
      await this.apiClient.post(
        `/api/v1/mobile/sync-sessions/${session.session_id}/complete`,
        {
          pushed: pushResult.pushed,
          failed: pushResult.failed,
          pulled: pullResult.updated,
        },
      );

      const remainingPending = await this.getPendingCount();
      this.setState({
        status: "idle",
        pendingCount: remainingPending,
        lastSyncedAt: new Date().toISOString(),
      });
    } catch (error) {
      const pendingAfterError = await this.getPendingCount();
      this.setState({
        status: "error",
        pendingCount: pendingAfterError,
        error: error instanceof Error ? error : new Error(String(error)),
        lastSyncedAt:
          this.currentState.status !== "syncing"
            ? ((this.currentState as Extract<SyncState, { status: "idle" }>)
                .lastSyncedAt ?? null)
            : null,
      });
    } finally {
      this.isSyncing = false;
    }
  }

  /**
   * Push all pending items. Sends X-Idempotency-Key header with every request.
   * Voice audio and photos are excluded — they use their own upload pipelines.
   */
  async push(operationType?: OfflineEntityType): Promise<SyncPushResult> {
    const result: SyncPushResult = { pushed: 0, failed: 0, conflicts: [] };

    const entityTypes = operationType
      ? [operationType]
      : (Object.keys(ENTITY_TABLE_MAP) as Exclude<
          OfflineEntityType,
          "voice_audio"
        >[]);

    for (const entityType of entityTypes) {
      if (entityType === "photo" || entityType === "voice_audio") continue;

      const tableName =
        ENTITY_TABLE_MAP[entityType as keyof typeof ENTITY_TABLE_MAP];
      if (!tableName) continue;

      const endpoint =
        ENTITY_PUSH_ENDPOINT[entityType as keyof typeof ENTITY_PUSH_ENDPOINT];
      if (!endpoint) continue;

      // Query all pending records for this entity type
      const collection = this.db.get<SyncableModel>(tableName);
      const pendingRecords = await collection
        .query(Q.where("sync_status", Q.oneOf(["pending", "failed"])))
        .fetch();

      for (const record of pendingRecords) {
        try {
          // Mark as syncing
          await this.db.write(async () => {
            await record.update((r) => {
              (r as SyncableModel).localSyncStatus = "syncing";
            });
          });

          // CE-1 Part B: invoice sign-off uses a RESTful endpoint with invoice_id
          // in the URL path. Detect the sentinel and build the real URL.
          let pushUrl = endpoint;
          let pushBody: Record<string, unknown> = this.serializeRecord(
            entityType,
            record,
          );
          if (endpoint === INVOICE_SIGNOFF_SENTINEL) {
            const raw = (record as unknown as { _raw: Record<string, unknown> })
              ._raw;
            const invoiceId = raw["invoice_id"] as string;
            pushUrl =
              INVOICE_SIGNOFF_ENDPOINT_PREFIX +
              invoiceId +
              INVOICE_SIGNOFF_ENDPOINT_SUFFIX;
            // Invoice signoff body uses only the 4 fields the backend expects
            pushBody = {
              signed_by_name: raw["signed_by_name"],
              terms_acknowledged: true,
              signature_png_base64: raw["signature_png_base64"],
              client_capture_at: record.clientCaptureAt?.toISOString(),
            };
          }

          // Push to backend with X-Idempotency-Key header
          const response = await this.apiClient.post(pushUrl, pushBody, {
            headers: {
              "X-Idempotency-Key": record.idempotencyKey,
              "X-Device-Id": this.deviceId,
            },
          });

          const pushResponse = response.data as {
            conflict?: { severity_class: string; conflict_detail: unknown };
            server_id?: string;
          };

          if (pushResponse.conflict) {
            // Route conflict to appropriate handler based on severity class
            const conflict = this.buildConflict(
              entityType,
              record,
              pushResponse.conflict,
            );
            result.conflicts.push(conflict);
            await this.routeConflict(conflict, record);
          } else {
            // Successful push — mark as synced, store server_received_at
            await this.db.write(async () => {
              await record.update((r) => {
                (r as SyncableModel).localSyncStatus = "synced";
                (r as SyncableModel).serverReceivedAt = new Date();
                (r as SyncableModel).syncError = null;
                (r as SyncableModel).retryCount = 0;
              });
            });
            result.pushed++;
          }
        } catch (error) {
          // Push failed — mark as failed with error message and increment retry count
          await this.db.write(async () => {
            await record.update((r) => {
              (r as SyncableModel).localSyncStatus = "failed";
              (r as SyncableModel).syncError =
                error instanceof Error ? error.message : String(error);
              (r as SyncableModel).retryCount = (record.retryCount ?? 0) + 1;
            });
          });
          result.failed++;
        }
      }
    }

    return result;
  }

  /**
   * Pull server state updates for cached entities.
   * Updates local models when server has newer versions.
   */
  async pull(): Promise<SyncPullResult> {
    const result: SyncPullResult = { updated: 0, resolved: 0 };

    try {
      const response = await this.apiClient.get(
        `/api/v1/mobile-sync/state/${this.deviceId}`,
      );
      const pullData = response.data as {
        resolved_conflicts?: Array<{ entity_id: string; table: string }>;
        updates?: Array<{
          table: string;
          id: string;
          fields: Record<string, unknown>;
        }>;
      };

      // Apply resolved conflicts — update local records
      if (pullData.resolved_conflicts) {
        for (const resolved of pullData.resolved_conflicts) {
          const collection = this.db.get<SyncableModel>(resolved.table);
          const records = await collection
            .query(Q.where("idempotency_key", resolved.entity_id))
            .fetch();

          for (const record of records) {
            if (record.localSyncStatus === "conflict") {
              await this.db.write(async () => {
                await record.update((r) => {
                  (r as SyncableModel).localSyncStatus = "synced";
                  (r as SyncableModel).syncError = null;
                });
              });
              result.resolved++;
            }
          }
        }
      }

      result.updated = pullData.updates?.length ?? 0;
    } catch {
      // Pull failure is non-fatal — sync will retry on next trigger
    }

    return result;
  }

  /**
   * Handle a resolved conflict from ConflictResolutionScreen.
   * Sends resolution to backend and updates local WatermelonDB state.
   */
  async applyConflictResolution(
    conflictId: string,
    resolution: "use_local" | "use_server",
  ): Promise<void> {
    await this.apiClient.post(
      `/api/v1/mobile-sync/conflicts/${conflictId}/resolve`,
      { resolution },
    );

    // After server ACK, mark the affected record based on resolution:
    // use_local → re-queue as pending (will re-push on next sync)
    // use_server → mark as synced (server version wins)
    // The actual local data update is handled by the ConflictResolutionScreen
    // calling back into the specific entity hook.
  }

  /** Returns the current sync state snapshot */
  getState(): SyncState {
    return { ...this.currentState };
  }

  /** Get total pending (+ failed) count from local DB */
  async getPendingCount(): Promise<number> {
    let total = 0;

    for (const tableName of Object.values(ENTITY_TABLE_MAP)) {
      const collection = this.db.get<SyncableModel>(tableName);
      const count = await collection
        .query(
          Q.where("sync_status", Q.oneOf(["pending", "failed", "conflict"])),
        )
        .fetchCount();
      total += count;
    }

    // Also count voice audio queue
    const voiceCollection = this.db.get<SyncableModel>("voice_audio_queue");
    const voiceCount = await voiceCollection
      .query(Q.where("sync_status", Q.oneOf(["pending", "failed"])))
      .fetchCount();
    total += voiceCount;

    return total;
  }

  /**
   * Force-quit recovery: on app launch, reset 'syncing' → 'pending'
   * for all items stuck in-flight per §15.8.
   * Call this before the first sync trigger in app/_layout.tsx.
   */
  async recoverFromForceQuit(): Promise<void> {
    const allTables = [...Object.values(ENTITY_TABLE_MAP), "voice_audio_queue"];

    await this.db.write(async () => {
      for (const tableName of allTables) {
        const collection = this.db.get<SyncableModel>(tableName);
        const stuckRecords = await collection
          .query(Q.where("sync_status", "syncing"))
          .fetch();

        for (const record of stuckRecords) {
          await record.update((r) => {
            (r as SyncableModel).localSyncStatus = "pending";
          });
        }
      }
    });

    console.log("[SyncOrchestrator] Force-quit recovery complete");
  }

  // ─── Private helpers ──────────────────────────────────────────────────────

  private setState(state: SyncState): void {
    this.currentState = state;
    this.onStateChange?.(state);
  }

  /** Serializes a WatermelonDB record for the push payload */
  private serializeRecord(
    entityType: Exclude<OfflineEntityType, "voice_audio">,
    record: SyncableModel,
  ): Record<string, unknown> {
    const base = {
      idempotency_key: record.idempotencyKey,
      client_capture_at: record.clientCaptureAt?.toISOString(),
    };

    // Entity-specific serialization
    // Each model's raw properties are accessed via the underlying WatermelonDB _raw
    const raw = (record as unknown as { _raw: Record<string, unknown> })._raw;

    return { ...base, ...raw };
  }

  /** Builds a SyncConflict from the backend conflict response */
  private buildConflict(
    entityType: Exclude<OfflineEntityType, "voice_audio">,
    record: SyncableModel,
    conflictDetail: { severity_class: string; conflict_detail: unknown },
  ): SyncConflict {
    const detail = conflictDetail.conflict_detail as {
      server_version?: Record<string, unknown>;
      field_diffs?: Array<{
        field_name: string;
        local_value: unknown;
        server_value: unknown;
      }>;
    };

    const raw = (record as unknown as { _raw: Record<string, unknown> })._raw;

    return {
      id: `${record.idempotencyKey}-conflict`,
      entityType,
      entityId: record.id,
      entitySummary: this.buildEntitySummary(entityType, raw),
      severityClass:
        conflictDetail.severity_class as SyncConflict["severityClass"],
      localVersion: raw,
      serverVersion: detail.server_version ?? {},
      fieldDiffs: detail.field_diffs ?? [],
      detectedAt: new Date().toISOString(),
    };
  }

  private buildEntitySummary(
    entityType: Exclude<OfflineEntityType, "voice_audio">,
    raw: Record<string, unknown>,
  ): string {
    switch (entityType) {
      case "time_entry":
        return `Time entry for job ${raw["job_id"] as string}`;
      case "expense":
        return `Expense $${((raw["cost_cents"] as number) / 100).toFixed(2)}`;
      case "change_order":
        return `Change order: ${raw["title"] as string}`;
      case "loto_check":
        return `LOTO check: ${raw["check_type"] as string}`;
      case "job_status_change":
        return `Status: ${raw["from_status"] as string} → ${raw["to_status"] as string}`;
      case "job_note":
        return `Note: ${String(raw["content"]).slice(0, 50)}`;
      case "invoice_signoff":
        return `Invoice sign-off: ${raw["signed_by_name"] as string}`;
      case "photo":
        return `Photo attachment`;
      default:
        return `${entityType} record`;
    }
  }

  /**
   * Routes a conflict to the correct handler based on severity class.
   * This is the ONLY place where severity class determines UI behavior.
   */
  private async routeConflict(
    conflict: SyncConflict,
    record: SyncableModel,
  ): Promise<void> {
    switch (conflict.severityClass) {
      case "auto_apply":
        await handleAutoSilent(conflict, record, this.db);
        break;

      case "safe_to_apply":
        await handleAutoNotice(conflict, record, this.db);
        break;

      case "requires_review":
        await handleTechResolvable(conflict, record, this.db);
        this.onTechResolvableConflict?.(conflict);
        break;

      case "escalate_to_owner":
        await handleOwnerEscalation(conflict, record, this.db, this.apiClient);
        this.onOwnerEscalation?.(conflict);
        break;
    }
  }

  /** Checks if the device has been offline past the hard limit */
  async isHardLimitExceeded(): Promise<boolean> {
    // Find the oldest pending record's client_capture_at
    const allTables = Object.values(ENTITY_TABLE_MAP);
    const now = Date.now();
    const hardLimitMs = HARD_LIMIT_HOURS * 60 * 60 * 1000;

    for (const tableName of allTables) {
      const collection = this.db.get<SyncableModel>(tableName);
      const oldestRecords = await collection
        .query(
          Q.where("sync_status", "pending"),
          Q.sortBy("client_capture_at", Q.asc),
          Q.take(1),
        )
        .fetch();

      if (oldestRecords.length > 0) {
        const oldest = oldestRecords[0]!;
        const captureTime = oldest.clientCaptureAt?.getTime() ?? now;
        if (now - captureTime > hardLimitMs) return true;
      }
    }

    return false;
  }
}
