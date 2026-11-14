/**
 * PricebookItemForm — form for creating or editing a pricebook item
 *
 * Location: apps/web/src/features/catalog/components/PricebookItemForm.tsx
 *
 * When isEdit=true, SKU is rendered as read-only text (immutable after creation).
 * Initial Unit Price is required on create but shown read-only on edit
 * (use UpdatePriceModal for price changes after creation).
 */

"use client";

import { useState } from "react";

export interface PricebookItemFormValues {
  sku: string;
  name: string;
  description: string;
  initial_price_dollars: string; // user enters dollars; caller converts to cents
  taxability_code: string;
}

interface PricebookItemFormProps {
  initialValues?: Partial<PricebookItemFormValues>;
  isEdit?: boolean; // when true, SKU is read-only
  onSubmit: (values: PricebookItemFormValues) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  submitLabel?: string;
  currentPriceCents?: number; // shown as reference when isEdit=true
}

const TAXABILITY_OPTIONS = [
  { value: "", label: "Select..." },
  { value: "taxable", label: "Taxable" },
  { value: "exempt", label: "Exempt" },
  { value: "non_taxable", label: "Non-taxable" },
];

export function PricebookItemForm({
  initialValues,
  isEdit = false,
  onSubmit,
  onCancel,
  isSubmitting,
  submitLabel,
  currentPriceCents,
}: PricebookItemFormProps) {
  const [sku, setSku] = useState(initialValues?.sku ?? "");
  const [name, setName] = useState(initialValues?.name ?? "");
  const [description, setDescription] = useState(
    initialValues?.description ?? "",
  );
  const [initialPriceDollars, setInitialPriceDollars] = useState(
    initialValues?.initial_price_dollars ?? "",
  );
  const [taxabilityCode, setTaxabilityCode] = useState(
    initialValues?.taxability_code ?? "",
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      sku,
      name,
      description,
      initial_price_dollars: initialPriceDollars,
      taxability_code: taxabilityCode,
    });
  }

  const labelClass = "block text-sm font-medium text-neutral-700 mb-1";
  const inputClass =
    "w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:border-brand-600";
  const readOnlyClass =
    "w-full rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-500";

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="space-y-4">
        {/* SKU */}
        <div>
          <label htmlFor="pb-sku" className={labelClass}>
            SKU <span className="text-error-600">*</span>
          </label>
          {isEdit ? (
            <div className={readOnlyClass} aria-label="SKU (read-only)">
              {sku}
            </div>
          ) : (
            <input
              id="pb-sku"
              type="text"
              required
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              className={inputClass}
              placeholder="e.g. SW-200A"
            />
          )}
          {isEdit && (
            <p className="mt-1 text-xs text-neutral-400">
              SKU cannot be changed after creation.
            </p>
          )}
        </div>

        {/* Name */}
        <div>
          <label htmlFor="pb-name" className={labelClass}>
            Name <span className="text-error-600">*</span>
          </label>
          <input
            id="pb-name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputClass}
            placeholder="e.g. 200A Service Panel"
          />
        </div>

        {/* Description */}
        <div>
          <label htmlFor="pb-description" className={labelClass}>
            Description
          </label>
          <textarea
            id="pb-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={inputClass}
            rows={2}
            placeholder="Optional description"
          />
        </div>

        {/* Unit Price */}
        <div>
          <label htmlFor="pb-price" className={labelClass}>
            Unit Price ($){" "}
            {!isEdit && <span className="text-error-600">*</span>}
          </label>
          {isEdit && currentPriceCents !== undefined ? (
            <div
              className={readOnlyClass}
              aria-label="Current price (read-only)"
            >
              ${(currentPriceCents / 100).toFixed(2)}{" "}
              <span className="text-xs text-neutral-400">
                (use &ldquo;Update Price&rdquo; to change)
              </span>
            </div>
          ) : (
            <input
              id="pb-price"
              type="number"
              min="0"
              step="0.01"
              required={!isEdit}
              value={initialPriceDollars}
              onChange={(e) => setInitialPriceDollars(e.target.value)}
              className={inputClass}
              placeholder="0.00"
            />
          )}
        </div>

        {/* Taxability Code */}
        <div>
          <label htmlFor="pb-taxability" className={labelClass}>
            Taxability
          </label>
          <select
            id="pb-taxability"
            value={taxabilityCode}
            onChange={(e) => setTaxabilityCode(e.target.value)}
            className={inputClass}
          >
            {TAXABILITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-6 flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 rounded-md border border-neutral-300 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50"
        >
          {isSubmitting
            ? "Saving…"
            : (submitLabel ?? (isEdit ? "Save Changes" : "Add Item"))}
        </button>
      </div>
    </form>
  );
}
