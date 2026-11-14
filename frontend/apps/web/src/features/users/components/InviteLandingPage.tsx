/**
 * InviteLandingPage — TEAM-INVITE-1 / TEAM-INVITE-2
 *
 * Location: apps/web/src/features/users/components/InviteLandingPage.tsx
 *
 * Public landing page for /invite/[token]. Uses bare fetch() (sanctioned
 * unauthenticated-surface exception — same as PublicQuotePage). No auth,
 * no app sidebar, no auth chrome.
 *
 * States:
 *  - loading: skeleton spinner
 *  - valid: tenant name, invited email, role display, expiry, accept flow
 *    (TEAM-INVITE-2: form → verify → joined; replaces the old /signup CTA)
 *  - invalid (404): one neutral "link no longer valid" state
 *  - error (non-404): retry state
 *
 * RULE 1: NEVER calls useAuth(), RequireAuth, RoleGate, or any auth hook.
 *         (The auth call lives in InviteVerifyStep, mirroring VerifyEmailStep.)
 * RULE 2: Bare fetch() exception — unauthenticated surface (no Amplify session).
 * WCAG 3.3.7: displays invited email prominently beside the form (Redundant Entry).
 */

"use client";

import React, { useEffect, useState } from "react";
import { PoweredByPilotFooter } from "@/features/public-quote/PoweredByPilotFooter";
import { InviteAcceptForm } from "@/features/users/components/InviteAcceptForm";
import { InviteVerifyStep } from "@/features/users/components/InviteVerifyStep";

interface InviteData {
  tenant_name: string;
  email: string;
  role_code: string | null;
  expires_at: string;
}

type PageState =
  | { phase: "loading" }
  | { phase: "valid"; data: InviteData }
  | { phase: "invalid" }
  | { phase: "error" };

const ROLE_LABELS: Record<string, string> = {
  owner: "Owner",
  technician: "Field Technician",
  office_staff: "Office Staff",
  accountant: "Accountant",
};

interface InviteLandingPageProps {
  token: string;
}

// TEAM-INVITE-2 §F: phase state machine for the accept flow.
type AcceptPhase = { step: "form" } | { step: "verify"; password: string };

export function InviteLandingPage({ token }: InviteLandingPageProps) {
  const [pageState, setPageState] = useState<PageState>({ phase: "loading" });
  const [acceptPhase, setAcceptPhase] = useState<AcceptPhase>({ step: "form" });

  async function fetchInvite() {
    setPageState({ phase: "loading" });
    try {
      const res = await fetch(`/api/v1/invites/${token}`);

      if (res.status === 404) {
        // Uniform 404 for all failure modes (expired/accepted/revoked/unknown)
        setPageState({ phase: "invalid" });
        return;
      }

      if (!res.ok) {
        setPageState({ phase: "error" });
        return;
      }

      const data = (await res.json()) as InviteData;
      setPageState({ phase: "valid", data });
    } catch {
      setPageState({ phase: "error" });
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchInvite();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // ─── Loading ──────────────────────────────────────────────────────────────
  if (pageState.phase === "loading") {
    return (
      <div
        className="min-h-screen bg-neutral-50 flex items-center justify-center"
        data-testid="invite-loading"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-2 border-neutral-300 border-t-brand-600 animate-spin" />
          <p className="text-sm text-neutral-500">Loading invite…</p>
        </div>
      </div>
    );
  }

  // ─── Invalid (404 — uniform) ──────────────────────────────────────────────
  if (pageState.phase === "invalid") {
    return (
      <div
        className="min-h-screen bg-neutral-50 flex flex-col"
        data-testid="invite-invalid-page"
      >
        <main className="flex-1 flex items-center justify-center px-4 py-16">
          <div className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-8 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-neutral-800">
              This invite link is no longer valid.
            </h1>
            <p className="mt-2 text-sm text-neutral-600">
              Ask the business owner to send you a fresh invite.
            </p>
          </div>
        </main>
        <PoweredByPilotFooter />
      </div>
    );
  }

  // ─── Error (non-404) ──────────────────────────────────────────────────────
  if (pageState.phase === "error") {
    return (
      <div
        className="min-h-screen bg-neutral-50 flex flex-col"
        data-testid="invite-error-page"
      >
        <main className="flex-1 flex items-center justify-center px-4 py-16">
          <div className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-8 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-neutral-800">
              Something went wrong
            </h1>
            <p className="mt-2 text-sm text-neutral-500">
              Could not load the invite. Check your connection and try again.
            </p>
            <button
              onClick={() => void fetchInvite()}
              className="mt-4 rounded-lg border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              Try again
            </button>
          </div>
        </main>
        <PoweredByPilotFooter />
      </div>
    );
  }

  // ─── Valid ────────────────────────────────────────────────────────────────
  const { data } = pageState;
  const roleLabel = data.role_code
    ? (ROLE_LABELS[data.role_code] ?? data.role_code)
    : "Team Member";
  const expiryFormatted = new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date(data.expires_at));

  return (
    <div
      className="min-h-screen bg-neutral-50 flex flex-col"
      data-testid="invite-landing-page"
    >
      {/* Brand header — minimal */}
      <header className="w-full border-b border-neutral-200 bg-white">
        <div className="mx-auto max-w-2xl px-4 py-4">
          <p className="text-sm font-semibold text-brand-600">
            Pilot for Trades
          </p>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-neutral-900">
            You{"'"}ve been invited to join{" "}
            <span className="text-brand-600">{data.tenant_name}</span>
          </h1>

          <dl className="mt-6 space-y-3">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                Invited email
              </dt>
              <dd className="mt-1 text-sm font-medium text-neutral-900">
                {data.email}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                Role
              </dt>
              <dd className="mt-1 text-sm text-neutral-900">{roleLabel}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                Expires
              </dt>
              <dd className="mt-1 text-sm text-neutral-900">
                {expiryFormatted}
              </dd>
            </div>
          </dl>

          {/* TEAM-INVITE-2: accept flow replaces the old /signup CTA link. */}
          {acceptPhase.step === "form" ? (
            <InviteAcceptForm
              email={data.email}
              onSignedUp={(password) =>
                setAcceptPhase({ step: "verify", password })
              }
            />
          ) : (
            <InviteVerifyStep
              email={data.email}
              password={acceptPhase.password}
              roleCode={data.role_code}
            />
          )}
        </div>
      </main>

      <PoweredByPilotFooter />
    </div>
  );
}
