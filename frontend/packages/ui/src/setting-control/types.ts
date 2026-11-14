/**
 * setting-control/types.ts — FE-B11
 *
 * Canonical settings domain types (frontend camelCase representation of
 * backend snake_case Pydantic schemas).
 *
 * ⚠️ LOCKED after FE-B11 ships. FE-B12 may add optional fields only.
 */

// ─── Catalog entry ────────────────────────────────────────────────────────────

export interface CatalogEntry {
  key: string;
  label: string;
  description: string;
  subSurfacePath: string;
  dataType: "boolean" | "integer" | "decimal" | "string" | "array";
  validationRules: {
    min?: number;
    max?: number;
    allowedValues?: string[];
  };
  systemDefault: unknown;
  currentEffectiveValue: unknown;
  currentScope: "user" | "tenant" | "system" | "fallback";
  revertible: boolean;
  requiresRole: string | null;
  allowsUserOverride: boolean;
}

// ─── Effective setting value ──────────────────────────────────────────────────

export interface EffectiveSettingValue {
  key: string;
  value: unknown;
  scope: "user" | "tenant" | "system" | "fallback";
  tenantOverrideExists: boolean;
  userOverrideExists: boolean;
  allowsUserOverride: boolean;
}

// ─── SettingControl props ─────────────────────────────────────────────────────

/**
 * <SettingControl> — Locked public API
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 * FE-B12 may add OPTIONAL props via backward-compatible extension only.
 */
export interface SettingControlProps<T = unknown> {
  /** The setting key (matches catalog key) — used for accessibility and test IDs */
  settingKey: string;

  /** Human-readable label rendered above the field */
  label: string;

  /** Optional 1-2 sentence description rendered below the label */
  description?: string;

  /** The current effective value to display */
  value: T;

  /** The system default value — displayed in State 1 annotation: "Default · {defaultValue} {unit}" */
  defaultValue: T;

  /**
   * The current scope of the effective value.
   * 'system' → State 1 (inheriting default; muted annotation)
   * 'tenant' | 'user' → State 2 (actively overridden; "Revert to default" link visible)
   * 'fallback' → treated same as 'system'
   */
  scope: "system" | "tenant" | "user" | "fallback";

  /**
   * The save behavior for this field.
   * 'blur' — save fires on field blur (or toggle change)
   * 'group' — part of a save-on-group-complete group; caller manages save via useFormSaveStrategy
   * 'explicit' — save button; caller manages save via useFormSaveStrategy
   */
  saveMode: "blur" | "group" | "explicit";

  /**
   * Called when the value should be saved (blur mode only).
   * For 'group' and 'explicit' modes, the caller manages saving via useFormSaveStrategy.
   */
  onSave: (value: T) => Promise<void>;

  /** Called when the revert-to-default is confirmed. Caller fires DELETE mutation. */
  onRevert?: () => Promise<void>;

  /** When true, renders value display only — no edit affordance. Used for mobile read-only tenant settings. */
  readOnly?: boolean;

  /**
   * Input type — drives the rendered control.
   * Default: 'integer'
   */
  inputType?: "integer" | "boolean" | "string" | "select" | "preset-select";

  /** Validation constraints passed from catalog */
  validationRules?: {
    min?: number;
    max?: number;
    allowedValues?: string[];
  };

  /** Options for 'select' and 'preset-select' input types */
  selectOptions?: Array<{
    value: string;
    label: string;
    recommended?: boolean;
  }>;

  /** Unit suffix rendered after the value (e.g. "days", "%") */
  unit?: string;

  /**
   * For State 3: show effective range helper text below the field.
   * e.g. "Effective: 30 days · Pre-warning at: 7 days"
   */
  effectiveRangeLabel?: string;

  /**
   * When readOnly=true on mobile: provenance annotation shown below value.
   * 'tenant' → "Set by your tenant"; 'system' → "Default value"
   */
  provenanceAnnotation?: "tenant" | "system";

  /** Test ID for e2e and unit tests */
  testID?: string;
}

// ─── RevertToDefaultDialog props ─────────────────────────────────────────────

/**
 * <RevertToDefaultDialog> — inline confirmation component
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */
export interface RevertToDefaultDialogProps {
  /** The human-readable label of the setting being reverted */
  settingLabel: string;

  /** The current tenant override value (displayed as "from X") */
  currentValue: unknown;

  /** The system default value (displayed as "→ Y (system default)") */
  defaultValue: unknown;

  /** Unit suffix for display (e.g. "days") */
  unit?: string;

  /** Called when the owner confirms the revert */
  onConfirm: () => void;

  /** Called when the owner cancels the revert */
  onCancel: () => void;

  /** True while the revert DELETE mutation is in-flight */
  isReverting: boolean;

  /** Test ID */
  testID?: string;
}

// ─── EffectiveSettingDisplay props ───────────────────────────────────────────

/**
 * <EffectiveSettingDisplay> — Locked public API
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */
export interface EffectiveSettingDisplayProps {
  /** The setting key (matches catalog key) */
  settingKey: string;

  /** Human-readable label */
  label: string;

  /** Optional description */
  description?: string;

  /** The three-tier resolution chain values */
  tiers: {
    system: { value: unknown; exists: boolean };
    tenant: { value: unknown; exists: boolean };
    user: { value: unknown; exists: boolean };
  };

  /**
   * The active tier (which layer is currently providing the effective value).
   */
  activeTier: "user" | "tenant" | "system" | "fallback";

  /** Whether the current user can edit their own user-tier override */
  userCanEdit: boolean;

  /**
   * Whether the tenant allows per-user override for this setting.
   */
  allowsUserOverride: boolean;

  /** Called when user saves their own override value */
  onSaveUserOverride?: (value: unknown) => Promise<void>;

  /** Called when user reverts their override to inherit tenant/system value */
  onRevertUserOverride?: () => Promise<void>;

  /**
   * Web mode: shows all three tiers + the per_user_override_allowed meta-toggle
   * Mobile mode: shows user tier + tenant tier summary
   * Default: derived from Platform.OS
   */
  displayMode?: "web" | "mobile";

  /** Input type for the user-tier edit affordance */
  inputType?: "boolean" | "select";

  /** Options for select inputType */
  selectOptions?: Array<{ value: string; label: string }>;

  /** Test ID */
  testID?: string;
}

// ─── SaveOnGroupCompleteIndicator props ──────────────────────────────────────

/**
 * <SaveOnGroupCompleteIndicator>
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */
export interface SaveOnGroupCompleteIndicatorProps {
  /** From useFormSaveStrategy({ mode: 'group' }) return */
  groupIsComplete: boolean;
  incompleteFields: string[];

  /**
   * Timestamp of last successful group save.
   * When present and recent (< 2000ms), shows "Saved ✓" tick before fading.
   */
  savedAt: number | null;

  /** True when bulk write is in-flight — shows spinner */
  savePending: boolean;

  /** Group-level error message from failed bulk write */
  error: string | null;

  /** Prompt shown when group is incomplete */
  incompletePrompt?: string;

  /** Test ID */
  testID?: string;
}

// ─── SettingControl state machine ────────────────────────────────────────────

export type SettingControlPhase =
  | { phase: "clean" }
  | { phase: "editing"; draftValue: unknown }
  | { phase: "save-pending"; draftValue: unknown }
  | { phase: "saved"; confirmedAt: number }
  | { phase: "error"; error: string; draftValue: unknown }
  | { phase: "revert-pending" };
