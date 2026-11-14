/**
 * Password Change Page — FE-B12
 * Route: /settings/my-account/password
 */
"use client";
import React from "react";
import { PasswordChangeForm } from "../../../../../features/account-settings/components/PasswordChangeForm";

export default function PasswordPage() {
  return (
    <div className="flex flex-col gap-6 max-w-lg">
      <div>
        <h1 className="text-h2 font-semibold text-neutral-900">
          Change password
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Update your account password. All other devices will be signed out.
        </p>
      </div>
      <PasswordChangeForm />
    </div>
  );
}
