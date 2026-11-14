/**
 * SetLaborRateModal — modal for creating/superseding a labor rate version
 *
 * Location: apps/web/src/features/catalog/components/SetLaborRateModal.tsx
 *
 * Pattern: temporal supersession via POST /api/v1/settings
 * Burdened rate preview = hourly_rate × (1 + burden_pct), shown live.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useSetLaborRate } from "../hooks/useSetLaborRate";

interface SetLaborRateModalProps {
  open: boolean;
  onClose: () => void;
}

const SKILL_LEVEL_OPTIONS = [
  { value: "master", label: "Master Electrician" },
  { value: "journeyman", label: "Journeyman" },
  { value: "apprentice", label: "Apprentice" },
  { value: "__custom__", label: "Custom…" },
];

export function SetLaborRateModal({ open, onClose }: SetLaborRateModalProps) {
  const { mutate, isPending, reset } = useSetLaborRate();
  const firstFocusRef = useRef<HTMLDivElement>(null);

  const [skillLevel, setSkillLevel] = useState("master");
  const [customSkillLevel, setCustomSkillLevel] = useState("");
  const [hourlyRateDollars, setHourlyRateDollars] = useState("");
  const [burdenPctStr, setBurdenPctStr] = useState("0");
  const [effectiveFrom, setEffectiveFrom] = useState(
    new Date().toISOString().slice(0, 10),
  );

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  // Focus trap on open
  useEffect(() => {
    if (open) {
      setTimeout(() => firstFocusRef.current?.focus(), 50);
    } else {
      reset();
    }
  }, [open, reset]);

  if (!open) return null;

  const hourlyRate = parseFloat(hourlyRateDollars) || 0;
  const burdenPct = parseFloat(burdenPctStr) || 0;
  // burdened rate preview — same formula as backend: hourly_rate_cents * (1 + burden_pct)
  const burdenedRate = hourlyRate * (1 + burdenPct / 100);

  const resolvedSkillLevel =
    skillLevel === "__custom__" ? customSkillLevel : skillLevel;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const hourlyRateCents = Math.round(hourlyRate * 100);
    const burdenPctDecimal = burdenPct / 100;
    const effectiveFromISO = new Date(
      effectiveFrom + "T00:00:00Z",
    ).toISOString();

    mutate(
      {
        skill_level_code: resolvedSkillLevel,
        hourly_rate_cents: hourlyRateCents,
        burden_pct: burdenPctDecimal,
        effective_from: effectiveFromISO,
      },
      { onSuccess: () => onClose() },
    );
  }

  const inputClass =
    "w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="set-labor-rate-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={firstFocusRef}
        tabIndex={-1}
        className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4 focus:outline-none"
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2
              id="set-labor-rate-modal-title"
              className="text-lg font-semibold text-neutral-900"
            >
              Set Labor Rate
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="text-neutral-400 hover:text-neutral-600 transition-colors"
              aria-label="Close modal"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            <div className="space-y-4">
              {/* Skill Level */}
              <div>
                <label
                  htmlFor="skill-level-select"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Skill Level <span className="text-error-600">*</span>
                </label>
                <select
                  id="skill-level-select"
                  value={skillLevel}
                  onChange={(e) => setSkillLevel(e.target.value)}
                  className={inputClass}
                >
                  {SKILL_LEVEL_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                {skillLevel === "__custom__" && (
                  <input
                    type="text"
                    placeholder="Enter skill level code"
                    value={customSkillLevel}
                    onChange={(e) => setCustomSkillLevel(e.target.value)}
                    className={`mt-2 ${inputClass}`}
                    required
                  />
                )}
              </div>

              {/* Hourly Rate */}
              <div>
                <label
                  htmlFor="hourly-rate"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Hourly Rate ($) <span className="text-error-600">*</span>
                </label>
                <input
                  id="hourly-rate"
                  type="number"
                  min="0.01"
                  step="0.01"
                  required
                  value={hourlyRateDollars}
                  onChange={(e) => setHourlyRateDollars(e.target.value)}
                  className={inputClass}
                  placeholder="0.00"
                />
              </div>

              {/* Burden % */}
              <div>
                <label
                  htmlFor="burden-pct"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Burden %{" "}
                  <span className="text-xs text-neutral-400">(0–999.99)</span>
                </label>
                <input
                  id="burden-pct"
                  type="number"
                  min="0"
                  max="999.99"
                  step="0.01"
                  value={burdenPctStr}
                  onChange={(e) => setBurdenPctStr(e.target.value)}
                  className={inputClass}
                  placeholder="0"
                />
              </div>

              {/* Burdened Rate Preview */}
              {hourlyRate > 0 && (
                <div className="rounded-md bg-neutral-50 border border-neutral-200 px-4 py-3">
                  <p className="text-sm text-neutral-600">
                    Burdened Rate:{" "}
                    <span className="font-semibold text-neutral-900">
                      ${burdenedRate.toFixed(2)}/hr
                    </span>
                    <span className="text-xs text-neutral-400 ml-2">
                      (${hourlyRate.toFixed(2)} × (1 + {burdenPct}%))
                    </span>
                  </p>
                </div>
              )}

              {/* Effective From */}
              <div>
                <label
                  htmlFor="effective-from-lr"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Effective From <span className="text-error-600">*</span>
                </label>
                <input
                  id="effective-from-lr"
                  type="date"
                  required
                  value={effectiveFrom}
                  onChange={(e) => setEffectiveFrom(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isPending}
                className="px-4 py-2 rounded-md border border-neutral-300 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={
                  isPending ||
                  !hourlyRateDollars ||
                  (skillLevel === "__custom__" && !customSkillLevel)
                }
                className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50"
              >
                {isPending ? "Saving…" : "Set Rate"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
