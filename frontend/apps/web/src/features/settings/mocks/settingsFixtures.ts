/**
 * settingsFixtures.ts — FE-B11
 *
 * Location: apps/web/src/features/settings/mocks/settingsFixtures.ts
 *
 * Typed fixture data for all settings MSW handlers.
 * Covers all 18 Tier 2 #4 settings with scope=system and scope=tenant variants.
 */

export interface CatalogEntryRaw {
  key: string;
  label: string;
  description: string;
  sub_surface_path: string;
  data_type: "boolean" | "integer" | "decimal" | "string" | "array";
  validation_rules: {
    min?: number;
    max?: number;
    allowed_values?: string[];
  };
  system_default: unknown;
  current_effective_value: unknown;
  current_scope: "user" | "tenant" | "system" | "fallback";
  revertible: boolean;
  requires_role: string | null;
  allows_user_override: boolean;
}

export interface CatalogResponseRaw {
  settings: CatalogEntryRaw[];
}

export interface EffectiveSettingResponseRaw {
  key: string;
  value: unknown;
  scope: "user" | "tenant" | "system" | "fallback";
  tenant_override_exists: boolean;
  user_override_exists: boolean;
  allows_user_override: boolean;
}

export interface TenantSettingWriteResponseRaw {
  key: string;
  value: unknown;
  effective_value: unknown;
  scope: string;
  updated_at: string;
  pending_quote_count?: number;
}

export interface BulkSettingWriteResponseRaw {
  updated: string[];
  results: TenantSettingWriteResponseRaw[];
}

export interface UserOverrideWriteResponseRaw {
  key: string;
  value: unknown;
  effective_value: unknown;
  scope: string;
  updated_at: string;
}

// ─── Catalog fixture (all 18 settings at scope=system) ───────────────────────

export const ALL_SETTINGS_CATALOG_SYSTEM: CatalogEntryRaw[] = [
  // Calendar settings (A)
  {
    key: "calendar_conflict_auto_expire_days",
    label: "Auto-expire calendar conflicts",
    description:
      "Days before an unresolved conflict auto-resolves to Pilot's version.",
    sub_surface_path: "/settings/integrations/general",
    data_type: "integer",
    validation_rules: { min: 1, max: 365 },
    system_default: 30,
    current_effective_value: 30,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "calendar_conflict_pre_warning_days",
    label: "Calendar conflict pre-warning",
    description:
      "Days before expiry when the warning badge appears on pending conflicts.",
    sub_surface_path: "/settings/integrations/general",
    data_type: "integer",
    validation_rules: { min: 1, max: 30 },
    system_default: 7,
    current_effective_value: 7,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  // QB auto-expiry settings (B)
  {
    key: "qb_auto_expire_invoice_enabled",
    label: "Auto-expire QB invoices",
    description: "Automatically resolve QB invoice sync conflicts.",
    sub_surface_path: "/settings/integrations/quickbooks/auto-expiry",
    data_type: "boolean",
    validation_rules: {},
    system_default: false,
    current_effective_value: false,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "qb_auto_expire_invoice_direction",
    label: "QB invoice conflict resolution direction",
    description: "Which version wins when a QB invoice conflict auto-expires.",
    sub_surface_path: "/settings/integrations/quickbooks/auto-expiry",
    data_type: "string",
    validation_rules: {
      allowed_values: ["accept_remote", "accept_local"],
    },
    system_default: null,
    current_effective_value: null,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "qb_auto_expire_estimate_enabled",
    label: "Auto-expire QB estimates",
    description: "Automatically resolve QB estimate sync conflicts.",
    sub_surface_path: "/settings/integrations/quickbooks/auto-expiry",
    data_type: "boolean",
    validation_rules: {},
    system_default: false,
    current_effective_value: false,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "qb_auto_expire_estimate_direction",
    label: "QB estimate conflict resolution direction",
    description: "Which version wins when a QB estimate conflict auto-expires.",
    sub_surface_path: "/settings/integrations/quickbooks/auto-expiry",
    data_type: "string",
    validation_rules: {
      allowed_values: ["accept_remote", "accept_local"],
    },
    system_default: null,
    current_effective_value: null,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "qb_invoice_pre_warning_days",
    label: "QB invoice pre-warning period",
    description: "Days before QB invoice auto-expiry when warning badge shows.",
    sub_surface_path: "/settings/integrations/quickbooks/auto-expiry",
    data_type: "integer",
    validation_rules: { min: 1, max: 30 },
    system_default: 7,
    current_effective_value: 7,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "qb_invoice_auto_expire_days",
    label: "QB invoice auto-expiry period",
    description:
      "Days before unresolved QB invoice conflicts auto-expire to the configured direction.",
    sub_surface_path: "/settings/integrations/quickbooks/auto-expiry",
    data_type: "integer",
    validation_rules: { min: 1, max: 365 },
    system_default: 30,
    current_effective_value: 30,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  // Background sync (C)
  {
    key: "background_sync_enabled",
    label: "Background sync",
    description: "Enable automatic background sync of Pilot data.",
    sub_surface_path: "/settings/sync-storage/background-sync",
    data_type: "boolean",
    validation_rules: {},
    system_default: true,
    current_effective_value: true,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: true,
  },
  {
    key: "background_sync_wifi_only",
    label: "Sync on Wi-Fi only",
    description: "Restrict background sync to Wi-Fi connections only.",
    sub_surface_path: "/settings/sync-storage/background-sync",
    data_type: "boolean",
    validation_rules: {},
    system_default: true,
    current_effective_value: true,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "background_sync_battery_floor_pct",
    label: "Minimum battery for sync",
    description: "Background sync pauses when battery drops below this level.",
    sub_surface_path: "/settings/sync-storage/background-sync",
    data_type: "integer",
    validation_rules: { min: 5, max: 50 },
    system_default: 20,
    current_effective_value: 20,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "background_sync_interval_minutes",
    label: "Background sync interval",
    description:
      "How often background sync runs when on a suitable connection.",
    sub_surface_path: "/settings/sync-storage/background-sync",
    data_type: "integer",
    validation_rules: { min: 5, max: 120 },
    system_default: 15,
    current_effective_value: 15,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  // Offline limits (D)
  {
    key: "offline_hard_limit_hours",
    label: "Offline data retention limit",
    description: "Maximum hours of offline data retained before forced sync.",
    sub_surface_path: "/settings/sync-storage/offline-limits",
    data_type: "integer",
    validation_rules: { min: 1, max: 168 },
    system_default: 48,
    current_effective_value: 48,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  // Photos (E)
  {
    key: "photo_upload_wifi_only",
    label: "Upload photos on Wi-Fi only",
    description:
      "Restrict photo uploads to Wi-Fi connections to save mobile data.",
    sub_surface_path: "/settings/sync-storage/photos",
    data_type: "boolean",
    validation_rules: {},
    system_default: true,
    current_effective_value: true,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "photo_max_resolution_px",
    label: "Maximum photo resolution",
    description: "Maximum pixel dimension for uploaded photos.",
    sub_surface_path: "/settings/sync-storage/photos",
    data_type: "integer",
    validation_rules: { min: 720, max: 4096 },
    system_default: 2048,
    current_effective_value: 2048,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  // Voice capture (F)
  {
    key: "voice_capture_auto_delete_days",
    label: "Voice capture retention",
    description:
      "Days before voice capture recordings are automatically deleted.",
    sub_surface_path: "/settings/sync-storage/voice-capture",
    data_type: "integer",
    validation_rules: { min: 1, max: 365 },
    system_default: 90,
    current_effective_value: 90,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  // Margin buckets (G)
  {
    key: "margin_bucket_boundaries",
    label: "Margin bucket thresholds",
    description:
      "Percentage boundaries that define margin performance buckets.",
    sub_surface_path: "/settings/operations/margin-buckets",
    data_type: "array",
    validation_rules: {},
    system_default: [10, 20, 30],
    current_effective_value: [10, 20, 30],
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "low_margin_threshold_pct",
    label: "Low-margin alert threshold",
    description: "Jobs below this margin % trigger a low-margin alert.",
    sub_surface_path: "/settings/operations/margin-buckets",
    data_type: "integer",
    validation_rules: { min: 0, max: 100 },
    system_default: 15,
    current_effective_value: 15,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  // Profitability rules (H)
  {
    key: "etc_variance_note_required_pct",
    label: "ETC variance note required",
    description:
      "When ETC variance exceeds this %, a note is required before saving.",
    sub_surface_path: "/settings/operations/profitability-rules",
    data_type: "integer",
    validation_rules: { min: 0, max: 100 },
    system_default: 10,
    current_effective_value: 10,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "profitability_target_margin_pct",
    label: "Profitability target margin",
    description: "Target gross margin % for job profitability calculations.",
    sub_surface_path: "/settings/operations/profitability-rules",
    data_type: "integer",
    validation_rules: { min: 0, max: 100 },
    system_default: 25,
    current_effective_value: 25,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "overhead_allocation_pct",
    label: "Overhead allocation rate",
    description:
      "Percentage of revenue allocated to overhead in profitability calculations.",
    sub_surface_path: "/settings/operations/profitability-rules",
    data_type: "integer",
    validation_rules: { min: 0, max: 100 },
    system_default: 20,
    current_effective_value: 20,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  // Field operations (I)
  {
    key: "default_labor_rate_preset",
    label: "Default labor rate preset",
    description: "Preset labor rate category applied to new jobs by default.",
    sub_surface_path: "/settings/operations/field-operations",
    data_type: "string",
    validation_rules: {
      allowed_values: ["standard", "overtime", "emergency"],
    },
    system_default: "standard",
    current_effective_value: "standard",
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "require_approval_for_tech_quotes",
    label: "Require approval for technician quotes",
    description:
      "Quotes created by technicians must be approved by an owner before sending.",
    sub_surface_path: "/settings/operations/field-operations",
    data_type: "boolean",
    validation_rules: {},
    system_default: false,
    current_effective_value: false,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
  {
    key: "field_notes_required",
    label: "Field notes required on job close",
    description: "Technicians must add a field note before closing a job.",
    sub_surface_path: "/settings/operations/field-operations",
    data_type: "boolean",
    validation_rules: {},
    system_default: false,
    current_effective_value: false,
    current_scope: "system",
    revertible: false,
    requires_role: null,
    allows_user_override: false,
  },
];

// ─── Tenant-override variant — 5 settings at scope=tenant ────────────────────

export const ALL_SETTINGS_CATALOG_TENANT_OVERRIDES: CatalogEntryRaw[] =
  ALL_SETTINGS_CATALOG_SYSTEM.map((entry) => {
    const overrides: Record<string, { value: unknown }> = {
      calendar_conflict_auto_expire_days: { value: 45 },
      background_sync_battery_floor_pct: { value: 30 },
      etc_variance_note_required_pct: { value: 15 },
      low_margin_threshold_pct: { value: 20 },
      voice_capture_auto_delete_days: { value: 60 },
    };
    if (overrides[entry.key]) {
      return {
        ...entry,
        current_effective_value: overrides[entry.key].value,
        current_scope: "tenant" as const,
        revertible: true,
      };
    }
    return entry;
  });

// ─── Effective setting fixture helpers ───────────────────────────────────────

export function makeEffectiveSettingSystem(
  key: string,
  value: unknown,
): EffectiveSettingResponseRaw {
  return {
    key,
    value,
    scope: "system",
    tenant_override_exists: false,
    user_override_exists: false,
    allows_user_override: false,
  };
}

export function makeEffectiveSettingTenant(
  key: string,
  value: unknown,
): EffectiveSettingResponseRaw {
  return {
    key,
    value,
    scope: "tenant",
    tenant_override_exists: true,
    user_override_exists: false,
    allows_user_override: false,
  };
}

export function makeEffectiveSettingUser(
  key: string,
  value: unknown,
): EffectiveSettingResponseRaw {
  return {
    key,
    value,
    scope: "user",
    tenant_override_exists: false,
    user_override_exists: true,
    allows_user_override: true,
  };
}

// ─── Write response fixtures ──────────────────────────────────────────────────

export function makeTenantWriteSuccess(
  key: string,
  value: unknown,
  pendingQuoteCount?: number,
): TenantSettingWriteResponseRaw {
  return {
    key,
    value,
    effective_value: value,
    scope: "tenant",
    updated_at: new Date().toISOString(),
    ...(pendingQuoteCount !== undefined
      ? { pending_quote_count: pendingQuoteCount }
      : {}),
  };
}

export function makeRevertSuccess(
  key: string,
  systemDefault: unknown,
): TenantSettingWriteResponseRaw {
  return {
    key,
    value: null,
    effective_value: systemDefault,
    scope: "system",
    updated_at: new Date().toISOString(),
  };
}

export function makeBulkWriteSuccess(
  values: Record<string, unknown>,
): BulkSettingWriteResponseRaw {
  const results: TenantSettingWriteResponseRaw[] = Object.entries(values).map(
    ([key, value]) => makeTenantWriteSuccess(key, value),
  );
  return {
    updated: Object.keys(values),
    results,
  };
}
