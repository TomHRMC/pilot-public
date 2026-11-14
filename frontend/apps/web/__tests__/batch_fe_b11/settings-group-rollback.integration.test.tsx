/**
 * Group rollback integration test — FE-B11
 */

import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useFormSaveStrategy } from "@pilot/ui";

describe("useFormSaveStrategy group mode — rollback on abandon", () => {
  it("calls onRollback when component unmounts with incomplete group", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onRollback = vi.fn();

    const { result, unmount } = renderHook(() =>
      useFormSaveStrategy({
        mode: "group",
        fields: [
          { key: "toggle", required: true },
          { key: "direction", required: true },
        ],
        initialValues: { toggle: null, direction: null },
        onSave,
        onRollback,
      }),
    );

    await act(() => {
      (
        result.current as { setFieldValue: (k: string, v: unknown) => void }
      ).setFieldValue("toggle", true);
    });

    unmount();

    expect(onRollback).toHaveBeenCalled();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("does NOT call onRollback when group is complete before unmount", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onRollback = vi.fn();

    const { result, unmount } = renderHook(() =>
      useFormSaveStrategy({
        mode: "group",
        fields: [
          { key: "toggle", required: true },
          { key: "direction", required: true },
        ],
        initialValues: { toggle: null, direction: null },
        onSave,
        onRollback,
      }),
    );

    await act(async () => {
      (
        result.current as { setFieldValue: (k: string, v: unknown) => void }
      ).setFieldValue("toggle", true);
      (
        result.current as { setFieldValue: (k: string, v: unknown) => void }
      ).setFieldValue("direction", "accept_remote");
    });

    await waitFor(() => expect(onSave).toHaveBeenCalled());
    unmount();

    expect(onRollback).not.toHaveBeenCalled();
  });
});
