/**
 * StalenessRefreshDialog — Shared Types
 *
 * Location: packages/ui/src/staleness-refresh-dialog/types.ts
 * Exported from: packages/ui/src/index.ts (via StalenessRefreshDialog barrel)
 *
 * Established in FE-B4. Consumed by FE-B5, FE-B8, FE-B9, FE-B10 via
 * useStalenessRetry() — consumers never render this directly.
 *
 * ⚠️ INTERFACE LOCKED — changes require downstream impact review.
 * See batch-fe-b4-design.md §F.2 §G.3.
 */

import type React from "react";

export interface StalenessRefreshDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;

  /** Called when user clicks "Retry with updated data" */
  onRetry: () => void;

  /** Called when user clicks "Cancel" or closes the dialog */
  onCancel: () => void;

  /** Dialog title — defaults to "This record was updated while you were working" */
  title?: string;

  /**
   * Custom content to render in the dialog body above action buttons.
   * FE-B4: renders refreshed slot info (date, tech, time range).
   * FE-B5+: renders <DiffView> showing what changed.
   * If omitted, dialog renders a generic explanation paragraph.
   */
  children?: React.ReactNode;

  /**
   * If true, the "Retry" button is disabled (used while useStalenessRetry is
   * preparing the retry variables). Default false.
   */
  isRetrying?: boolean;
}
