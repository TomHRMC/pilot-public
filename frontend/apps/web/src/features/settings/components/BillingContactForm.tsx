/**
 * BillingContactForm — STRIPE-CONNECT-1-C (B5)
 *
 * Location: apps/web/src/features/settings/components/BillingContactForm.tsx
 *
 * Two labeled inputs (phone / email) composing the existing settings-form pattern.
 * Authed surface → apiClient + TanStack Query v5 + RHF 7 + Zod v4.
 *
 * Helper copy: "Shown to customers on your invoice payment page when card payments are off."
 * Empty-state nudge when both values are null: "Add a billing contact so customers can reach you to arrange payment."
 *
 * Empty string clears = send explicit null; omitted = unchanged — mirrors the backend's
 * model_fields_set semantics: always send both keys, null when empty.
 *
 * RBAC is enforced by the page's <RoleGate permission="settings.tenant.write"> — no second gate here.
 */

"use client";

import React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { PhoneInput } from "@pilot/ui/phone-input";
import {
  usePaymentContact,
  useUpdatePaymentContact,
} from "../hooks/usePaymentContact";

// Zod v4: top-level z.email(), unified error param (rules §34)
const billingContactSchema = z.object({
  billing_contact_email: z
    .email({ error: "Enter a valid email address" })
    .optional()
    .or(z.literal("")),
  billing_contact_phone: z
    .string()
    .trim()
    .max(32, { error: "Phone must be 32 characters or fewer" })
    .optional(),
});

type BillingContactFormValues = z.infer<typeof billingContactSchema>;

export function BillingContactForm() {
  const { data, isLoading } = usePaymentContact();
  const updateMutation = useUpdatePaymentContact();

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isDirty },
  } = useForm<BillingContactFormValues>({
    resolver: zodResolver(billingContactSchema),
    // Hydrate once the GET resolves; defaultValues are stable per render cycle
    values: {
      billing_contact_email: data?.billing_contact_email ?? "",
      billing_contact_phone: data?.billing_contact_phone ?? "",
    },
  });

  const bothEmpty =
    !data?.billing_contact_phone && !data?.billing_contact_email;

  function onSubmit(values: BillingContactFormValues) {
    // Always send both keys; empty string → null (clears). Mirrors model_fields_set semantics.
    const payload = {
      billing_contact_phone: values.billing_contact_phone?.trim()
        ? values.billing_contact_phone.trim()
        : null,
      billing_contact_email: values.billing_contact_email?.trim()
        ? values.billing_contact_email.trim()
        : null,
    };
    updateMutation.mutate(payload, {
      onSuccess: () => {
        // Reset dirty state to the saved values
        reset({
          billing_contact_email: payload.billing_contact_email ?? "",
          billing_contact_phone: payload.billing_contact_phone ?? "",
        });
      },
    });
  }

  if (isLoading) {
    return (
      <div className="animate-pulse" data-testid="billing-contact-form-loading">
        <div className="h-5 w-48 bg-neutral-200 rounded" />
        <div className="mt-4 h-10 w-full bg-neutral-100 rounded-md" />
        <div className="mt-3 h-10 w-full bg-neutral-100 rounded-md" />
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="mt-4"
      data-testid="billing-contact-form"
      noValidate
    >
      <div className="flex items-center gap-2">
        <h4 className="text-sm font-medium text-neutral-900">
          Billing contact
        </h4>
      </div>
      <p className="text-xs text-neutral-500 mt-1">
        Shown to customers on your invoice payment page when card payments are
        off.
      </p>

      {bothEmpty && (
        <p className="text-xs text-neutral-600 mt-3">
          Add a billing contact so customers can reach you to arrange payment.
        </p>
      )}

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Phone */}
        <div>
          <label
            htmlFor="billing-contact-phone"
            className="block text-sm font-medium text-neutral-700"
          >
            Billing contact phone
          </label>
          <Controller
            control={control}
            name="billing_contact_phone"
            render={({ field }) => (
              <PhoneInput
                id="billing-contact-phone"
                value={field.value ?? ""}
                onChange={(e164) => field.onChange(e164 ?? "")}
                onBlur={field.onBlur}
                autoComplete="tel"
                className="mt-1 block w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                data-testid="billing-contact-phone-input"
              />
            )}
          />
        </div>

        {/* Email */}
        <div>
          <label
            htmlFor="billing-contact-email"
            className="block text-sm font-medium text-neutral-700"
          >
            Billing contact email
          </label>
          <input
            id="billing-contact-email"
            type="email"
            autoComplete="email"
            aria-invalid={!!errors.billing_contact_email}
            aria-describedby={
              errors.billing_contact_email
                ? "billing-contact-email-error"
                : undefined
            }
            {...register("billing_contact_email")}
            className="mt-1 block w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            data-testid="billing-contact-email-input"
          />
          {errors.billing_contact_email && (
            <p
              id="billing-contact-email-error"
              className="mt-1 text-xs text-fault-600"
              data-testid="billing-contact-email-error"
            >
              {errors.billing_contact_email.message}
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          type="submit"
          disabled={updateMutation.isPending || !isDirty}
          className="inline-flex items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
          data-testid="billing-contact-save-button"
        >
          {updateMutation.isPending ? "Saving…" : "Save"}
        </button>

        {updateMutation.isSuccess && (
          <span
            className="text-xs text-margin-700"
            data-testid="billing-contact-save-success"
          >
            Saved
          </span>
        )}
        {updateMutation.isError && (
          <span
            className="text-xs text-fault-600"
            data-testid="billing-contact-save-error"
          >
            Could not save. Please try again.
          </span>
        )}
      </div>
    </form>
  );
}
