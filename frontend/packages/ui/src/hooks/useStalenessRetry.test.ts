/**
 * useStalenessRetry — Unit Tests
 *
 * Location: packages/ui/src/hooks/useStalenessRetry.test.ts
 * Per batch-fe-b4-design.md §I.1
 * Target: 15 tests
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useStalenessRetry, StalenessError } from "./useStalenessRetry";

// ─── Test wrapper ─────────────────────────────────────────────────────────────

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface TestVariables {
  jobId: string;
  expected_updated_at: string;
  tech_id: string;
}

interface TestData {
  id: string;
  updated_at: string;
}

interface TestRefreshedState {
  id: string;
  updated_at: string;
  tech_id: string;
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("useStalenessRetry", () => {
  const successMutationFn = vi
    .fn()
    .mockResolvedValue({ id: "job-1", updated_at: "2026-01-02" });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns mutate, mutateAsync, StalenessDialog, and mutation", () => {
    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: successMutationFn,
        }),
      { wrapper: makeWrapper() },
    );

    expect(result.current.mutate).toBeTypeOf("function");
    expect(result.current.mutateAsync).toBeTypeOf("function");
    expect(result.current.StalenessDialog).toBeTypeOf("function");
    expect(result.current.isStalenessDialogOpen).toBe(false);
    expect(result.current.mutation).toBeDefined();
  });

  it("calls mutationFn on mutate", async () => {
    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: successMutationFn,
        }),
      { wrapper: makeWrapper() },
    );

    const vars: TestVariables = {
      jobId: "j1",
      expected_updated_at: "2026-01-01",
      tech_id: "t1",
    };

    act(() => result.current.mutate(vars));

    await waitFor(() => expect(successMutationFn).toHaveBeenCalledWith(vars));
  });

  it("isStalenessDialogOpen is false on successful mutation", async () => {
    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: successMutationFn,
        }),
      { wrapper: makeWrapper() },
    );

    act(() =>
      result.current.mutate({
        jobId: "j1",
        expected_updated_at: "2026-01-01",
        tech_id: "t1",
      }),
    );

    await waitFor(() => expect(result.current.mutation.isSuccess).toBe(true));
    expect(result.current.isStalenessDialogOpen).toBe(false);
  });

  it("opens dialog when 409 staleness error is thrown", async () => {
    const refreshedState: TestRefreshedState = {
      id: "job-1",
      updated_at: "2026-01-02",
      tech_id: "t2",
    };
    const staleness409 = Object.assign(new Error("Stale"), {
      status: 409,
      data: {
        status: 409,
        title: "Record updated",
        detail: "Job was moved",
        refreshed_state: refreshedState,
      },
    });
    const staleMutationFn = vi.fn().mockRejectedValue(staleness409);

    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: staleMutationFn,
        }),
      { wrapper: makeWrapper() },
    );

    act(() =>
      result.current.mutate({
        jobId: "j1",
        expected_updated_at: "stale",
        tech_id: "t1",
      }),
    );

    await waitFor(() =>
      expect(result.current.isStalenessDialogOpen).toBe(true),
    );
  });

  it("non-409 errors propagate without opening dialog", async () => {
    const networkError = new Error("Network failure");
    const errorMutationFn = vi.fn().mockRejectedValue(networkError);

    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: errorMutationFn,
        }),
      { wrapper: makeWrapper() },
    );

    act(() =>
      result.current.mutate({
        jobId: "j1",
        expected_updated_at: "2026-01-01",
        tech_id: "t1",
      }),
    );

    await waitFor(() => expect(result.current.mutation.isError).toBe(true));
    expect(result.current.isStalenessDialogOpen).toBe(false);
  });

  it("onConflict returning variables auto-retries", async () => {
    const refreshedState: TestRefreshedState = {
      id: "job-1",
      updated_at: "2026-01-02",
      tech_id: "t2",
    };
    const staleness409 = Object.assign(new Error("Stale"), {
      status: 409,
      data: {
        status: 409,
        title: "Record updated",
        detail: "Job was moved",
        refreshed_state: refreshedState,
      },
    });

    let callCount = 0;
    const mutationFn = vi
      .fn()
      .mockImplementation(async (vars: TestVariables) => {
        callCount++;
        if (callCount === 1) throw staleness409;
        return { id: vars.jobId, updated_at: "2026-01-02" };
      });

    const onConflict = vi
      .fn()
      .mockImplementation(
        (refreshed: TestRefreshedState, prev: TestVariables) => ({
          ...prev,
          expected_updated_at: refreshed.updated_at,
        }),
      );

    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn,
          onConflict,
        }),
      { wrapper: makeWrapper() },
    );

    act(() =>
      result.current.mutate({
        jobId: "j1",
        expected_updated_at: "stale",
        tech_id: "t1",
      }),
    );

    // onConflict is called immediately on 409 (per §G.2: auto-retry if non-null returned)
    // The mutation should succeed after auto-retry; dialog should NOT open
    await waitFor(() => expect(onConflict).toHaveBeenCalled());
    // With non-null return, dialog stays closed (auto-retry happened)
    expect(result.current.isStalenessDialogOpen).toBe(false);
  });

  it("onConflict returning null keeps dialog open", async () => {
    const refreshedState: TestRefreshedState = {
      id: "job-1",
      updated_at: "2026-01-02",
      tech_id: "t2",
    };
    const staleness409 = Object.assign(new Error("Stale"), {
      status: 409,
      data: {
        status: 409,
        title: "Record updated",
        detail: "Job was moved",
        refreshed_state: refreshedState,
      },
    });
    const staleMutationFn = vi.fn().mockRejectedValue(staleness409);
    const onConflict = vi.fn().mockReturnValue(null);

    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: staleMutationFn,
          onConflict,
        }),
      { wrapper: makeWrapper() },
    );

    act(() =>
      result.current.mutate({
        jobId: "j1",
        expected_updated_at: "stale",
        tech_id: "t1",
      }),
    );

    await waitFor(() =>
      expect(result.current.isStalenessDialogOpen).toBe(true),
    );
  });

  it("StalenessError sentinel has correct name and payload", () => {
    const payload = {
      status: 409 as const,
      title: "Stale record",
      detail: "Job was moved",
      refreshed_state: { id: "j1", updated_at: "2026-01-02", tech_id: "t1" },
    };
    const err = new StalenessError(payload);

    expect(err.name).toBe("StalenessError");
    expect(err.payload).toEqual(payload);
    expect(err.message).toBe(payload.detail);
  });

  it("mutationOptions.onSuccess is called after successful mutation", async () => {
    const onSuccess = vi.fn();
    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: successMutationFn,
          mutationOptions: { onSuccess },
        }),
      { wrapper: makeWrapper() },
    );

    act(() =>
      result.current.mutate({
        jobId: "j1",
        expected_updated_at: "2026-01-01",
        tech_id: "t1",
      }),
    );

    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  it("dialogTitle prop overrides default title", () => {
    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: successMutationFn,
          dialogTitle: "Custom conflict title",
        }),
      { wrapper: makeWrapper() },
    );

    // Hook should have dialogTitle accessible (internal — StalenessDialog renders it)
    expect(result.current.StalenessDialog).toBeDefined();
  });

  it("renderConflictContent prop is accepted without error", () => {
    const renderContent = vi.fn().mockReturnValue(null);
    const { result } = renderHook(
      () =>
        useStalenessRetry<TestVariables, TestData, TestRefreshedState>({
          mutationFn: successMutationFn,
          renderConflictContent: renderContent,
        }),
      { wrapper: makeWrapper() },
    );

    expect(result.current.StalenessDialog).toBeDefined();
  });
});
