/**
 * Data Export Page — FE-B12
 * Route: /settings/my-account/data-export
 */
"use client";
import React from "react";
import { DataExportSection } from "../../../../../features/account-settings/components/DataExportSection";

export default function DataExportPage() {
  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-h2 font-semibold text-neutral-900">Data export</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Download a copy of your Pilot data. Exports are available for 7 days.
        </p>
      </div>
      <DataExportSection />
    </div>
  );
}
