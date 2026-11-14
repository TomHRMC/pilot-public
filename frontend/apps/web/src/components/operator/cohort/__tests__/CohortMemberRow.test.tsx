/**
 * CohortMemberRow unit tests — web (C-B11 Part B)
 *
 * Location: apps/web/src/components/operator/cohort/__tests__/CohortMemberRow.test.tsx
 *
 * Tests: renders all columns, red alert, amber alert, none alert.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  renderMemberCell,
  renderDaysLeftCell,
  renderStripeStatusCell,
  renderCardCell,
  renderMessagingStatusCell,
  renderCustomerCountCell,
  renderInvoiceCountCell,
  renderLastJobCell,
  renderActionsCell,
  getCohortRowClassName,
  type CohortMember,
} from "../CohortMemberRow";

const baseMember: CohortMember = {
  tenant_id: "tenant-001",
  business_name: "Acme Electric",
  charter_member_number: 1,
  free_period_ends_at: "2026-11-04T00:00:00Z",
  days_remaining: 90,
  stripe_status: "trialing",
  has_payment_method: false,
  messaging_status: "not_started",
  customer_count: 3,
  invoice_count: 2,
  days_since_last_job: 5,
  last_contact: null,
  alert_level: "none",
};

describe("CohortMemberRow cell renderers", () => {
  it("renders all columns with correct data", () => {
    render(
      <table>
        <tbody>
          <tr>
            <td>{renderMemberCell(baseMember)}</td>
            <td>{renderDaysLeftCell(baseMember)}</td>
            <td>{renderStripeStatusCell(baseMember)}</td>
            <td>{renderCardCell(baseMember)}</td>
            <td>{renderMessagingStatusCell(baseMember)}</td>
            <td>{renderCustomerCountCell(baseMember)}</td>
            <td>{renderInvoiceCountCell(baseMember)}</td>
            <td>{renderLastJobCell(baseMember)}</td>
            <td>{renderActionsCell(baseMember, true, () => {})}</td>
          </tr>
        </tbody>
      </table>,
    );

    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("Acme Electric")).toBeInTheDocument();
    expect(screen.getByText("90")).toBeInTheDocument();
    expect(screen.getByText("Trialing")).toBeInTheDocument();
    expect(screen.getByText("Not started")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("5d")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /extend/i })).toBeInTheDocument();
  });

  it("renders red alert styling for activation risk", () => {
    const redMember = {
      ...baseMember,
      alert_level: "red",
      days_since_last_job: 10,
    };
    const className = getCohortRowClassName(redMember);
    expect(className).toContain("bg-fault-50");
    expect(className).toContain("border-fault-500");
  });

  it("renders amber alert styling for expiring soon", () => {
    const amberMember = {
      ...baseMember,
      alert_level: "amber",
      days_remaining: 7,
    };
    const className = getCohortRowClassName(amberMember);
    expect(className).toContain("bg-alert-50");
    expect(className).toContain("border-alert-500");
  });

  it("renders no alert styling for healthy members", () => {
    const className = getCohortRowClassName(baseMember);
    expect(className).not.toContain("bg-fault");
    expect(className).not.toContain("bg-alert");
    expect(className).toContain("hover:bg-neutral-50");
  });
});
