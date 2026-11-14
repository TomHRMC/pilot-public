/**
 * Data & Privacy — BETA-B4 / STEP 11
 *
 * Route: /settings/data-privacy
 * Static informational page — no data fetching, no "use client" needed.
 */

import Link from "next/link";

export default function DataPrivacyPage() {
  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-2">
        Data & Privacy
      </h1>
      <p className="text-sm text-neutral-500 mb-6">
        Pilot retains your data for the duration of your subscription. You can
        export your data at any time.
      </p>

      <div className="space-y-4">
        {/* Data Retention Card */}
        <div className="rounded-md border border-neutral-200 p-4">
          <p className="font-medium text-neutral-900 text-sm mb-1">
            Data Retention
          </p>
          <p className="text-xs text-neutral-500">
            Audit logs are retained for 12 months. Job records, quotes, and
            financial data are retained indefinitely while your subscription is
            active.
          </p>
        </div>

        {/* Data Export Link */}
        <Link
          href="/settings/my-account/data-export"
          className="flex items-center justify-between p-4 rounded-md border border-neutral-200 hover:border-brand-400 hover:bg-brand-50 transition-colors group"
        >
          <div>
            <p className="font-medium text-neutral-900 text-sm">
              Export Your Data
            </p>
            <p className="text-xs text-neutral-500 mt-0.5">
              Download a copy of all your data
            </p>
          </div>
          <span
            className="text-neutral-400 group-hover:text-brand-600 text-lg"
            aria-hidden="true"
          >
            →
          </span>
        </Link>
      </div>
    </div>
  );
}
