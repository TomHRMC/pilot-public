/**
 * WizardProgressBar — 5-step visual progress indicator
 *
 * Location: apps/web/src/features/signup/components/WizardProgressBar.tsx
 *
 * Token audit (Section H):
 *  - Completed step: bg-brand-600 (brand indigo — design doc uses brand-600 for all completed)
 *  - Current step: bg-brand-300 (mid-brand for active step)
 *  - Future step: bg-neutral-200 (neutral for pending)
 */

"use client";

import React from "react";

const STEPS = [
  { key: "account", label: "Account" },
  { key: "verify", label: "Verify" },
  { key: "legal", label: "Legal" },
  { key: "phone", label: "Phone" },
  { key: "plan", label: "Plan" },
  { key: "ready", label: "Ready" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

interface WizardProgressBarProps {
  currentStep: string;
  className?: string;
}

function getStepStatus(
  stepKey: StepKey,
  currentStep: string,
): "completed" | "current" | "pending" {
  const stepOrder = STEPS.map((s) => s.key);
  const currentIndex = stepOrder.indexOf(currentStep as StepKey);
  const thisIndex = stepOrder.indexOf(stepKey);

  if (currentIndex === -1) return "pending";
  if (thisIndex < currentIndex) return "completed";
  if (thisIndex === currentIndex) return "current";
  return "pending";
}

export function WizardProgressBar({
  currentStep,
  className,
}: WizardProgressBarProps) {
  return (
    <nav
      aria-label="Signup progress"
      className={`flex items-center justify-center gap-2 ${className ?? ""}`}
    >
      {STEPS.map((step, index) => {
        const status = getStepStatus(step.key, currentStep);

        return (
          <React.Fragment key={step.key}>
            {/* Step dot + label */}
            <div className="flex flex-col items-center gap-1">
              <div
                role="img"
                aria-label={`Step ${index + 1}: ${step.label} — ${status}`}
                data-testid={`wizard-step-dot-${step.key}`}
                className={`
                  w-2.5 h-2.5 rounded-full transition-colors
                  ${
                    status === "completed"
                      ? "bg-brand-600"
                      : status === "current"
                        ? "bg-brand-300"
                        : "bg-neutral-200"
                  }
                `}
              />
              <span
                className={`text-xs font-medium hidden sm:block ${
                  status === "current"
                    ? "text-brand-600"
                    : status === "completed"
                      ? "text-neutral-600"
                      : "text-neutral-400"
                }`}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line (not after last step) */}
            {index < STEPS.length - 1 && (
              <div
                aria-hidden="true"
                className={`
                  h-0.5 w-8 sm:w-12 rounded-full transition-colors
                  ${
                    getStepStatus(step.key, currentStep) === "completed"
                      ? "bg-brand-600"
                      : "bg-neutral-200"
                  }
                `}
              />
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
