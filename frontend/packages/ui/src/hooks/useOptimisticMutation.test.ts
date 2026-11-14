/**
 * useOptimisticMutation Unit Tests
 *
 * Location: packages/ui/src/hooks/useOptimisticMutation.test.ts
 *
 * Tests: immediate local write; deferToOrchestrator path; rollback on error; isPending state
 * Per batch-fe-b7-design.md Section I.1.
 */

import { renderHook, act } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { useOptimisticMutation } from "./useOptimisticMutation";

describe("useOptimisticMutation", () => {
  it("calls optimisticUpdate immediately on mutate", async () => {
    const optimisticUpdate = vi.fn().mockResolvedValue({ id: "local-1" });

    const { result } = renderHook(() =>
      useOptimisticMutation({ optimisticUpdate }),
    );

    await act(async () => {
      await result.current.mutateAsync({ foo: "bar" });
    });

    expect(optimisticUpdate).toHaveBeenCalledWith({ foo: "bar" });
  });

  it("sets isPending during optimistic write", async () => {
    let resolveFn: () => void;
    const optimisticUpdate = vi.fn(
      () =>
        new Promise<{ id: string }>((resolve) => {
          resolveFn = () => resolve({ id: "1" });
        }),
    );

    const { result } = renderHook(() =>
      useOptimisticMutation({ optimisticUpdate }),
    );

    act(() => {
      result.current.mutate({ foo: "bar" });
    });

    expect(result.current.isPending).toBe(true);

    await act(async () => {
      resolveFn!();
      await Promise.resolve();
    });

    expect(result.current.isPending).toBe(false);
  });

  it("defers to orchestrator by default (does not call mutationFn)", async () => {
    const optimisticUpdate = vi.fn().mockResolvedValue({ id: "1" });
    const mutationFn = vi.fn().mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useOptimisticMutation({ optimisticUpdate, mutationFn }),
    );

    await act(async () => {
      await result.current.mutateAsync({});
    });

    expect(mutationFn).not.toHaveBeenCalled();
  });

  it("calls mutationFn when deferToOrchestrator=false", async () => {
    const optimisticUpdate = vi.fn().mockResolvedValue({ id: "1" });
    const mutationFn = vi.fn().mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useOptimisticMutation({
        optimisticUpdate,
        mutationFn,
        deferToOrchestrator: false,
      }),
    );

    await act(async () => {
      await result.current.mutateAsync({});
    });

    expect(mutationFn).toHaveBeenCalledTimes(1);
  });

  it("calls rollbackFn on mutationFn error", async () => {
    const localRecord = { id: "local-1", syncStatus: "failed" };
    const optimisticUpdate = vi.fn().mockResolvedValue(localRecord);
    const mutationFn = vi.fn().mockRejectedValue(new Error("Network error"));
    const rollbackFn = vi.fn().mockResolvedValue(undefined);

    const { result } = renderHook(() =>
      useOptimisticMutation({
        optimisticUpdate,
        mutationFn,
        rollbackFn,
        deferToOrchestrator: false,
      }),
    );

    await act(async () => {
      try {
        await result.current.mutateAsync({});
      } catch {
        // expected
      }
    });

    expect(rollbackFn).toHaveBeenCalledWith(localRecord, expect.any(Error));
    expect(result.current.isError).toBe(true);
    expect(result.current.error?.message).toBe("Network error");
  });

  it("reset() clears error state", async () => {
    const optimisticUpdate = vi
      .fn()
      .mockRejectedValue(new Error("Write failed"));

    const { result } = renderHook(() =>
      useOptimisticMutation({ optimisticUpdate }),
    );

    await act(async () => {
      try {
        await result.current.mutateAsync({});
      } catch {
        // expected
      }
    });

    expect(result.current.isError).toBe(true);

    act(() => {
      result.current.reset();
    });

    expect(result.current.isError).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("mutate() fires and forget (no throw)", () => {
    const optimisticUpdate = vi.fn().mockResolvedValue({});

    const { result } = renderHook(() =>
      useOptimisticMutation({ optimisticUpdate }),
    );

    expect(() => {
      result.current.mutate({});
    }).not.toThrow();
  });
});
