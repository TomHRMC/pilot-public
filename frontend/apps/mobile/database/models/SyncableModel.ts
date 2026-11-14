/**
 * SyncableModel — Abstract base class for all offline-capable WatermelonDB models
 *
 * Location: apps/mobile/database/models/SyncableModel.ts
 *
 * IMPORTANT: WatermelonDB's Model base class has a built-in `syncStatus` property
 * used by its internal sync engine. Since we use a CUSTOM SyncOrchestrator (NOT
 * WatermelonDB's built-in sync), we name our field `localSyncStatus` to avoid
 * the type collision.
 *
 * DB column name remains `sync_status` — the TypeScript accessor is `localSyncStatus`.
 *
 * Per batch-fe-b7-design.md Section F.5 and §11.2 custom sync requirement.
 */

import { Model } from "@nozbe/watermelondb";
import { field, date, readonly } from "@nozbe/watermelondb/decorators";

export type LocalSyncStatus =
  | "pending"
  | "syncing"
  | "synced"
  | "failed"
  | "conflict";

export abstract class SyncableModel extends Model {
  /**
   * Our custom sync lifecycle state.
   * Named `localSyncStatus` (not `syncStatus`) to avoid WatermelonDB built-in type conflict.
   * DB column: `sync_status`
   */
  @field("sync_status") declare localSyncStatus: LocalSyncStatus;

  /** UUID v4 generated at capture time; sent as X-Idempotency-Key header; never changes */
  @field("idempotency_key") declare idempotencyKey: string;

  /** Last sync error message; populated on push failure */
  @field("sync_error") declare syncError: string | null;

  /** Incremented on each failed push attempt; used for exponential backoff */
  @field("retry_count") declare retryCount: number;

  /** Unix ms timestamp at device capture time; preserved across sync boundary */
  @date("client_capture_at") declare clientCaptureAt: Date;

  /** Populated after successful push; undefined until synced */
  @date("server_received_at") declare serverReceivedAt: Date | undefined;

  @readonly @date("created_at") declare createdAt: Date;
}

// Re-export for convenience
export type { LocalSyncStatus as SyncStatus };
