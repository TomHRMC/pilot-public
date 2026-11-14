/**
 * MSW Photo Upload Handlers — Mobile unit/integration test mocks
 *
 * Location: apps/mobile/mocks/handlers/photos.ts
 *
 * Provides mock responses for S3 multipart photo upload endpoints.
 *
 * Per batch-fe-b7-design.md Section D.
 */

import { http, HttpResponse } from "msw";

const BASE_URL = "http://localhost:8000";

export const photoHandlers = [
  // POST /api/v1/photos/initiate-upload — start multipart upload
  http.post(
    `${BASE_URL}/api/v1/photos/initiate-upload`,
    async ({ request }) => {
      const body = (await request.json()) as { total_chunks?: number };
      const totalChunks = body.total_chunks ?? 1;

      // Generate mock presigned URLs for each chunk
      const chunkUrls = Array.from(
        { length: totalChunks },
        (_, i) =>
          `https://mock-s3.example.com/bucket/upload?chunk=${i}&token=mock-token`,
      );

      return HttpResponse.json({
        session_id: `upload-session-${Date.now()}`,
        upload_id: `upload-id-${Date.now()}`,
        chunk_urls: chunkUrls,
        photo_id: `photo-${Date.now()}`,
      });
    },
  ),

  // POST /api/v1/photos/complete-upload — finalize multipart upload
  http.post(`${BASE_URL}/api/v1/photos/complete-upload`, () => {
    return HttpResponse.json({
      pilot_photo_id: `photo-${Date.now()}`,
      s3_key: `jobs/attachments/photo-${Date.now()}.jpg`,
      status: "completed",
    });
  }),

  // POST /api/v1/photos/resume-upload — get remaining chunk URLs
  http.post(`${BASE_URL}/api/v1/photos/resume-upload`, async ({ request }) => {
    const body = (await request.json()) as { from_chunk?: number };
    const fromChunk = body.from_chunk ?? 0;
    const remainingChunks = 3 - fromChunk;

    const chunkUrls = Array.from(
      { length: remainingChunks },
      (_, i) =>
        `https://mock-s3.example.com/bucket/upload?chunk=${fromChunk + i}&token=mock-resume-token`,
    );

    return HttpResponse.json({
      chunk_urls: chunkUrls,
    });
  }),
];
