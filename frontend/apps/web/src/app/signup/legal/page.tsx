/**
 * /signup/legal — Step 2: Legal Acceptance
 *
 * Location: apps/web/src/app/signup/legal/page.tsx
 *
 * RULE 7: Legal acceptance is IMMUTABLE. Checks already_accepted before POSTing.
 * RULE 4: On mount, verifies backend state ≥ step2_legal or redirects back.
 * "Continue" disabled until all 3 required checkboxes checked.
 */

"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient, getApiProblem } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import { WizardProgressBar } from "@/features/signup/components/WizardProgressBar";
import {
  LegalCheckboxGroup,
  type LegalCheckboxState,
} from "@/features/signup/components/LegalCheckboxGroup";
import { LegalDocModal } from "@/features/signup/components/LegalDocModal";
import {
  WIZARD_TENANT_ID_KEY,
  signupStateToStep,
  stepToUrl,
  OnboardingStep,
  type WizardSignupState,
} from "@/features/signup/types";
import type { LegalRequiredResponse } from "@/features/signup/types";

export default function SignupLegalPage() {
  const router = useRouter();
  const { user } = useAuth();
  // Lazy init: reads sessionStorage synchronously, falls back to user.tenantId
  // (SIGNUP-UI-FIX-1: sessionStorage is cleared when the browser tab closes,
  // but an authenticated user returning to the wizard should still resume).
  const [tenantId] = useState<string | null>(() =>
    typeof window !== "undefined"
      ? (sessionStorage.getItem(WIZARD_TENANT_ID_KEY) ?? user?.tenantId ?? null)
      : null,
  );
  const [openDoc, setOpenDoc] = useState<"tos" | "privacy" | "eula" | null>(
    null,
  );

  // User-toggled checkbox state (separate from server-accepted overlay)
  const [userChecked, setUserChecked] = useState<LegalCheckboxState>({
    tos: false,
    privacy: false,
    eula: false,
    marketingEmail: false,
  });

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch signup state for redirect + ownerName
  const { data: signupStateData } = useQuery({
    queryKey: ["signup-state", tenantId],
    queryFn: async () => {
      const res = await apiClient.get(`/api/v1/signup/${tenantId}/state`);
      return res.data;
    },
    enabled: !!tenantId,
    staleTime: 30 * 1000,
  });

  // Redirect based on backend state — pure side effect, no setState.
  // SIGNUP-GA-B1: Model B — `signup_state = stepN` means step N is done and
  // the user is now on UI page N+1. Legal is the page for `step1_account`
  // (account done ⇒ collect legal), so a `step1_account` user must NOT be
  // bounced. Redirect only when the user belongs on a different page.
  useEffect(() => {
    if (!tenantId) {
      router.replace("/signup/account");
      return;
    }
    // SIGNUP-UI-FIX-1: persist tenantId to sessionStorage for subsequent steps
    if (!sessionStorage.getItem(WIZARD_TENANT_ID_KEY) && tenantId) {
      sessionStorage.setItem(WIZARD_TENANT_ID_KEY, tenantId);
    }
    if (!signupStateData) return;
    const current = signupStateData.signup_state as WizardSignupState;
    // complete is special-cased to /dashboard (clears session on ready page).
    if (current === "complete") {
      router.replace("/dashboard");
      return;
    }
    const belongsOn = signupStateToStep[current]; // Model B page for this state
    if (belongsOn !== OnboardingStep.Legal) {
      router.replace(stepToUrl[belongsOn] ?? "/signup/account");
    }
  }, [router, tenantId, signupStateData]);

  const ownerName = signupStateData?.collected_data?.owner_first_name ?? null;

  // Fetch legal requirements (to check already_accepted — RULE 7)
  const { data: legalRequired } = useQuery({
    queryKey: ["legal-required", tenantId],
    queryFn: async (): Promise<LegalRequiredResponse> => {
      const res = await apiClient.get<LegalRequiredResponse>(
        `/api/v1/signup/${tenantId}/legal/required`,
      );
      return res.data;
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000,
  });

  // Derive server-accepted overlay from legalRequired — no setState needed
  const serverAccepted = useMemo<Partial<LegalCheckboxState>>(() => {
    if (!legalRequired) return {};
    const acc: Partial<LegalCheckboxState> = {};
    for (const doc of legalRequired.required_documents) {
      if (doc.already_accepted) {
        acc[doc.document_type as keyof LegalCheckboxState] = true;
      }
    }
    return acc;
  }, [legalRequired]);

  // Merge server-accepted with user-toggled (RULE 7: already-accepted stay checked)
  const checkboxState: LegalCheckboxState = {
    tos: serverAccepted.tos ?? userChecked.tos,
    privacy: serverAccepted.privacy ?? userChecked.privacy,
    eula: serverAccepted.eula ?? userChecked.eula,
    marketingEmail: userChecked.marketingEmail,
  };

  const setCheckboxState = (
    updater:
      | LegalCheckboxState
      | ((prev: LegalCheckboxState) => LegalCheckboxState),
  ) => {
    setUserChecked(
      typeof updater === "function" ? updater(checkboxState) : updater,
    );
  };

  const allRequiredChecked =
    checkboxState.tos && checkboxState.privacy && checkboxState.eula;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!allRequiredChecked || !tenantId || !legalRequired) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // RULE 7: Only POST for docs not already accepted
      const docsToAccept = legalRequired.required_documents.filter(
        (doc) => !doc.already_accepted,
      );

      // Accept each non-already-accepted document
      for (const doc of docsToAccept) {
        await apiClient.post(`/api/v1/signup/${tenantId}/legal/accept`, {
          document_type: doc.document_type,
          document_version_hash: doc.current_version_hash,
          accepted_at: new Date().toISOString(),
        });
      }

      // Optional marketing email opt-in
      if (checkboxState.marketingEmail) {
        await apiClient.post(`/api/v1/signup/${tenantId}/legal/accept`, {
          document_type: "marketing_email_optin",
          document_version_hash: "marketing-v1",
          accepted_at: new Date().toISOString(),
        });
      }

      // Advance wizard step
      await apiClient.put(`/api/v1/signup/${tenantId}/step2`, {
        documents_accepted: ["tos", "privacy", "eula"],
      });

      router.push("/signup/phone");
    } catch (err: unknown) {
      const problem = getApiProblem(err);
      setSubmitError(
        problem.detail ?? "Failed to save your agreements. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <WizardProgressBar currentStep="legal" />

      {ownerName && (
        <div className="rounded-lg bg-brand-50 border border-brand-100 px-4 py-3 text-sm text-brand-700">
          Welcome back, {ownerName}. Let&apos;s pick up where you left off.
        </div>
      )}

      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-neutral-900">
          Review &amp; agree
        </h1>
        <p className="text-sm text-neutral-600">
          Please review and agree to our policies before continuing.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-6"
        data-testid="signup-legal-form"
      >
        <LegalCheckboxGroup
          value={checkboxState}
          onChange={setCheckboxState}
          onReadDocument={setOpenDoc}
        />

        {submitError && (
          <p role="alert" className="text-fault-600 text-sm">
            {submitError}
          </p>
        )}

        <button
          type="submit"
          disabled={!allRequiredChecked || isSubmitting}
          aria-disabled={!allRequiredChecked || isSubmitting}
          data-testid="signup-legal-continue"
          className={`
            w-full py-3 px-6 rounded-lg text-sm font-semibold transition-colors
            focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
            ${
              !allRequiredChecked || isSubmitting
                ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
                : "bg-brand-600 hover:bg-brand-800 text-white"
            }
          `}
        >
          {isSubmitting ? "Saving…" : "Continue →"}
        </button>
      </form>

      <LegalDocModal docType={openDoc} onClose={() => setOpenDoc(null)} />
    </div>
  );
}
