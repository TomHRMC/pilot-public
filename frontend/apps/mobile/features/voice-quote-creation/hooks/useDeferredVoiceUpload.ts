/**
 * useDeferredVoiceUpload — offline voice queue (FE-B7: WatermelonDB-backed)
 *
 * Location: apps/mobile/features/voice-quote-creation/hooks/useDeferredVoiceUpload.ts
 *
 * FE-B7 UPGRADE: Persistence has been upgraded from AsyncStorage to WatermelonDB.
 * The public API is UNCHANGED per design doc §G.7 — callers from FE-B3 are unaffected.
 *
 * Public API (unchanged from FE-B3 stub):
 *   queuedAudio   — list of items in the queue (from WatermelonDB)
 *   enqueue()     — add an audio item to the persistent queue
 *   uploadWhenOnline() — trigger upload of all pending items; called by SyncOrchestrator
 *   uploadStatus  — current upload status
 *   clearQueue()  — remove all items from queue
 *
 * SyncOrchestrator.push('voice_audio') calls uploadWhenOnline() on reconnect.
 * The FE-B3 voice session shell continues to call enqueue() — no changes needed.
 *
 * Per batch-fe-b7-design.md §G.7 and Section A.2.3.
 */

import { useCallback, useEffect, useState } from "react";
import { database } from "../../../database";
import {
  queueVoiceAudio,
  uploadPendingVoiceAudio,
  getPendingVoiceCount,
  clearVoiceQueue,
} from "../../../database/sync/voice-upload";
import type { VoiceAudioQueue } from "../../../database/models/VoiceAudioQueue";
import { apiClient } from "@pilot/shared-api";

interface QueuedAudioItem {
  id: string;
  sessionId: string;
  audioPath: string;
  capturedAt: string;
  idempotencyKey: string;
}

type UploadStatus = "idle" | "uploading" | "completed" | "failed";

interface UseDeferredVoiceUploadReturn {
  queuedAudio: QueuedAudioItem[];
  enqueue: (item: Omit<QueuedAudioItem, "id" | "capturedAt">) => Promise<void>;
  uploadWhenOnline: () => Promise<void>;
  uploadStatus: UploadStatus;
  clearQueue: () => Promise<void>;
}

/** Converts WatermelonDB VoiceAudioQueue record to the public QueuedAudioItem shape */
function toQueuedAudioItem(record: VoiceAudioQueue): QueuedAudioItem {
  return {
    id: record.id,
    sessionId: record.sessionId,
    audioPath: record.audioPath,
    capturedAt: record.capturedAt,
    idempotencyKey: record.idempotencyKey,
  };
}

export function useDeferredVoiceUpload(): UseDeferredVoiceUploadReturn {
  const [queuedAudio, setQueuedAudio] = useState<QueuedAudioItem[]>([]);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");

  // Load queue from WatermelonDB on mount
  useEffect(() => {
    const collection = database.get<VoiceAudioQueue>("voice_audio_queue");
    const subscription = collection
      .query()
      .observe()
      .subscribe((records) => {
        setQueuedAudio(records.map(toQueuedAudioItem));
      });

    return () => subscription.unsubscribe();
  }, []);

  const enqueue = useCallback(
    async (item: Omit<QueuedAudioItem, "id" | "capturedAt">) => {
      await queueVoiceAudio(database, {
        sessionId: item.sessionId,
        audioPath: item.audioPath,
        capturedAt: new Date(),
        idempotencyKey: item.idempotencyKey,
      });
      // State updates via WatermelonDB observable subscription above
    },
    [],
  );

  const uploadWhenOnline = useCallback(async () => {
    const pendingCount = await getPendingVoiceCount(database);
    if (pendingCount === 0) return;

    setUploadStatus("uploading");

    const boundApiClient = {
      post: async (
        url: string,
        data: unknown,
        options?: { headers?: Record<string, string> },
      ) => {
        const response = await (
          apiClient as unknown as {
            post: (
              url: string,
              data: unknown,
              config?: unknown,
            ) => Promise<{ data: unknown }>;
          }
        ).post(url, data, { headers: options?.headers });
        return response;
      },
    };

    const result = await uploadPendingVoiceAudio(database, boundApiClient);
    setUploadStatus(result.failed === 0 ? "completed" : "failed");
  }, []);

  const clearQueueFn = useCallback(async () => {
    await clearVoiceQueue(database);
    setUploadStatus("idle");
  }, []);

  return {
    queuedAudio,
    enqueue,
    uploadWhenOnline,
    uploadStatus,
    clearQueue: clearQueueFn,
  };
}
