/**
 * useCreateInvoiceSignoff unit tests
 *
 * Location: apps/mobile/features/offline-sync/hooks/__tests__/useCreateInvoiceSignoff.test.tsx
 *
 * Tests:
 *   - Local write sets localSyncStatus "pending" + idempotencyKey + clientCaptureAt
 *   - Returns the created record
 *   - Error state on DB failure
 */

import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCreateInvoiceSignoff } from "../useCreateInvoiceSignoff";

// ── Mock WatermelonDB ─────────────────────────────────────────────────────────

const mockCreate = jest.fn();
const mockRecord: Record<string, unknown> = {};

jest.mock("../../../../database", () => ({
  database: {
    write: jest.fn(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn: (record: unknown) => void) => {
        fn(mockRecord);
        return Promise.resolve(mockRecord);
      }),
    })),
  },
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

const INPUT = {
  invoiceId: "invoice-test-001",
  signedByName: "John Smith",
  termsAcknowledged: true as const,
  signaturePngBase64: "iVBORw0KGgo=",
  capturedBy: "tech-user-001",
};

describe("useCreateInvoiceSignoff", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset the mock record
    Object.keys(mockRecord).forEach((k) => delete mockRecord[k]);
  });

  it("writes a local record with localSyncStatus pending + idempotencyKey + clientCaptureAt", async () => {
    const { result } = renderHook(() => useCreateInvoiceSignoff(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.create(INPUT);
    });

    expect(mockRecord.localSyncStatus).toBe("pending");
    expect(mockRecord.idempotencyKey).toBeTruthy();
    expect(typeof mockRecord.idempotencyKey).toBe("string");
    expect(mockRecord.clientCaptureAt).toBeInstanceOf(Date);
    expect(mockRecord.invoiceId).toBe(INPUT.invoiceId);
    expect(mockRecord.signedByName).toBe(INPUT.signedByName);
    expect(mockRecord.signaturePngBase64).toBe(INPUT.signaturePngBase64);
    expect(mockRecord.capturedBy).toBe(INPUT.capturedBy);
    expect(mockRecord.termsAcknowledged).toBe(true);
    expect(mockRecord.syncError).toBeNull();
    expect(mockRecord.retryCount).toBe(0);
  });

  it("returns isPending false after successful write", async () => {
    const { result } = renderHook(() => useCreateInvoiceSignoff(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.create(INPUT);
    });

    expect(result.current.isPending).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sets error on DB failure", async () => {
    // Override the database mock to throw on the next write call
    const { database } = jest.requireMock("../../../../database") as {
      database: { write: jest.Mock };
    };
    database.write.mockImplementationOnce(async () => {
      throw new Error("DB write failed");
    });

    const { result } = renderHook(() => useCreateInvoiceSignoff(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      try {
        await result.current.create(INPUT);
      } catch {
        // expected
      }
    });

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
      expect(result.current.error?.message).toBe("DB write failed");
    });
  });
});
