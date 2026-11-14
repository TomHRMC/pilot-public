/**
 * PendingBadge — Platform entry point
 *
 * Location: packages/ui/src/pending-badge/PendingBadge.tsx
 *
 * This file is the default export for web builds.
 * Metro bundler will prefer PendingBadge.native.tsx for native builds
 * (see PendingBadge.native.tsx which re-exports from mobile/).
 *
 * Web environments import from web/, mobile from mobile/.
 */

export { PendingBadge } from "./web/PendingBadge";
