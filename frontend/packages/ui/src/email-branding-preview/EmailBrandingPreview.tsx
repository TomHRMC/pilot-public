/**
 * EmailBrandingPreview — FE-B14 (fleshed from FE-B1 skeleton)
 *
 * Location: packages/ui/src/email-branding-preview/EmailBrandingPreview.tsx
 *
 * FE-B1: Skeleton with placeholder layout.
 * FE-B14: Renders actual email template HTML in a sandboxed iframe.
 *
 * RULE 8: Email templates are server-rendered (BE-B15/A82).
 *         This component renders the server-provided body_html, it does NOT
 *         re-implement the template engine client-side.
 *
 * BACKWARD COMPATIBILITY: FE-B1 usages that pass only branding/previewWidth/className
 * continue to work without any changes — all FE-B14 props are optional.
 *
 * iframe sandbox: "allow-same-origin" only — no allow-scripts.
 * Server-rendered templates do not require JS; this prevents XSS.
 */

import React from "react";
import type { EmailBrandingPreviewProps, EmailTemplateId } from "./types";
import { EMAIL_TEMPLATE_CATEGORIES } from "./types";

const TEMPLATE_DISPLAY_NAMES: Record<EmailTemplateId, string> = {
  welcome: "Welcome / signup confirmation",
  email_verification: "Email verification code",
  quote_sent: "Quote sent",
  quote_accepted: "Quote accepted",
  quote_declined: "Quote declined",
  quote_expiring_soon: "Quote expiring soon",
  invoice_sent: "Invoice sent",
  payment_received_tenant: "Payment received (your copy)",
  payment_received_customer: "Payment received (receipt)",
  payment_failed: "Payment failed",
  subscription_renewal_receipt: "Subscription renewal receipt",
  subscription_payment_failed: "Subscription payment failed",
  trial_expiring_soon: "Trial expiring soon",
  trial_expired: "Trial expired",
  password_reset: "Password reset",
  mfa_reset_by_owner: "MFA reset by owner",
  data_export_ready: "Data export ready",
};

/**
 * EmailBrandingPreview (web-only)
 *
 * @example
 * // FE-B1 usage (unchanged):
 * <EmailBrandingPreview branding={tenantBranding} />
 *
 * @example
 * // FE-B14 usage with server HTML:
 * <EmailBrandingPreview
 *   branding={tenantBranding}
 *   templateKey="quote_sent"
 *   previewHtml={serverRenderedHtml}
 *   isLoading={isRefetching}
 * />
 */
export function EmailBrandingPreview({
  branding,
  previewWidth = 560,
  className,
  templateKey = "quote_sent",
  previewHtml,
  isLoading = false,
}: EmailBrandingPreviewProps) {
  const isNullBranding = branding === null;
  const showSkeleton = isNullBranding || isLoading;
  const templateName = TEMPLATE_DISPLAY_NAMES[templateKey];
  const templateCategory = EMAIL_TEMPLATE_CATEGORIES[templateKey];

  return (
    <div
      data-testid="email-branding-preview"
      className={`border border-neutral-200 rounded-lg overflow-hidden bg-neutral-50 ${className ?? ""}`}
      style={{ width: previewWidth, maxWidth: "100%" }}
    >
      {/* Preview header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 bg-white">
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-neutral-700">
            Email Preview
          </span>
          {!isNullBranding && (
            <span className="text-xs text-neutral-500">
              {templateName}
              {templateCategory === "customer_facing" && (
                // eslint-disable-next-line pilot/no-hardcoded-design-values
                <span className="ml-2 inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-brand-50 text-brand-700">
                  Customer-facing
                </span>
              )}
            </span>
          )}
        </div>
        {branding?.logoUrl && (
          <img
            src={branding.logoUrl}
            alt={`${branding.senderName} logo`}
            className="h-6 object-contain"
            data-testid="preview-logo"
          />
        )}
      </div>

      {/* Preview body */}
      {/* eslint-disable-next-line pilot/no-hardcoded-design-values */}
      <div className="relative min-h-[400px]">
        {/* Loading skeleton overlay */}
        {showSkeleton && (
          <div
            className="absolute inset-0 z-10 bg-neutral-50 flex flex-col gap-3 p-6"
            data-testid="preview-skeleton"
          >
            {/* Skeleton: header bar */}
            <div className="h-16 rounded bg-neutral-200 animate-pulse" />
            {/* Skeleton: content lines */}
            <div className="h-4 w-3/4 rounded bg-neutral-200 animate-pulse mt-4" />
            <div className="h-4 w-full rounded bg-neutral-200 animate-pulse" />
            <div className="h-4 w-5/6 rounded bg-neutral-200 animate-pulse" />
            <div className="h-4 w-2/3 rounded bg-neutral-200 animate-pulse" />
            {/* Skeleton: CTA button */}
            <div className="h-10 w-40 rounded bg-neutral-200 animate-pulse mt-4 mx-auto" />
            {/* Skeleton: footer */}
            <div className="h-3 w-1/2 rounded bg-neutral-200 animate-pulse mt-8 mx-auto" />
          </div>
        )}

        {/* Iframe: server-rendered HTML */}
        {!showSkeleton && previewHtml && (
          <iframe
            data-testid="preview-iframe"
            srcDoc={previewHtml}
            sandbox="allow-same-origin"
            title={`Email preview: ${templateName}`}
            style={{
              width: "100%",
              height: 480,
              border: "none",
              display: "block",
            }}
          />
        )}

        {/* Placeholder: branding set but no HTML yet fetched */}
        {!showSkeleton && !previewHtml && branding && (
          <div
            className="flex flex-col items-center justify-center gap-4 p-8 text-center"
            style={{ minHeight: 400 }}
            data-testid="preview-placeholder"
          >
            {/* Tenant color accent bar */}
            <div
              className="w-full h-2 rounded-t"
              style={{ backgroundColor: branding.primaryColorHex }}
            />
            <div className="flex flex-col gap-2 w-full max-w-xs">
              {branding.logoUrl ? (
                <img
                  src={branding.logoUrl}
                  alt={branding.senderName}
                  className="h-10 object-contain mx-auto"
                />
              ) : (
                <p className="text-sm font-semibold text-neutral-700">
                  {branding.senderName}
                </p>
              )}
              <p className="text-xs text-neutral-400">
                From: {branding.senderName} &lt;{branding.replyToEmail}&gt;
              </p>
            </div>
            <p className="text-xs text-neutral-400 italic">
              Select a template and save your settings to see a live preview.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
