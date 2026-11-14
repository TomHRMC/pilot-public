/**
 * Money + percent formatting helpers — billing feature
 *
 * Location: apps/web/src/features/billing/utils/format.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * All `_cents` fields are integer cents → USD currency string.
 * `percent` is numeric(5,2) arriving as a string — display 2-decimal.
 *
 * Mirrors InvoiceBuilderPage.formatCents (§13.5 of the UI spec).
 * Centralized here so DrawRow, ReconciliationBar, and the builder share
 * one implementation (no duplication).
 */

/**
 * Format integer cents as a USD currency string.
 * @example formatCents(57914) → "$579.14"
 */
export function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

/**
 * Convert a dollar string (e.g. "579.14") to integer cents.
 * Rounds to the nearest cent. Returns null if the input is not a valid number.
 * @example dollarsToCents("579.14") → 57914
 */
export function dollarsToCents(dollars: string): number | null {
  const parsed = parseFloat(dollars);
  if (isNaN(parsed)) return null;
  return Math.round(parsed * 100);
}

/**
 * Convert integer cents to a dollar string for display in a $ input.
 * @example centsToDollars(57914) → "579.14"
 */
export function centsToDollars(cents: number | null | undefined): string {
  if (cents == null) return "";
  return (cents / 100).toFixed(2);
}

/**
 * Format a percent value (numeric(5,2) arriving as string|number) to a
 * 2-decimal display string. Returns "" for null/undefined.
 * @example formatPercent("33.3") → "33.30"
 */
export function formatPercent(
  percent: string | number | null | undefined,
): string {
  if (percent == null || percent === "") return "";
  const num = typeof percent === "string" ? parseFloat(percent) : percent;
  if (isNaN(num)) return "";
  return num.toFixed(2);
}
