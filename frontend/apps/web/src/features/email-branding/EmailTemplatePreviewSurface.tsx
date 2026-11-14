/**
 * EmailTemplatePreviewSurface — FE-B14
 *
 * Location: apps/web/src/features/email-branding/EmailTemplatePreviewSurface.tsx
 *
 * Two-pane layout: template list (left) + iframe preview (right).
 * 17 templates grouped by category (customer-facing vs internal).
 *
 * RULE 8: Server renders templates via POST /preview. No client-side template rendering.
 */

"use client";

import React, { useCallback, useState } from "react";
import { EmailBrandingPreview } from "@pilot/ui";
import type { EmailTemplateId } from "@pilot/ui";
import { EMAIL_TEMPLATE_CATEGORIES } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";

interface TemplateEntry {
  id: EmailTemplateId;
  displayName: string;
  triggerDescription: string;
  audience: "customer" | "tenant_user";
}

const TEMPLATE_LIST: TemplateEntry[] = [
  // Customer-facing
  {
    id: "quote_sent",
    displayName: "Quote sent",
    triggerDescription: "Tenant sends a quote",
    audience: "customer",
  },
  {
    id: "quote_expiring_soon",
    displayName: "Quote expiring soon",
    triggerDescription: "3 days before quote expiry",
    audience: "customer",
  },
  {
    id: "invoice_sent",
    displayName: "Invoice sent",
    triggerDescription: "Tenant sends an invoice",
    audience: "customer",
  },
  {
    id: "payment_received_customer",
    displayName: "Payment received (receipt)",
    triggerDescription: "Stripe payment success",
    audience: "customer",
  },
  {
    id: "payment_failed",
    displayName: "Payment failed",
    triggerDescription: "Stripe payment failure",
    audience: "customer",
  },
  // Internal
  {
    id: "welcome",
    displayName: "Welcome / signup confirmation",
    triggerDescription: "Tenant signup complete",
    audience: "tenant_user",
  },
  {
    id: "email_verification",
    displayName: "Email verification code",
    triggerDescription: "Email verify request",
    audience: "tenant_user",
  },
  {
    id: "quote_accepted",
    displayName: "Quote accepted",
    triggerDescription: "Customer accepts quote",
    audience: "tenant_user",
  },
  {
    id: "quote_declined",
    displayName: "Quote declined",
    triggerDescription: "Customer declines quote",
    audience: "tenant_user",
  },
  {
    id: "payment_received_tenant",
    displayName: "Payment received (your copy)",
    triggerDescription: "Stripe payment success",
    audience: "tenant_user",
  },
  {
    id: "subscription_renewal_receipt",
    displayName: "Subscription renewal receipt",
    triggerDescription: "Stripe subscription renews",
    audience: "tenant_user",
  },
  {
    id: "subscription_payment_failed",
    displayName: "Subscription payment failed",
    triggerDescription: "Stripe subscription fails",
    audience: "tenant_user",
  },
  {
    id: "trial_expiring_soon",
    displayName: "Trial expiring soon",
    triggerDescription: "7/3/1 days before trial end",
    audience: "tenant_user",
  },
  {
    id: "trial_expired",
    displayName: "Trial expired",
    triggerDescription: "Trial end date reached",
    audience: "tenant_user",
  },
  {
    id: "password_reset",
    displayName: "Password reset",
    triggerDescription: "Password reset request",
    audience: "tenant_user",
  },
  {
    id: "mfa_reset_by_owner",
    displayName: "MFA reset by owner",
    triggerDescription: "Owner resets user MFA",
    audience: "tenant_user",
  },
  {
    id: "data_export_ready",
    displayName: "Data export ready",
    triggerDescription: "Data export completion",
    audience: "tenant_user",
  },
];

const CUSTOMER_FACING = TEMPLATE_LIST.filter(
  (t) => EMAIL_TEMPLATE_CATEGORIES[t.id] === "customer_facing",
);
const INTERNAL = TEMPLATE_LIST.filter(
  (t) => EMAIL_TEMPLATE_CATEGORIES[t.id] === "internal",
);

export function EmailTemplatePreviewSurface() {
  const [selectedId, setSelectedId] = useState<EmailTemplateId>("quote_sent");
  const [previewHtml, setPreviewHtml] = useState<string | undefined>();
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const fetchPreview = useCallback(async (templateId: EmailTemplateId) => {
    setIsPreviewLoading(true);
    setPreviewError(null);
    try {
      const res = await apiClient.post(
        "/api/v1/settings/email-branding/preview",
        {
          template_id: templateId,
        },
      );
      const data = res.data as { body_html: string };
      setPreviewHtml(data.body_html);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed.");
    } finally {
      setIsPreviewLoading(false);
    }
  }, []);

  function handleSelectTemplate(templateId: EmailTemplateId) {
    setSelectedId(templateId);
    void fetchPreview(templateId);
  }

  return (
    <div
      className="flex flex-col lg:flex-row gap-0 border border-neutral-200 rounded-xl overflow-hidden"
      data-testid="email-template-preview-surface"
    >
      {/* ─── Left pane: template list ──────────────────────────────────────── */}
      <div className="w-full lg:w-72 flex-shrink-0 border-r border-neutral-200 bg-neutral-50 overflow-y-auto">
        {/* Customer-facing group */}
        <div className="px-4 pt-4 pb-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">
            Customer-facing
          </p>
        </div>
        {CUSTOMER_FACING.map((template) => (
          <TemplateListRow
            key={template.id}
            template={template}
            isSelected={selectedId === template.id}
            onSelect={() => handleSelectTemplate(template.id)}
          />
        ))}

        {/* Internal group */}
        <div className="px-4 pt-5 pb-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">
            Internal (Pilot branding)
          </p>
        </div>
        {INTERNAL.map((template) => (
          <TemplateListRow
            key={template.id}
            template={template}
            isSelected={selectedId === template.id}
            onSelect={() => handleSelectTemplate(template.id)}
          />
        ))}
      </div>

      {/* ─── Right pane: preview ───────────────────────────────────────────── */}
      <div className="flex-1 bg-white p-5 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-neutral-800">
              {TEMPLATE_LIST.find((t) => t.id === selectedId)?.displayName ??
                selectedId}
            </p>
            <p className="text-xs text-neutral-400 mt-0.5">
              {
                TEMPLATE_LIST.find((t) => t.id === selectedId)
                  ?.triggerDescription
              }
            </p>
          </div>
          <button
            onClick={() => void fetchPreview(selectedId)}
            className="text-xs text-neutral-500 hover:text-neutral-700 underline"
            data-testid="refresh-template-preview"
          >
            Refresh
          </button>
        </div>

        {previewError ? (
          <div
            className="flex flex-col items-center gap-2 py-10 text-center"
            data-testid="preview-error"
          >
            <p className="text-sm text-fault-600">{previewError}</p>
            <button
              onClick={() => void fetchPreview(selectedId)}
              className="text-xs text-neutral-500 hover:text-neutral-700 underline"
            >
              Try again
            </button>
          </div>
        ) : (
          <EmailBrandingPreview
            branding={{
              // eslint-disable-next-line pilot/no-hardcoded-design-values
              primaryColorHex: "#3B43D6",
              logoUrl: null,
              senderName: "Your Company",
              replyToEmail: "noreply@example.com",
            }}
            templateKey={selectedId}
            previewHtml={previewHtml}
            isLoading={isPreviewLoading}
          />
        )}
      </div>
    </div>
  );
}

interface TemplateListRowProps {
  template: TemplateEntry;
  isSelected: boolean;
  onSelect: () => void;
}

function TemplateListRow({
  template,
  isSelected,
  onSelect,
}: TemplateListRowProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        "w-full text-left px-4 py-3 flex flex-col gap-0.5 hover:bg-neutral-100 transition-colors",
        isSelected
          ? "bg-brand-50 border-l-2 border-l-brand-600"
          : "border-l-2 border-l-transparent",
      ].join(" ")}
      data-testid={`template-row-${template.id}`}
    >
      <span
        className={`text-sm ${isSelected ? "font-semibold text-brand-700" : "font-medium text-neutral-800"}`}
      >
        {template.displayName}
      </span>
      <span className="text-xs text-neutral-400 truncate">
        {template.triggerDescription}
      </span>
    </button>
  );
}
