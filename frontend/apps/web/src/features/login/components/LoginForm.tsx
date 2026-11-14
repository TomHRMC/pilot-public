/**
 * LoginForm — web
 *
 * Location: apps/web/src/features/login/components/LoginForm.tsx
 *
 * Email + password form for Cognito authentication on web.
 * In mock mode (NEXT_PUBLIC_USE_MOCK_AUTH=true): renders role-selector
 * dropdown instead of password field.
 *
 * FE-B2: design doc §A.2 LoginForm (web)
 */

"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@pilot/ui/auth";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import type { PilotRole } from "@pilot/ui/auth";
import { useLoginFlow } from "../hooks/useLoginFlow";
import { MfaChallengeStep } from "./MfaChallengeStep";
import { MfaEnrollmentRequiredGate } from "./MfaEnrollmentRequiredGate";

interface LoginFormProps {
  onSuccess: (role: PilotRole) => void;
  /** Dev-only: when true, renders role-selector dropdown instead of password field */
  mockMode?: boolean;
}

const PILOT_ROLES: PilotRole[] = [
  "owner",
  "technician",
  "office_staff",
  "accountant",
];

function RoleLabel(role: PilotRole): string {
  switch (role) {
    case "owner":
      return "Owner";
    case "technician":
      return "Technician";
    case "office_staff":
      return "Office Staff";
    case "accountant":
      return "Accountant";
    default:
      return role;
  }
}

function MockLoginForm({
  onSuccess,
  defaultRole,
}: {
  onSuccess: (role: PilotRole) => void;
  defaultRole: PilotRole;
}) {
  const [email, setEmail] = useState("mockuser@pilot-dev.example.com");
  const [selectedRole, setSelectedRole] = useState<PilotRole>(defaultRole);
  const { signIn } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await signIn(email, "");
      onSuccess(selectedRole);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      aria-label="Sign in"
      className="flex flex-col gap-4"
    >
      {/* DEV MODE indicator */}
      <div className="rounded-md bg-alert-50 border border-alert-200 px-3 py-2 text-center">
        <span className="text-caption text-alert-600">
          DEV MODE — Mock Auth Active
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="mock-email" className="text-body-lg text-neutral-900">
          Email
        </label>
        <input
          id="mock-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="mock-role" className="text-body-lg text-neutral-900">
          Role
        </label>
        <select
          id="mock-role"
          value={selectedRole}
          onChange={(e) => setSelectedRole(e.target.value as PilotRole)}
          className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
        >
          {PILOT_ROLES.map((r) => (
            <option key={r} value={r}>
              {RoleLabel(r)}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-md bg-brand-600 px-4 py-2 text-body-lg text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:opacity-50"
      >
        {isLoading ? "Signing in…" : `Sign in as ${RoleLabel(selectedRole)}`}
      </button>
    </form>
  );
}

export function LoginForm({ onSuccess, mockMode = false }: LoginFormProps) {
  const { signOut } = useAuth();
  const { addNotification } = useNotificationQueue();

  const {
    step,
    isLoading,
    error,
    mfaChallenge,
    submitCredentials,
    submitMfaCode,
    cancelMfa,
    clearError,
  } = useLoginFlow(onSuccess);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Enqueue error as notification banner when it changes
  useEffect(() => {
    if (error) {
      addNotification({
        id: `login-error-${Date.now()}`,
        severity: "error",
        title: error,
      });
      clearError();
    }
  }, [error, addNotification, clearError]);

  // Default role from env
  const defaultRole =
    ((typeof process !== "undefined" &&
      process.env?.NEXT_PUBLIC_MOCK_USER_ROLE) as PilotRole | undefined) ??
    "owner";

  if (mockMode) {
    return <MockLoginForm onSuccess={onSuccess} defaultRole={defaultRole} />;
  }

  if (step === "mfa-enrollment-required") {
    return (
      <MfaEnrollmentRequiredGate
        onBeginEnrollment={() => {
          window.location.href = "/settings/my-account";
        }}
        onSignOut={() => void signOut()}
      />
    );
  }

  if (step === "mfa-challenge" && mfaChallenge) {
    return (
      <MfaChallengeStep
        challengeName={mfaChallenge.challengeName}
        destination={mfaChallenge.destination}
        onConfirm={submitMfaCode}
        onCancel={cancelMfa}
        isLoading={isLoading}
        error={error}
      />
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitCredentials(email, password);
  };

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      aria-label="Sign in"
      className="flex flex-col gap-4"
    >
      <div className="flex flex-col gap-1">
        <label htmlFor="login-email" className="text-body-lg text-neutral-900">
          Email
        </label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isLoading}
          aria-required="true"
          placeholder="you@example.com"
          className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:opacity-50"
        />
      </div>

      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <label
            htmlFor="login-password"
            className="text-body-lg text-neutral-900"
          >
            Password
          </label>
          <Link
            href="/password-reset"
            className="text-caption text-brand-600 hover:underline focus:outline-none"
          >
            Forgot password?
          </Link>
        </div>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={isLoading}
          aria-required="true"
          className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:opacity-50"
        />
      </div>

      <button
        type="submit"
        disabled={isLoading || !email || !password}
        className="w-full rounded-md bg-brand-600 px-4 py-2 text-body-lg text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:opacity-50"
        aria-busy={isLoading}
      >
        {isLoading ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
