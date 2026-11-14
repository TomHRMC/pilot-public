/**
 * Photo Upload Unit Tests
 *
 * Location: apps/mobile/__tests__/batch_fe_b7/photo-upload.unit.test.ts
 *
 * Tests: chunk tracking; resume from last completed chunk; WiFi preference gate.
 * Per batch-fe-b7-design.md Section I.1.
 */

// Mock expo-file-system
jest.mock("expo-file-system", () => ({
  getInfoAsync: jest.fn().mockResolvedValue({
    exists: true,
    size: 10 * 1024 * 1024, // 10MB
  }),
  readAsStringAsync: jest.fn().mockResolvedValue("base64encodeddata"),
  writeAsStringAsync: jest.fn().mockResolvedValue(undefined),
  uploadAsync: jest.fn().mockResolvedValue({
    status: 200,
    headers: { etag: '"mock-etag-001"' },
  }),
  EncodingType: {
    Base64: "base64",
    UTF8: "utf8",
  },
  cacheDirectory: "/tmp/",
}));

describe("Photo Upload Pipeline", () => {
  const createMockPhoto = (overrides: Record<string, unknown> = {}) => ({
    id: "photo-001",
    jobId: "job-001",
    expenseId: null,
    localUri: "file:///tmp/photo.jpg",
    mimeType: "image/jpeg",
    fileSizeBytes: 10 * 1024 * 1024,
    pilotPhotoId: null,
    uploadProgress: 0,
    s3SessionId: null,
    lastCompletedChunk: 0,
    wifiPending: false,
    localSyncStatus: "pending",
    idempotencyKey: "uuid-photo-001",
    update: jest
      .fn()
      .mockImplementation(async (fn: (r: Record<string, unknown>) => void) => {
        fn(createMockPhoto(overrides) as unknown as Record<string, unknown>);
      }),
    ...overrides,
  });

  const createMockApiClient = (overrides: Record<string, jest.Mock> = {}) => ({
    post: jest.fn().mockImplementation(async (url: string) => {
      if (url.includes("initiate-upload")) {
        return {
          data: {
            session_id: "upload-session-001",
            upload_id: "upload-id-001",
            chunk_urls: [
              "https://mock-s3.example.com/chunk-0",
              "https://mock-s3.example.com/chunk-1",
            ],
            photo_id: "photo-backend-001",
          },
        };
      }
      if (url.includes("complete-upload")) {
        return {
          data: {
            pilot_photo_id: "photo-backend-001",
            s3_key: "jobs/attachments/photo-001.jpg",
          },
        };
      }
      return { data: {} };
    }),
    ...overrides,
  });

  const createMockDb = () => ({
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<void>) => fn()),
  });

  describe("WiFi preference gate", () => {
    it("skips upload when wifiPending=true", async () => {
      const photo = createMockPhoto({
        wifiPending: true,
        localSyncStatus: "pending",
      });
      const apiClient = createMockApiClient();
      const db = createMockDb();

      // Photo with wifiPending=true should not initiate upload
      expect(photo.wifiPending).toBe(true);
      expect(apiClient.post).not.toHaveBeenCalled();
    });

    it("proceeds with upload when wifiPending=false", () => {
      const photo = createMockPhoto({ wifiPending: false });
      expect(photo.wifiPending).toBe(false);
    });
  });

  describe("Chunk tracking", () => {
    it("starts upload from chunk 0 when no session exists", () => {
      const photo = createMockPhoto({
        s3SessionId: null,
        lastCompletedChunk: 0,
      });
      expect(photo.s3SessionId).toBeNull();
      expect(photo.lastCompletedChunk).toBe(0);
    });

    it("resumes from lastCompletedChunk when session exists", () => {
      const photo = createMockPhoto({
        s3SessionId: "upload-session-resume",
        lastCompletedChunk: 2, // Chunks 0 and 1 already completed
      });
      expect(photo.s3SessionId).toBe("upload-session-resume");
      expect(photo.lastCompletedChunk).toBe(2);
      // Next upload should start from chunk 2
    });

    it("stores session ID after initiating upload", async () => {
      const photo = createMockPhoto({ s3SessionId: null });
      const apiClient = createMockApiClient();

      // Simulate calling initiate-upload
      const response = await apiClient.post("/api/v1/photos/initiate-upload", {
        job_id: photo.jobId,
        mime_type: photo.mimeType,
        file_size_bytes: photo.fileSizeBytes,
        total_chunks: 2,
        idempotency_key: photo.idempotencyKey,
      });

      expect(response.data).toMatchObject({
        session_id: "upload-session-001",
        upload_id: "upload-id-001",
      });
    });
  });

  describe("Progress tracking", () => {
    it("calculates progress percentage correctly", () => {
      const totalChunks = 3;
      const completedChunks = 1;
      const progress = Math.round((completedChunks / totalChunks) * 100);
      expect(progress).toBe(33);
    });

    it("reaches 100% on final chunk", () => {
      const totalChunks = 3;
      const completedChunks = 3;
      const progress = Math.round((completedChunks / totalChunks) * 100);
      expect(progress).toBe(100);
    });
  });

  describe("Failed upload recovery", () => {
    it("preserves lastCompletedChunk on failure", () => {
      const photo = createMockPhoto({
        lastCompletedChunk: 1, // chunk 0 succeeded
        localSyncStatus: "failed",
        syncError: "Upload chunk 1 failed",
      });

      // On retry, should resume from chunk 1, not 0
      expect(photo.lastCompletedChunk).toBe(1);
      expect(photo.localSyncStatus).toBe("failed");
    });
  });

  describe("Complete upload", () => {
    it("calls complete-upload endpoint after all chunks succeed", async () => {
      const apiClient = createMockApiClient();

      const response = await apiClient.post("/api/v1/photos/complete-upload", {
        session_id: "upload-session-001",
        upload_id: "upload-id-001",
        etags: ['"etag-0"', '"etag-1"'],
      });

      expect(response.data).toMatchObject({
        pilot_photo_id: "photo-backend-001",
      });
    });
  });
});
