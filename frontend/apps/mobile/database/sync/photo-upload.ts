/**
 * Photo Upload Pipeline — S3 Multipart Resumable Upload
 *
 * Location: apps/mobile/database/sync/photo-upload.ts
 *
 * Photos use S3 multipart upload, NOT the sync orchestrator push loop.
 * This pipeline:
 *   1. Reads local photo file via expo-file-system
 *   2. Calls POST /api/v1/photos/initiate-upload → gets presigned chunk URLs + session ID
 *   3. Uploads each chunk directly to S3 via the presigned URLs
 *   4. Tracks progress in WatermelonDB (upload_progress, last_completed_chunk)
 *   5. On failure: resumes from last_completed_chunk on next attempt
 *   6. On success: calls POST /api/v1/photos/complete-upload → backend finalizes multipart
 *
 * WiFi preference: if photo_upload_wifi_only=true and device is on cellular,
 * photo stays 'pending' with wifi_pending=true. Upload starts when WiFi connects.
 *
 * Per batch-fe-b7-design.md Section A.2.3, §15.5, and Section A.3.4.
 */

// expo-file-system v19 moved legacy APIs (EncodingType, FileSystemUploadType,
// readAsStringAsync, uploadAsync) to the /legacy sub-path.
// Use /legacy to preserve the v17 API surface without rewriting the upload logic.
import * as FileSystem from "expo-file-system/legacy";
import { Database, Q } from "@nozbe/watermelondb";
import type { Photo } from "../models/Photo";
import type { SyncableModel } from "../models/SyncableModel";

/** S3 chunk size — 5MB per AWS S3 multipart minimum */
const CHUNK_SIZE_BYTES = 5 * 1024 * 1024;

type ApiClient = {
  post: (
    url: string,
    data: unknown,
    options?: Record<string, unknown>,
  ) => Promise<{ data: unknown }>;
};

interface InitiateUploadResponse {
  session_id: string;
  upload_id: string;
  chunk_urls: string[]; // Pre-signed S3 URLs, one per chunk
  photo_id: string; // Backend-assigned photo ID
}

interface CompleteUploadResponse {
  pilot_photo_id: string;
  s3_key: string;
}

/**
 * Uploads a single photo using S3 multipart, with resume capability.
 * Updates WatermelonDB with progress on each chunk.
 */
export async function uploadPhoto(
  photo: Photo,
  db: Database,
  apiClient: ApiClient,
  onProgress?: (progress: number) => void,
): Promise<void> {
  // Check WiFi preference gate
  if (photo.wifiPending) {
    console.log(`[PhotoUpload] Photo ${photo.id} held pending WiFi`);
    return;
  }

  // Get file info
  const fileInfo = await FileSystem.getInfoAsync(photo.localUri);
  if (!fileInfo.exists) {
    await db.write(async () => {
      await photo.update((p) => {
        (p as SyncableModel).localSyncStatus = "failed";
        (p as SyncableModel).syncError = "Local file not found";
      });
    });
    return;
  }

  const fileSize = fileInfo.size ?? photo.fileSizeBytes;
  const totalChunks = Math.ceil(fileSize / CHUNK_SIZE_BYTES);

  // Mark as syncing
  await db.write(async () => {
    await photo.update((p) => {
      (p as SyncableModel).localSyncStatus = "syncing";
    });
  });

  try {
    let sessionId = photo.s3SessionId;
    let chunkUrls: string[] = [];
    let startChunk = photo.lastCompletedChunk; // Resume from last completed chunk

    // If no session yet, initiate a new multipart upload
    if (!sessionId) {
      const initResponse = await apiClient.post(
        "/api/v1/photos/initiate-upload",
        {
          job_id: photo.jobId,
          expense_id: photo.expenseId,
          mime_type: photo.mimeType,
          file_size_bytes: fileSize,
          total_chunks: totalChunks,
          idempotency_key: (photo as SyncableModel).idempotencyKey,
        },
      );

      const initData = initResponse.data as InitiateUploadResponse;
      sessionId = initData.session_id;
      chunkUrls = initData.chunk_urls;
      startChunk = 0;

      // Persist session ID to WatermelonDB for resume capability
      await db.write(async () => {
        await photo.update((p) => {
          p.s3SessionId = sessionId!;
          p.lastCompletedChunk = 0;
        });
      });
    } else {
      // Resume: re-request chunk URLs for remaining chunks
      const resumeResponse = await apiClient.post(
        "/api/v1/photos/resume-upload",
        {
          session_id: sessionId,
          from_chunk: startChunk,
        },
      );
      chunkUrls = (resumeResponse.data as { chunk_urls: string[] }).chunk_urls;
    }

    // Upload chunks from startChunk onwards
    const etags: string[] = [];

    for (let chunkIndex = startChunk; chunkIndex < totalChunks; chunkIndex++) {
      const chunkStart = chunkIndex * CHUNK_SIZE_BYTES;
      const chunkEnd = Math.min(chunkStart + CHUNK_SIZE_BYTES, fileSize);
      const chunkUrl = chunkUrls[chunkIndex - startChunk];

      if (!chunkUrl) {
        throw new Error(`Missing presigned URL for chunk ${chunkIndex}`);
      }

      // Read chunk from local file using expo-file-system
      const chunkBase64 = await FileSystem.readAsStringAsync(photo.localUri, {
        encoding: FileSystem.EncodingType.Base64,
        position: chunkStart,
        length: chunkEnd - chunkStart,
      });

      // Upload chunk directly to S3 via presigned URL
      const uploadResult = await FileSystem.uploadAsync(
        chunkUrl,
        photo.localUri,
        {
          uploadType: FileSystem.FileSystemUploadType.BINARY_CONTENT,
          httpMethod: "PUT",
          headers: {
            "Content-Type": photo.mimeType,
            "Content-Range": `bytes ${chunkStart}-${chunkEnd - 1}/${fileSize}`,
          },
        },
      );

      if (uploadResult.status !== 200 && uploadResult.status !== 201) {
        throw new Error(
          `Chunk ${chunkIndex} upload failed: HTTP ${uploadResult.status}`,
        );
      }

      // Extract ETag from response headers for multipart completion
      const etag =
        uploadResult.headers["etag"] ??
        uploadResult.headers["ETag"] ??
        `chunk-${chunkIndex}`;
      etags.push(etag);

      // Update progress in WatermelonDB after each successful chunk
      const progress = Math.round(((chunkIndex + 1) / totalChunks) * 100);
      await db.write(async () => {
        await photo.update((p) => {
          p.lastCompletedChunk = chunkIndex + 1;
          p.uploadProgress = progress;
        });
      });

      onProgress?.(progress);

      // Suppress unused variable warning
      void chunkBase64;
    }

    // All chunks uploaded — complete the multipart upload
    const completeResponse = await apiClient.post(
      "/api/v1/photos/complete-upload",
      {
        session_id: sessionId,
        upload_id: sessionId, // S3 upload ID same as session for this API
        etags,
      },
    );

    const completeData = completeResponse.data as CompleteUploadResponse;

    // Mark as synced and store backend photo ID
    await db.write(async () => {
      await photo.update((p) => {
        (p as SyncableModel).localSyncStatus = "synced";
        (p as SyncableModel).serverReceivedAt = new Date();
        p.pilotPhotoId = completeData.pilot_photo_id;
        p.uploadProgress = 100;
        p.s3SessionId = null;
      });
    });
  } catch (error) {
    // Upload failed — mark as failed but PRESERVE lastCompletedChunk for resume
    await db.write(async () => {
      await photo.update((p) => {
        (p as SyncableModel).localSyncStatus = "failed";
        (p as SyncableModel).syncError =
          error instanceof Error ? error.message : String(error);
        // Do NOT reset lastCompletedChunk — resume from here next time
      });
    });
    throw error;
  }
}

/**
 * Processes all pending photo uploads in the database.
 * Called by the sync provider when connectivity is available.
 */
export async function uploadPendingPhotos(
  db: Database,
  apiClient: ApiClient,
  options: { wifiOnly: boolean; isWifi: boolean } = {
    wifiOnly: false,
    isWifi: true,
  },
): Promise<void> {
  const photosCollection = db.get<Photo>("photos");
  const pendingPhotos = await photosCollection
    .query(
      Q.where("sync_status", Q.oneOf(["pending", "failed"])),
      Q.where("wifi_pending", false),
    )
    .fetch();

  // If WiFi-only setting is on and we're not on WiFi, update all pending to wifi_pending
  if (options.wifiOnly && !options.isWifi) {
    await db.write(async () => {
      for (const photo of pendingPhotos) {
        await photo.update((p) => {
          p.wifiPending = true;
        });
      }
    });
    return;
  }

  // If WiFi just connected, clear wifi_pending flag on all WiFi-held photos
  if (options.isWifi) {
    const wifiHeldPhotos = await photosCollection
      .query(Q.where("wifi_pending", true))
      .fetch();

    await db.write(async () => {
      for (const photo of wifiHeldPhotos) {
        await photo.update((p) => {
          p.wifiPending = false;
        });
      }
    });
  }

  // Upload each pending photo
  for (const photo of pendingPhotos) {
    try {
      await uploadPhoto(photo, db, apiClient);
    } catch {
      // Individual photo failure is non-fatal; continue with remaining photos
    }
  }
}
