/**
 * PeriodSelector — Report period pill selector
 *
 * Location: apps/web/src/features/profitability/components/PeriodSelector.tsx
 *
 * Canonical pattern for all report period selectors.
 * 7d / 30d / MTD / YTD / Custom pills.
 * Per batch-fe-b4-design.md §A.2.6
 *
 * BETA-B6: Added "Custom" pill with date range inputs (From / To).
 * Uses native <input type="date"> — no new dependency. Dates are passed
 * up via onCustomDatesChange prop for the parent to wire to useProfitability.
 */

import React from "react";
import type { ProfitabilityPeriod } from "../hooks/useProfitability";

interface PeriodSelectorProps {
  value: ProfitabilityPeriod;
  onChange: (period: ProfitabilityPeriod) => void;
  // BETA-B6: Custom date range props (only used when value === "custom")
  customDateFrom?: string; // YYYY-MM-DD
  customDateTo?: string; // YYYY-MM-DD
  onCustomDatesChange?: (from: string, to: string) => void;
}

const PERIODS: Array<{ value: ProfitabilityPeriod; label: string }> = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "mtd", label: "MTD" },
  { value: "ytd", label: "YTD" },
  { value: "custom", label: "Custom" },
];

/**
 * PeriodSelector
 *
 * Canonical period pill selector — used by all report surfaces.
 * FE-B8+ should import this component from this location.
 */
export function PeriodSelector({
  value,
  onChange,
  customDateFrom,
  customDateTo,
  onCustomDatesChange,
}: PeriodSelectorProps) {
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="flex flex-col items-end gap-2">
      {/* Period pills */}
      <div
        className="flex items-center rounded-md border border-neutral-200 overflow-hidden"
        role="group"
        aria-label="Report period"
      >
        {PERIODS.map((period) => (
          <button
            key={period.value}
            type="button"
            onClick={() => onChange(period.value)}
            aria-pressed={value === period.value}
            className={[
              "px-3 py-1.5 text-body font-medium",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-600",
              "border-r border-neutral-200 last:border-r-0",
              value === period.value
                ? "bg-brand-600 text-white"
                : "bg-white text-neutral-600 hover:bg-neutral-50",
            ].join(" ")}
          >
            {period.label}
          </button>
        ))}
      </div>

      {/* Custom date range inputs — only shown when "Custom" is selected */}
      {value === "custom" && (
        <div className="flex items-center gap-2">
          <label
            htmlFor="period-date-from"
            className="text-xs text-neutral-600 flex-shrink-0"
          >
            From
          </label>
          <input
            id="period-date-from"
            type="date"
            value={customDateFrom ?? ""}
            onChange={(e) =>
              onCustomDatesChange?.(e.target.value, customDateTo ?? "")
            }
            max={customDateTo || today}
            className="px-2 py-1 text-sm border border-neutral-200 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
          />
          <label
            htmlFor="period-date-to"
            className="text-xs text-neutral-600 flex-shrink-0"
          >
            To
          </label>
          <input
            id="period-date-to"
            type="date"
            value={customDateTo ?? ""}
            onChange={(e) =>
              onCustomDatesChange?.(customDateFrom ?? "", e.target.value)
            }
            min={customDateFrom ?? undefined}
            max={today}
            className="px-2 py-1 text-sm border border-neutral-200 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
          />
        </div>
      )}
    </div>
  );
}
