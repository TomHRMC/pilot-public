/**
 * States catalog — Root barrel
 * Location: packages/ui/src/states/index.ts
 *
 * This file is the default resolution for `@pilot/ui/states`.
 * It re-exports from the web platform subfolder.
 *
 * Mobile resolution is controlled via package.json conditional exports:
 *   "./states": {
 *     "react-native": "./src/states/mobile/index.ts",
 *     "default":      "./src/states/web/index.ts"
 *   }
 *
 * Consumers import as:
 *   import { EmptyState, LoadingState, ErrorState, FirstTimeUserState } from '@pilot/ui/states'
 */

// Default export is the web platform
export {
  EmptyState,
  LoadingState,
  ErrorState,
  FirstTimeUserState,
} from "./web/index";

// Type exports — platform-agnostic
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
} from "./types";

export {
  FTU_DEFAULTS,
  EMPTY_STATE_DEFAULTS,
  ERROR_STATE_DEFAULTS,
  MOBILE_SUPPORTED_FTU_TYPES,
} from "./types";
