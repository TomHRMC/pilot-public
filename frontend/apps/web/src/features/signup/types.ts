/**
 * Signup Wizard — Types
 * Location: apps/web/src/features/signup/types.ts
 *
 * FE-B13: Onboarding wizard state machine types.
 * RULE 4: Wizard step navigation is driven by backend onboarding state.
 *         No client-side step logic — all from backend `signup_state`.
 */

// ─── Onboarding Step Enum ────────────────────────────────────────────────────

export enum OnboardingStep {
  Account = "account",
  Legal = "legal",
  Phone = "phone",
  Plan = "plan",
  Ready = "ready",
  Pay = "pay",
}

// ─── Backend Signup State Canonical Values ───────────────────────────────────

export type WizardSignupState =
  | "step1_account"
  | "step2_legal"
  | "step3_phone"
  | "step4_tier"
  | "step5_confirm"
  | "complete";

/**
 * Maps backend signup_state → the wizard step (UI page) the user should be ON.
 *
 * SIGNUP-GA-B1: This is the canonical "Model B" mapping — `signup_state = stepN`
 * means *step N is complete; the user is now on UI page N+1*. The backend state
 * machine (`VALID_STATE_TRANSITIONS` in tenant_signup.py) is authoritative.
 *
 *   step1_account  → Legal    (account step done ⇒ collect legal)
 *   step2_legal    → Phone
 *   step3_phone    → Plan
 *   step4_tier     → Ready
 *   step5_confirm  → Ready (payment/confirm)
 *   complete       → Ready   (special-cased to /dashboard in page guards)
 */
export const signupStateToStep: Record<WizardSignupState, OnboardingStep> = {
  step1_account: OnboardingStep.Legal,
  step2_legal: OnboardingStep.Phone,
  step3_phone: OnboardingStep.Plan,
  step4_tier: OnboardingStep.Ready,
  step5_confirm: OnboardingStep.Ready,
  complete: OnboardingStep.Ready,
};

/**
 * Backend state ordering for forward-only navigation guards.
 * Shared so every page reads the same ordering (no inline re-declarations).
 */
export const stateOrder: Record<WizardSignupState, number> = {
  step1_account: 1,
  step2_legal: 2,
  step3_phone: 3,
  step4_tier: 4,
  step5_confirm: 5,
  complete: 6,
};

/**
 * Maps a wizard step (OnboardingStep) → its route URL.
 * Shared so every page guard resolves redirects from one source.
 * `complete` is NOT a step here — page guards special-case it to `/dashboard`.
 */
export const stepToUrl: Record<OnboardingStep, string> = {
  [OnboardingStep.Account]: "/signup/account",
  [OnboardingStep.Legal]: "/signup/legal",
  [OnboardingStep.Phone]: "/signup/phone",
  [OnboardingStep.Plan]: "/signup/plan",
  [OnboardingStep.Ready]: "/signup/ready",
  [OnboardingStep.Pay]: "/signup/ready/pay",
};

/** Maps wizard step → expected minimum backend state */
export const stepToMinimumSignupState: Record<
  OnboardingStep,
  WizardSignupState
> = {
  [OnboardingStep.Account]: "step1_account",
  [OnboardingStep.Legal]: "step1_account",
  [OnboardingStep.Phone]: "step2_legal",
  [OnboardingStep.Plan]: "step3_phone",
  [OnboardingStep.Ready]: "step4_tier",
  [OnboardingStep.Pay]: "step4_tier",
};

// ─── Wizard State Machine ─────────────────────────────────────────────────────

export interface WizardMachineState {
  tenantId: string | null;
  currentStep: OnboardingStep;
  signupState: WizardSignupState;
  collectedData: WizardFormData;
  isLoading: boolean;
  error: string | null;
  isResuming: boolean;
}

export type WizardAction =
  | { type: "STEP1_COMPLETE"; tenantId: string; email: string }
  | { type: "STEP2_COMPLETE" }
  | { type: "STEP3_COMPLETE"; phoneVerified: boolean }
  | { type: "STEP4_COMPLETE"; tierId: string; isTrial: boolean }
  | { type: "STEP5_COMPLETE" }
  | { type: "RESUME"; state: SignupStateResponse }
  | { type: "SET_ERROR"; error: string }
  | { type: "CLEAR_ERROR" }
  | { type: "SET_LOADING"; isLoading: boolean };

// ─── API Request / Response Types ─────────────────────────────────────────────

export interface SignupInitiateRequest {
  business_name: string;
  trade: string;
  business_size: string;
  zip: string;
  time_zone: string;
  owner_email: string;
  owner_first_name: string;
  owner_last_name: string;
}

export interface SignupInitiateResponse {
  tenant_id: string;
  signup_state: "step1_account";
  owner_email: string;
  /**
   * SIGNUP-GA-1 (ADR-0011): true when the Cognito credential has not yet
   * been confirmed (client raced ahead of email confirmation). In the
   * confirm-first flow this is normally false. When true, the UI keeps the
   * user on a "we're finishing setting up your account" state and retries
   * the wizard resolve rather than erroring.
   */
  credential_pending: boolean;
}

export interface SignupStepRequest {
  documents_accepted?: string[];
  phone_verified?: boolean;
  phone_skipped?: boolean;
  selected_tier_id?: string;
  confirmed?: boolean;
  stripe_payment_method_id?: string;
}

export interface SignupStepResponse {
  tenant_id: string;
  signup_state: WizardSignupState;
  next_step: string | null;
}

export interface SignupStateResponse {
  tenant_id: string;
  signup_state: WizardSignupState;
  collected_data: {
    business_name?: string;
    owner_first_name?: string;
    owner_email?: string;
    selected_tier_id?: string;
    phone_skipped?: boolean;
    phone_verified?: boolean;
    // C-B5: Charter program lifecycle fields (returned by backend for
    // step4_tier / step5_confirm / complete states).
    free_period_ends_at?: string | null;
    requires_payment_method?: boolean;
    charter_member_number?: number | null;
  };
}

// ─── Legal Acceptance Types ───────────────────────────────────────────────────

export type LegalDocumentType =
  | "tos"
  | "privacy"
  | "eula"
  | "marketing_email_optin";

export interface LegalRequiredDocument {
  document_type: "tos" | "privacy" | "eula";
  current_version_hash: string;
  already_accepted: boolean;
}

export interface LegalRequiredResponse {
  required_documents: LegalRequiredDocument[];
}

export interface LegalAcceptRequest {
  document_type: LegalDocumentType;
  document_version_hash: string;
  accepted_at: string;
}

export interface LegalAcceptResponse {
  acceptance_id: string;
  document_type: string;
  accepted_at: string;
}

// ─── Subscription Tier Types ──────────────────────────────────────────────────

export interface SubscriptionTierAPI {
  tier_id: string;
  tier_name: string;
  display_label: string;
  monthly_price_cents: number;
  is_trial: boolean;
  trial_duration_days: number | null;
  max_users: number;
  max_sms_segments_per_month: number | null;
  display_order: number;
  is_active: boolean;
  // C-B5: Charter program lifecycle fields
  free_period_days?: number | null;
  requires_payment_method?: boolean;
  signup_cap?: number | null;
}

export interface SubscriptionTiersListResponse {
  tiers: SubscriptionTierAPI[];
}

// ─── Accumulated Wizard Form Data ─────────────────────────────────────────────

export interface WizardFormData {
  // Step 1
  businessName?: string;
  trade?: string;
  businessSize?: "solo" | "small" | "medium" | "large";
  zip?: string;
  timeZone?: string;
  ownerEmail?: string;
  ownerFirstName?: string;
  ownerLastName?: string;
  // Step 2
  tosAccepted?: boolean;
  privacyAccepted?: boolean;
  eulaAccepted?: boolean;
  marketingEmailOptIn?: boolean;
  // Step 3
  phoneVerified?: boolean;
  phoneSkipped?: boolean;
  // Step 4
  selectedTierId?: string;
  selectedTierIsTrial?: boolean;
  // Step 5
  stripePaymentMethodId?: string;
  // C-B5: Charter program lifecycle fields (carried via RESUME action)
  freePeriodEndsAt?: string | null;
  requiresPaymentMethod?: boolean;
  charterMemberNumber?: number | null;
}

// ─── Phone OTP Types ──────────────────────────────────────────────────────────

export interface PhoneOtpSendRequest {
  phone_number: string;
}

export interface PhoneOtpSendResponse {
  message: string;
  expires_in_seconds: number;
}

export interface PhoneOtpConfirmRequest {
  code: string;
}

export interface PhoneOtpConfirmResponse {
  phone_verified: boolean;
  message: string;
}

// ─── Step completion key for sessionStorage ───────────────────────────────────

export const WIZARD_TENANT_ID_KEY = "pilot_signup_tenant_id";
