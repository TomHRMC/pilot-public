/**
 * /settings/operations/field-operations — Field Operations settings page
 *
 * Location: apps/web/src/app/(authed)/settings/operations/field-operations/page.tsx
 *
 * Role gate: settings.tenant.write
 * Settings: I1 (default_labor_rate_preset — preset-select, blur),
 *           I2 (require_approval_for_tech_quotes — boolean, blur + pending-quote confirm),
 *           I3 (field_notes_required — boolean, blur)
 */

import React from "react";
import { FieldOperationsPage } from "@/features/settings-operations/components/FieldOperationsPage";

export default function FieldOperationsRoute() {
  return <FieldOperationsPage />;
}
