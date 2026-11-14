/**
 * useVoiceConfirmation unit tests
 *
 * Location: packages/ui/src/voice-confirm-turn/useVoiceConfirmation.test.ts
 *
 * Test plan §I — 6 tests
 */

import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVoiceConfirmation } from "./useVoiceConfirmation";

const MOCK_CONFIRMATION = {
  intentId: "intent-001",
  prompt: "Send the Johnson quote?",
  expiresAt: new Date(Date.now() + 60_000).toISOString(),
};

describe("useVoiceConfirmation", () => {
  it("initial state: pendingConfirmation is null, isConfirming is false", () => {
    const { result } = renderHook(() => useVoiceConfirmation());
    expect(result.current.pendingConfirmation).toBeNull();
    expect(result.current.isConfirming).toBe(false);
  });

  it("setPendingConfirmation updates state", () => {
    const { result } = renderHook(() => useVoiceConfirmation());
    act(() => {
      result.current.setPendingConfirmation(MOCK_CONFIRMATION);
    });
    expect(result.current.pendingConfirmation).toEqual(MOCK_CONFIRMATION);
  });

  it("confirm executes action and clears pending state", async () => {
    const { result } = renderHook(() => useVoiceConfirmation());
    const executeAction = vi.fn().mockResolvedValue(undefined);

    act(() => {
      result.current.setPendingConfirmation(MOCK_CONFIRMATION);
    });

    await act(async () => {
      await result.current.confirm(MOCK_CONFIRMATION.intentId, executeAction);
    });

    expect(executeAction).toHaveBeenCalledTimes(1);
    expect(result.current.pendingConfirmation).toBeNull();
  });

  it("cancel clears pending state without executing action", () => {
    const { result } = renderHook(() => useVoiceConfirmation());

    act(() => {
      result.current.setPendingConfirmation(MOCK_CONFIRMATION);
    });
    act(() => {
      result.current.cancel();
    });

    expect(result.current.pendingConfirmation).toBeNull();
    expect(result.current.isConfirming).toBe(false);
  });

  it("confirm sets isConfirming=true during async action execution", async () => {
    const { result } = renderHook(() => useVoiceConfirmation());
    let resolveAction!: () => void;
    const slowAction = () =>
      new Promise<void>((resolve) => {
        resolveAction = resolve;
      });

    act(() => {
      result.current.setPendingConfirmation(MOCK_CONFIRMATION);
    });

    // Start confirm — don't await yet
    let confirmPromise!: Promise<void>;
    act(() => {
      confirmPromise = result.current.confirm(
        MOCK_CONFIRMATION.intentId,
        slowAction,
      );
    });

    // During execution isConfirming should be true
    expect(result.current.isConfirming).toBe(true);

    // Resolve action
    await act(async () => {
      resolveAction();
      await confirmPromise;
    });

    expect(result.current.isConfirming).toBe(false);
  });

  it("confirm clears isConfirming after action resolves", async () => {
    const { result } = renderHook(() => useVoiceConfirmation());
    const fastAction = vi.fn().mockResolvedValue(undefined);

    act(() => {
      result.current.setPendingConfirmation(MOCK_CONFIRMATION);
    });

    await act(async () => {
      await result.current.confirm(MOCK_CONFIRMATION.intentId, fastAction);
    });

    expect(result.current.isConfirming).toBe(false);
    expect(result.current.pendingConfirmation).toBeNull();
  });
});
