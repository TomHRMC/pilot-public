/**
 * SiteForm — shared form for create and edit site
 *
 * Location: apps/web/src/features/customers/components/SiteForm.tsx
 *
 * Used by SiteListPanel modal for both add and edit operations.
 * Name is the only required field (customer_id is passed separately).
 * Address sub-section is optional.
 */

"use client";

import { useState } from "react";
import type {
  SiteCreateRequest,
  AddressCreateInput,
} from "../hooks/useCreateSite";

export interface SiteFormValues {
  name: string;
  notes: string;
  jurisdiction_code: string;
  gate_code?: string; // Note: not in SiteCreate schema, stored in notes for MVP
  site_type?: "commercial" | "residential" | "industrial" | null;
  address: {
    line1: string;
    line2: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  showAddress: boolean;
}

interface SiteFormProps {
  customerId: string;
  initialValues?: Partial<SiteFormValues>;
  customerType?: "person" | "company";
  onSubmit: (data: SiteCreateRequest) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  submitLabel?: string;
}

const INPUT_CLASS =
  "w-full border border-neutral-200 rounded-md px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-400";

const LABEL_CLASS = "block text-sm font-medium text-neutral-700 mb-1";

export function SiteForm({
  customerId,
  initialValues,
  customerType,
  onSubmit,
  onCancel,
  isSubmitting,
  submitLabel = "Save",
}: SiteFormProps) {
  const defaultSiteType =
    initialValues?.site_type ??
    (customerType === "company" ? "commercial" : "residential");
  const [name, setName] = useState(initialValues?.name ?? "");
  const [notes, setNotes] = useState(initialValues?.notes ?? "");
  const [siteType, setSiteType] = useState<
    "commercial" | "residential" | "industrial"
  >(defaultSiteType ?? "residential");
  const [jurisdictionCode, setJurisdictionCode] = useState(
    initialValues?.jurisdiction_code ?? "",
  );
  const [showAddress, setShowAddress] = useState(
    initialValues?.showAddress ?? false,
  );
  const [line1, setLine1] = useState(initialValues?.address?.line1 ?? "");
  const [line2, setLine2] = useState(initialValues?.address?.line2 ?? "");
  const [city, setCity] = useState(initialValues?.address?.city ?? "");
  const [state, setState] = useState(initialValues?.address?.state ?? "");
  const [postalCode, setPostalCode] = useState(
    initialValues?.address?.postal_code ?? "",
  );
  const [country, setCountry] = useState(
    initialValues?.address?.country ?? "US",
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    let address: AddressCreateInput | null = null;
    if (showAddress && (line1.trim() || city.trim())) {
      address = {
        line1: line1.trim() || null,
        line2: line2.trim() || null,
        city: city.trim() || null,
        state: state.trim() || null,
        postal_code: postalCode.trim() || null,
        country: country.trim() || "US",
      };
    }

    onSubmit({
      customer_id: customerId,
      name: name.trim() || null,
      notes: notes.trim() || null,
      jurisdiction_code: jurisdictionCode.trim() || null,
      address,
      site_type: siteType,
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      {/* Name */}
      <div className="mb-4">
        <label htmlFor="site-name" className={LABEL_CLASS}>
          Site Name <span className="text-alert-600">*</span>
        </label>
        <input
          id="site-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Main Office"
          className={INPUT_CLASS}
          required
          aria-required="true"
        />
      </div>

      {/* Site Type */}
      <div className="mb-4">
        <label htmlFor="site-type" className={LABEL_CLASS}>
          Site Type
        </label>
        <select
          id="site-type"
          value={siteType}
          onChange={(e) =>
            setSiteType(
              e.target.value as "commercial" | "residential" | "industrial",
            )
          }
          className={INPUT_CLASS}
          data-testid="site-type-select"
        >
          <option value="commercial">Commercial</option>
          <option value="residential">Residential</option>
          <option value="industrial">Industrial</option>
        </select>
      </div>

      {/* Notes */}
      <div className="mb-4">
        <label htmlFor="site-notes" className={LABEL_CLASS}>
          Notes
        </label>
        <textarea
          id="site-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Gate code, access instructions, hazard notes..."
          rows={3}
          className={`${INPUT_CLASS} resize-none`}
        />
      </div>

      {/* Jurisdiction Code */}
      <div className="mb-4">
        <label htmlFor="site-jurisdiction" className={LABEL_CLASS}>
          Jurisdiction Code
        </label>
        <input
          id="site-jurisdiction"
          type="text"
          value={jurisdictionCode}
          onChange={(e) => setJurisdictionCode(e.target.value)}
          placeholder="e.g. TX-AUSTIN"
          className={INPUT_CLASS}
        />
      </div>

      {/* Address toggle */}
      <div className="mb-4">
        <button
          type="button"
          onClick={() => setShowAddress(!showAddress)}
          className="text-sm text-brand-600 hover:text-brand-700 font-medium"
        >
          {showAddress ? "− Hide address" : "+ Add address"}
        </button>
      </div>

      {showAddress && (
        <div className="mb-4 p-4 bg-neutral-50 rounded-md space-y-3">
          <div>
            <label htmlFor="site-line1" className={LABEL_CLASS}>
              Address Line 1
            </label>
            <input
              id="site-line1"
              type="text"
              value={line1}
              onChange={(e) => setLine1(e.target.value)}
              placeholder="123 Main St"
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label htmlFor="site-line2" className={LABEL_CLASS}>
              Address Line 2
            </label>
            <input
              id="site-line2"
              type="text"
              value={line2}
              onChange={(e) => setLine2(e.target.value)}
              placeholder="Suite 200"
              className={INPUT_CLASS}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="site-city" className={LABEL_CLASS}>
                City
              </label>
              <input
                id="site-city"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Austin"
                className={INPUT_CLASS}
              />
            </div>
            <div>
              <label htmlFor="site-state" className={LABEL_CLASS}>
                State
              </label>
              <input
                id="site-state"
                type="text"
                value={state}
                onChange={(e) => setState(e.target.value)}
                placeholder="TX"
                maxLength={2}
                className={INPUT_CLASS}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="site-postal" className={LABEL_CLASS}>
                Postal Code
              </label>
              <input
                id="site-postal"
                type="text"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                placeholder="78701"
                className={INPUT_CLASS}
              />
            </div>
            <div>
              <label htmlFor="site-country" className={LABEL_CLASS}>
                Country
              </label>
              <input
                id="site-country"
                type="text"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="US"
                maxLength={2}
                className={INPUT_CLASS}
              />
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 text-sm font-medium text-neutral-800 border border-neutral-200 rounded-md hover:bg-neutral-100 disabled:opacity-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting || !name.trim()}
          className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md disabled:opacity-50 transition-colors"
          data-testid="site-form-submit"
        >
          {isSubmitting ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
