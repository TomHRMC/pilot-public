/**
 * Account Settings Types — FE-B12
 *
 * Location: apps/web/src/features/account-settings/types.ts
 *
 * Covers: MFA, active sessions, data export, password change, profile.
 */

// ─── MFA ─────────────────────────────────────────────────────────────────────

export type MFAEnrollmentPath = "totp" | "sms" | "email";

export interface MfaMethodInfo {
  method_id: string;
  method_type: string;
  enrolled_at: string;
  last_used_at?: string | null;
  destination_masked?: string | null;
}

export interface MfaStatusResponse {
  enrolled_methods: MFAEnrollmentPath[];
  /** MFA-WIRE-1 (design §D.4): additive methods[] array for the web card list. */
  methods: MfaMethodInfo[];
  tenant_policy_required: boolean;
  grace_period_active: boolean;
  grace_ends_at: string | null;
  enforcement_activated: boolean;
}

export interface MfaEnrollStartResponse {
  method_type: MFAEnrollmentPath;
  qr_code_uri?: string;
  secret?: string;
  destination_masked?: string;
}

export interface MfaEnrollConfirmResponse {
  method_id: string;
  enrolled_at: string;
}

export interface MfaRecoveryCodesGenerateResponse {
  codes: string[];
  set_id: string;
}

export interface MfaRecoveryCodesStatusResponse {
  unused_code_count: number;
  last_generated_at: string | null;
}

// ─── Active Sessions ──────────────────────────────────────────────────────────

export interface ActiveSession {
  session_id: string;
  display_label: string;
  ip_address: string;
  geolocation: string | null;
  created_at: string;
  last_active_at: string;
  is_current: boolean;
  revoked_at: string | null;
}

export interface RevokeOthersResponse {
  revoked_count: number;
}

// ─── Data Export ──────────────────────────────────────────────────────────────

export type DataExportStatus =
  | "pending"
  | "processing"
  | "ready"
  | "expired"
  | "failed";

export interface DataExportCreateResponse {
  export_id: string;
  status: "pending";
  requested_at: string;
}

export interface DataExportStatusResponse {
  export_id: string;
  status: DataExportStatus;
  requested_at: string;
  expires_at: string | null;
  signed_url: string | null;
  data_scope: "full_tenant" | "user_specific";
  failure_reason: string | null;
}

export interface DataExportPageState {
  activeExportId: string | null;
  status: DataExportStatus | "idle";
  signedUrl: string | null;
  expiresAt: string | null;
  failureReason: string | null;
}

// ─── Password Change ──────────────────────────────────────────────────────────

export type PasswordChangePhase = "idle" | "submitting" | "success" | "error";

export interface PasswordChangeFormState {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
  phase: PasswordChangePhase;
  errorMessage: string | null;
}

// ─── Profile ──────────────────────────────────────────────────────────────────

export interface UserProfile {
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  timezone: string;
  language: string;
  avatar_url: string | null;
}

export interface ProfileUpdateRequest {
  first_name?: string;
  last_name?: string;
  phone?: string | null;
  timezone?: string;
  language?: string;
}
