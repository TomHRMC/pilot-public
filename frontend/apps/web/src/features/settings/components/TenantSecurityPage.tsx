/**
 * TenantSecurityPage — BETA-B4 / STEP 2
 *
 * Location: apps/web/src/features/settings/components/TenantSecurityPage.tsx
 *
 * Tenant-level security policy: enable/disable MFA required for all users.
 * Route: /settings/security
 */

"use client";

import React from "react";
import { RoleGate } from "@pilot/ui/role-gate";
import { useTenantMfaPolicy } from "../hooks/useTenantMfaPolicy";

function TenantSecurityContent() {
  const { policy, isLoading, isError, setMfaRequired, isUpdating } =
    useTenantMfaPolicy();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6 max-w-2xl">
        <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
          Could not load security policy. Please refresh the page.
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-2">
        Security & MFA
      </h1>
      <p className="text-sm text-neutral-500 mb-6">
        Configure security policies for all team members.
      </p>

      <div className="rounded-md border border-neutral-200 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-medium text-neutral-900 text-sm">
              Require MFA for all users
            </p>
            <p className="text-xs text-neutral-500 mt-1">
              When enabled, all team members must enroll in MFA within a 7-day
              grace period.
              {policy?.gracePeriodStartsAt && (
                <span className="block mt-1 text-alert-600">
                  Grace period started{" "}
                  {new Date(policy.gracePeriodStartsAt).toLocaleDateString()}.
                </span>
              )}
            </p>
          </div>
          <button
            role="switch"
            aria-checked={policy?.tenantMfaRequired ?? false}
            aria-label="Require MFA for all users"
            disabled={isUpdating}
            onClick={() =>
              void setMfaRequired(!(policy?.tenantMfaRequired ?? false))
            }
            className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 ${
              policy?.tenantMfaRequired ? "bg-brand-600" : "bg-neutral-200"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                policy?.tenantMfaRequired ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  );
}

export function TenantSecurityPage() {
  return (
    <RoleGate permission="settings.manage">
      <TenantSecurityContent />
    </RoleGate>
  );
}
