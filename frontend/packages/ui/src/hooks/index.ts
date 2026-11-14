/**
 * @pilot/ui hooks — Public API barrel
 *
 * Location: packages/ui/src/hooks/index.ts
 * Exported from: packages/ui/src/index.ts (top-level) and ./hooks subpath
 */

// FE-B4
export { useStalenessRetry, StalenessError } from "./useStalenessRetry";
export type {
  UseStalenessRetryOptions,
  UseStalenessRetryReturn,
  StalenessConflictPayload,
} from "./useStalenessRetry";

// FE-B4
export { useSseChannel } from "./useSseChannel";
export type {
  SseMessage,
  UseSseChannelOptions,
  UseSseChannelReturn,
} from "./useSseChannel";

// FE-B5
export { useApproveWithEdits } from "./useApproveWithEdits";
export type {
  UseApproveWithEditsOptions,
  UseApproveWithEditsReturn,
  QuotePendingEditCreate,
  QuotePendingEditResponse,
  QuoteApproveRequest,
  QuoteApproveResponse,
} from "./useApproveWithEdits";

// FE-B6
export { usePreviewBeforeSend } from "./usePreviewBeforeSend";
export type {
  UsePreviewBeforeSendOptions,
  UsePreviewBeforeSendReturn,
  PreviewInput,
} from "./usePreviewBeforeSend";

// FE-B15
export { useInFlightSyncStatus } from "./useInFlightSyncStatus";
export type { InFlightSyncStatus } from "./useInFlightSyncStatus";
