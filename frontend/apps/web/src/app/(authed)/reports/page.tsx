/**
 * /reports — Profitability reports page
 *
 * Location: apps/web/src/app/(authed)/reports/page.tsx
 *
 * Replaces the FE-B0 placeholder with ProfitabilityPage.
 * Protected by RoleGate (owner | operator) inside ProfitabilityPage.
 * Other report types are FTU state for MVP.
 *
 * Per batch-fe-b4-design.md §C
 */

import { ProfitabilityPage } from "@/features/profitability/components/ProfitabilityPage";

export default function ReportsPage() {
  return <ProfitabilityPage />;
}
