/* eslint-disable react-hooks/set-state-in-effect */
"use client";

/**
 * InvoiceBuilderPage — Full-page invoice builder at /invoices/new
 *
 * Location: apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx
 *
 * FE-B29: Implements UI-DS-B1 §Surface 1. Mirrors QuoteCreatePage shell pattern.
 *
 * 5 sections:
 *  1. Header Panel — Customer + Site comboboxes, linked job badge
 *  2. Billing Mode Toggle — Line Items | Progress billing (%)
 *  3. Line Items Panel — billable items checklist + custom line item row
 *  4. Payment Terms Panel — terms dropdown + due date label/picker
 *  5. Notes Panel — customer-facing note + internal memo
 *
 * Entry points:
 *  - /invoices/new (blank)
 *  - /invoices/new?job_id= (pre-filled from job)
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: Always-preview-before-send via SendInvoicePreviewModal (§16.8).
 * RULE: Preview Invoice button is disabled in FE-B29 (Phase 1.5 deferral).
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RoleGate } from "@pilot/ui/role-gate";
import { ErrorState } from "@pilot/ui/states";
import { CustomerCombobox } from "../../../components/CustomerCombobox";
import { SiteCombobox } from "../../../components/SiteCombobox";
import { JobCombobox } from "../../../components/JobCombobox";
import { useJob } from "../../jobs/hooks/useJob";
import { useBillableItems } from "../hooks/useBillableItems";
import { useCreateInvoice } from "../hooks/useCreateInvoice";
import { TaxSetupSubFlowModal } from "./TaxSetupSubFlowModal";
import { SendInvoicePreviewModal } from "./SendInvoicePreviewModal";

// ── Types ─────────────────────────────────────────────────────────────────────

interface InvoiceBuilderPageProps {
  jobId?: string | null;
  quoteId?: string | null; // Phase 2.0 — not implemented in FE-B29
}

interface CustomLineItem {
  localId: string;
  description: string;
  unitPriceCents: number;
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

const PAYMENT_TERMS_DAYS: Record<string, number> = {
  due_on_receipt: 0,
  net_15: 15,
  net_30: 30,
};

function computeDueDate(
  terms: string,
  issuedAt: Date = new Date(),
): string | null {
  if (terms === "custom_date") return null;
  const days = PAYMENT_TERMS_DAYS[terms];
  if (days === undefined) return null;
  const due = new Date(issuedAt);
  due.setDate(due.getDate() + days);
  return due.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function InvoiceBuilderPage({
  jobId: initialJobId,
}: InvoiceBuilderPageProps) {
  return (
    <RoleGate permission="invoices.create">
      <InvoiceBuilderPageContent initialJobId={initialJobId ?? null} />
    </RoleGate>
  );
}

function InvoiceBuilderPageContent({
  initialJobId,
}: {
  initialJobId: string | null;
}) {
  const router = useRouter();

  // ── Page state ────────────────────────────────────────────────────────────
  const [activeJobId, setActiveJobId] = useState<string | null>(initialJobId);
  const [customerId, setCustomerId] = useState<string>("");
  const [siteId, setSiteId] = useState<string>("");
  const [billingMode, setBillingMode] = useState<"line_item" | "progress">(
    "line_item",
  );
  const [progressPct, setProgressPct] = useState<string>("");
  const [selectedItemIds, setSelectedItemIds] = useState<Set<string>>(
    new Set(),
  );
  const [customLines, setCustomLines] = useState<CustomLineItem[]>([]);
  const [paymentTerms, setPaymentTerms] = useState<string>("due_on_receipt");
  const [customDueDate, setCustomDueDate] = useState<string>("");
  const [customerNotes, setCustomerNotes] = useState<string>("");
  const [internalMemo, setInternalMemo] = useState<string>("");
  const [pendingAction, setPendingAction] = useState<"draft" | "send">("draft");
  const [taxSetupOpen, setTaxSetupOpen] = useState(false);
  const [taxSetupDetail, setTaxSetupDetail] = useState<string>("");
  const [createdInvoiceId, setCreatedInvoiceId] = useState<string | null>(null);
  const [createdInvoiceNumber, setCreatedInvoiceNumber] = useState<string>("");
  const [sendModalOpen, setSendModalOpen] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Custom line item form state
  const [customLineDesc, setCustomLineDesc] = useState<string>("");
  const [customLineAmount, setCustomLineAmount] = useState<string>("");
  const [showCustomLineForm, setShowCustomLineForm] = useState(false);

  // ── Data fetching ─────────────────────────────────────────────────────────
  const { data: job, isLoading: jobLoading } = useJob(activeJobId ?? "");

  const {
    data: billableItems,
    isLoading: billableLoading,
    isError: billableError,
    refetch: refetchBillable,
  } = useBillableItems(activeJobId);

  // Pre-fill customer + site from job
  useEffect(() => {
    if (job && activeJobId) {
      setCustomerId(job.customer_id ?? "");
      setSiteId(job.site_id ?? "");
    }
  }, [job, activeJobId]);

  // Pre-select all billable items when they load
  useEffect(() => {
    if (billableItems) {
      const allIds = new Set<string>([
        ...billableItems.time_entries.map((te) => te.id),
        ...billableItems.expenses.map((exp) => exp.id),
      ]);
      setSelectedItemIds(allIds);
    }
  }, [billableItems]);

  // ── Computed values ───────────────────────────────────────────────────────
  const dueDateDisplay =
    paymentTerms !== "custom_date" ? computeDueDate(paymentTerms) : null;

  const totalSelectedCents = (() => {
    let total = 0;
    if (billableItems) {
      for (const te of billableItems.time_entries) {
        if (selectedItemIds.has(te.id)) total += te.total_cost_cents;
      }
      for (const exp of billableItems.expenses) {
        if (selectedItemIds.has(exp.id)) total += exp.billable_cents;
      }
    }
    for (const cl of customLines) {
      total += cl.unitPriceCents;
    }
    return total;
  })();

  const progressAmountCents =
    billingMode === "progress" && progressPct
      ? Math.round(totalSelectedCents * (parseFloat(progressPct) / 100))
      : 0;

  // ── Mutation ──────────────────────────────────────────────────────────────
  const { mutate: createInvoice, isPending: isSaving } = useCreateInvoice({
    onTaxSetupRequired: (detail) => {
      setTaxSetupDetail(detail);
      setTaxSetupOpen(true);
    },
    onSuccess: (invoice) => {
      if (pendingAction === "send") {
        setCreatedInvoiceId(invoice.id);
        setCreatedInvoiceNumber(invoice.invoice_number ?? "");
        setSendModalOpen(true);
      } else {
        router.push(`/invoices/${invoice.id}`);
      }
    },
  });

  // ── Validation ────────────────────────────────────────────────────────────
  function validate(): string | null {
    if (!customerId) return "Please select a customer.";
    if (!siteId) return "Please select a site.";
    if (billingMode === "progress") {
      const pct = parseFloat(progressPct);
      if (isNaN(pct) || pct <= 0 || pct > 100) {
        return "Progress billing % must be a number between 1 and 100.";
      }
    }
    if (paymentTerms === "custom_date" && !customDueDate) {
      return "Please select a custom due date.";
    }
    return null;
  }

  // ── Save handler ──────────────────────────────────────────────────────────
  function handleSave(action: "draft" | "send") {
    const error = validate();
    if (error) {
      setSaveError(error);
      return;
    }
    setSaveError(null);
    setPendingAction(action);
    createInvoice({
      customer_id: customerId || null,
      site_id: siteId || null,
      job_id: activeJobId ?? null,
      payment_terms: paymentTerms,
      billing_mode: billingMode,
      progress_pct: billingMode === "progress" ? parseFloat(progressPct) : null,
      internal_memo: internalMemo || null,
      customer_notes: customerNotes || null,
      issued_at: new Date().toISOString(),
      due_at: paymentTerms === "custom_date" ? customDueDate : null,
      idempotency_key: `inv-create-${customerId}-${Date.now()}`,
      // PLP-FIX-2 / FE-B29-1: persist custom ad-hoc lines (backend defaults qco_line_type to 'misc' by code)
      line_items: customLines.length
        ? customLines.map((cl) => ({
            description: cl.description,
            quantity: 1,
            unit_price_cents: cl.unitPriceCents,
          }))
        : null,
    });
  }

  // ── Toggle item checkbox ──────────────────────────────────────────────────
  function toggleItem(id: string) {
    setSelectedItemIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  // ── Add custom line item ──────────────────────────────────────────────────
  function handleAddCustomLine() {
    if (!customLineDesc.trim()) return;
    const amountCents = Math.round(parseFloat(customLineAmount) * 100);
    if (isNaN(amountCents)) return;
    setCustomLines((prev) => [
      ...prev,
      {
        localId: `cl-${Date.now()}`,
        description: customLineDesc.trim(),
        unitPriceCents: amountCents,
      },
    ]);
    setCustomLineDesc("");
    setCustomLineAmount("");
    setShowCustomLineForm(false);
  }

  // ── Clear linked job ──────────────────────────────────────────────────────
  // PLP-FIX-5 (Issue 13b): "Clear job" resets to standalone — customer/site
  // stay as the prefill set them (do NOT reset them). Only clears the job
  // link + selected billable items.
  function handleClearJob() {
    setActiveJobId(null);
    setSelectedItemIds(new Set());
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-4xl mx-auto p-6 pb-24">
      {/* Breadcrumb + Top Action Row */}
      <div className="flex items-center justify-between mb-4">
        <nav className="text-sm text-neutral-500">
          <Link href="/invoices" className="hover:text-brand-600">
            Invoices
          </Link>
          {" / "}
          <span className="text-neutral-900 font-medium">New Invoice</span>
        </nav>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => router.back()}
            className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => handleSave("draft")}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-brand-700 border border-brand-200 bg-brand-50 rounded-md hover:bg-brand-100 transition-colors disabled:opacity-50"
          >
            {isSaving && pendingAction === "draft"
              ? "Saving…"
              : "Save as Draft"}
          </button>
          <button
            type="button"
            onClick={() => handleSave("send")}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
          >
            {isSaving && pendingAction === "send"
              ? "Saving…"
              : "Send Invoice →"}
          </button>
        </div>
      </div>

      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">
        New Invoice
      </h1>

      {/* Section 1: Header Panel */}
      <section className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 space-y-4 mb-4">
        <h2 className="text-base font-semibold text-neutral-800 mb-3">
          Customer &amp; Site
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Customer <span className="text-fault-600">*</span>
            </label>
            <CustomerCombobox
              value={customerId}
              onChange={(id) => {
                setCustomerId(id);
                setSiteId(""); // reset site when customer changes
              }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Site <span className="text-fault-600">*</span>
            </label>
            <SiteCombobox
              customerId={customerId || null}
              value={siteId}
              onChange={setSiteId}
              disabled={!customerId}
            />
          </div>
        </div>

        {/* PLP-FIX-5 (Issue 13b): Job-link selector — visible when a customer is
            set AND no job is linked. Lets the user pick a job to pre-fill billable
            items without relying on the ?job_id= URL param. */}
        {customerId && !activeJobId && (
          <div data-testid="invoice-job-link-selector">
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Link a job to pre-fill billable items{" "}
              <span className="text-neutral-400 font-normal">(optional)</span>
            </label>
            <JobCombobox
              customerId={customerId}
              value={null}
              onChange={(jobId) => {
                if (jobId) setActiveJobId(jobId);
              }}
            />
          </div>
        )}

        {/* Linked Job chip — PLP-FIX-5 (Issue 13b): chip summary + "Clear job"
            (no confirm dialog; customer/site stay as the prefill set them). */}
        {activeJobId && (
          <div>
            <span
              data-testid="invoice-source-job-badge"
              className="inline-flex items-center gap-1.5 bg-alert-50 border border-alert-200 text-alert-700 text-caption font-medium rounded-full px-2.5 py-1 mt-3"
            >
              {jobLoading ? (
                "Loading job…"
              ) : (
                <Link
                  href={`/jobs/${activeJobId}`}
                  className="hover:underline"
                  data-testid="invoice-source-job-link"
                >
                  {`${job?.job_number ?? ""} · ${job?.title ?? job?.status_code ?? activeJobId.slice(0, 8)}`}
                </Link>
              )}
              <button
                type="button"
                onClick={handleClearJob}
                className="hover:text-alert-900 leading-none"
                aria-label="Clear job"
              >
                ×
              </button>
            </span>
          </div>
        )}
      </section>

      {/* Section 2: Billing Mode Toggle */}
      <section className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4">
        <h2 className="text-base font-semibold text-neutral-800 mb-3">
          Billing Mode
        </h2>
        <div className="bg-neutral-100 rounded-md p-1 inline-flex">
          <button
            type="button"
            onClick={() => setBillingMode("line_item")}
            className={
              billingMode === "line_item"
                ? "bg-white shadow-sm rounded px-3 py-1 text-sm font-medium text-neutral-900"
                : "px-3 py-1 text-sm font-medium text-neutral-500 hover:text-neutral-700"
            }
          >
            Select line items
          </button>
          <button
            type="button"
            onClick={() => setBillingMode("progress")}
            className={
              billingMode === "progress"
                ? "bg-white shadow-sm rounded px-3 py-1 text-sm font-medium text-neutral-900"
                : "px-3 py-1 text-sm font-medium text-neutral-500 hover:text-neutral-700"
            }
          >
            Progress billing (%)
          </button>
        </div>
      </section>

      {/* Section 3: Line Items Panel */}
      <section className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4">
        <h2 className="text-base font-semibold text-neutral-800 mb-3">
          Line Items
        </h2>

        {billingMode === "line_item" ? (
          <>
            {!activeJobId && (
              <p className="text-neutral-500 text-sm text-center py-8">
                Link a job above to pre-fill billable items, or add custom line
                items manually
              </p>
            )}

            {activeJobId && billableLoading && (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="animate-pulse bg-neutral-100 rounded h-8"
                  />
                ))}
              </div>
            )}

            {activeJobId && billableError && (
              <ErrorState
                type="server"
                title="Could not load billable items"
                description="Check your connection and try again."
                onRetry={() => void refetchBillable()}
              />
            )}

            {activeJobId &&
              !billableLoading &&
              !billableError &&
              billableItems && (
                <div>
                  {/* Time Entries */}
                  {billableItems.time_entries.map((te) => {
                    const checked = selectedItemIds.has(te.id);
                    return (
                      <div
                        key={te.id}
                        className="flex items-center gap-3 py-2 border-b border-neutral-100"
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleItem(te.id)}
                          className="w-4 h-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
                          aria-label={`Include ${te.tech_name ?? "technician"} time entry`}
                        />
                        <span
                          className={
                            checked
                              ? "text-sm text-neutral-800 flex-1"
                              : "text-sm text-neutral-400 line-through flex-1"
                          }
                        >
                          {te.tech_name ? `Labor: ${te.tech_name}` : "Labor"} —{" "}
                          {te.hours ?? "?"}h{te.notes ? ` (${te.notes})` : ""}
                        </span>
                        <span
                          className={
                            checked
                              ? "text-sm font-medium text-neutral-900 ml-auto"
                              : "text-sm text-neutral-400 ml-auto"
                          }
                        >
                          {formatCents(te.total_cost_cents)}
                        </span>
                      </div>
                    );
                  })}

                  {/* Expenses */}
                  {billableItems.expenses.map((exp) => {
                    const checked = selectedItemIds.has(exp.id);
                    return (
                      <div
                        key={exp.id}
                        className="flex items-center gap-3 py-2 border-b border-neutral-100"
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleItem(exp.id)}
                          className="w-4 h-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
                          aria-label={`Include ${exp.description}`}
                        />
                        <span
                          className={
                            checked
                              ? "text-sm text-neutral-800 flex-1"
                              : "text-sm text-neutral-400 line-through flex-1"
                          }
                        >
                          {exp.description}
                        </span>
                        <span
                          className={
                            checked
                              ? "text-sm font-medium text-neutral-900 ml-auto"
                              : "text-sm text-neutral-400 ml-auto"
                          }
                        >
                          {formatCents(exp.billable_cents)}
                        </span>
                      </div>
                    );
                  })}

                  {/* Custom lines added by user */}
                  {customLines.map((cl) => (
                    <div
                      key={cl.localId}
                      className="flex items-center gap-3 py-2 border-b border-neutral-100"
                    >
                      <input
                        type="checkbox"
                        checked
                        readOnly
                        className="w-4 h-4 rounded border-neutral-300 text-brand-600"
                      />
                      <span className="text-sm text-neutral-800 flex-1">
                        {cl.description}
                      </span>
                      <span className="text-sm font-medium text-neutral-900 ml-auto">
                        {formatCents(cl.unitPriceCents)}
                      </span>
                    </div>
                  ))}
                </div>
              )}

            {/* PLP-FIX-9 (INV-BUG-11): Custom lines render OUTSIDE the
                job-conditional block so they appear immediately on add,
                even when no job is linked. Previously they only rendered
                inside the activeJobId && billableItems block. */}
            {!activeJobId && customLines.length > 0 && (
              <div>
                {customLines.map((cl) => (
                  <div
                    key={cl.localId}
                    className="flex items-center gap-3 py-2 border-b border-neutral-100"
                  >
                    <input
                      type="checkbox"
                      checked
                      readOnly
                      className="w-4 h-4 rounded border-neutral-300 text-brand-600"
                    />
                    <span className="text-sm text-neutral-800 flex-1">
                      {cl.description}
                    </span>
                    <span className="text-sm font-medium text-neutral-900 ml-auto">
                      {formatCents(cl.unitPriceCents)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* + Add custom line item — PLP-FIX-2 / FE-B29-1: custom lines persist via line_items[] */}
            {showCustomLineForm ? (
              <div className="flex items-center gap-2 pt-3">
                <input
                  type="text"
                  value={customLineDesc}
                  onChange={(e) => setCustomLineDesc(e.target.value)}
                  placeholder="Description"
                  className="flex-1 border border-neutral-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-brand-400"
                />
                <input
                  type="number"
                  value={customLineAmount}
                  onChange={(e) => setCustomLineAmount(e.target.value)}
                  placeholder="Amount ($)"
                  className="w-28 border border-neutral-200 rounded px-2 py-1 text-sm focus:outline-none focus:border-brand-400"
                />
                <button
                  type="button"
                  onClick={handleAddCustomLine}
                  className="bg-brand-600 text-white text-sm px-3 py-1.5 rounded-md hover:bg-brand-700"
                >
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => setShowCustomLineForm(false)}
                  className="text-sm text-neutral-500 hover:text-neutral-700"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowCustomLineForm(true)}
                className="mt-3 text-sm text-brand-600 hover:text-brand-700 font-medium"
              >
                + Add custom line item
              </button>
            )}
          </>
        ) : (
          /* Progress billing mode */
          <div className="flex flex-col items-center py-6">
            <div className="flex items-baseline gap-1">
              <input
                type="number"
                min={0}
                max={100}
                value={progressPct}
                onChange={(e) => setProgressPct(e.target.value)}
                placeholder="0"
                className="text-3xl font-semibold text-neutral-900 w-24 text-center border-b-2 border-brand-500 focus:outline-none bg-transparent"
                aria-label="Progress billing percentage"
              />
              <span className="text-3xl font-semibold text-neutral-500">%</span>
            </div>
            {progressPct && !isNaN(parseFloat(progressPct)) && (
              <p className="text-neutral-500 text-sm mt-1">
                = {formatCents(progressAmountCents)}
              </p>
            )}
          </div>
        )}
      </section>

      {/* Section 4: Payment Terms Panel */}
      <section className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4">
        <h2 className="text-base font-semibold text-neutral-800 mb-3">
          Payment Terms
        </h2>
        <div className="flex items-center flex-wrap gap-2">
          <select
            value={paymentTerms}
            onChange={(e) => setPaymentTerms(e.target.value)}
            className="border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400"
          >
            <option value="due_on_receipt">Due on Receipt</option>
            <option value="net_15">Net 15</option>
            <option value="net_30">Net 30</option>
            <option value="custom_date">Custom Date</option>
          </select>
          {dueDateDisplay && (
            <span className="text-sm text-neutral-500 ml-3">
              Due: {dueDateDisplay}
            </span>
          )}
        </div>
        {paymentTerms === "custom_date" && (
          <input
            type="date"
            value={customDueDate}
            onChange={(e) => setCustomDueDate(e.target.value)}
            className="mt-2 border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400 w-44"
          />
        )}
      </section>

      {/* Section 5: Notes Panel */}
      <section className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4">
        <h2 className="text-base font-semibold text-neutral-800 mb-3">Notes</h2>
        <div>
          <p className="text-xs text-neutral-400 mt-0.5 mb-1">
            (shown on invoice PDF)
          </p>
          <textarea
            value={customerNotes}
            onChange={(e) => setCustomerNotes(e.target.value)}
            placeholder="Add a note for the customer (shown on invoice PDF)…"
            className="w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 resize-y min-h-[80px] focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder:text-neutral-400"
          />
        </div>
        <div className="border-t border-neutral-100 my-4" />
        <div>
          <p className="text-xs text-neutral-400 mt-0.5 mb-1">
            (not shown on PDF)
          </p>
          <textarea
            value={internalMemo}
            onChange={(e) => setInternalMemo(e.target.value)}
            placeholder="Add internal memo (not visible to customer)…"
            className="w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 resize-y min-h-[80px] focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder:text-neutral-400"
          />
        </div>
      </section>

      {/* Save error */}
      {saveError && (
        <div className="text-sm text-alert-700 bg-alert-50 border border-alert-200 rounded px-3 py-2 mb-4">
          {saveError}
        </div>
      )}

      {/* Action Footer */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-neutral-200 px-6 py-4 flex items-center justify-end gap-3 z-40">
        <button
          type="button"
          disabled
          title="Invoice preview coming soon"
          className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Preview Invoice
        </button>
        <button
          type="button"
          onClick={() => handleSave("draft")}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium text-brand-700 border border-brand-200 bg-brand-50 rounded-md hover:bg-brand-100 transition-colors disabled:opacity-50"
        >
          {isSaving && pendingAction === "draft" ? "Saving…" : "Save as Draft"}
        </button>
        <button
          type="button"
          onClick={() => handleSave("send")}
          disabled={isSaving}
          className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
        >
          {isSaving && pendingAction === "send" ? "Saving…" : "Send Invoice →"}
        </button>
      </div>

      {/* Tax Setup Sub-Flow Modal — intercepts 412 */}
      <TaxSetupSubFlowModal
        open={taxSetupOpen}
        detail={taxSetupDetail}
        onClose={() => setTaxSetupOpen(false)}
      />

      {/* Send Invoice Preview Modal — always-preview-before-send (§16.8) */}
      {createdInvoiceId && sendModalOpen && (
        <SendInvoicePreviewModal
          open={sendModalOpen}
          invoiceId={createdInvoiceId}
          invoiceNumber={createdInvoiceNumber}
          customerEmail={null}
          onClose={() => setSendModalOpen(false)}
          onConfirm={() => {
            router.push(`/invoices/${createdInvoiceId}`);
          }}
          isConfirming={false}
        />
      )}
    </div>
  );
}
