/**
 * useSignupWizard — Signup wizard state machine hook
 *
 * Location: apps/web/src/features/signup/hooks/useSignupWizard.ts
 *
 * RULE 4: Wizard step navigation is driven by backend onboarding state.
 *         This hook reads current_step from the API response and renders accordingly.
 *         No client-side step progression logic. Refresh lands user on correct step.
 *
 * RULE 7: Legal acceptance is checked before re-POSTing — never re-POST if already accepted.
 *
 * On mount: reads tenant_id from sessionStorage; if present, fetches
 * GET /api/v1/signup/{tenant_id}/state and navigates to the current backend step.
 * sessionStorage is cleared after wizard completes.
 */

"use client";

import { useCallback, useReducer } from "react";
import { useRouter } from "next/navigation";
import { apiClient, getApiProblem } from "@pilot/shared-api";
import type {
  WizardMachineState,
  WizardAction,
  SignupStateResponse,
} from "../types";
import {
  signupStateToStep,
  stateOrder,
  stepToUrl,
  WIZARD_TENANT_ID_KEY,
  type WizardSignupState,
  type OnboardingStep,
} from "../types";

// ─── Initial State ────────────────────────────────────────────────────────────

function getInitialState(): WizardMachineState {
  return {
    tenantId: null,
    currentStep: "account" as OnboardingStep,
    signupState: "step1_account",
    collectedData: {},
    isLoading: false,
    error: null,
    isResuming: false,
  };
}

// ─── Reducer ──────────────────────────────────────────────────────────────────

function wizardReducer(
  state: WizardMachineState,
  action: WizardAction,
): WizardMachineState {
  switch (action.type) {
    case "STEP1_COMPLETE":
      return {
        ...state,
        tenantId: action.tenantId,
        signupState: "step2_legal",
        currentStep: signupStateToStep["step2_legal"],
        collectedData: {
          ...state.collectedData,
          ownerEmail: action.email,
        },
        isLoading: false,
        error: null,
      };

    case "STEP2_COMPLETE":
      return {
        ...state,
        signupState: "step3_phone",
        currentStep: signupStateToStep["step3_phone"],
        collectedData: {
          ...state.collectedData,
          tosAccepted: true,
          privacyAccepted: true,
          eulaAccepted: true,
        },
        isLoading: false,
        error: null,
      };

    case "STEP3_COMPLETE":
      return {
        ...state,
        signupState: "step4_tier",
        currentStep: signupStateToStep["step4_tier"],
        collectedData: {
          ...state.collectedData,
          phoneVerified: action.phoneVerified,
          phoneSkipped: !action.phoneVerified,
        },
        isLoading: false,
        error: null,
      };

    case "STEP4_COMPLETE":
      return {
        ...state,
        signupState: "step5_confirm",
        currentStep: signupStateToStep["step5_confirm"],
        collectedData: {
          ...state.collectedData,
          selectedTierId: action.tierId,
          selectedTierIsTrial: action.isTrial,
        },
        isLoading: false,
        error: null,
      };

    case "STEP5_COMPLETE":
      return {
        ...state,
        signupState: "complete",
        currentStep: signupStateToStep["complete"],
        isLoading: false,
        error: null,
      };

    case "RESUME": {
      const step =
        signupStateToStep[action.state.signup_state] ??
        signupStateToStep["step1_account"];
      return {
        ...state,
        tenantId: action.state.tenant_id,
        signupState: action.state.signup_state,
        currentStep: step,
        collectedData: {
          businessName: action.state.collected_data.business_name,
          ownerFirstName: action.state.collected_data.owner_first_name,
          ownerEmail: action.state.collected_data.owner_email,
          selectedTierId: action.state.collected_data.selected_tier_id,
          phoneSkipped: action.state.collected_data.phone_skipped,
          phoneVerified: action.state.collected_data.phone_verified,
          // C-B5: Charter program lifecycle fields
          freePeriodEndsAt: action.state.collected_data.free_period_ends_at,
          requiresPaymentMethod:
            action.state.collected_data.requires_payment_method,
          charterMemberNumber:
            action.state.collected_data.charter_member_number,
        },
        isLoading: false,
        isResuming: false,
        error: null,
      };
    }

    case "SET_ERROR":
      return { ...state, error: action.error, isLoading: false };

    case "CLEAR_ERROR":
      return { ...state, error: null };

    case "SET_LOADING":
      return { ...state, isLoading: action.isLoading };

    default:
      return state;
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────
// SIGNUP-GA-B1: `stepToUrl` and `stateOrder` are now imported from the shared
// `../types` module (the single canonical Model-B source) so this hook cannot
// drift from the page guards.

export interface UseSignupWizardReturn {
  state: WizardMachineState;
  dispatch: React.Dispatch<WizardAction>;
  /** Persists tenant_id to sessionStorage after step 1 */
  persistTenantId: (tenantId: string) => void;
  /** Clears sessionStorage wizard data after completion */
  clearWizardSession: () => void;
  /** Fetches backend state and navigates to correct step (resumability) */
  resumeFromBackend: () => Promise<void>;
  /** Returns true if the given signupState meets the minimum for currentStep */
  isStepAccessible: (
    currentStepName: string,
    backendState: WizardSignupState,
  ) => boolean;
}

export function useSignupWizard(): UseSignupWizardReturn {
  const [state, dispatch] = useReducer(wizardReducer, getInitialState());
  const router = useRouter();

  const persistTenantId = useCallback((tenantId: string) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem(WIZARD_TENANT_ID_KEY, tenantId);
    }
  }, []);

  const clearWizardSession = useCallback(() => {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
    }
  }, []);

  const resumeFromBackend = useCallback(async () => {
    if (typeof window === "undefined") return;

    const storedTenantId = sessionStorage.getItem(WIZARD_TENANT_ID_KEY);
    if (!storedTenantId) return;

    dispatch({ type: "SET_LOADING", isLoading: true });

    try {
      const response = await apiClient.get<SignupStateResponse>(
        `/api/v1/signup/${storedTenantId}/state`,
      );
      const serverState = response.data;

      dispatch({ type: "RESUME", state: serverState });

      // Navigate to the canonical step URL for the backend state
      const targetStep = signupStateToStep[serverState.signup_state];
      const targetUrl = stepToUrl[targetStep] ?? "/signup/account";
      router.replace(targetUrl);
    } catch (err: unknown) {
      const problem = getApiProblem(err);
      // 404 → session expired, clear and restart
      if (problem.status === 404) {
        clearWizardSession();
        dispatch({ type: "SET_ERROR", error: "session_expired" });
        router.replace("/signup/account?expired=true");
      } else {
        dispatch({
          type: "SET_ERROR",
          error:
            problem.detail ?? "Failed to resume session. Please try again.",
        });
      }
    }
  }, [router, clearWizardSession]);

  const isStepAccessible = useCallback(
    (currentStepName: string, backendState: WizardSignupState): boolean => {
      const stepMinimumStateMap: Record<string, WizardSignupState> = {
        account: "step1_account",
        legal: "step1_account",
        phone: "step2_legal",
        plan: "step3_phone",
        ready: "step4_tier",
        pay: "step4_tier",
      };
      const minimumState = stepMinimumStateMap[currentStepName];
      if (!minimumState) return true; // unknown step — allow
      return stateOrder[backendState] >= stateOrder[minimumState];
    },
    [],
  );

  return {
    state,
    dispatch,
    persistTenantId,
    clearWizardSession,
    resumeFromBackend,
    isStepAccessible,
  };
}
