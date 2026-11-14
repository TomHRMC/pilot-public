/**
 * Email Branding — Types
 * Location: apps/web/src/features/email-branding/types.ts
 *
 * FE-B14: Tenant email branding settings panel types.
 * RULE 5: brand_color_hex is a free hex — NOT a Pilot token.
 */

export interface EmailBrandingSettings {
  tenantId: string;
  logoUrl: string | null;
  brandColorHex: string | null; // null = use Pilot default
  emailSignature: string | null;
  customFooter: string | null;
}

export interface EmailBrandingFormState {
  logoUrl: string | null;
  logoS3Path: string | null;
  brandColorHex: string; // never null in form — defaults to '#3B43D6'
  emailSignature: string;
  customFooter: string;
}

export type LogoUploadPhase =
  | "idle"
  | "requesting-url"
  | "uploading"
  | "committing"
  | "success"
  | "error";

export interface LogoUploadState {
  phase: LogoUploadPhase;
  error: string | null;
  previewUrl: string | null;
}

/** Normalize snake_case API response to camelCase */
export function normalizeBrandingSettings(
  raw: Record<string, unknown>,
): EmailBrandingSettings {
  return {
    tenantId: raw.tenant_id as string,
    logoUrl: (raw.logo_url as string | null) ?? null,
    brandColorHex: (raw.brand_color_hex as string | null) ?? null,
    emailSignature: (raw.email_signature as string | null) ?? null,
    customFooter: (raw.custom_footer as string | null) ?? null,
  };
}

/** Convert form state to API PATCH payload */
export function formStateToApiPayload(
  formState: Partial<EmailBrandingFormState>,
): Record<string, string | null> {
  const payload: Record<string, string | null> = {};
  if (formState.logoS3Path !== undefined)
    payload.logo_s3_path = formState.logoS3Path;
  if (formState.brandColorHex !== undefined)
    payload.brand_color_hex = formState.brandColorHex;
  if (formState.emailSignature !== undefined)
    payload.email_signature = formState.emailSignature;
  if (formState.customFooter !== undefined)
    payload.custom_footer = formState.customFooter;
  return payload;
}
