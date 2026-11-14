/**
 * InvoiceFinancialDeltaCallout unit tests — FE-B9
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { InvoiceFinancialDeltaCallout } from "./InvoiceFinancialDeltaCallout";

const baseProps = {
  pilotAmountCents: 285000,
  qbAmountCents: 322500,
  financialDeltaCents: 3750,
  arImpactDescription:
    "QB version includes sales tax. Accepting Pilot removes $375 from AR.",
  taxPeriodWarning: null,
  qbTransactionUrl: null,
};

describe("InvoiceFinancialDeltaCallout", () => {
  it("renders positive delta as 'QB higher'", () => {
    render(
      <InvoiceFinancialDeltaCallout
        {...baseProps}
        financialDeltaCents={3750}
      />,
    );
    expect(screen.getByTestId("financial-delta-amount")).toHaveTextContent(
      /QB is/i,
    );
  });

  it("renders negative delta as 'Pilot higher'", () => {
    render(
      <InvoiceFinancialDeltaCallout
        {...baseProps}
        financialDeltaCents={-5000}
        pilotAmountCents={322500}
        qbAmountCents={285000}
      />,
    );
    expect(screen.getByTestId("financial-delta-amount")).toHaveTextContent(
      /Pilot is/i,
    );
  });

  it("renders both Pilot and QB amounts", () => {
    render(<InvoiceFinancialDeltaCallout {...baseProps} />);
    expect(screen.getByTestId("pilot-amount")).toBeInTheDocument();
    expect(screen.getByTestId("qb-amount")).toBeInTheDocument();
  });

  it("renders taxPeriodWarning banner when non-null", () => {
    render(
      <InvoiceFinancialDeltaCallout
        {...baseProps}
        taxPeriodWarning="Q1 2026"
      />,
    );
    expect(screen.getByTestId("tax-period-warning-banner")).toBeInTheDocument();
    expect(screen.getByText(/Q1 2026/)).toBeInTheDocument();
  });

  it("does NOT render taxPeriodWarning banner when null", () => {
    render(
      <InvoiceFinancialDeltaCallout {...baseProps} taxPeriodWarning={null} />,
    );
    expect(
      screen.queryByTestId("tax-period-warning-banner"),
    ).not.toBeInTheDocument();
  });

  it("renders QB deep-link when qbTransactionUrl non-null", () => {
    render(
      <InvoiceFinancialDeltaCallout
        {...baseProps}
        qbTransactionUrl="https://app.qbo.intuit.com/invoice/1"
      />,
    );
    const link = screen.getByTestId("qb-transaction-link");
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute(
      "href",
      "https://app.qbo.intuit.com/invoice/1",
    );
  });

  it("does NOT render QB deep-link when qbTransactionUrl null", () => {
    render(
      <InvoiceFinancialDeltaCallout {...baseProps} qbTransactionUrl={null} />,
    );
    expect(screen.queryByTestId("qb-transaction-link")).not.toBeInTheDocument();
  });

  it("renders AR impact description verbatim", () => {
    render(<InvoiceFinancialDeltaCallout {...baseProps} />);
    expect(screen.getByTestId("ar-impact-description")).toHaveTextContent(
      "QB version includes sales tax. Accepting Pilot removes $375 from AR.",
    );
  });

  it("formats dollar amounts correctly", () => {
    render(<InvoiceFinancialDeltaCallout {...baseProps} />);
    expect(screen.getByTestId("pilot-amount")).toHaveTextContent("$2,850.00");
    expect(screen.getByTestId("qb-amount")).toHaveTextContent("$3,225.00");
  });
});
