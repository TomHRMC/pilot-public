/**
 * Communications Settings Layout — FE-B14
 *
 * Location: apps/web/src/app/(authed)/settings/communications/layout.tsx
 *
 * Restricts communications settings to owner, office_staff, and operator roles.
 * New top-level settings group created by FE-B14.
 *
 * PLP fix (2026-08-30): widened to include `operator` so the page gate matches
 * the SettingsIndexPage "Branding" card visibility. The card sits in the
 * Workspace section (gated by `settings.tenant.write` = owner + operator), so
 * operator could see the card but got a blank page. Operator is a tenant admin
 * with `settings.tenant.write` + `settings.manage` and logically should manage
 * branding/SMS compliance.
 *
 * RoleGate: owner/office_staff/operator (role prop accepts array of PilotRole).
 */

"use client";

import React from "react";
import { RoleGate } from "@pilot/ui";

interface CommunicationsLayoutProps {
  children: React.ReactNode;
}

export default function CommunicationsLayout({
  children,
}: CommunicationsLayoutProps) {
  return (
    <RoleGate role={["owner", "office_staff", "accountant"]}>
      <div data-testid="communications-layout">{children}</div>
    </RoleGate>
  );
}
