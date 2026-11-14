/**
 * /settings/operations/profitability-rules — Profitability Rules settings page
 *
 * Location: apps/web/src/app/(authed)/settings/operations/profitability-rules/page.tsx
 *
 * Role gate: settings.tenant.write
 * Settings: H1 (etc_variance_note_required_pct), H2 (profitability_target_margin_pct),
 *           H3 (overhead_allocation_pct) — all save-on-blur
 */

import React from "react";
import { ProfitabilityRulesPage } from "@/features/settings-operations/components/ProfitabilityRulesPage";

export default function ProfitabilityRulesRoute() {
  return <ProfitabilityRulesPage />;
}
