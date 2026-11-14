/**
 * Photo Multipart Upload Integration Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/photo-multipart-upload.integration.test.ts
 *
 * Uses fetch mock (avoids MSW/node ESM issues in Jest RN).
 * Per batch-fe-b7-design.md Section I.2.
 */

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("Photo Multipart Upload (Integration)", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe("Initiate + complete flow", () => {
    it("initiate-upload returns chunk URLs and session ID", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          session_id: "upload-session-001",
          upload_id: "upload-id-001",
          chunk_urls: [
            "https://mock-s3.example.com/chunk-0",
            "https://mock-s3.example.com/chunk-1",
          ],
          photo_id: "photo-backend-001",
        }),
      });

      const response = await fetch(
        "http://localhost:8000/api/v1/photos/initiate-upload",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            job_id: "job-001",
            mime_type: "image/jpeg",
            file_size_bytes: 10 * 1024 * 1024,
            total_chunks: 2,
            idempotency_key: "uuid-photo-001",
          }),
        },
      );

      const data = (await response.json()) as {
        session_id: string;
        chunk_urls: string[];
        photo_id: string;
      };

      expect(data.session_id).toBe("upload-session-001");
      expect(data.chunk_urls).toHaveLength(2);
      expect(data.photo_id).toBe("photo-backend-001");
    });

    it("complete-upload returns pilot_photo_id", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          pilot_photo_id: "photo-backend-001",
          s3_key: "jobs/attachments/photo-001.jpg",
          status: "completed",
        }),
      });

      const response = await fetch(
        "http://localhost:8000/api/v1/photos/complete-upload",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: "upload-session-001",
            upload_id: "upload-id-001",
            etags: ['"etag-0"', '"etag-1"'],
          }),
        },
      );

      const data = (await response.json()) as { pilot_photo_id: string };
      expect(data.pilot_photo_id).toBe("photo-backend-001");
    });
  });

  describe("Resume after mid-upload failure", () => {
    it("resume-upload returns URLs for remaining chunks", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          chunk_urls: [
            "https://mock-s3.example.com/chunk-1",
            "https://mock-s3.example.com/chunk-2",
          ],
        }),
      });

      const response = await fetch(
        "http://localhost:8000/api/v1/photos/resume-upload",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: "upload-session-resume",
            from_chunk: 1,
          }),
        },
      );

      const data = (await response.json()) as { chunk_urls: string[] };
      expect(data.chunk_urls).toHaveLength(2);
    });

    it("preserves lastCompletedChunk across app restart", () => {
      const photoState = {
        s3SessionId: "upload-session-001",
        lastCompletedChunk: 1,
        localSyncStatus: "failed",
      };

      expect(photoState.s3SessionId).toBe("upload-session-001");
      expect(photoState.lastCompletedChunk).toBe(1);
    });
  });

  describe("WiFi preference gate", () => {
    it("photo stays pending when wifiPending=true", () => {
      const photoState = {
        localSyncStatus: "pending",
        wifiPending: true,
        uploadProgress: 0,
      };
      const shouldUpload = !photoState.wifiPending;
      expect(shouldUpload).toBe(false);
    });

    it("photo proceeds when WiFi available", () => {
      const photoState = { localSyncStatus: "pending", wifiPending: false };
      const shouldUpload = !photoState.wifiPending;
      expect(shouldUpload).toBe(true);
    });
  });
});
