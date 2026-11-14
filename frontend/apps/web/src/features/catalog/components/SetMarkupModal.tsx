/**
 * SetMarkupModal — modal for setting a markup % for a category (temporal supersession)
 *
 * Location: apps/web/src/features/catalog/components/SetMarkupModal.tsx
 *
 * Category dropdown loaded from GET /api/v1/job-expense-categories.
 * Falls back to hardcoded 3 values if endpoint unavailable (deterministic seed data).
 * Pattern: temporal supersession via POST /api/v1/settings/markups
 * Field: job_expense_category_code (NOT category_code)
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useSetMarkup } from "../hooks/useSetMarkup";

const FALLBACK_CATEGORIES = [
  { code: "materials", label: "Materials" },
  { code: "equipment", label: "Equipment" },
  { code: "permits", label: "Permits" },
];

interface JobExpenseCategory {
  code: string;
  label: string;
}

interface SetMarkupModalProps {
  open: boolean;
  onClose: () => void;
}

export function SetMarkupModal({ open, onClose }: SetMarkupModalProps) {
  const { mutate, isPending, reset } = useSetMarkup();
  const firstFocusRef = useRef<HTMLDivElement>(null);

  const [categoryCode, setCategoryCode] = useState(FALLBACK_CATEGORIES[0].code);
  const [markupPct, setMarkupPct] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(
    new Date().toISOString().slice(0, 10),
  );

  // Load categories from API — fall back to hardcoded on error
  const { data: categoriesData } = useQuery({
    queryKey: ["job-expense-categories"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/job-expense-categories");
      return (res.data as { categories: JobExpenseCategory[] }).categories;
    },
    staleTime: 300_000,
    retry: 1,
  });

  const categories = categoriesData ?? FALLBACK_CATEGORIES;

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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const effectiveFromISO = new Date(
      effectiveFrom + "T00:00:00Z",
    ).toISOString();
    mutate(
      {
        job_expense_category_code: categoryCode,
        markup_pct: parseFloat(markupPct),
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
      aria-labelledby="set-markup-modal-title"
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
              id="set-markup-modal-title"
              className="text-lg font-semibold text-neutral-900"
            >
              Set Markup
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
              {/* Category */}
              <div>
                <label
                  htmlFor="markup-category"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Category <span className="text-error-600">*</span>
                </label>
                <select
                  id="markup-category"
                  value={categoryCode}
                  onChange={(e) => setCategoryCode(e.target.value)}
                  className={inputClass}
                >
                  {categories.map((cat) => (
                    <option key={cat.code} value={cat.code}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Markup % */}
              <div>
                <label
                  htmlFor="markup-pct"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Markup % <span className="text-error-600">*</span>
                </label>
                <input
                  id="markup-pct"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  required
                  value={markupPct}
                  onChange={(e) => setMarkupPct(e.target.value)}
                  className={inputClass}
                  placeholder="0"
                />
              </div>

              {/* Effective From */}
              <div>
                <label
                  htmlFor="effective-from-markup"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Effective From <span className="text-error-600">*</span>
                </label>
                <input
                  id="effective-from-markup"
                  type="date"
                  required
                  value={effectiveFrom}
                  onChange={(e) => setEffectiveFrom(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            <p className="mt-3 text-xs text-neutral-400">
              Posting a new markup for this category supersedes the current
              value.
            </p>

            <div className="mt-4 flex justify-end gap-3">
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
                disabled={isPending || !markupPct || !categoryCode}
                className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50"
              >
                {isPending ? "Saving…" : "Set Markup"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
