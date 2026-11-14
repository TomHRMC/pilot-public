/**
 * States catalog — Web platform index
 * Location: packages/ui/src/states/web/index.ts
 *
 * Resolved via package.json conditional exports when default (browser) is used.
 */

export { EmptyState } from "./EmptyState";
export { LoadingState } from "./LoadingState";
export { ErrorState } from "./ErrorState";
export { FirstTimeUserState } from "./FirstTimeUserState";

// Re-export shared types and constants for consumers importing from @pilot/ui/states
export type {
  EmptyStateProps,
  EmptyStateType,
  EmptyStateIllustration,
  LoadingStateProps,
  LoadingStateType,
  ErrorStateProps,
  ErrorStateType,
  FirstTimeUserStateProps,
  FTUSurface,
} from "../types";
export {
  FTU_DEFAULTS,
  EMPTY_STATE_DEFAULTS,
  ERROR_STATE_DEFAULTS,
  MOBILE_SUPPORTED_FTU_TYPES,
} from "../types";
