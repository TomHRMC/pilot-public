"use client";

/**
 * EntityTypeSelector — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/EntityTypeSelector.tsx
 *
 * "Does your business have an EIN?" → Yes (standard) / No (sole_proprietor).
 * Two selectable cards with help text explaining the difference.
 *
 * UI spec §4.2. WCAG 2.2 AA: color-independent selection (CheckCircleIcon +
 * ring + aria-checked), ≥24×24px targets, focus-visible rings.
 *
 * RULE 5: all tokens via Tailwind utilities — zero hex codes.
 * RULE 11: no hand-written useMemo/useCallback (React Compiler).
 */

import React from "react";
import {
  CheckCircleIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import { CheckCircleIcon as CheckCircleIconSolid } from "@heroicons/react/24/solid";
import type { EntityType } from "@/features/messaging/types";

export interface EntityTypeSelectorProps {
  value: EntityType | null;
  onChange: (value: EntityType) => void;
  disabled?: boolean;
}

const CARD_BASE =
  "border rounded-lg p-4 cursor-pointer transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none";
const CARD_DEFAULT = "border-neutral-200 bg-white hover:bg-neutral-50";
const CARD_SELECTED = "border-brand-500 bg-brand-50 ring-2 ring-brand-500";

export function EntityTypeSelector({
  value,
  onChange,
  disabled = false,
}: EntityTypeSelectorProps) {
  const options: {
    value: EntityType;
    label: string;
    description: string;
    helpTitle: string;
    helpText: string;
    helpClass: string;
  }[] = [
    {
      value: "standard",
      label: "Yes, we have an EIN",
      description:
        "Standard brand registration. Automated path. Faster approval.",
      helpTitle: "Standard",
      helpText:
        "Automated brand registration with the carrier. Faster approval.",
      helpClass: "bg-brand-50 border border-brand-200 text-brand-700",
    },
    {
      value: "sole_proprietor",
      label: "No, I'm a sole proprietor",
      description: "OTP verification loop required. ~1,000 msg/day cap.",
      helpTitle: "Sole Proprietor",
      helpText:
        "Carrier sends a PIN via SMS to your business phone. You enter it here to verify. Lower throughput cap.",
      helpClass: "bg-alert-50 border border-alert-200 text-alert-700",
    },
  ];

  return (
    <fieldset className="space-y-4" disabled={disabled}>
      <legend className="sr-only">Business type</legend>
      <div>
        <h2 className="text-h2 font-semibold text-neutral-900">
          Business Type
        </h2>
        <p className="text-sm text-neutral-500 mt-1">
          Does your business have an EIN (Employer Identification Number)?
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {options.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={isSelected}
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              className={`${CARD_BASE} ${
                isSelected ? CARD_SELECTED : CARD_DEFAULT
              } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
              data-testid={`entity-type-${opt.value}`}
            >
              <div className="flex items-start gap-3">
                {isSelected ? (
                  <CheckCircleIconSolid className="w-5 h-5 text-brand-600 shrink-0" />
                ) : (
                  <CheckCircleIcon className="w-5 h-5 text-neutral-400 shrink-0" />
                )}
                <div>
                  <p className="text-sm font-medium text-neutral-900">
                    {opt.label}
                  </p>
                  <p className="text-xs text-neutral-500 mt-1">
                    {opt.description}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {options.map((opt) => {
        const isSelected = value === opt.value;
        if (!isSelected) return null;
        return (
          <div
            key={`help-${opt.value}`}
            className={`rounded-md p-3 text-sm flex items-start gap-2 ${opt.helpClass}`}
            data-testid={`entity-type-help-${opt.value}`}
          >
            <InformationCircleIcon className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">{opt.helpTitle}</p>
              <p className="mt-0.5">{opt.helpText}</p>
            </div>
          </div>
        );
      })}
    </fieldset>
  );
}
