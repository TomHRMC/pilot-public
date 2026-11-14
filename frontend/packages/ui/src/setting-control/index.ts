/**
 * setting-control barrel — FE-B11
 *
 * Location: packages/ui/src/setting-control/index.ts
 */

export { SettingControl } from "./SettingControl";
export type { SettingControlProps } from "./types";

export { RevertToDefaultDialog } from "./RevertToDefaultDialog";
export type { RevertToDefaultDialogProps } from "./types";

export { EffectiveSettingDisplay } from "./EffectiveSettingDisplay";
export type { EffectiveSettingDisplayProps } from "./types";

export { SaveOnGroupCompleteIndicator } from "./SaveOnGroupCompleteIndicator";
export type { SaveOnGroupCompleteIndicatorProps } from "./types";

export { SettingsSidebarSearch } from "./SettingsSidebarSearch";
export type { SettingsSidebarSearchProps } from "./SettingsSidebarSearch";

// Domain types (camelCase frontend representation of backend Pydantic schemas)
export type {
  CatalogEntry,
  EffectiveSettingValue,
  SettingControlPhase,
} from "./types";

// Synonym utility (consumed by search)
export { getSynonymMatches, SETTINGS_SYNONYMS } from "./synonyms";
