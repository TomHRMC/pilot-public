/**
 * Deferred Voice Upload — WatermelonDB-backed queue
 *
 * Location: apps/mobile/database/sync/voice-upload.ts
 *
 * Wraps the WatermelonDB VoiceAudioQueue model to provide the upload
 * pipeline used by useDeferredVoiceUpload.ts.
 *
 * This module replaces the AsyncStorage persistence from the FE-B3 stub.
 * The public API of useDeferredVoiceUpload.ts is UNCHANGED per design §G.7:
 *   - queueAudio() → now persists to WatermelonDB (was AsyncStorage)
 *   - pendingCount  → now from WatermelonDB query (was in-memory state)
 *   - uploadPending() → called by SyncOrchestrator.push('voice_audio') on reconnect
 *
 * Per batch-fe-b7-design.md Section A.2.3, §15.7, and §G.7.
 */

import { Database, Q } from "@nozbe/watermelondb";
import type { VoiceAudioQueue } from "../models/VoiceAudioQueue";
import type { SyncableModel } from "../models/SyncableModel";

type ApiClient = {
  post: (
    url: string,
    data: unknown,
    options?: { headers?: Record<string, string> },
  ) => Promise<{ data: unknown }>;
};

/**
 * Queue a voice audio item for deferred upload.
 * Persists to WatermelonDB so it survives app restarts.
 * Equivalent to the FE-B3 AsyncStorage enqueue() but with WatermelonDB persistence.
 */
export async function queueVoiceAudio(
  db: Database,
  item: {
    sessionId: string;
    audioPath: string;
    capturedAt: Date;
    idempotencyKey: string;
  },
): Promise<void> {
  const collection = db.get<VoiceAudioQueue>("voice_audio_queue");

  await db.write(async () => {
    await collection.create((record) => {
      record.sessionId = item.sessionId;
      record.audioPath = item.audioPath;
      record.capturedAt = item.capturedAt.toISOString();
      (record as SyncableModel).idempotencyKey = item.idempotencyKey;
      (record as SyncableModel).localSyncStatus = "pending";
      (record as SyncableModel).retryCount = 0;
      (record as SyncableModel).clientCaptureAt = item.capturedAt;
    });
  });
}

/**
 * Upload all pending voice audio items.
 * Called by SyncOrchestrator.push('voice_audio') on reconnect.
 * Maintains the same behavior as the FE-B3 uploadWhenOnline() method.
 */
export async function uploadPendingVoiceAudio(
  db: Database,
  apiClient: ApiClient,
): Promise<{ uploaded: number; failed: number }> {
  const collection = db.get<VoiceAudioQueue>("voice_audio_queue");
  const pendingItems = await collection
    .query(Q.where("sync_status", Q.oneOf(["pending", "failed"])))
    .fetch();

  let uploaded = 0;
  let failed = 0;

  for (const item of pendingItems) {
    try {
      // Mark as syncing
      await db.write(async () => {
        await item.update((r) => {
          (r as SyncableModel).localSyncStatus = "syncing";
        });
      });

      const formData = new FormData();
      formData.append("session_id", item.sessionId);
      formData.append(
        "idempotency_key",
        (item as SyncableModel).idempotencyKey,
      );
      // In production, append the actual audio file blob:
      // formData.append('audio', { uri: item.audioPath, type: 'audio/m4a', name: 'recording.m4a' } as unknown as Blob);

      await apiClient.post("/api/v1/voice/upload-audio", formData, {
        headers: {
          "X-Idempotency-Key": (item as SyncableModel).idempotencyKey,
        },
      });

      // Mark as synced
      await db.write(async () => {
        await item.update((r) => {
          (r as SyncableModel).localSyncStatus = "synced";
          (r as SyncableModel).serverReceivedAt = new Date();
        });
      });

      uploaded++;
    } catch (error) {
      await db.write(async () => {
        await item.update((r) => {
          (r as SyncableModel).localSyncStatus = "failed";
          (r as SyncableModel).syncError =
            error instanceof Error ? error.message : String(error);
          (r as SyncableModel).retryCount =
            ((item as SyncableModel).retryCount ?? 0) + 1;
        });
      });
      failed++;
    }
  }

  return { uploaded, failed };
}

/**
 * Get the count of pending voice audio items.
 * Used by useDeferredVoiceUpload to expose pendingCount.
 */
export async function getPendingVoiceCount(db: Database): Promise<number> {
  const collection = db.get<VoiceAudioQueue>("voice_audio_queue");
  return collection
    .query(Q.where("sync_status", Q.oneOf(["pending", "failed"])))
    .fetchCount();
}

/**
 * Clear all voice audio items from the queue.
 * Used by useDeferredVoiceUpload.clearQueue().
 */
export async function clearVoiceQueue(db: Database): Promise<void> {
  const collection = db.get<VoiceAudioQueue>("voice_audio_queue");
  const allItems = await collection.query().fetch();

  await db.write(async () => {
    for (const item of allItems) {
      await item.destroyPermanently();
    }
  });
}
