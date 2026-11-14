/**
 * useFormSaveStrategy unit tests — FE-B11
 *
 * Location: packages/ui/src/hooks/useFormSaveStrategy.test.ts
 *
 * Tests all three modes: blur, group, explicit.
 */

import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFormSaveStrategy } from "./useFormSaveStrategy";

// ─── Blur mode ────────────────────────────────────────────────────────────────

describe("useFormSaveStrategy — blur mode", () => {
  it("calls onSave on field blur with new value", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useFormSaveStrategy({ mode: "blur", onSave }),
    );

    // Simulate onChange then onBlur
    const { getFieldProps } = result.current as {
      getFieldProps: (key: string) => {
        onBlur: () => void;
        onChange: (v: unknown) => void;
      };
    };
    const { onBlur, onChange } = getFieldProps("my_setting");
    act(() => onChange(45));
    await act(() => onBlur());

    expect(onSave).toHaveBeenCalledWith("my_setting", 45);
  });

  it("sets savePending=true during onSave in-flight", async () => {
    let resolve: () => void;
    const onSave = vi.fn().mockReturnValue(
      new Promise<void>((r) => {
        resolve = r;
      }),
    );
    const { result } = renderHook(() =>
      useFormSaveStrategy({ mode: "blur", onSave }),
    );

    const { getFieldProps } = result.current as {
      getFieldProps: (key: string) => {
        onBlur: () => void;
        onChange: (v: unknown) => void;
      };
    };
    const { onBlur, onChange } = getFieldProps("my_setting");
    act(() => onChange(45));

    // Start save but don't resolve
    act(() => {
      onBlur();
    });

    await vi.waitFor(() => {
      expect((result.current as { savePending: boolean }).savePending).toBe(
        true,
      );
    });

    act(() => resolve!());
  });

  it("returns lastError when onSave rejects", async () => {
    const onSave = vi.fn().mockRejectedValue(new Error("Server fail"));
    const { result } = renderHook(() =>
      useFormSaveStrategy({ mode: "blur", onSave }),
    );

    const { getFieldProps } = result.current as {
      getFieldProps: (key: string) => {
        onBlur: () => void;
        onChange: (v: unknown) => void;
      };
    };
    const { onBlur, onChange } = getFieldProps("my_setting");
    act(() => onChange(45));
    await act(() => onBlur());

    expect((result.current as { lastError: string | null }).lastError).toBe(
      "Server fail",
    );
  });
});

// ─── Group mode ───────────────────────────────────────────────────────────────

describe("useFormSaveStrategy — group mode", () => {
  const onRollback = vi.fn();

  it("does NOT fire onSave when group incomplete", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
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

    // Set only one of two required fields
    await act(() => {
      (
        result.current as { setFieldValue: (k: string, v: unknown) => void }
      ).setFieldValue("toggle", true);
    });

    // Small wait to ensure no save fired
    await new Promise((r) => setTimeout(r, 50));
    expect(onSave).not.toHaveBeenCalled();
  });

  it("fires onSave when all required fields set", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
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

    await vi.waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({
        toggle: true,
        direction: "accept_remote",
      }),
    );
  });

  it("incompleteFields lists unfilled required keys", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
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

    const { incompleteFields } = result.current as {
      incompleteFields: string[];
    };
    expect(incompleteFields).toContain("direction");
    expect(incompleteFields).not.toContain("toggle");
  });

  it("group fires atomically when toggle turned OFF (direction not required)", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useFormSaveStrategy({
        mode: "group",
        fields: [
          { key: "toggle", required: true },
          { key: "direction", required: false },
        ],
        initialValues: { toggle: true, direction: "accept_remote" },
        onSave,
        onRollback,
      }),
    );

    // Group starts complete (toggle=true, direction has value)
    // Now toggle OFF
    await act(async () => {
      (
        result.current as { setFieldValue: (k: string, v: unknown) => void }
      ).setFieldValue("toggle", false);
    });

    await vi.waitFor(() => expect(onSave).toHaveBeenCalled());
  });
});

// ─── Explicit mode ────────────────────────────────────────────────────────────

describe("useFormSaveStrategy — explicit mode", () => {
  it("isDirty=false when values match initialValues", () => {
    const { result } = renderHook(() =>
      useFormSaveStrategy({
        mode: "explicit",
        initialValues: { boundary_0: 10, boundary_1: 20 },
        onSave: vi.fn().mockResolvedValue(undefined),
      }),
    );

    expect((result.current as { isDirty: boolean }).isDirty).toBe(false);
  });

  it("isDirty=true after any field change", async () => {
    const { result } = renderHook(() =>
      useFormSaveStrategy({
        mode: "explicit",
        initialValues: { boundary_0: 10 },
        onSave: vi.fn().mockResolvedValue(undefined),
      }),
    );

    await act(() => {
      (
        result.current as { setFieldValue: (k: string, v: unknown) => void }
      ).setFieldValue("boundary_0", 15);
    });

    expect((result.current as { isDirty: boolean }).isDirty).toBe(true);
  });

  it("handleDiscard resets fieldValues to initialValues", async () => {
    const { result } = renderHook(() =>
      useFormSaveStrategy({
        mode: "explicit",
        initialValues: { boundary_0: 10 },
        onSave: vi.fn().mockResolvedValue(undefined),
      }),
    );

    await act(() => {
      (
        result.current as { setFieldValue: (k: string, v: unknown) => void }
      ).setFieldValue("boundary_0", 99);
    });

    await act(() => {
      (result.current as { handleDiscard: () => void }).handleDiscard();
    });

    expect(
      (result.current as { fieldValues: Record<string, unknown> }).fieldValues
        .boundary_0,
    ).toBe(10);
    expect((result.current as { isDirty: boolean }).isDirty).toBe(false);
  });

  it("handleSave calls onSave with current fieldValues", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useFormSaveStrategy({
        mode: "explicit",
        initialValues: { boundary_0: 10 },
        onSave,
      }),
    );

    await act(() => {
      (
        result.current as { setFieldValue: (k: string, v: unknown) => void }
      ).setFieldValue("boundary_0", 25);
    });

    await act(() => {
      (result.current as { handleSave: () => Promise<void> }).handleSave();
    });

    expect(onSave).toHaveBeenCalledWith({ boundary_0: 25 });
  });
});
