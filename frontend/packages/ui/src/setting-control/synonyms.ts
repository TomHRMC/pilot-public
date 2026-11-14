/**
 * synonyms.ts — FE-B11
 *
 * Location: packages/ui/src/setting-control/synonyms.ts
 *
 * Settings search synonym dictionary.
 * Maps alternate search terms → setting keys.
 * Used by SettingsSidebarSearch for client-side synonym matching.
 *
 * Design doc Decision 7: client-side filter over loaded catalog.
 */

/** Map of synonym → array of setting keys it matches */
export const SETTINGS_SYNONYMS: Record<string, string[]> = {
  // Calendar
  expire: ["calendar_conflict_auto_expire_days", "qb_auto_expire_invoice_days"],
  expiry: ["calendar_conflict_auto_expire_days", "qb_auto_expire_invoice_days"],
  "auto-resolve": ["calendar_conflict_auto_expire_days"],
  conflict: [
    "calendar_conflict_auto_expire_days",
    "calendar_conflict_pre_warning_days",
    "qb_auto_expire_invoice_enabled",
    "qb_auto_expire_estimate_enabled",
  ],
  warning: [
    "calendar_conflict_pre_warning_days",
    "qb_invoice_pre_warning_days",
  ],
  alert: ["calendar_conflict_pre_warning_days", "low_margin_threshold_pct"],

  // QuickBooks
  quickbooks: [
    "qb_auto_expire_invoice_enabled",
    "qb_auto_expire_invoice_direction",
    "qb_auto_expire_estimate_enabled",
    "qb_auto_expire_estimate_direction",
    "qb_invoice_pre_warning_days",
    "qb_invoice_auto_expire_days",
  ],
  qbo: [
    "qb_auto_expire_invoice_enabled",
    "qb_auto_expire_invoice_direction",
    "qb_auto_expire_estimate_enabled",
    "qb_auto_expire_estimate_direction",
    "qb_invoice_pre_warning_days",
    "qb_invoice_auto_expire_days",
  ],
  invoice: [
    "qb_auto_expire_invoice_enabled",
    "qb_auto_expire_invoice_direction",
    "qb_invoice_pre_warning_days",
    "qb_invoice_auto_expire_days",
  ],
  estimate: [
    "qb_auto_expire_estimate_enabled",
    "qb_auto_expire_estimate_direction",
  ],
  direction: [
    "qb_auto_expire_invoice_direction",
    "qb_auto_expire_estimate_direction",
  ],

  // Background sync
  sync: [
    "background_sync_enabled",
    "background_sync_wifi_only",
    "background_sync_battery_floor_pct",
    "background_sync_interval_minutes",
  ],
  wifi: ["background_sync_wifi_only", "photo_upload_wifi_only"],
  "wi-fi": ["background_sync_wifi_only", "photo_upload_wifi_only"],
  battery: ["background_sync_battery_floor_pct"],
  interval: ["background_sync_interval_minutes"],
  frequency: ["background_sync_interval_minutes"],

  // Offline limits
  offline: ["offline_hard_limit_hours"],
  limit: ["offline_hard_limit_hours", "photo_max_resolution_px"],
  retention: ["offline_hard_limit_hours", "voice_capture_auto_delete_days"],
  hours: ["offline_hard_limit_hours"],

  // Photos
  photo: ["photo_upload_wifi_only", "photo_max_resolution_px"],
  image: ["photo_upload_wifi_only", "photo_max_resolution_px"],
  resolution: ["photo_max_resolution_px"],
  upload: ["photo_upload_wifi_only"],

  // Voice capture
  voice: ["voice_capture_auto_delete_days"],
  recording: ["voice_capture_auto_delete_days"],
  audio: ["voice_capture_auto_delete_days"],
  "auto-delete": ["voice_capture_auto_delete_days"],

  // Operations — Margin
  margin: [
    "margin_bucket_boundaries",
    "low_margin_threshold_pct",
    "profitability_target_margin_pct",
  ],
  bucket: ["margin_bucket_boundaries"],
  threshold: [
    "margin_bucket_boundaries",
    "low_margin_threshold_pct",
    "etc_variance_note_required_pct",
  ],
  profitability: [
    "profitability_target_margin_pct",
    "overhead_allocation_pct",
    "low_margin_threshold_pct",
  ],

  // Operations — Profitability
  "etc variance": ["etc_variance_note_required_pct"],
  variance: ["etc_variance_note_required_pct"],
  overhead: ["overhead_allocation_pct"],
  target: ["profitability_target_margin_pct"],

  // Operations — Field ops
  labor: ["default_labor_rate_preset"],
  rate: ["default_labor_rate_preset"],
  approval: ["require_approval_for_tech_quotes"],
  "tech quote": ["require_approval_for_tech_quotes"],
  technician: ["require_approval_for_tech_quotes"],
  "field notes": ["field_notes_required"],
  notes: ["field_notes_required"],
  close: ["field_notes_required"],
};

/**
 * Get setting keys that match a synonym query.
 * Returns empty array if no synonym match.
 */
export function getSynonymMatches(query: string): string[] {
  const lower = query.toLowerCase().trim();
  const matches = new Set<string>();

  for (const [synonym, keys] of Object.entries(SETTINGS_SYNONYMS)) {
    if (synonym.includes(lower) || lower.includes(synonym)) {
      keys.forEach((k) => matches.add(k));
    }
  }

  return Array.from(matches);
}
