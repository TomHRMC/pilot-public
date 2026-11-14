/**
 * /schedule — Dispatch Board page
 *
 * Location: apps/web/src/app/(authed)/schedule/page.tsx
 *
 * Replaces the FE-B0 placeholder with the full DispatchBoardPage.
 * Protected by RoleGate (owner | operator) inside DispatchBoardPage.
 *
 * Per batch-fe-b4-design.md §C
 */

import { DispatchBoardPage } from "@/features/dispatch-board/components/DispatchBoardPage";

export default function SchedulePage() {
  return <DispatchBoardPage />;
}
