/**
 * CustomerForm — shared form for create and edit customer
 *
 * Location: apps/web/src/features/customers/components/CustomerForm.tsx
 *
 * Used by CreateCustomerModal (create) and CustomerOverviewTab (inline edit).
 * Type selector conditionally shows person vs company name fields.
 * Display Name is always required regardless of type.
 *
 * DLC-1: Added sms_attestation_checked + sms_consent_ip_address to form values.
 * Submit is blocked when mobile_phone is present but sms_attestation_checked is false.
 */

"use client";

import { useState } from "react";
import { z } from "zod";
import { PhoneInput } from "@pilot/ui/phone-input";

export interface CustomerFormValues {
  type: "person" | "company";
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  email: string | null;
  mobile_phone: string | null;
  // DLC-1: SMS offline consent attestation
  sms_attestation_checked?: boolean;
  sms_consent_ip_address?: string;
}

interface CustomerFormProps {
  initialValues?: Partial<CustomerFormValues>;
  onSubmit: (values: CustomerFormValues) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  submitLabel?: string;
}

const INPUT_CLASS =
  "w-full border border-neutral-200 rounded-md px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-400";

const LABEL_CLASS = "block text-sm font-medium text-neutral-700 mb-1";

export function CustomerForm({
  initialValues,
  onSubmit,
  onCancel,
  isSubmitting,
  submitLabel = "Save",
}: CustomerFormProps) {
  const [type, setType] = useState<"person" | "company">(
    initialValues?.type ?? "person",
  );
  const [displayName, setDisplayName] = useState(
    initialValues?.display_name ?? "",
  );
  const [firstName, setFirstName] = useState(initialValues?.first_name ?? "");
  const [lastName, setLastName] = useState(initialValues?.last_name ?? "");
  const [companyName, setCompanyName] = useState(
    initialValues?.company_name ?? "",
  );
  const [email, setEmail] = useState(initialValues?.email ?? "");
  const [mobilePhone, setMobilePhone] = useState<string | null>(
    initialValues?.mobile_phone ?? null,
  );
  // DLC-1: SMS consent attestation state
  const [smsAttestationChecked, setSmsAttestationChecked] = useState(
    initialValues?.sms_attestation_checked ?? false,
  );

  // PLP-FIX-4 Issue 10: entry-time email validation (Zod v4 top-level z.email()).
  // Field-level safeParse on the existing useState pattern — no RHF rewrite (design §G Q5).
  const emailError =
    email.trim() && !z.email().safeParse(email.trim()).success
      ? "Enter a valid email address."
      : null;

  // DLC-1: submit is blocked if phone present but attestation not checked.
  // PLP-FIX-4: mobilePhone is now string | null (E.164 or null from PhoneInput).
  const isSubmitDisabled =
    isSubmitting ||
    !displayName.trim() ||
    !!emailError ||
    (mobilePhone != null && !smsAttestationChecked);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      type,
      display_name: displayName.trim(),
      first_name: firstName.trim() || null,
      last_name: lastName.trim() || null,
      company_name: companyName.trim() || null,
      email: email.trim() || null,
      mobile_phone: mobilePhone,
      // DLC-1: include attestation fields
      sms_attestation_checked: smsAttestationChecked,
      // sms_consent_ip_address: omitted — backend defaults to "unknown"
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      {/* Type selector */}
      <div className="mb-4">
        <span className={LABEL_CLASS}>Type</span>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm text-neutral-700 cursor-pointer">
            <input
              type="radio"
              name="customer-type"
              value="person"
              checked={type === "person"}
              onChange={() => setType("person")}
              className="accent-brand-600"
            />
            Person
          </label>
          <label className="flex items-center gap-2 text-sm text-neutral-700 cursor-pointer">
            <input
              type="radio"
              name="customer-type"
              value="company"
              checked={type === "company"}
              onChange={() => setType("company")}
              className="accent-brand-600"
            />
            Company
          </label>
        </div>
      </div>

      {/* Conditional name fields */}
      {type === "person" ? (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label htmlFor="customer-first-name" className={LABEL_CLASS}>
              First Name
            </label>
            <input
              id="customer-first-name"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="First"
              className={INPUT_CLASS}
              autoComplete="given-name"
            />
          </div>
          <div>
            <label htmlFor="customer-last-name" className={LABEL_CLASS}>
              Last Name
            </label>
            <input
              id="customer-last-name"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Last"
              className={INPUT_CLASS}
              autoComplete="family-name"
            />
          </div>
        </div>
      ) : (
        <div className="mb-4">
          <label htmlFor="customer-company-name" className={LABEL_CLASS}>
            Company Name
          </label>
          <input
            id="customer-company-name"
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="Acme Electrical LLC"
            className={INPUT_CLASS}
            autoComplete="organization"
          />
        </div>
      )}

      {/* Display Name — always required */}
      <div className="mb-4">
        <label htmlFor="customer-display-name" className={LABEL_CLASS}>
          Display Name <span className="text-alert-600">*</span>
        </label>
        <input
          id="customer-display-name"
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="How this customer appears throughout the app"
          className={INPUT_CLASS}
          required
          aria-required="true"
        />
      </div>

      {/* Email */}
      <div className="mb-4">
        <label htmlFor="customer-email" className={LABEL_CLASS}>
          Email
        </label>
        <input
          id="customer-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="customer@example.com"
          className={INPUT_CLASS}
          autoComplete="email"
          aria-invalid={!!emailError}
          aria-describedby={emailError ? "customer-email-error" : undefined}
        />
        {emailError && (
          <p
            id="customer-email-error"
            className="text-fault-600 text-sm mt-1"
            role="alert"
          >
            {emailError}
          </p>
        )}
      </div>

      {/* Mobile Phone */}
      <div className="mb-4">
        <label htmlFor="customer-mobile-phone" className={LABEL_CLASS}>
          Mobile Phone
        </label>
        <PhoneInput
          id="customer-mobile-phone"
          value={mobilePhone ?? ""}
          onChange={(e164) => setMobilePhone(e164)}
          className={INPUT_CLASS}
          autoComplete="tel"
          data-testid="customer-mobile-phone"
        />
      </div>

      {/* DLC-1: SMS Offline Consent Attestation — required when phone is entered */}
      {mobilePhone != null && (
        <div className="mb-6 p-4 border border-neutral-200 rounded-md bg-neutral-50">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              id="sms-attestation-checkbox"
              checked={smsAttestationChecked}
              onChange={(e) => setSmsAttestationChecked(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
              data-testid="sms-attestation-checkbox"
            />
            <span className="text-sm text-neutral-700 leading-relaxed">
              I confirm that I have received explicit, documented consent from
              this customer to send them SMS notifications regarding their
              service. I understand that sending unsolicited messages violates
              platform policy and federal law.
            </span>
          </label>
          {mobilePhone != null && !smsAttestationChecked && (
            <p
              className="mt-2 text-xs text-alert-600"
              data-testid="sms-attestation-warning"
              role="alert"
            >
              ⚠ You must confirm consent before saving a mobile phone number.
            </p>
          )}
          {/* DLC-B2: Consumer-facing 10DLC disclosure — required for MNO campaign review */}
          <p
            className="mt-3 text-xs text-neutral-600 leading-relaxed"
            data-testid="customer-sms-consent-disclosure"
          >
            By saving a mobile number, this customer will receive service SMS
            from Pilot for Trades on behalf of your business — appointment
            reminders, job updates, and invoice links. Message frequency varies.
            Msg &amp; data rates may apply. Reply STOP to opt out, HELP for
            help. See our{" "}
            <a
              href="https://www.pilotfortrades.com/legal/privacy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-600 underline hover:text-brand-700"
            >
              Privacy Policy
            </a>
            .
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3">
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
          disabled={isSubmitDisabled}
          className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md disabled:opacity-50 transition-colors"
          data-testid="customer-form-submit"
        >
          {isSubmitting ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
