/**
 * Active Sessions Page — FE-B12
 * Route: /settings/my-account/sessions
 */
"use client";
import React from "react";
import { ActiveSessionsList } from "../../../../../features/account-settings/components/ActiveSessionsList";

export default function SessionsPage() {
  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-h2 font-semibold text-neutral-900">
          Active sessions
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          These are the devices currently signed in to your account.
        </p>
      </div>
      <ActiveSessionsList />
    </div>
  );
}
