/**
 * Account Settings Fixtures — FE-B12
 *
 * Location: apps/web/src/features/account-settings/mocks/accountFixtures.ts
 *
 * Fixture data for MSW handlers covering:
 *  - Profile GET/PUT
 *  - Password change POST
 *  - MFA status, enroll-start, enroll-confirm, recovery codes
 *  - Active sessions GET/DELETE
 *  - Data export POST/GET
 *  - Voice persona GET/PUT
 */

import type {
  MfaStatusResponse,
  MfaEnrollStartResponse,
  MfaEnrollConfirmResponse,
  MfaRecoveryCodesGenerateResponse,
  MfaRecoveryCodesStatusResponse,
  ActiveSession,
  DataExportCreateResponse,
  DataExportStatusResponse,
  UserProfile,
} from "../types";

// ─── Profile ──────────────────────────────────────────────────────────────────

export const PROFILE_FIXTURE: UserProfile = {
  user_id: "user-abc-123",
  first_name: "Mike",
  last_name: "Thornton",
  email: "mike@thorntonelectric.example.com",
  phone: "+15551234567",
  timezone: "America/New_York",
  language: "en",
  avatar_url: null,
};

// ─── MFA Status ───────────────────────────────────────────────────────────────

export const MFA_STATUS_NONE: MfaStatusResponse = {
  enrolled_methods: [],
  methods: [],
  tenant_policy_required: false,
  grace_period_active: false,
  grace_ends_at: null,
  enforcement_activated: false,
};

export const MFA_STATUS_GRACE_PERIOD: MfaStatusResponse = {
  enrolled_methods: [],
  methods: [],
  tenant_policy_required: true,
  grace_period_active: true,
  grace_ends_at: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
  enforcement_activated: false,
};

export const MFA_STATUS_TOTP_ENROLLED: MfaStatusResponse = {
  enrolled_methods: ["totp"],
  methods: [
    {
      method_id: "mfa-method-totp",
      method_type: "totp",
      enrolled_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      last_used_at: null,
      destination_masked: null,
    },
  ],
  tenant_policy_required: false,
  grace_period_active: false,
  grace_ends_at: null,
  enforcement_activated: false,
};

// ─── MFA Enroll-Start Payloads ────────────────────────────────────────────────

export const MFA_TOTP_ENROLL_START: MfaEnrollStartResponse = {
  method_type: "totp",
  qr_code_uri:
    "otpauth://totp/Pilot%3Amike%40thorntonelectric.example.com?secret=JBSWY3DPEHPK3PXP&issuer=Pilot&algorithm=SHA1&digits=6&period=30",
  secret: "JBSWY3DPEHPK3PXP",
};

export const MFA_SMS_ENROLL_START: MfaEnrollStartResponse = {
  method_type: "sms",
  destination_masked: "+1 (555) ***-4567",
};

export const MFA_EMAIL_ENROLL_START: MfaEnrollStartResponse = {
  method_type: "email",
  destination_masked: "m***@thorntonelectric.example.com",
};

// ─── MFA Enroll-Confirm ───────────────────────────────────────────────────────

export const MFA_ENROLL_CONFIRM_SUCCESS: MfaEnrollConfirmResponse = {
  method_id: "mfa-method-totp-001",
  enrolled_at: new Date().toISOString(),
};

// ─── MFA Recovery Codes ───────────────────────────────────────────────────────

export const MFA_RECOVERY_CODES_STATUS_EMPTY: MfaRecoveryCodesStatusResponse = {
  unused_code_count: 0,
  last_generated_at: null,
};

export const MFA_RECOVERY_CODES_STATUS_HAS_CODES: MfaRecoveryCodesStatusResponse =
  {
    unused_code_count: 8,
    last_generated_at: new Date(
      Date.now() - 30 * 24 * 60 * 60 * 1000,
    ).toISOString(),
  };

export const MFA_RECOVERY_CODES_GENERATE: MfaRecoveryCodesGenerateResponse = {
  codes: [
    "ABCD-1234-EFGH",
    "IJKL-5678-MNOP",
    "QRST-9012-UVWX",
    "YZ01-2345-ABCD",
    "EFGH-6789-IJKL",
    "MNOP-0123-QRST",
    "UVWX-4567-YZ01",
    "2345-ABCD-EFGH",
    "6789-IJKL-MNOP",
    "0123-QRST-UVWX",
  ],
  set_id: "recovery-set-001",
};

// ─── Active Sessions ──────────────────────────────────────────────────────────

export const ACTIVE_SESSIONS: ActiveSession[] = [
  {
    session_id: "sess-current-001",
    display_label: "Chrome on macOS",
    ip_address: "192.168.1.100",
    geolocation: "Brooklyn, NY",
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    last_active_at: new Date().toISOString(),
    is_current: true,
    revoked_at: null,
  },
  {
    session_id: "sess-mobile-002",
    display_label: "Pilot mobile on iPhone",
    ip_address: "10.0.0.55",
    geolocation: "Brooklyn, NY",
    created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    last_active_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    is_current: false,
    revoked_at: null,
  },
  {
    session_id: "sess-safari-003",
    display_label: "Safari on iPad",
    ip_address: "10.0.0.78",
    geolocation: "Unknown location",
    created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    last_active_at: new Date(
      Date.now() - 2 * 24 * 60 * 60 * 1000,
    ).toISOString(),
    is_current: false,
    revoked_at: null,
  },
];

// ─── Data Export ──────────────────────────────────────────────────────────────

export const DATA_EXPORT_CREATE: DataExportCreateResponse = {
  export_id: "export-001",
  status: "pending",
  requested_at: new Date().toISOString(),
};

export const DATA_EXPORT_STATUS_PENDING: DataExportStatusResponse = {
  export_id: "export-001",
  status: "pending",
  requested_at: new Date().toISOString(),
  expires_at: null,
  signed_url: null,
  data_scope: "user_specific",
  failure_reason: null,
};

export const DATA_EXPORT_STATUS_PROCESSING: DataExportStatusResponse = {
  export_id: "export-001",
  status: "processing",
  requested_at: new Date().toISOString(),
  expires_at: null,
  signed_url: null,
  data_scope: "user_specific",
  failure_reason: null,
};

export const DATA_EXPORT_STATUS_READY: DataExportStatusResponse = {
  export_id: "export-001",
  status: "ready",
  requested_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
  expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  signed_url:
    "https://pilot-exports.s3.amazonaws.com/export-001.zip?X-Amz-Expires=604800",
  data_scope: "user_specific",
  failure_reason: null,
};

export const DATA_EXPORT_STATUS_EXPIRED: DataExportStatusResponse = {
  export_id: "export-002",
  status: "expired",
  requested_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
  expires_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  signed_url: null,
  data_scope: "user_specific",
  failure_reason: null,
};

export const RECENT_EXPORTS: DataExportStatusResponse[] = [
  DATA_EXPORT_STATUS_READY,
  DATA_EXPORT_STATUS_EXPIRED,
];
