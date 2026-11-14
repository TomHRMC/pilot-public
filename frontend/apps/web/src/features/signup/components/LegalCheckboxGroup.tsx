/**
 * LegalCheckboxGroup — Step 2 legal checkboxes
 *
 * Location: apps/web/src/features/signup/components/LegalCheckboxGroup.tsx
 *
 * 3 required checkboxes (ToS, Privacy, EULA) + 1 optional (marketing email).
 * "Continue" is disabled until all 3 required boxes are checked.
 *
 * RULE 7: Does not trigger POST — only collects checkbox state.
 *         The parent page (SignupLegalPage) calls useSignupLegalAccept on submit.
 *
 * Token audit (Section H):
 *  - Required asterisk: text-fault-600
 *  - Continue disabled: opacity-40 cursor-not-allowed
 */

"use client";

import React from "react";

interface LegalCheckboxGroupProps {
  /** Called with { tos, privacy, eula, marketingEmail } when all required boxes checked */
  onAllRequiredChecked?: (checked: boolean) => void;
  /** Called when user clicks "Read full →" for a document */
  onReadDocument?: (docType: "tos" | "privacy" | "eula") => void;
  /** Initial checked states (e.g., from resumed session — but RULE 7: don't re-POST) */
  initialChecked?: {
    tos?: boolean;
    privacy?: boolean;
    eula?: boolean;
  };
  disabled?: boolean;
}

const REQUIRED_DOCS = [
  {
    key: "tos" as const,
    label: "Terms of Service",
    description: "I agree to the Pilot Terms of Service.",
  },
  {
    key: "privacy" as const,
    label: "Privacy Policy",
    description: "I agree to the Pilot Privacy Policy.",
  },
  {
    key: "eula" as const,
    label: "End User License Agreement",
    description: "I agree to the Pilot EULA.",
  },
];

export interface LegalCheckboxState {
  tos: boolean;
  privacy: boolean;
  eula: boolean;
  marketingEmail: boolean;
}

interface LegalCheckboxGroupWithStateProps extends LegalCheckboxGroupProps {
  value: LegalCheckboxState;
  onChange: (state: LegalCheckboxState) => void;
}

export function LegalCheckboxGroup({
  value,
  onChange,
  onReadDocument,
  disabled = false,
}: LegalCheckboxGroupWithStateProps) {
  const allRequiredChecked = value.tos && value.privacy && value.eula;

  const handleToggle = (key: keyof LegalCheckboxState) => {
    if (disabled) return;
    onChange({ ...value, [key]: !value[key] });
  };

  return (
    <div className="flex flex-col gap-4" data-testid="legal-checkbox-group">
      {REQUIRED_DOCS.map((doc) => (
        <div key={doc.key} className="flex items-start gap-3">
          <input
            type="checkbox"
            id={`legal-${doc.key}`}
            checked={value[doc.key]}
            onChange={() => handleToggle(doc.key)}
            disabled={disabled}
            aria-required="true"
            data-testid={`legal-checkbox-${doc.key}`}
            className={`
              mt-0.5 h-4 w-4 rounded focus:ring-brand-600 accent-brand-600
              ${!value[doc.key] ? "border-neutral-300" : ""}
            `}
          />
          <div className="flex flex-col gap-0.5 flex-1">
            <label
              htmlFor={`legal-${doc.key}`}
              className="text-sm font-medium text-neutral-900 cursor-pointer"
            >
              {doc.description}{" "}
              <span
                className="text-fault-600 text-xs align-super"
                aria-label="required"
              >
                *
              </span>
            </label>
            {onReadDocument && (
              <button
                type="button"
                onClick={() => onReadDocument(doc.key)}
                className="text-xs text-brand-600 hover:text-brand-800 w-fit focus:outline-none focus-visible:underline"
                aria-label={`Read full ${doc.label}`}
                data-testid={`legal-read-full-${doc.key}`}
              >
                Read full {doc.label} →
              </button>
            )}
          </div>
        </div>
      ))}

      {/* Optional: marketing email opt-in */}
      <div className="flex items-start gap-3 pt-2 border-t border-neutral-100">
        <input
          type="checkbox"
          id="legal-marketing-email"
          checked={value.marketingEmail}
          onChange={() => handleToggle("marketingEmail")}
          disabled={disabled}
          data-testid="legal-checkbox-marketing-email"
          className="mt-0.5 h-4 w-4 rounded focus:ring-brand-600 accent-brand-600"
        />
        <label
          htmlFor="legal-marketing-email"
          className="text-sm text-neutral-600 cursor-pointer"
        >
          I&apos;d like to receive product updates and tips from Pilot.{" "}
          <span className="text-neutral-400 text-xs">(Optional)</span>
        </label>
      </div>

      {/* Helper text when not all required docs checked */}
      {!allRequiredChecked && (
        <p
          role="status"
          aria-live="polite"
          className="text-xs text-neutral-500 mt-1"
          data-testid="legal-required-helper"
        >
          All three agreements are required to continue.
        </p>
      )}
    </div>
  );
}
