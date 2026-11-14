/**
 * Settings > Help & About > Feedback page — FE-B16
 *
 * Location: apps/web/src/app/(authed)/settings/help-and-about/feedback/page.tsx
 *
 * Route: /settings/help-and-about/feedback
 * Auth: all authenticated users
 */

import type { Metadata } from "next";
import { FeedbackFormPage } from "../../../../../features/help/components/FeedbackFormPage";

export const metadata: Metadata = {
  title: "Send Feedback — Pilot",
};

export default function FeedbackPage() {
  return (
    <div className="px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-neutral-900">
          Send feedback
        </h1>
        <p className="text-sm text-neutral-500 mt-1">
          Report a bug, request a feature, or share general feedback with the
          Pilot team.
        </p>
      </div>
      <FeedbackFormPage />
    </div>
  );
}
