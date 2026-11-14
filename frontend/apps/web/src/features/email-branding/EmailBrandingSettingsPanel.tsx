/**
 * EmailBrandingSettingsPanel — FE-B14
 *
 * Location: apps/web/src/features/email-branding/EmailBrandingSettingsPanel.tsx
 *
 * Tenant email branding settings with live EmailBrandingPreview.
 * Composes FE-B11's SettingControl (LOCKED — no modifications).
 *
 * Field save pattern: saveMode='blur' via SettingControl → onSave callback
 * → PATCH /api/v1/settings/email-branding → refetchPreview.
 *
 * RULE 8: Preview HTML fetched from server (BE-B15/A82), not rendered client-side.
 * RoleGate: owner/accountant (applied at the layout level).
 */

"use client";

import React, { useCallback, useEffect, useState } from "react";
import { SettingControl, EmailBrandingPreview } from "@pilot/ui";
import type { EmailTemplateId } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";
import type { EmailBrandingFormState } from "./types";
import { normalizeBrandingSettings } from "./types";
import { LogoUploadField } from "./LogoUploadField";
import { BrandColorField } from "./BrandColorField";

const DEFAULT_TEMPLATE_KEY: EmailTemplateId = "quote_sent";
const BRANDING_API = "/api/v1/settings/email-branding";

export function EmailBrandingSettingsPanel() {
  const [formState, setFormState] = useState<EmailBrandingFormState>({
    logoUrl: null,
    logoS3Path: null,
    // eslint-disable-next-line pilot/no-hardcoded-design-values
    brandColorHex: "#3B43D6",
    emailSignature: "",
    customFooter: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [previewHtml, setPreviewHtml] = useState<string | undefined>();
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewTemplateKey, setPreviewTemplateKey] =
    useState<EmailTemplateId>(DEFAULT_TEMPLATE_KEY);
  const [testSendStatus, setTestSendStatus] = useState<
    "idle" | "sending" | "sent" | "error"
  >("idle");

  // Load initial branding settings
  useEffect(() => {
    void (async () => {
      try {
        const { data: raw } =
          await apiClient.get<Record<string, unknown>>(BRANDING_API);
        const settings = normalizeBrandingSettings(raw);
        setFormState({
          logoUrl: settings.logoUrl,
          logoS3Path: null,
          // eslint-disable-next-line pilot/no-hardcoded-design-values
          brandColorHex: settings.brandColorHex ?? "#3B43D6",
          emailSignature: settings.emailSignature ?? "",
          customFooter: settings.customFooter ?? "",
        });
      } catch {
        // leave defaults — user will see empty form
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const refetchPreview = useCallback(
    async (templateKey: EmailTemplateId = previewTemplateKey) => {
      setIsPreviewLoading(true);
      try {
        const { data } = await apiClient.post<{ body_html: string }>(
          `${BRANDING_API}/preview`,
          { template_id: templateKey },
        );
        setPreviewHtml(data.body_html);
      } catch {
        // preview failure is non-critical; keep existing HTML
      } finally {
        setIsPreviewLoading(false);
      }
    },
    [previewTemplateKey],
  );

  async function patchBranding(patch: Record<string, string | null>) {
    const { data } = await apiClient.patch<Record<string, unknown>>(
      BRANDING_API,
      patch,
    );
    return data;
  }

  async function handleSignatureSave(value: unknown) {
    const sig = value as string;
    await patchBranding({ email_signature: sig });
    setFormState((prev) => ({ ...prev, emailSignature: sig }));
    void refetchPreview();
  }

  async function handleFooterSave(value: unknown) {
    const footer = value as string;
    await patchBranding({ custom_footer: footer });
    setFormState((prev) => ({ ...prev, customFooter: footer }));
    void refetchPreview();
  }

  async function handleColorSave(newColor: string) {
    await patchBranding({ brand_color_hex: newColor });
    setFormState((prev) => ({ ...prev, brandColorHex: newColor }));
    void refetchPreview();
  }

  async function handleLogoCommitted(s3Path: string) {
    // PATCH then re-fetch so logoUrl is the real resolved S3 URL from the backend
    await patchBranding({ logo_s3_path: s3Path });
    try {
      const { data: raw } =
        await apiClient.get<Record<string, unknown>>(BRANDING_API);
      const settings = normalizeBrandingSettings(raw);
      setFormState((prev) => ({
        ...prev,
        logoUrl: settings.logoUrl,
        logoS3Path: s3Path,
      }));
    } catch {
      // fallback: keep local s3_path ref so at least the local preview shows
      setFormState((prev) => ({ ...prev, logoS3Path: s3Path }));
    }
    void refetchPreview();
  }

  async function handleLogoRemoved() {
    await patchBranding({ logo_s3_path: null });
    setFormState((prev) => ({ ...prev, logoUrl: null, logoS3Path: null }));
    void refetchPreview();
  }

  async function handleTestSend() {
    setTestSendStatus("sending");
    try {
      await apiClient.post(`${BRANDING_API}/test-send`);
      setTestSendStatus("sent");
      setTimeout(() => setTestSendStatus("idle"), 3000);
    } catch {
      setTestSendStatus("error");
      setTimeout(() => setTestSendStatus("idle"), 3000);
    }
  }

  function handleTemplateKeyChange(key: EmailTemplateId) {
    setPreviewTemplateKey(key);
    void refetchPreview(key);
  }

  if (isLoading) {
    return (
      <div className="animate-pulse flex flex-col gap-4 p-6">
        <div className="h-4 w-40 rounded bg-neutral-200" />
        <div className="h-10 w-full rounded bg-neutral-200" />
        <div className="h-4 w-32 rounded bg-neutral-200" />
        <div className="h-10 w-full rounded bg-neutral-200" />
      </div>
    );
  }

  // Build TenantBranding for EmailBrandingPreview
  const tenantBranding = {
    primaryColorHex: formState.brandColorHex,
    logoUrl: formState.logoUrl,
    senderName: "Your Company",
    replyToEmail: "noreply@yourcompany.com",
  };

  return (
    <div
      className="flex flex-col lg:flex-row gap-8"
      data-testid="email-branding-settings-panel"
    >
      {/* ─── Settings form (left pane) ─────────────────────────────────────── */}
      <div className="flex-1 flex flex-col gap-6 max-w-lg">
        <div>
          <h2 className="text-base font-semibold text-neutral-900">
            Email Branding
          </h2>
          <p className="text-sm text-neutral-500 mt-0.5">
            Customize how your emails appear to customers.
          </p>
        </div>

        {/* Logo upload */}
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-neutral-700">Logo</p>
          <LogoUploadField
            currentLogoUrl={formState.logoUrl}
            onLogoCommitted={handleLogoCommitted}
            onLogoRemoved={handleLogoRemoved}
          />
        </div>

        {/* Brand color — RULE 5: free hex, NOT Pilot token */}
        <BrandColorField
          value={formState.brandColorHex}
          onSave={handleColorSave}
        />

        {/* Email signature — SettingControl with saveMode='blur' */}
        <SettingControl
          settingKey="email_branding.email_signature"
          label="Email signature"
          description="Appears at the bottom of every customer-facing email."
          value={formState.emailSignature}
          defaultValue=""
          scope="tenant"
          saveMode="blur"
          inputType="string"
          validationRules={{ max: 500 }}
          onSave={handleSignatureSave}
          onRevert={async () => {}}
          testID="email-signature-control"
        />

        {/* Custom footer — SettingControl with saveMode='blur' */}
        <SettingControl
          settingKey="email_branding.custom_footer"
          label="Footer text"
          description="Shown in the footer of customer-facing emails. Max 200 characters."
          value={formState.customFooter}
          defaultValue=""
          scope="tenant"
          saveMode="blur"
          inputType="string"
          validationRules={{ max: 200 }}
          onSave={handleFooterSave}
          onRevert={async () => {}}
          testID="email-footer-control"
        />

        {/* Test send */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled={testSendStatus === "sending"}
            onClick={() => void handleTestSend()}
            className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
            data-testid="test-send-button"
          >
            {testSendStatus === "sending"
              ? "Sending…"
              : "Send test email to my address"}
          </button>
          {testSendStatus === "sent" && (
            <span
              className="text-sm text-margin-700"
              data-testid="test-send-success"
            >
              ✓ Test email sent!
            </span>
          )}
          {testSendStatus === "error" && (
            <span
              className="text-sm text-fault-600"
              data-testid="test-send-error"
            >
              Test email could not be sent. Try again.
            </span>
          )}
        </div>
      </div>

      {/* ─── Preview pane (right pane) ─────────────────────────────────────── */}
      <div className="flex-1 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-neutral-700">Live preview</p>
          {/* Template selector */}
          <select
            value={previewTemplateKey}
            onChange={(e) =>
              handleTemplateKeyChange(e.target.value as EmailTemplateId)
            }
            className="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 focus:outline-none"
            data-testid="template-selector"
          >
            <option value="quote_sent">Quote sent</option>
            <option value="quote_expiring_soon">Quote expiring soon</option>
            <option value="invoice_sent">Invoice sent</option>
            <option value="payment_received_customer">
              Payment received (customer)
            </option>
            <option value="payment_failed">Payment failed</option>
            <option value="welcome">Welcome (internal)</option>
          </select>
        </div>

        <EmailBrandingPreview
          branding={tenantBranding}
          templateKey={previewTemplateKey}
          previewHtml={previewHtml}
          isLoading={isPreviewLoading}
          className="shadow-sm"
        />

        <button
          type="button"
          onClick={() => void refetchPreview()}
          className="text-xs text-neutral-500 hover:text-neutral-700 underline self-end"
          data-testid="refresh-preview-button"
        >
          Refresh preview
        </button>
      </div>
    </div>
  );
}
