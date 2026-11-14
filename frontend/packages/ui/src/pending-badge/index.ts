/**
 * PendingBadge — Platform-resolved barrel
 *
 * Location: packages/ui/src/pending-badge/index.ts
 *
 * Metro bundler resolves .native.tsx → mobile; webpack resolves .tsx → web.
 * Both variants implement the same PendingBadgeProps interface.
 *
 * The root PendingBadge.tsx uses React.Platform to resolve at runtime
 * for environments that don't use Metro's file extension resolution.
 */

export { PendingBadge } from "./PendingBadge";
export type { PendingBadgeProps, PendingBadgeVariant } from "./types";
