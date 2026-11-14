/**
 * DiffView — shared types
 *
 * Location: packages/ui/src/diff-view/types.ts
 *
 * ⚠️ LOCKED — established FE-B5. FE-B7 ("entity"), FE-B8 ("calendar-event"),
 * FE-B9 ("qb-entity") import and compose this interface. Adding optional props
 * is acceptable; renaming or removing existing props is NOT permitted without a
 * multi-batch impact review.
 */

/**
 * The four valid variant values.
 *
 * "quote-line"     → FE-B5: owner diff of quote line items pre/post edit
 * "calendar-event" → FE-B8: Pilot-vs-external calendar event diff
 * "qb-entity"      → FE-B9: Pilot-vs-QB entity diff (customer, quote, invoice, expense)
 * "entity"         → FE-B7: generic mobile sync conflict entity diff (requires_review class)
 */
export type DiffViewVariant =
  | "quote-line"
  | "calendar-event"
  | "qb-entity"
  | "entity";

/**
 * A single field diff entry. Normalizes the §16.2 server-computed payload and the
 * FE-B5 client-side quote pending-edit representation into a common shape.
 */
export interface DiffField {
  /** The machine-readable field name (e.g., "unit_price_cents", "scheduled_start_at") */
  fieldName: string;

  /**
   * Human-readable label. When omitted, DiffView generates one from fieldName
   * (snake_case → Title Case with domain-specific overrides per variant).
   */
  label?: string;

  /**
   * The "before" value. For quote-line: old_value from quote_pending_edit.
   * For calendar/qb: pilot_value or base_value from §16.2 server payload.
   * null means "this field did not exist before" (added case → green).
   */
  baseValue: string | number | boolean | null;

  /**
   * The "after" value.
   * For quote-line: new_value from quote_pending_edit.
   * For calendar/qb: external_value or modified_value from §16.2 server payload.
   * null means "this field was removed" (deleted case → red).
   */
  modifiedValue: string | number | boolean | null;

  /**
   * Explicit change type override. When provided, overrides the auto-derived type.
   * When absent, DiffView derives: baseValue=null → "added"; modifiedValue=null → "removed";
   * values equal → "unchanged"; else → "modified".
   */
  changeType?: "unchanged" | "modified" | "added" | "removed";

  /**
   * Optional: annotation text appended below the field value pair.
   * Used for owner comments per line in kickback mode.
   */
  annotation?: string;

  /**
   * For quote-line variant only: the UUID of the quote_pending_edit row that
   * produced this diff. Required when onRevertField is provided.
   */
  pendingEditId?: string;
}

/**
 * A single line item with its associated field diffs. Used by "quote-line" variant.
 */
export interface DiffLineItem {
  /** UUID of the quote_line row */
  lineItemId: string;

  /** Display label for this line item */
  label: string;

  /** Whether this line item is customer-visible */
  customerVisible: boolean;

  /** Change type for the entire line */
  lineChangeType: "added" | "removed" | "modified" | "unchanged";

  /** The individual field diffs within this line. Empty array for unchanged lines. */
  fields: DiffField[];
}

/**
 * Props for variant="quote-line" (FE-B5 owner approval diff).
 */
export interface QuoteLineDiffViewProps {
  variant: "quote-line";

  /**
   * The structured line items to render. Include ALL lines for context.
   */
  lineItems: DiffLineItem[];

  /**
   * When provided, each modified/removed field renders a "Revert this change" button.
   */
  onRevertField?: (pendingEditId: string) => void;

  /** Mobile "Show changes / Hide changes" toggle. Default: false. */
  showToggle?: boolean;

  /** Initial visibility when showToggle=true. Default: true. */
  defaultShowChanges?: boolean;

  /** Test ID for e2e and unit tests */
  testID?: string;
}

/**
 * Props for variant="calendar-event" (FE-B8) or "qb-entity" (FE-B9).
 */
export interface IntegrationDiffViewProps {
  variant: "calendar-event" | "qb-entity";

  /** Server-computed §16.2 field_diffs payload mapped via normalizeFieldDiffs(). */
  fieldDiffs: DiffField[];

  /** Human-readable label for the entity being compared. */
  entityLabel: string;

  /**
   * Labels for the two sides of the diff.
   * Default for "calendar-event": { base: 'Pilot', modified: 'Google Calendar' }
   * Default for "qb-entity": { base: 'Pilot', modified: 'QuickBooks' }
   */
  sideLabels?: { base: string; modified: string };

  /** Test ID for e2e and unit tests */
  testID?: string;
}

/**
 * Props for variant="entity" (FE-B7 mobile offline sync conflict review).
 */
export interface EntityDiffViewProps {
  variant: "entity";

  /** Server-computed field diffs from BE-B7b/A40 conflict detail. */
  fieldDiffs: DiffField[];

  /** Entity display name */
  entityLabel: string;

  /** Test ID */
  testID?: string;
}

/**
 * Full props interface for <DiffView> — discriminated union.
 */
export type DiffViewProps =
  | QuoteLineDiffViewProps
  | IntegrationDiffViewProps
  | EntityDiffViewProps;
