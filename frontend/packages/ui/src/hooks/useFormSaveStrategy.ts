/**
 * useFormSaveStrategy — FE-B11
 *
 * Location: packages/ui/src/hooks/useFormSaveStrategy.ts
 *
 * Canonical hook implementing three save modes:
 *   'blur'     — saves a single field immediately on blur/toggle change
 *   'group'    — defers save until all required fields in the group are filled
 *   'explicit' — caller provides Save button; hook tracks dirty state
 *
 * All settings writes route through this hook. Never use ad-hoc useEffect → apiClient patterns.
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */

import { useState, useCallback, useEffect, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BlurSaveOptions<T = unknown> {
  mode: "blur";
  onSave: (key: string, value: T) => Promise<void>;
}

export interface BlurSaveReturn<T = unknown> {
  mode: "blur";
  getFieldProps: (key: string) => {
    onBlur: () => void;
    onChange: (value: T) => void;
  };
  savePending: boolean;
  lastError: string | null;
}

export interface GroupFieldDef {
  key: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  required: boolean | ((values: Record<string, any>) => boolean);
}

export interface GroupSaveOptions<T = unknown> {
  mode: "group";
  fields: GroupFieldDef[];
  initialValues: Record<string, T>;
  onSave: (values: Record<string, T>) => Promise<void>;
  onRollback: () => void;
}

export interface GroupSaveReturn<T = unknown> {
  mode: "group";
  groupIsComplete: boolean;
  incompleteFields: string[];
  fieldValues: Record<string, T>;
  setFieldValue: (key: string, value: T) => void;
  savePending: boolean;
  savedAt: number | null;
  lastError: string | null;
}

export interface ExplicitSaveOptions<T = unknown> {
  mode: "explicit";
  initialValues: Record<string, T>;
  onSave: (values: Record<string, T>) => Promise<void>;
}

export interface ExplicitSaveReturn<T = unknown> {
  mode: "explicit";
  isDirty: boolean;
  fieldValues: Record<string, T>;
  setFieldValue: (key: string, value: T) => void;
  handleSave: () => Promise<void>;
  handleDiscard: () => void;
  savePending: boolean;
  lastError: string | null;
}

export type UseFormSaveStrategyOptions<T = unknown> =
  | BlurSaveOptions<T>
  | GroupSaveOptions<T>
  | ExplicitSaveOptions<T>;

export type UseFormSaveStrategyReturn<T = unknown> =
  | BlurSaveReturn<T>
  | GroupSaveReturn<T>
  | ExplicitSaveReturn<T>;

// ─── Blur mode implementation ─────────────────────────────────────────────────

function useBlurSaveStrategy<T>(
  options: BlurSaveOptions<T>,
): BlurSaveReturn<T> {
  const [savePending, setSavePending] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const pendingValueRef = useRef<Map<string, T>>(new Map());

  const getFieldProps = useCallback(
    (key: string) => {
      const handleBlur = async () => {
        const pending = pendingValueRef.current.get(key);
        if (pending === undefined) return; // No change
        pendingValueRef.current.delete(key);

        setSavePending(true);
        setLastError(null);
        try {
          await options.onSave(key, pending);
        } catch (err) {
          setLastError(err instanceof Error ? err.message : "Save failed.");
        } finally {
          setSavePending(false);
        }
      };

      const handleChange = (value: T) => {
        pendingValueRef.current.set(key, value);
      };

      return { onBlur: handleBlur, onChange: handleChange };
    },
    [options],
  );

  return { mode: "blur", getFieldProps, savePending, lastError };
}

// ─── Group mode implementation ────────────────────────────────────────────────

function useGroupSaveStrategy<T>(
  options: GroupSaveOptions<T>,
): GroupSaveReturn<T> {
  const [fieldValues, setFieldValuesState] = useState<Record<string, T>>(
    options.initialValues,
  );
  const [savePending, setSavePending] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const saveRef = useRef(options.onSave);
  const rollbackRef = useRef(options.onRollback);
  const lastSavedValuesRef = useRef<Record<string, T>>(options.initialValues);

  // Keep refs fresh
  useEffect(() => {
    saveRef.current = options.onSave;
  }, [options.onSave]);
  useEffect(() => {
    rollbackRef.current = options.onRollback;
  }, [options.onRollback]);

  // Determine incomplete required fields
  const requiredFields = options.fields.filter((f) =>
    typeof f.required === "function" ? f.required(fieldValues) : f.required,
  );
  const incompleteFields = requiredFields
    .filter((f) => {
      const val = fieldValues[f.key];
      return val === null || val === undefined || val === "";
    })
    .map((f) => f.key);

  const groupIsComplete = incompleteFields.length === 0;

  const setFieldValue = useCallback((key: string, value: T) => {
    setFieldValuesState((prev) => {
      const next = { ...prev, [key]: value };
      return next;
    });
  }, []);

  // Auto-save when group becomes complete or when a value changes while complete
  const prevCompleteRef = useRef(groupIsComplete);
  useEffect(() => {
    const wasComplete = prevCompleteRef.current;
    prevCompleteRef.current = groupIsComplete;

    const hasChanges =
      JSON.stringify(fieldValues) !==
      JSON.stringify(lastSavedValuesRef.current);

    if (groupIsComplete && (hasChanges || !wasComplete) && !savePending) {
      const doSave = async () => {
        setSavePending(true);
        setLastError(null);
        try {
          await saveRef.current(fieldValues);
          lastSavedValuesRef.current = { ...fieldValues };
          setSavedAt(Date.now());
        } catch (err) {
          setLastError(err instanceof Error ? err.message : "Save failed.");
          // Rollback to last saved values
          setFieldValuesState({ ...lastSavedValuesRef.current });
          rollbackRef.current();
        } finally {
          setSavePending(false);
        }
      };
      doSave();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupIsComplete, fieldValues]);

  // Detect navigation-away with incomplete group → rollback
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!groupIsComplete) {
        e.preventDefault();
        rollbackRef.current();
      }
    };

    if (typeof window !== "undefined") {
      window.addEventListener("beforeunload", handleBeforeUnload);
    }

    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener("beforeunload", handleBeforeUnload);
      }
      // On cleanup (component unmount = navigation): rollback if incomplete
      if (!prevCompleteRef.current) {
        rollbackRef.current();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    mode: "group",
    groupIsComplete,
    incompleteFields,
    fieldValues,
    setFieldValue,
    savePending,
    savedAt,
    lastError,
  };
}

// ─── Explicit mode implementation ─────────────────────────────────────────────

function useExplicitSaveStrategy<T>(
  options: ExplicitSaveOptions<T>,
): ExplicitSaveReturn<T> {
  const [fieldValues, setFieldValuesState] = useState<Record<string, T>>(
    options.initialValues,
  );
  const [savePending, setSavePending] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  const isDirty =
    JSON.stringify(fieldValues) !== JSON.stringify(options.initialValues);

  const setFieldValue = useCallback((key: string, value: T) => {
    setFieldValuesState((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSave = useCallback(async () => {
    setSavePending(true);
    setLastError(null);
    try {
      await options.onSave(fieldValues);
    } catch (err) {
      setLastError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSavePending(false);
    }
  }, [options, fieldValues]);

  const handleDiscard = useCallback(() => {
    setFieldValuesState({ ...options.initialValues });
    setLastError(null);
  }, [options.initialValues]);

  return {
    mode: "explicit",
    isDirty,
    fieldValues,
    setFieldValue,
    handleSave,
    handleDiscard,
    savePending,
    lastError,
  };
}

// ─── Unified hook ─────────────────────────────────────────────────────────────

export function useFormSaveStrategy<T = unknown>(
  options: BlurSaveOptions<T>,
): BlurSaveReturn<T>;
export function useFormSaveStrategy<T = unknown>(
  options: GroupSaveOptions<T>,
): GroupSaveReturn<T>;
export function useFormSaveStrategy<T = unknown>(
  options: ExplicitSaveOptions<T>,
): ExplicitSaveReturn<T>;
export function useFormSaveStrategy<T = unknown>(
  options: UseFormSaveStrategyOptions<T>,
): UseFormSaveStrategyReturn<T> {
  // NOTE: Hooks cannot be conditionally called; the mode is constant per instance.
  // Each surface instantiates this hook once with a fixed mode.
  const blurResult = useBlurSaveStrategy<T>(
    options.mode === "blur"
      ? (options as BlurSaveOptions<T>)
      : { mode: "blur", onSave: async () => {} },
  );
  const groupResult = useGroupSaveStrategy<T>(
    options.mode === "group"
      ? (options as GroupSaveOptions<T>)
      : {
          mode: "group",
          fields: [],
          initialValues: {},
          onSave: async () => {},
          onRollback: () => {},
        },
  );
  const explicitResult = useExplicitSaveStrategy<T>(
    options.mode === "explicit"
      ? (options as ExplicitSaveOptions<T>)
      : { mode: "explicit", initialValues: {}, onSave: async () => {} },
  );

  if (options.mode === "blur") return blurResult;
  if (options.mode === "group") return groupResult;
  return explicitResult;
}
