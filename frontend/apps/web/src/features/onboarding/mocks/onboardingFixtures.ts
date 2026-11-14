/**
 * Onboarding Fixtures — FE-B13
 *
 * Location: apps/web/src/features/onboarding/mocks/onboardingFixtures.ts
 *
 * Provides MSW fixture data for:
 *  - Subscription tiers (trial, starter, professional, enterprise)
 *  - Signup state per step
 *  - Legal acceptance
 *  - OTP phone verification
 *  - Stripe payment intent (test mode)
 *  - Onboarding checklist (5 items: 2 complete, 2 incomplete, 1 skipped)
 *  - Push permission states
 */

// ─── Subscription Tiers ────────────────────────────────────────────────────

export const TRIAL_TIER = {
  tier_id: "tier-trial-00000000-0000-0000-0000-000000000001",
  tier_name: "trial",
  display_label: "Free Trial",
  monthly_price_cents: 0,
  is_trial: true,
  trial_duration_days: 14,
  max_users: 1,
  max_sms_segments_per_month: 50,
  display_order: 0,
  is_active: true,
};

// Fixture values from an earlier pricing draft (tests depend on them). Canonical
// pricing: Starter $59 / Teams $179 monthly ($49 / $149 billed annually),
// Charter $49, unlimited users.
export const STARTER_TIER = {
  tier_id: "tier-starter-0000-0000-0000-000000000002",
  tier_name: "starter",
  display_label: "Starter",
  monthly_price_cents: 9900,
  is_trial: false,
  trial_duration_days: null,
  max_users: 5,
  max_sms_segments_per_month: 500,
  display_order: 1,
  is_active: true,
};

export const PROFESSIONAL_TIER = {
  tier_id: "tier-professional-000-0000-0000-000000000003",
  tier_name: "professional",
  display_label: "Professional",
  monthly_price_cents: 24900,
  is_trial: false,
  trial_duration_days: null,
  max_users: 15,
  max_sms_segments_per_month: 2000,
  display_order: 2,
  is_active: true,
};

export const ENTERPRISE_TIER = {
  tier_id: "tier-enterprise-000-0000-0000-000000000004",
  tier_name: "enterprise",
  display_label: "Enterprise",
  monthly_price_cents: 59900,
  is_trial: false,
  trial_duration_days: null,
  max_users: 100,
  max_sms_segments_per_month: null,
  display_order: 3,
  is_active: true,
};

// C-B5: Charter tier — 90-day free period, no card required, capped at 12 members
export const CHARTER_TIER = {
  tier_id: "tier-charter-0000-0000-0000-000000000005",
  tier_name: "charter",
  display_label: "Charter",
  monthly_price_cents: 4900,
  is_trial: false,
  trial_duration_days: null,
  max_users: 12,
  max_sms_segments_per_month: 2000,
  display_order: 0,
  is_active: true,
  free_period_days: 90,
  requires_payment_method: false,
  signup_cap: 12,
};

export const SUBSCRIPTION_TIERS_LIST = {
  tiers: [TRIAL_TIER, STARTER_TIER, PROFESSIONAL_TIER, ENTERPRISE_TIER],
};

// C-B5: Charter-mode tiers list — only the Charter tier is active
export const SUBSCRIPTION_TIERS_LIST_CHARTER = {
  tiers: [CHARTER_TIER],
};

// ─── Signup State Fixtures (per step) ──────────────────────────────────────

export const SIGNUP_STATE_STEP1 = {
  tenant_id: "tenant-test-00000000-0000-0000-0000-000000000001",
  signup_state: "step1_account",
  collected_data: {
    business_name: "Apex Electric LLC",
    owner_first_name: "Mike",
    owner_email: "mike@apexelectric.example.com",
    phone_skipped: false,
    phone_verified: false,
  },
};

export const SIGNUP_STATE_STEP2 = {
  ...SIGNUP_STATE_STEP1,
  signup_state: "step2_legal",
};

export const SIGNUP_STATE_STEP3 = {
  ...SIGNUP_STATE_STEP1,
  signup_state: "step3_phone",
  collected_data: {
    ...SIGNUP_STATE_STEP1.collected_data,
  },
};

export const SIGNUP_STATE_STEP4 = {
  ...SIGNUP_STATE_STEP1,
  signup_state: "step4_tier",
  collected_data: {
    ...SIGNUP_STATE_STEP1.collected_data,
    phone_verified: true,
  },
};

export const SIGNUP_STATE_STEP5_TRIAL = {
  ...SIGNUP_STATE_STEP1,
  signup_state: "step5_confirm",
  collected_data: {
    ...SIGNUP_STATE_STEP1.collected_data,
    phone_verified: true,
    selected_tier_id: TRIAL_TIER.tier_id,
  },
};

export const SIGNUP_STATE_STEP5_PAID = {
  ...SIGNUP_STATE_STEP1,
  signup_state: "step5_confirm",
  collected_data: {
    ...SIGNUP_STATE_STEP1.collected_data,
    phone_verified: true,
    selected_tier_id: STARTER_TIER.tier_id,
  },
};

export const SIGNUP_STATE_COMPLETE = {
  ...SIGNUP_STATE_STEP1,
  signup_state: "complete",
  collected_data: {
    ...SIGNUP_STATE_STEP1.collected_data,
    phone_verified: true,
    selected_tier_id: TRIAL_TIER.tier_id,
  },
};

// C-B5: Charter signup state — requires_payment_method=false, free_period_ends_at set
export const SIGNUP_STATE_STEP5_CHARTER = {
  ...SIGNUP_STATE_STEP1,
  signup_state: "step5_confirm",
  collected_data: {
    ...SIGNUP_STATE_STEP1.collected_data,
    phone_verified: true,
    selected_tier_id: CHARTER_TIER.tier_id,
    free_period_ends_at: new Date(
      Date.now() + 90 * 24 * 60 * 60 * 1000,
    ).toISOString(),
    requires_payment_method: false,
    charter_member_number: 7,
  },
};

export const SIGNUP_STATE_COMPLETE_CHARTER = {
  ...SIGNUP_STATE_STEP5_CHARTER,
  signup_state: "complete",
};

// ─── Account Creation Responses ────────────────────────────────────────────

export const SIGNUP_INITIATE_SUCCESS = {
  tenant_id: SIGNUP_STATE_STEP1.tenant_id,
  signup_state: "step1_account",
  owner_email: "mike@apexelectric.example.com",
  credential_pending: false,
};

export const SIGNUP_DUPLICATE_EMAIL_ERROR = {
  detail: "An account with this email already exists.",
  code: "email_already_registered",
};

// ─── Legal Acceptance Fixtures ─────────────────────────────────────────────

export const LEGAL_REQUIRED_RESPONSE = {
  required_documents: [
    {
      document_type: "tos",
      current_version_hash: "sha256-tos-v1.2-abc123def456",
      already_accepted: false,
    },
    {
      document_type: "privacy",
      current_version_hash: "sha256-privacy-v1.1-789xyz012",
      already_accepted: false,
    },
    {
      document_type: "eula",
      current_version_hash: "sha256-eula-v1.0-qrstuv678",
      already_accepted: false,
    },
  ],
};

export const LEGAL_REQUIRED_ALREADY_ACCEPTED = {
  required_documents: [
    {
      document_type: "tos",
      current_version_hash: "sha256-tos-v1.2-abc123def456",
      already_accepted: true,
    },
    {
      document_type: "privacy",
      current_version_hash: "sha256-privacy-v1.1-789xyz012",
      already_accepted: true,
    },
    {
      document_type: "eula",
      current_version_hash: "sha256-eula-v1.0-qrstuv678",
      already_accepted: true,
    },
  ],
};

export const LEGAL_ACCEPT_TOS_RESPONSE = {
  acceptance_id: "accept-tos-00000000-0000-0000-0000-000000000001",
  document_type: "tos",
  accepted_at: new Date().toISOString(),
};

export const LEGAL_ACCEPT_PRIVACY_RESPONSE = {
  acceptance_id: "accept-privacy-0000-0000-0000-000000000002",
  document_type: "privacy",
  accepted_at: new Date().toISOString(),
};

export const LEGAL_ACCEPT_EULA_RESPONSE = {
  acceptance_id: "accept-eula-00000-0000-0000-000000000003",
  document_type: "eula",
  accepted_at: new Date().toISOString(),
};

// ─── Phone OTP Fixtures ────────────────────────────────────────────────────

export const PHONE_OTP_SEND_SUCCESS = {
  message: "Verification code sent.",
  expires_in_seconds: 300,
};

export const PHONE_OTP_CONFIRM_SUCCESS = {
  phone_verified: true,
  message: "Phone number verified.",
};

export const PHONE_OTP_CONFIRM_WRONG_CODE = {
  detail: "Incorrect code. Try again.",
  code: "otp_invalid",
};

// ─── Stripe Test Mode Fixtures ─────────────────────────────────────────────

/**
 * RULE 5: Always test-mode client_secret (pi_test or seti_test prefix)
 * This is a structurally valid test-mode secret — never a real Stripe key.
 */
export const STRIPE_SUBSCRIPTION_PAYMENT_INTENT = {
  client_secret:
    "seti_1test00000000000000000000_secret_test00000000000000000000000000",
  payment_intent_id: "pi_test_00000000000000000000000000",
};

export const STRIPE_PAYMENT_INTENT_FAILED = {
  detail: "Card was declined.",
  code: "card_declined",
  decline_code: "insufficient_funds",
};

// ─── Subscription Confirm Fixtures ────────────────────────────────────────

export const SUBSCRIPTION_CONFIRM_SUCCESS = {
  new_tier_id: STARTER_TIER.tier_id,
  stripe_subscription_id: "sub_test_00000000000000000000",
  activated_at: new Date().toISOString(),
};

// ─── Onboarding Checklist Fixtures ────────────────────────────────────────
// 5-item state: account_created ✓, legal_accepted ✓, tier_selected ✓,
//               first_customer_added ✗, catalog_setup ✗,
//               quickbooks_connected ✗ (skipped), calendar_connected ✗, team_invited ✗

export const CHECKLIST_INITIAL = {
  tenant_id: SIGNUP_STATE_STEP1.tenant_id,
  account_created: true,
  legal_accepted: true,
  tier_selected: true,
  first_customer_added: false,
  first_customer_added_at: null,
  catalog_setup: false,
  catalog_setup_at: null,
  messaging_setup: false,
  quickbooks_connected: false,
  quickbooks_skipped: true,
  calendar_connected: false,
  calendar_skipped: false,
  team_invited: false,
  team_skipped: false,
  checklist_hidden: false,
  checklist_dismissed_permanently: false,
};

export const CHECKLIST_ALL_COMPLETE = {
  ...CHECKLIST_INITIAL,
  first_customer_added: true,
  first_customer_added_at: new Date().toISOString(),
  catalog_setup: true,
  catalog_setup_at: new Date().toISOString(),
  messaging_setup: true,
  calendar_connected: true,
  team_invited: true,
};

export const CHECKLIST_DISMISSED = {
  ...CHECKLIST_INITIAL,
  checklist_dismissed_permanently: true,
};

export const CHECKLIST_HIDDEN = {
  ...CHECKLIST_INITIAL,
  checklist_hidden: true,
};

// ─── Push Permission Fixtures ──────────────────────────────────────────────

export const PUSH_PERMISSION_NOT_ASKED = {
  device_id: "device-test-00000000-0000-0000-0000-000000000001",
  permission_state: "not_asked",
  last_state_change_at: new Date().toISOString(),
  dismissable_banner_dismissed_at: null,
  banner_should_appear: false,
};

export const PUSH_PERMISSION_GRANTED = {
  ...PUSH_PERMISSION_NOT_ASKED,
  permission_state: "granted",
  banner_should_appear: false,
};

export const PUSH_PERMISSION_DENIED_OS = {
  ...PUSH_PERMISSION_NOT_ASKED,
  permission_state: "denied_by_os",
  banner_should_appear: true,
};

export const PUSH_PERMISSION_DENIED_USER = {
  ...PUSH_PERMISSION_NOT_ASKED,
  permission_state: "denied_by_user_choice",
  banner_should_appear: false,
};

// ─── Trial Status Fixtures ─────────────────────────────────────────────────

export const TENANT_ON_TRIAL_7_DAYS = {
  tenant_id: SIGNUP_STATE_STEP1.tenant_id,
  is_on_trial: true,
  trial_ends_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  trial_expired: false,
};

export const TENANT_ON_TRIAL_3_DAYS = {
  ...TENANT_ON_TRIAL_7_DAYS,
  trial_ends_at: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
};

export const TENANT_ON_TRIAL_1_DAY = {
  ...TENANT_ON_TRIAL_7_DAYS,
  trial_ends_at: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString(),
};

export const TENANT_TRIAL_EXPIRED = {
  ...TENANT_ON_TRIAL_7_DAYS,
  trial_ends_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
  trial_expired: true,
};

export const TENANT_PAID = {
  tenant_id: SIGNUP_STATE_STEP1.tenant_id,
  is_on_trial: false,
  trial_ends_at: null,
  trial_expired: false,
};
