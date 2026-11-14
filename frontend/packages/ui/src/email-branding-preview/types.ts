/**
 * Email Branding Preview — Types
 * Location: packages/ui/src/email-branding-preview/types.ts
 *
 * FE-B1: Base skeleton props (branding, previewWidth, className).
 * FE-B14: Additive extension — templateKey, previewHtml, isLoading.
 *
 * All FE-B14 additions are optional — FE-B1 skeleton usages unchanged.
 */

/** Tenant branding data consumed by the preview pane. */
export interface TenantBranding {
  /** Primary accent color (hex string from tenant settings) */
  primaryColorHex: string;
  /** Logo URL (S3 signed URL or null if not yet uploaded) */
  logoUrl: string | null;
  /** Display name for emails (defaults to tenant company name) */
  senderName: string;
  /** Reply-to email address */
  replyToEmail: string;
}

/**
 * Union type for all 17 valid email template IDs.
 * Matches BE-B15/A82 template pipeline and spec §7 Table 1.
 */
export type EmailTemplateId =
  | "welcome"
  | "email_verification"
  | "quote_sent"
  | "quote_accepted"
  | "quote_declined"
  | "quote_expiring_soon"
  | "invoice_sent"
  | "payment_received_tenant"
  | "payment_received_customer"
  | "payment_failed"
  | "subscription_renewal_receipt"
  | "subscription_payment_failed"
  | "trial_expiring_soon"
  | "trial_expired"
  | "password_reset"
  | "mfa_reset_by_owner"
  | "data_export_ready";

/** Category lookup for all 17 email templates. */
export const EMAIL_TEMPLATE_CATEGORIES: Record<
  EmailTemplateId,
  "customer_facing" | "internal"
> = {
  quote_sent: "customer_facing",
  quote_expiring_soon: "customer_facing",
  invoice_sent: "customer_facing",
  payment_received_customer: "customer_facing",
  payment_failed: "customer_facing",
  welcome: "internal",
  email_verification: "internal",
  quote_accepted: "internal",
  quote_declined: "internal",
  payment_received_tenant: "internal",
  subscription_renewal_receipt: "internal",
  subscription_payment_failed: "internal",
  trial_expiring_soon: "internal",
  trial_expired: "internal",
  password_reset: "internal",
  mfa_reset_by_owner: "internal",
  data_export_ready: "internal",
};

export interface EmailBrandingPreviewProps {
  // ─── FE-B1 props (unchanged) ─────────────────────────────────────────────
  /**
   * Tenant branding to preview.
   * null → renders shimmer placeholder skeleton.
   */
  branding: TenantBranding | null;
  /** Width of the preview pane in pixels (default: 560 — standard email width) */
  previewWidth?: number;
  className?: string;

  // ─── FE-B14 additions (all optional — backward-compatible) ───────────────
  /**
   * Which email template to preview (default: 'quote_sent').
   * FE-B1 skeleton: ignored.
   * FE-B14 fleshed: controls which template label is shown in header.
   */
  templateKey?: EmailTemplateId;
  /**
   * Server-rendered HTML blob from POST /api/v1/settings/email-branding/preview.
   * When provided, rendered inside a sandboxed iframe.
   * When undefined, renders a placeholder with branding info.
   */
  previewHtml?: string;
  /**
   * When true, shows loading skeleton over the preview pane.
   * Use during re-fetch after a field save.
   */
  isLoading?: boolean;
}
