"use client";

import { useState, useRef, type KeyboardEvent } from "react";

/**
 * PricingToggle — C-B13 Part B
 *
 * Segmented control (Monthly | Annual) for the General Release pricing page.
 * Implements the WAI-ARIA radiogroup pattern with full keyboard support:
 *   - Tab moves focus into the toggle (focuses the selected option)
 *   - ← / → arrow keys move between options and select the focused option
 *   - Space / Enter selects the focused option
 *
 * Default: "monthly". Calls onToggle(interval) when the selection changes.
 *
 * @see mkt-c-b13-design-spec.md (private design spec, not in the public snapshot) §2.2, §5.2, §9.4
 */

export type BillingInterval = "monthly" | "annual";

interface PricingToggleProps {
  /** Called when the user changes the billing interval. */
  onToggle: (interval: BillingInterval) => void;
  /** Controlled value (optional). If omitted, the component manages its own state. */
  value?: BillingInterval;
}

const OPTIONS: { label: string; value: BillingInterval }[] = [
  { label: "Monthly", value: "monthly" },
  { label: "Annual", value: "annual" },
];

export default function PricingToggle({
  onToggle,
  value: controlledValue,
}: PricingToggleProps) {
  const [internalValue, setInternalValue] =
    useState<BillingInterval>("monthly");
  const monthlyRef = useRef<HTMLButtonElement>(null);
  const annualRef = useRef<HTMLButtonElement>(null);

  const isControlled = controlledValue !== undefined;
  const selected = isControlled ? controlledValue : internalValue;

  function select(interval: BillingInterval) {
    if (!isControlled) {
      setInternalValue(interval);
    }
    onToggle(interval);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown": {
        e.preventDefault();
        const next = selected === "monthly" ? "annual" : "monthly";
        select(next);
        (next === "monthly" ? monthlyRef : annualRef).current?.focus();
        break;
      }
      case "ArrowLeft":
      case "ArrowUp": {
        e.preventDefault();
        const prev = selected === "monthly" ? "annual" : "monthly";
        select(prev);
        (prev === "monthly" ? monthlyRef : annualRef).current?.focus();
        break;
      }
      case " ":
      case "Enter": {
        e.preventDefault();
        select(selected);
        break;
      }
    }
  }

  // The sliding pill translates to the right when "annual" is selected.
  const sliderTranslateX = selected === "annual" ? "100%" : "0%";

  return (
    <div className="flex flex-col items-center mb-10">
      <div
        role="radiogroup"
        aria-label="Billing interval"
        className="inline-flex items-center rounded-full p-1 relative"
        style={{
          background: "var(--neutral-100)",
          border: "var(--divider-thin) solid var(--neutral-200)",
        }}
        onKeyDown={handleKeyDown}
      >
        {/* Sliding pill background */}
        <div
          className="pricing-toggle-slider absolute rounded-full"
          aria-hidden="true"
          style={{
            top: "0.25rem",
            left: "0.25rem",
            width: "calc(50% - 0.25rem)",
            height: "calc(100% - 0.5rem)",
            background: "var(--brand-600)",
            transform: `translateX(${sliderTranslateX})`,
          }}
        />

        {OPTIONS.map((option) => {
          const isSelected = selected === option.value;
          const ref = option.value === "monthly" ? monthlyRef : annualRef;
          return (
            <button
              key={option.value}
              ref={ref}
              type="button"
              role="radio"
              aria-checked={isSelected}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => select(option.value)}
              className="pricing-toggle-option relative z-10 px-6 py-3 rounded-full font-medium"
              style={{
                fontSize: "var(--text-caption-lg)",
                lineHeight: "var(--lh-caption-lg)",
                fontWeight: isSelected ? 600 : 500,
                color: isSelected ? "var(--white)" : "var(--neutral-600)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                transition: "color 200ms ease-in-out",
              }}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <p className="text-xs mt-2" style={{ color: "var(--neutral-600)" }}>
        Save ~17% with annual
      </p>
    </div>
  );
}
