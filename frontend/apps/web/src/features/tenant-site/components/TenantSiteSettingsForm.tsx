"use client";

/**
 * TenantSiteSettingsForm — C-B16 top-level settings client component
 *
 * Location: apps/web/src/features/tenant-site/components/TenantSiteSettingsForm.tsx
 *
 * Manages useTenantSite loading/error/empty states. Renders option cards,
 * hosted-site form, preview/publish sections. RoleGate wraps the form/action
 * area (settings.manage).
 *
 * web spec §6–§13: page shell, option cards, form, preview, publish/unpublish.
 * RULE 6: RoleGate hides form for unauthorized roles (hide-not-disable).
 * RULE 33: TanStack Query v5 object-form; invalidate onSettled.
 * RULE 34: Zod v4 + RHF for form validation.
 */

import React, { useState } from "react";
import { RoleGate, LoadingState, ErrorState, EmptyState } from "@pilot/ui";
import { PhoneInput } from "@pilot/ui/phone-input";
import { useTenantSite } from "../hooks/useTenantSite";
import { useUpsertTenantSite } from "../hooks/useUpsertTenantSite";
import {
  usePublishTenantSite,
  extractOverwriteConflict,
} from "../hooks/usePublishTenantSite";
import { useUnpublishTenantSite } from "../hooks/useUnpublishTenantSite";
import { SiteOptionCard, type SiteOptionKind } from "./SiteOptionCard";
import { SlugAvailabilityInput } from "./SlugAvailabilityInput";
import { SitePreviewPanel } from "./SitePreviewPanel";
import { PublishConfirmDialog } from "./PublishConfirmDialog";
import { BrandStateNotice } from "./BrandStateNotice";
import { WebsiteRequirementsPanel } from "./WebsiteRequirementsPanel";
import { DefaultsAnnotatedField } from "./DefaultsAnnotatedField";
import type { WebsiteOverwriteConflict } from "../hooks/usePublishTenantSite";
import { ExclamationTriangleIcon as ExclamationTriangleIconSolid } from "@heroicons/react/24/solid";

const INPUT_CLASS =
  "w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500";

export function TenantSiteSettingsForm() {
  const { data, isPending, isError, refetch } = useTenantSite();
  const upsertMutation = useUpsertTenantSite();
  const publishMutation = usePublishTenantSite();
  const unpublishMutation = useUnpublishTenantSite();

  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [overwriteConflict, setOverwriteConflict] =
    useState<WebsiteOverwriteConflict | null>(null);
  const [slugAvailable, setSlugAvailable] = useState(false);

  // Form state — initialized from the GET response
  const site = data?.site ?? null;
  const defaults = data?.defaults;
  const configured = data?.configured ?? false;

  const [formData, setFormData] = useState({
    site_kind: site?.site_kind ?? "hosted_compliance",
    slug: site?.slug ?? "",
    display_name: site?.display_name ?? defaults?.display_name ?? "",
    tagline: site?.tagline ?? "",
    public_email: site?.public_email ?? defaults?.public_email ?? "",
    public_phone: site?.public_phone ?? defaults?.public_phone ?? "",
    public_city: site?.public_city ?? defaults?.public_city ?? "",
    public_state: site?.public_state ?? defaults?.public_state ?? "",
    show_full_address: site?.show_full_address ?? false,
  });

  // Sync formData when the GET response arrives.
  // Uses the "adjusting state during render" pattern (React docs) instead of
  // useEffect+setState (which the React Compiler lint rule forbids).
  // During isPending, site/defaults are null → formData is empty. When data
  // arrives, this conditional re-derives formData from the fresh payload.
  const [prevData, setPrevData] = useState(data);
  if (data !== prevData) {
    setPrevData(data);
    setFormData({
      site_kind: site?.site_kind ?? "hosted_compliance",
      slug: site?.slug ?? "",
      display_name: site?.display_name ?? defaults?.display_name ?? "",
      tagline: site?.tagline ?? "",
      public_email: site?.public_email ?? defaults?.public_email ?? "",
      public_phone: site?.public_phone ?? defaults?.public_phone ?? "",
      public_city: site?.public_city ?? defaults?.public_city ?? "",
      public_state: site?.public_state ?? defaults?.public_state ?? "",
      show_full_address: site?.show_full_address ?? false,
    });
  }

  // Re-initialize form when data loads (key-based remount pattern)
  const formKey = site?.id ?? defaults?.display_name ?? "new";

  if (isPending) {
    return <LoadingState type="inline" label="Loading website settings..." />;
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load website settings"
        description="Check your connection and try again."
        onRetry={() => void refetch()}
      />
    );
  }

  const isPublished = site?.status === "published";
  const isUnpublished = site?.status === "unpublished";
  const slugLocked = site?.published_at != null;
  const brandStatus = site?.site_url ? "none" : "none"; // TODO: from publish response

  const handleOptionSelect = (kind: SiteOptionKind) => {
    if (kind === "starter_site") return; // disabled
    setFormData((prev) => ({ ...prev, site_kind: kind }));
    // Save the option selection immediately
    upsertMutation.mutate({
      site_kind: kind,
      slug: formData.slug || "temp-" + Date.now(),
      display_name: formData.display_name || null,
      tagline: formData.tagline || null,
      public_email: formData.public_email || null,
      public_phone: formData.public_phone || null,
      public_city: formData.public_city || null,
      public_state: formData.public_state || null,
      show_full_address: formData.show_full_address,
    });
  };

  const handleSaveDraft = (e: React.FormEvent) => {
    e.preventDefault();
    upsertMutation.mutate({
      site_kind: formData.site_kind,
      slug: formData.slug,
      display_name: formData.display_name || null,
      tagline: formData.tagline || null,
      public_email: formData.public_email || null,
      public_phone: formData.public_phone || null,
      public_city: formData.public_city || null,
      public_state: formData.public_state || null,
      show_full_address: formData.show_full_address,
    });
  };

  const handlePublish = () => {
    setShowPublishDialog(true);
    setOverwriteConflict(null);
  };

  const handleConfirmPublish = (confirmOverwrite: boolean) => {
    publishMutation.mutate(
      { confirmWebsiteOverwrite: confirmOverwrite },
      {
        onSuccess: () => {
          setShowPublishDialog(false);
          setOverwriteConflict(null);
        },
        onError: (error) => {
          const conflict = extractOverwriteConflict(error);
          if (conflict) {
            setOverwriteConflict(conflict);
            // Dialog stays open, switches to overwrite variant
          } else {
            // Non-409 error — keep dialog open, show error
          }
        },
      },
    );
  };

  const handleUnpublish = () => {
    unpublishMutation.mutate();
  };

  const showHostedForm = formData.site_kind === "hosted_compliance";
  const showRequirementsPanel =
    formData.site_kind === "compliance_kit" ||
    (site?.site_url && !site.website_auto_populated);

  return (
    <div className="space-y-6" data-testid="tenant-site-settings-form">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-h1 font-semibold text-neutral-900">Website</h1>
          <p className="mt-1 text-body text-neutral-500">
            Satisfy TCR 10DLC website vetting for SMS compliance. Choose how to
            publish your business website — self-host with our Compliance Kit or
            let Pilot host a compliance site for you.
          </p>
        </div>
      </div>

      {/* BrandStateNotice */}
      <BrandStateNotice brandStatus={brandStatus} />

      {/* Empty state */}
      {!configured && (
        <EmptyState
          type="no-data"
          title="You haven't set up a website yet"
          description="Choose an option below to satisfy TCR 10DLC website vetting."
        />
      )}

      {/* Section: Choose your approach */}
      <section className="scroll-mt-20">
        <h2 className="text-h2 font-semibold text-neutral-900">
          Choose your approach
        </h2>
        <div
          role="radiogroup"
          aria-label="Website approach"
          className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"
        >
          <SiteOptionCard
            kind="compliance_kit"
            title="Compliance Kit"
            description="Self-host with our kit"
            selected={formData.site_kind === "compliance_kit"}
            onSelect={handleOptionSelect}
            statusBadge={{
              text:
                site?.site_kind === "compliance_kit" ? "Active" : "Not started",
              className:
                site?.site_kind === "compliance_kit"
                  ? "bg-brand-100 text-brand-700"
                  : "bg-neutral-100 text-neutral-700",
            }}
          >
            {showRequirementsPanel && (
              <WebsiteRequirementsPanel
                requirementsEmailedAt={site?.requirements_emailed_at ?? null}
              />
            )}
          </SiteOptionCard>

          <SiteOptionCard
            kind="hosted_compliance"
            title="Hosted Compliance Site"
            description="We host a 3-page site"
            selected={formData.site_kind === "hosted_compliance"}
            onSelect={handleOptionSelect}
            statusBadge={{
              text: isPublished
                ? "Published"
                : isUnpublished
                  ? "Unpublished"
                  : configured
                    ? "Draft"
                    : "Not configured",
              className: isPublished
                ? "bg-margin-100 text-margin-700"
                : "bg-neutral-100 text-neutral-700",
            }}
          />
        </div>

        {/* Option 3 — disabled (full width) */}
        <div className="mt-4">
          <SiteOptionCard
            kind="starter_site"
            title="Starter Site"
            description="A richer single business website with services, hours, logo, and a contact form — plus the compliance pages. Pricing and features in development."
            selected={false}
            disabled
            onSelect={() => {}}
            statusBadge={{
              text: "Coming in a future update",
              className: "bg-neutral-100 text-neutral-500",
            }}
          />
        </div>
      </section>

      {/* Section: Configure your hosted site (conditional) */}
      {showHostedForm && (
        <RoleGate permission="settings.manage">
          <section className="scroll-mt-20">
            <h2 className="text-h2 font-semibold text-neutral-900">
              Configure your hosted site
            </h2>
            <p className="mt-1 text-body text-neutral-500">
              These fields appear on your public compliance site. Defaults are
              merged from your 10DLC business profile — override any field to
              customize what the public sees.
            </p>

            <form
              key={formKey}
              onSubmit={handleSaveDraft}
              className="mt-4 space-y-6 rounded-xl border border-neutral-200 bg-white p-6 shadow-sm"
              data-testid="tenant-site-form"
            >
              {/* Display name */}
              <DefaultsAnnotatedField
                inputId="display-name"
                label="Display name"
                required
                value={formData.display_name}
                defaultValue={defaults?.display_name ?? null}
                helperText="The business name shown on your public site. Defaults to your DBA or legal name."
                onRevert={() =>
                  setFormData((p) => ({
                    ...p,
                    display_name: defaults?.display_name ?? "",
                  }))
                }
              >
                <input
                  id="display-name"
                  type="text"
                  maxLength={200}
                  value={formData.display_name}
                  onChange={(e) =>
                    setFormData((p) => ({ ...p, display_name: e.target.value }))
                  }
                  className={INPUT_CLASS}
                  data-testid="display-name-input"
                />
              </DefaultsAnnotatedField>

              {/* Tagline */}
              <div>
                <label
                  htmlFor="tagline"
                  className="mb-1 text-sm font-medium text-neutral-700"
                >
                  Tagline
                </label>
                <input
                  id="tagline"
                  type="text"
                  maxLength={300}
                  value={formData.tagline}
                  onChange={(e) =>
                    setFormData((p) => ({ ...p, tagline: e.target.value }))
                  }
                  className={INPUT_CLASS}
                  data-testid="tagline-input"
                />
                <p className="mt-1 text-xs text-neutral-500">
                  A one-line description of your business (optional).
                </p>
              </div>

              {/* Public phone */}
              <DefaultsAnnotatedField
                inputId="public-phone"
                label="Public phone"
                value={formData.public_phone}
                defaultValue={defaults?.public_phone ?? null}
                helperText="A phone number customers can reach you at. Defaults to your support phone."
                onRevert={() =>
                  setFormData((p) => ({
                    ...p,
                    public_phone: defaults?.public_phone ?? "",
                  }))
                }
              >
                <PhoneInput
                  id="public-phone"
                  value={formData.public_phone}
                  onChange={(e164) =>
                    setFormData((p) => ({
                      ...p,
                      public_phone: e164 ?? "",
                    }))
                  }
                  className={INPUT_CLASS}
                  data-testid="public-phone-input"
                />
              </DefaultsAnnotatedField>

              {/* Public email */}
              <DefaultsAnnotatedField
                inputId="public-email"
                label="Public email"
                value={formData.public_email}
                defaultValue={defaults?.public_email ?? null}
                helperText="An email customers can reach you at. Defaults to your support email."
                onRevert={() =>
                  setFormData((p) => ({
                    ...p,
                    public_email: defaults?.public_email ?? "",
                  }))
                }
              >
                <input
                  id="public-email"
                  type="email"
                  maxLength={320}
                  value={formData.public_email}
                  onChange={(e) =>
                    setFormData((p) => ({ ...p, public_email: e.target.value }))
                  }
                  className={INPUT_CLASS}
                  data-testid="public-email-input"
                />
              </DefaultsAnnotatedField>

              {/* City */}
              <DefaultsAnnotatedField
                inputId="public-city"
                label="City"
                required
                value={formData.public_city}
                defaultValue={defaults?.public_city ?? null}
                helperText="Your service city. Defaults to your HQ city."
                onRevert={() =>
                  setFormData((p) => ({
                    ...p,
                    public_city: defaults?.public_city ?? "",
                  }))
                }
              >
                <input
                  id="public-city"
                  type="text"
                  maxLength={120}
                  value={formData.public_city}
                  onChange={(e) =>
                    setFormData((p) => ({ ...p, public_city: e.target.value }))
                  }
                  className={INPUT_CLASS}
                  data-testid="public-city-input"
                />
              </DefaultsAnnotatedField>

              {/* State */}
              <DefaultsAnnotatedField
                inputId="public-state"
                label="State"
                required
                value={formData.public_state}
                defaultValue={defaults?.public_state ?? null}
                helperText="Your service state (2-letter). Defaults to your HQ state."
                onRevert={() =>
                  setFormData((p) => ({
                    ...p,
                    public_state: defaults?.public_state ?? "",
                  }))
                }
              >
                <input
                  id="public-state"
                  type="text"
                  maxLength={2}
                  value={formData.public_state}
                  onChange={(e) =>
                    setFormData((p) => ({
                      ...p,
                      public_state: e.target.value.toUpperCase(),
                    }))
                  }
                  className={INPUT_CLASS}
                  data-testid="public-state-input"
                />
              </DefaultsAnnotatedField>

              {/* Show full address toggle */}
              <div>
                <label className="mb-1 text-sm font-medium text-neutral-700">
                  Show full address
                </label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={formData.show_full_address}
                    onClick={() =>
                      setFormData((p) => ({
                        ...p,
                        show_full_address: !p.show_full_address,
                      }))
                    }
                    className={`relative h-6 w-11 rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2 ${
                      formData.show_full_address
                        ? "bg-brand-600"
                        : "bg-neutral-200"
                    }`}
                    data-testid="show-full-address-toggle"
                  >
                    <span
                      className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                        formData.show_full_address
                          ? "translate-x-5"
                          : "translate-x-0.5"
                      }`}
                    />
                  </button>
                  <span className="text-sm text-neutral-600">
                    {formData.show_full_address ? "On" : "Off"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-neutral-500">
                  Include your street address and ZIP on the public site. Off by
                  default — many sole proprietors register with a home address.
                </p>
                {formData.show_full_address && (
                  <div className="mt-2 flex items-start gap-2 rounded-md border border-alert-200 bg-alert-50 p-3">
                    <ExclamationTriangleIconSolid
                      className="h-5 w-5 shrink-0 text-alert-600"
                      aria-hidden="true"
                    />
                    <p className="text-sm text-alert-700">
                      Your street address and ZIP will be public. If your
                      business address is your home address, consider keeping
                      this off — the city and state are always shown and are
                      sufficient for TCR vetting.
                    </p>
                  </div>
                )}
              </div>

              {/* Slug */}
              <SlugAvailabilityInput
                value={formData.slug}
                onChange={(slug) => setFormData((p) => ({ ...p, slug }))}
                locked={slugLocked}
                onAvailabilityChange={setSlugAvailable}
              />

              {/* Form actions */}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setFormData({
                      site_kind: site?.site_kind ?? "hosted_compliance",
                      slug: site?.slug ?? "",
                      display_name:
                        site?.display_name ?? defaults?.display_name ?? "",
                      tagline: site?.tagline ?? "",
                      public_email:
                        site?.public_email ?? defaults?.public_email ?? "",
                      public_phone:
                        site?.public_phone ?? defaults?.public_phone ?? "",
                      public_city:
                        site?.public_city ?? defaults?.public_city ?? "",
                      public_state:
                        site?.public_state ?? defaults?.public_state ?? "",
                      show_full_address: site?.show_full_address ?? false,
                    });
                  }}
                  className="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2"
                  data-testid="discard-changes-btn"
                >
                  Discard Changes
                </button>
                <button
                  type="submit"
                  disabled={upsertMutation.isPending}
                  className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2 disabled:opacity-50"
                  data-testid="save-draft-btn"
                >
                  {upsertMutation.isPending ? "Saving…" : "Save Draft"}
                </button>
              </div>

              {/* Save feedback */}
              {upsertMutation.isSuccess && (
                <p
                  className="text-sm text-margin-700"
                  data-testid="save-success"
                >
                  ✓ Draft saved.
                </p>
              )}
              {upsertMutation.isError && (
                <p
                  className="text-sm text-fault-600"
                  role="alert"
                  data-testid="save-error"
                >
                  Failed to save draft. Please try again.
                </p>
              )}
            </form>
          </section>
        </RoleGate>
      )}

      {/* Section: Preview & publish (conditional) */}
      {showHostedForm && configured && (
        <section className="scroll-mt-20">
          <h2 className="text-h2 font-semibold text-neutral-900">
            Preview & publish
          </h2>

          <div className="mt-4">
            <SitePreviewPanel
              displayName={formData.display_name}
              tagline={formData.tagline || null}
              publicPhone={formData.public_phone || null}
              publicEmail={formData.public_email || null}
              publicCity={formData.public_city || null}
              publicState={formData.public_state || null}
              slug={formData.slug}
              pages={{
                landing: {
                  heading: formData.display_name,
                  body_paragraphs: [
                    "Lang Electric has been serving the Richmond metro area since 2015.",
                    "We specialize in residential panel upgrades, commercial tenant build-outs, and EV charger installations.",
                  ],
                },
                privacy: {
                  title: "Privacy Policy",
                  body_paragraphs: [
                    "This privacy policy describes how Lang Electric collects, uses, and protects your information.",
                    "SMS Communications: We may send you text messages regarding appointment confirmations, service updates, and account alerts.",
                  ],
                },
                terms: {
                  title: "Terms of Service",
                  body_paragraphs: [
                    "These terms govern the use of Lang Electric's services.",
                    "SMS Terms: By providing your phone number, you consent to receive SMS messages related to your service appointments and account.",
                  ],
                },
              }}
            />
          </div>

          <div className="mt-4 flex justify-end gap-3">
            {isPublished && (
              <button
                type="button"
                onClick={handleUnpublish}
                disabled={unpublishMutation.isPending}
                className="rounded-md border border-fault-300 px-4 py-2 text-sm font-medium text-fault-600 hover:bg-fault-50 focus-visible:outline-2 focus-visible:outline-fault-500 focus-visible:outline-offset-2 disabled:opacity-50"
                data-testid="unpublish-btn"
              >
                {unpublishMutation.isPending
                  ? "Unpublishing…"
                  : "Unpublish site"}
              </button>
            )}
            <button
              type="button"
              onClick={handlePublish}
              disabled={!slugAvailable && !slugLocked}
              className="rounded-md bg-brand-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-brand-700 focus-visible:outline-2 focus-visible:outline-brand-500 focus-visible:outline-offset-2 disabled:opacity-50"
              data-testid="publish-btn"
            >
              Preview & Publish
            </button>
          </div>

          {/* Unpublish feedback */}
          {unpublishMutation.isSuccess && (
            <p
              className="mt-2 text-sm text-alert-700"
              data-testid="unpublish-warning"
            >
              {unpublishMutation.data?.warning ?? "Site unpublished."}
            </p>
          )}
        </section>
      )}

      {/* Publish confirm dialog */}
      <PublishConfirmDialog
        open={showPublishDialog}
        onClose={() => {
          setShowPublishDialog(false);
          setOverwriteConflict(null);
        }}
        onConfirm={handleConfirmPublish}
        isPublishing={publishMutation.isPending}
        slug={formData.slug}
        displayName={formData.display_name}
        overwriteConflict={overwriteConflict}
      />
    </div>
  );
}
