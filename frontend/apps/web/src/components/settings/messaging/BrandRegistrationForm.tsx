"use client";

/**
 * BrandRegistrationForm — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/BrandRegistrationForm.tsx
 *
 * Form for brand registration data. Pre-filled from tenant_10dlc_profile
 * (via existing use10DlcProfile hook). Submits via useInitiateProvisioning
 * mutation (POST /messaging/provision).
 *
 * UI spec §4.3. Zod v4 + React Hook Form validation.
 * RULE 5: zero hex codes. RULE 11: no hand-memo. RULE 13: Zod v4.
 */

import React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { RoleGate, LoadingState, ErrorState } from "@pilot/ui";
import { PhoneInput } from "@pilot/ui/phone-input";
import { use10DlcProfile } from "@/features/sms-compliance/hooks/use10DlcProfile";
import { useInitiateProvisioning } from "@/features/messaging/hooks/useInitiateProvisioning";
import { useCarrierVerticals } from "@/features/messaging/hooks/useCarrierVerticals";
import { useNotificationQueue } from "@pilot/ui";
import type { EntityType } from "@/features/messaging/types";

const LABEL_CLASS = "block text-sm font-medium text-neutral-700 mb-1";
const INPUT_CLASS =
  "w-full border border-neutral-200 rounded-md px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent";
const ERROR_TEXT_CLASS = "text-xs text-fault-600 mt-1";

// ── Single unified schema — conditional validation via superRefine ────────────

const brandSchema = z
  .object({
    legal_business_name: z.string().min(1, "Legal Business Name is required"),
    dba_name: z.string().optional(),
    ein: z.string().optional(),
    hq_address_line1: z.string().optional(),
    hq_address_line2: z.string().optional(),
    hq_city: z.string().optional(),
    hq_state: z.string().optional(),
    hq_postal_code: z.string().optional(),
    hq_country: z.string(),
    support_email: z.email("Valid email required"),
    support_phone: z
      .string()
      .min(1, "Phone is required")
      .regex(/^\+1\d{10}$/, "Format: +1XXXXXXXXXX"),
    website: z.url("Valid URL required"),
    stock_symbol: z.string().optional(),
    vertical: z.string().min(1, "Vertical is required"),
  })
  .superRefine((data, ctx) => {
    // EIN and address required for standard entity type — validated server-side.
    // Client-side: only format-check EIN if provided.
    if (data.ein && data.ein.length > 0) {
      if (!/^\d{2}-?\d{7}$/.test(data.ein)) {
        ctx.addIssue({
          path: ["ein"],
          code: "custom",
          message: "Format: 12-3456789",
        });
      }
    }
  });

type BrandFormValues = z.infer<typeof brandSchema>;

export interface BrandRegistrationFormProps {
  entityType: EntityType;
  onProvisioned?: () => void;
}

export function BrandRegistrationForm({
  entityType,
  onProvisioned,
}: BrandRegistrationFormProps) {
  const {
    data: profile,
    isPending: profileLoading,
    isError: profileError,
  } = use10DlcProfile();
  const { data: verticalsData, isPending: verticalsLoading } =
    useCarrierVerticals();
  const initiateProvisioning = useInitiateProvisioning();
  const { addNotification } = useNotificationQueue();

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<BrandFormValues>({
    resolver: zodResolver(brandSchema),
    defaultValues: {
      legal_business_name: profile?.legal_business_name ?? "",
      dba_name: profile?.dba_name ?? "",
      ein: "",
      hq_address_line1: profile?.hq_address_line1 ?? "",
      hq_address_line2: profile?.hq_address_line2 ?? "",
      hq_city: profile?.hq_city ?? "",
      hq_state: profile?.hq_state ?? "",
      hq_postal_code: profile?.hq_postal_code ?? "",
      hq_country: profile?.hq_country ?? "US",
      support_email: profile?.support_email ?? "",
      support_phone: profile?.support_phone ?? "",
      website: "",
      stock_symbol: "",
      vertical: "",
    },
  });

  if (profileLoading) {
    return <LoadingState type="inline" label="Loading profile..." />;
  }

  if (profileError) {
    return (
      <ErrorState
        type="server"
        title="Could not load profile"
        description="Check your connection and try again."
      />
    );
  }

  async function onSubmit(values: BrandFormValues) {
    // For standard entity, EIN and address are required — validate client-side
    if (entityType === "standard") {
      if (!values.ein) {
        addNotification({
          id: `ein-required-${Date.now()}`,
          severity: "error",
          title: "EIN is required for standard entities.",
        });
        return;
      }
      if (!values.hq_address_line1 || !values.hq_city || !values.hq_state) {
        addNotification({
          id: `addr-required-${Date.now()}`,
          severity: "error",
          title: "HQ Address is required for standard entities.",
        });
        return;
      }
    }

    try {
      await initiateProvisioning.mutateAsync({
        entity_type: entityType,
        ...values,
      });
      onProvisioned?.();
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 409) {
        addNotification({
          id: `provision-409-${Date.now()}`,
          severity: "error",
          title:
            "Messaging setup is already in progress. Refresh to see current status.",
        });
      } else if (status === 422) {
        addNotification({
          id: `provision-422-${Date.now()}`,
          severity: "error",
          title: "Validation error. Please check your entries.",
        });
      } else {
        addNotification({
          id: `provision-err-${Date.now()}`,
          severity: "error",
          title: "Could not start provisioning. Please try again.",
        });
      }
    }
  }

  const isPending = initiateProvisioning.isPending;
  const verticals = verticalsData?.verticals ?? [];

  return (
    <RoleGate permission="settings.manage">
      <form
        onSubmit={(e) => void handleSubmit(onSubmit)(e)}
        className="space-y-4"
        data-testid="brand-registration-form"
      >
        <div>
          <h2 className="text-h2 font-semibold text-neutral-900">
            Brand Registration
          </h2>
          <p className="text-sm text-neutral-500 mt-1">
            This information is submitted to the carrier (Telnyx) for 10DLC
            brand registration.
          </p>
        </div>

        {/* Legal Business Name */}
        <div>
          <label htmlFor="legal-business-name" className={LABEL_CLASS}>
            Legal Business Name <span className="text-alert-600">*</span>
          </label>
          <input
            id="legal-business-name"
            type="text"
            {...register("legal_business_name")}
            className={INPUT_CLASS}
            aria-required="true"
            aria-invalid={!!errors.legal_business_name}
            aria-describedby={
              errors.legal_business_name
                ? "legal-business-name-error"
                : undefined
            }
            data-testid="legal-business-name-input"
          />
          {errors.legal_business_name && (
            <p id="legal-business-name-error" className={ERROR_TEXT_CLASS}>
              {errors.legal_business_name.message as string}
            </p>
          )}
        </div>

        {/* DBA Name */}
        <div>
          <label htmlFor="dba-name" className={LABEL_CLASS}>
            DBA Name (optional)
          </label>
          <input
            id="dba-name"
            type="text"
            {...register("dba_name")}
            className={INPUT_CLASS}
            data-testid="dba-name-input"
          />
        </div>

        {/* EIN — only for standard */}
        {entityType === "standard" && (
          <div>
            <label htmlFor="ein" className={LABEL_CLASS}>
              EIN / Tax ID <span className="text-alert-600">*</span>
            </label>
            <input
              id="ein"
              type="text"
              placeholder="12-3456789"
              {...register("ein")}
              className={INPUT_CLASS}
              aria-required="true"
              aria-invalid={!!errors.ein}
              aria-describedby={errors.ein ? "ein-error" : undefined}
              data-testid="ein-input"
            />
            {errors.ein && (
              <p id="ein-error" className={ERROR_TEXT_CLASS}>
                {errors.ein.message as string}
              </p>
            )}
            <p className="text-xs text-neutral-500 mt-1">Format: 12-3456789</p>
          </div>
        )}

        {/* HQ Address — only for standard */}
        {entityType === "standard" && (
          <fieldset className="space-y-3 border border-neutral-100 rounded-md p-4">
            <legend className="text-sm font-medium text-neutral-700 px-2">
              HQ Address
            </legend>
            <div>
              <label htmlFor="address-line1" className={LABEL_CLASS}>
                Address Line 1 <span className="text-alert-600">*</span>
              </label>
              <input
                id="address-line1"
                type="text"
                {...register("hq_address_line1")}
                className={INPUT_CLASS}
                data-testid="address-line1-input"
              />
            </div>
            <div>
              <label htmlFor="address-line2" className={LABEL_CLASS}>
                Address Line 2 (optional)
              </label>
              <input
                id="address-line2"
                type="text"
                {...register("hq_address_line2")}
                className={INPUT_CLASS}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <div>
                <label htmlFor="city" className={LABEL_CLASS}>
                  City <span className="text-alert-600">*</span>
                </label>
                <input
                  id="city"
                  type="text"
                  {...register("hq_city")}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label htmlFor="state" className={LABEL_CLASS}>
                  State <span className="text-alert-600">*</span>
                </label>
                <input
                  id="state"
                  type="text"
                  maxLength={2}
                  {...register("hq_state")}
                  className={INPUT_CLASS}
                />
              </div>
              <div>
                <label htmlFor="postal-code" className={LABEL_CLASS}>
                  ZIP <span className="text-alert-600">*</span>
                </label>
                <input
                  id="postal-code"
                  type="text"
                  {...register("hq_postal_code")}
                  className={INPUT_CLASS}
                />
              </div>
            </div>
          </fieldset>
        )}

        {/* Support Email + Phone */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="support-email" className={LABEL_CLASS}>
              Support Email
            </label>
            <input
              id="support-email"
              type="email"
              {...register("support_email")}
              className={INPUT_CLASS}
              aria-invalid={!!errors.support_email}
              aria-describedby={
                errors.support_email ? "support-email-error" : undefined
              }
              data-testid="support-email-input"
            />
            {errors.support_email && (
              <p id="support-email-error" className={ERROR_TEXT_CLASS}>
                {errors.support_email.message as string}
              </p>
            )}
          </div>
          <div>
            <label htmlFor="support-phone" className={LABEL_CLASS}>
              Support Phone
            </label>
            <Controller
              control={control}
              name="support_phone"
              render={({ field }) => (
                <PhoneInput
                  id="support-phone"
                  value={field.value ?? ""}
                  onChange={(e164) => field.onChange(e164 ?? "")}
                  onBlur={field.onBlur}
                  className={INPUT_CLASS}
                  ariaInvalid={!!errors.support_phone}
                  ariaDescribedby={
                    errors.support_phone ? "support-phone-error" : undefined
                  }
                  data-testid="support-phone-input"
                />
              )}
            />
            {errors.support_phone && (
              <p id="support-phone-error" className={ERROR_TEXT_CLASS}>
                {errors.support_phone.message as string}
              </p>
            )}
          </div>
        </div>

        {/* Website — NEW (C-B9) */}
        <div>
          <label htmlFor="website" className={LABEL_CLASS}>
            Website <span className="text-alert-600">*</span>
          </label>
          <input
            id="website"
            type="url"
            placeholder="https://yourbusiness.com"
            {...register("website")}
            className={INPUT_CLASS}
            aria-required="true"
            aria-invalid={!!errors.website}
            aria-describedby={errors.website ? "website-error" : undefined}
            data-testid="website-input"
          />
          {errors.website && (
            <p id="website-error" className={ERROR_TEXT_CLASS}>
              {errors.website.message as string}
            </p>
          )}
          <p className="text-xs text-neutral-500 mt-1">
            Required by the carrier for brand registration.
          </p>
        </div>

        {/* Business Vertical — NEW (C-B9), dropdown */}
        <div>
          <label htmlFor="vertical" className={LABEL_CLASS}>
            Business Vertical <span className="text-alert-600">*</span>
          </label>
          <select
            id="vertical"
            {...register("vertical")}
            disabled={verticalsLoading}
            className={INPUT_CLASS}
            aria-required="true"
            aria-invalid={!!errors.vertical}
            aria-describedby={errors.vertical ? "vertical-error" : undefined}
            data-testid="vertical-select"
          >
            <option value="">
              {verticalsLoading ? "Loading verticals..." : "Select a vertical"}
            </option>
            {verticals.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
          {errors.vertical && (
            <p id="vertical-error" className={ERROR_TEXT_CLASS}>
              {errors.vertical.message as string}
            </p>
          )}
          <p className="text-xs text-neutral-500 mt-1">
            Populated from carrier enum endpoint.
          </p>
        </div>

        {/* Stock Symbol — NEW (C-B9), conditional */}
        <div>
          <label htmlFor="stock-symbol" className={LABEL_CLASS}>
            Stock Symbol (optional — only if publicly traded)
          </label>
          <input
            id="stock-symbol"
            type="text"
            {...register("stock_symbol")}
            className={INPUT_CLASS}
            data-testid="stock-symbol-input"
          />
          <p className="text-xs text-neutral-500 mt-1">
            Only fill in if your company is publicly traded on a stock exchange.
          </p>
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={isPending}
            className="bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none active:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="brand-form-submit"
          >
            {isPending ? "Getting quote..." : "Get Quote →"}
          </button>
        </div>
      </form>
    </RoleGate>
  );
}
