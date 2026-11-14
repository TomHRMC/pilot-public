"use client";

/**
 * TenantDlcProfileForm — 10DLC business registration profile form.
 *
 * Location: apps/web/src/features/sms-compliance/components/TenantDlcProfileForm.tsx
 *
 * DLC-1: Used in /settings/communications/sms-compliance page under "SMS & 10DLC" section.
 * RBAC: settings.manage (PUT). settings.view (GET — read-only display).
 *
 * This data is required to provision Telnyx sub-brand per tenant
 * for SMS campaign registration (carrier TCR submission by Tom).
 *
 * RULE 2: uses apiClient via hooks, never raw fetch().
 * RULE 5: all styling via Tailwind token utilities — no hardcoded values.
 * RULE 6: RoleGate hides form for unauthorized roles (hide-not-disable).
 * RULE 7: LoadingState, ErrorState, RoleGate imported from @pilot/ui.
 *
 * Architecture note: Avoids setState-in-useEffect pattern (React Compiler lint rule).
 * The outer TenantDlcProfileForm handles loading/error states.
 * The inner DlcProfileFormInner receives profile as a prop and initializes
 * state at mount time — no useEffect needed.
 */

import React, { useState } from "react";
import { RoleGate, LoadingState, ErrorState } from "@pilot/ui";
import { PhoneInput } from "@pilot/ui/phone-input";
import {
  use10DlcProfile,
  type Tenant10DlcProfileData,
} from "../hooks/use10DlcProfile";
import { useUpdate10DlcProfile } from "../hooks/useUpdate10DlcProfile";
import { WebsiteRequirementsPanel } from "@/features/tenant-site/components/WebsiteRequirementsPanel";

const LABEL_CLASS = "block text-sm font-medium text-neutral-700 mb-1";
const INPUT_CLASS =
  "w-full border border-neutral-200 rounded-md px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent";

// ── Inner form — receives profile as prop, initializes state at mount ──────────

interface DlcProfileFormInnerProps {
  profile: Tenant10DlcProfileData | null;
}

function DlcProfileFormInner({ profile }: DlcProfileFormInnerProps) {
  const updateProfile = useUpdate10DlcProfile();

  // State initialized from profile at mount — no useEffect required
  const [legalBusinessName, setLegalBusinessName] = useState(
    profile?.legal_business_name ?? "",
  );
  const [dbaName, setDbaName] = useState(profile?.dba_name ?? "");
  // EIN is masked on read — do not pre-populate (user re-enters to update)
  const [ein, setEin] = useState("");
  const [addressLine1, setAddressLine1] = useState(
    profile?.hq_address_line1 ?? "",
  );
  const [addressLine2, setAddressLine2] = useState(
    profile?.hq_address_line2 ?? "",
  );
  const [city, setCity] = useState(profile?.hq_city ?? "");
  const [stateCode, setStateCode] = useState(profile?.hq_state ?? "");
  const [postalCode, setPostalCode] = useState(profile?.hq_postal_code ?? "");
  const [supportEmail, setSupportEmail] = useState(
    profile?.support_email ?? "",
  );
  const [supportPhone, setSupportPhone] = useState<string | null>(
    profile?.support_phone ?? null,
  );
  const [website, setWebsite] = useState(profile?.website ?? "");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaveError(null);
    setSaveSuccess(false);

    if (!legalBusinessName.trim()) {
      setSaveError("Legal Business Name is required.");
      return;
    }

    try {
      await updateProfile.mutateAsync({
        legal_business_name: legalBusinessName.trim(),
        dba_name: dbaName.trim() || null,
        ein: ein.trim() || undefined, // only send if user typed something
        hq_address_line1: addressLine1.trim() || null,
        hq_address_line2: addressLine2.trim() || null,
        hq_city: city.trim() || null,
        hq_state: stateCode.trim().toUpperCase() || null,
        hq_postal_code: postalCode.trim() || null,
        support_email: supportEmail.trim() || null,
        support_phone: supportPhone,
        website: website.trim() || null,
      });
      setSaveSuccess(true);
    } catch {
      setSaveError("Failed to save profile. Please try again.");
    }
  }

  return (
    <RoleGate permission="settings.manage">
      <form
        onSubmit={(e) => void handleSave(e)}
        className="space-y-4"
        data-testid="dlc-profile-form"
      >
        {/* Legal Business Name */}
        <div>
          <label htmlFor="dlc-legal-name" className={LABEL_CLASS}>
            Legal Business Name <span className="text-alert-600">*</span>
          </label>
          <input
            id="dlc-legal-name"
            type="text"
            value={legalBusinessName}
            onChange={(e) => setLegalBusinessName(e.target.value)}
            placeholder="Example Holdings, LLC"
            className={INPUT_CLASS}
            data-testid="dlc-legal-name-input"
          />
        </div>

        {/* DBA Name */}
        <div>
          <label htmlFor="dlc-dba-name" className={LABEL_CLASS}>
            DBA Name <span className="text-neutral-400">(optional)</span>
          </label>
          <input
            id="dlc-dba-name"
            type="text"
            value={dbaName}
            onChange={(e) => setDbaName(e.target.value)}
            placeholder="Pilot for Trades"
            className={INPUT_CLASS}
            data-testid="dlc-dba-name-input"
          />
        </div>

        {/* EIN */}
        <div>
          <label htmlFor="dlc-ein" className={LABEL_CLASS}>
            EIN / Tax ID <span className="text-neutral-400">(optional)</span>
          </label>
          <input
            id="dlc-ein"
            type="text"
            value={ein}
            onChange={(e) => setEin(e.target.value)}
            placeholder="12-3456789 (leave blank to keep existing)"
            className={INPUT_CLASS}
            data-testid="dlc-ein-input"
          />
        </div>

        {/* HQ Address */}
        <fieldset className="space-y-3 border border-neutral-100 rounded-md p-4">
          <legend className="text-sm font-medium text-neutral-700 px-1">
            HQ Address
          </legend>
          <div>
            <label htmlFor="dlc-address-line1" className={LABEL_CLASS}>
              Address Line 1
            </label>
            <input
              id="dlc-address-line1"
              type="text"
              value={addressLine1}
              onChange={(e) => setAddressLine1(e.target.value)}
              placeholder="123 Main Street"
              className={INPUT_CLASS}
              data-testid="dlc-address-line1-input"
            />
          </div>
          <div>
            <label htmlFor="dlc-address-line2" className={LABEL_CLASS}>
              Address Line 2{" "}
              <span className="text-neutral-400">(optional)</span>
            </label>
            <input
              id="dlc-address-line2"
              type="text"
              value={addressLine2}
              onChange={(e) => setAddressLine2(e.target.value)}
              placeholder="Suite 100"
              className={INPUT_CLASS}
            />
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="col-span-2 sm:col-span-1">
              <label htmlFor="dlc-city" className={LABEL_CLASS}>
                City
              </label>
              <input
                id="dlc-city"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Denver"
                className={INPUT_CLASS}
                data-testid="dlc-city-input"
              />
            </div>
            <div>
              <label htmlFor="dlc-state" className={LABEL_CLASS}>
                State
              </label>
              <input
                id="dlc-state"
                type="text"
                value={stateCode}
                onChange={(e) => setStateCode(e.target.value.toUpperCase())}
                placeholder="CO"
                maxLength={2}
                className={INPUT_CLASS}
                data-testid="dlc-state-input"
              />
            </div>
            <div>
              <label htmlFor="dlc-postal" className={LABEL_CLASS}>
                ZIP
              </label>
              <input
                id="dlc-postal"
                type="text"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                placeholder="80202"
                className={INPUT_CLASS}
                data-testid="dlc-postal-input"
              />
            </div>
          </div>
        </fieldset>

        {/* Support Contact */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="dlc-support-email" className={LABEL_CLASS}>
              Support Email
            </label>
            <input
              id="dlc-support-email"
              type="email"
              value={supportEmail}
              onChange={(e) => setSupportEmail(e.target.value)}
              placeholder="support@pilotfortrades.com"
              className={INPUT_CLASS}
              data-testid="dlc-support-email-input"
            />
          </div>
          <div>
            <label htmlFor="dlc-support-phone" className={LABEL_CLASS}>
              Support Phone
            </label>
            <PhoneInput
              id="dlc-support-phone"
              value={supportPhone ?? ""}
              onChange={(e164) => setSupportPhone(e164)}
              className={INPUT_CLASS}
              data-testid="dlc-support-phone-input"
            />
          </div>
        </div>

        {/* Website URL — C-B16 §14 */}
        <div>
          <label htmlFor="dlc-website" className={LABEL_CLASS}>
            Website URL
          </label>
          <input
            id="dlc-website"
            type="url"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="https://yourbusiness.com"
            maxLength={500}
            className={INPUT_CLASS}
            data-testid="dlc-website-input"
          />
          <p className="mt-1 text-xs text-neutral-500">
            Your business website URL. Used for 10DLC carrier vetting. If you
            use our hosted compliance site, this is set automatically when you
            publish.
          </p>
          {website &&
            !website.endsWith(
              `.${process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN ?? "localhost"}`,
            ) && <WebsiteRequirementsPanel />}
          {website &&
            website.endsWith(
              `.${process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN ?? "localhost"}`,
            ) && (
              <p className="mt-2 text-xs text-neutral-500">
                This is your Pilot-hosted compliance site URL. It was set
                automatically when you published.
              </p>
            )}
        </div>

        {/* Feedback */}
        {saveSuccess && (
          <p
            className="text-sm text-success-700 bg-success-50 border border-success-200 rounded px-3 py-2"
            data-testid="dlc-save-success"
          >
            ✓ 10DLC profile saved successfully.
          </p>
        )}
        {saveError && (
          <p
            className="text-sm text-alert-700 bg-alert-50 border border-alert-200 rounded px-3 py-2"
            role="alert"
            data-testid="dlc-save-error"
          >
            {saveError}
          </p>
        )}

        {/* Submit */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={updateProfile.isPending || !legalBusinessName.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
            data-testid="dlc-save-btn"
          >
            {updateProfile.isPending ? "Saving…" : "Save Profile"}
          </button>
        </div>
      </form>
    </RoleGate>
  );
}

// ── Outer component — handles loading/error, then mounts inner with profile ───

export function TenantDlcProfileForm() {
  const { data: profile, isLoading, isError } = use10DlcProfile();

  if (isLoading) {
    return <LoadingState type="inline" label="Loading 10DLC profile..." />;
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load 10DLC profile"
        description="Check your connection and try again."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-neutral-900">
          SMS Business Profile (10DLC)
        </h2>
        <p className="text-sm text-neutral-500 mt-1">
          Required for carrier registration. This data is used to provision your
          dedicated SMS number under TCR compliance.
        </p>
        {profile?.ein_masked && (
          <p className="text-xs text-neutral-400 mt-1">
            Current EIN on file:{" "}
            <span className="font-mono">{profile.ein_masked}</span>. Enter a new
            value below to update.
          </p>
        )}
      </div>

      {/*
        key=profile?.tenant_id forces re-mount when a new profile is loaded
        so DlcProfileFormInner initializes state fresh from the new profile.
      */}
      <DlcProfileFormInner
        key={profile?.tenant_id ?? "new"}
        profile={profile ?? null}
      />
    </div>
  );
}
