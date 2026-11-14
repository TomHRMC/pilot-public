/**
 * WIP formatting helpers
 *
 * Location: apps/web/src/features/wip/lib/wip-format.ts
 *
 * Currency-from-cents + percentage formatting per spec §9.3.
 * No existing util in apps/web/src/lib/ (only amplify-config.ts + react-native-stub.js).
 */

/**
 * Formats integer cents as a whole-dollar USD string.
 * null → "—" (em-dash affordance for no-quote rows).
 */
export function formatCents(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

/**
 * Formats a percentage value to 1 decimal place.
 * null → "—" (em-dash affordance for no-quote rows).
 */
export function formatPct(pct: number | null | undefined): string {
  if (pct == null) return "—";
  return `${pct.toFixed(1)}%`;
}

/**
 * Formats an ISO 8601 timestamp as "MMM d, yyyy h:mm a" (e.g. "Jul 29, 2026 2:00 PM").
 * Uses date-fns format — mirrors the app's existing date-fns usage.
 */
export function formatGeneratedAt(iso: string): string {
  // Lazy import to avoid pulling date-fns into bundles that don't need it.
  // date-fns is already a web dependency (used by useProfitability.ts).
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { format } = require("date-fns");
  return format(new Date(iso), "MMM d, yyyy h:mm a");
}
