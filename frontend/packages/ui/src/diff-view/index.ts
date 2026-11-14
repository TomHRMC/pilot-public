/**
 * DiffView shared barrel
 *
 * Location: packages/ui/src/diff-view/index.ts
 *
 * Platform resolution happens via package.json "exports" field:
 *   "react-native" → mobile/index.ts
 *   "default"      → web/index.ts
 *
 * This file re-exports from the web implementation as the default
 * (when consumed directly without the package.json condition resolution).
 */

export { DiffView } from "./web/DiffView";
export type {
  DiffViewProps,
  DiffViewVariant,
  DiffField,
  DiffLineItem,
  QuoteLineDiffViewProps,
  IntegrationDiffViewProps,
  EntityDiffViewProps,
} from "./types";
export {
  normalizeFieldDiffs,
  buildQuoteLineDiff,
  fieldNameToLabel,
} from "./utils";
