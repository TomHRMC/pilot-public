/**
 * JobExpensesTab — expenses list + add form
 *
 * Location: apps/web/src/features/jobs/components/JobExpensesTab.tsx
 *
 * Category dropdown from expense category codes.
 * "+ Add Expense" gated to jobs.edit (owner, office_staff, operator).
 */

"use client";

import React, { useState } from "react";
import { EmptyState, RoleGate } from "@pilot/ui";
import { useJobExpenses } from "../hooks/useJobExpenses";
import { useAddExpense } from "../hooks/useAddExpense";

interface JobExpensesTabProps {
  jobId: string;
}

function centsToDisplay(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

// Common expense categories from the backend
const EXPENSE_CATEGORIES = [
  { code: "material", label: "Material" },
  { code: "tool", label: "Tool/Equipment" },
  { code: "labor_subcontract", label: "Subcontract Labor" },
  { code: "permit", label: "Permit" },
  { code: "travel", label: "Travel" },
  { code: "other", label: "Other" },
];

interface AddExpenseFormProps {
  jobId: string;
  onCancel: () => void;
}

function AddExpenseForm({ jobId, onCancel }: AddExpenseFormProps) {
  const [categoryCode, setCategoryCode] = useState("material");
  const [description, setDescription] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [incurredAt, setIncurredAt] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [costDollars, setCostDollars] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { mutate: addExpense, isPending } = useAddExpense(jobId);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cost = parseFloat(costDollars);
    if (!description.trim()) {
      setError("Description is required.");
      return;
    }
    if (isNaN(cost) || cost <= 0) {
      setError("Enter a valid cost amount.");
      return;
    }
    setError(null);
    addExpense(
      {
        job_expense_category_code: categoryCode,
        description: description.trim(),
        vendor_name: vendorName || null,
        incurred_at: incurredAt,
        cost_cents: Math.round(cost * 100),
        is_billable: true,
      },
      { onSuccess: onCancel },
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-3 p-4 bg-neutral-50 rounded-lg border border-neutral-200 space-y-3"
    >
      <h4 className="text-sm font-semibold text-neutral-700">Add Expense</h4>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-neutral-500 mb-1">
            Category *
          </label>
          <select
            value={categoryCode}
            onChange={(e) => setCategoryCode(e.target.value)}
            className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {EXPENSE_CATEGORIES.map((cat) => (
              <option key={cat.code} value={cat.code}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-neutral-500 mb-1">Date *</label>
          <input
            type="date"
            value={incurredAt}
            onChange={(e) => setIncurredAt(e.target.value)}
            required
            className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs text-neutral-500 mb-1">
          Description *
        </label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          placeholder="What was purchased?"
          className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-neutral-500 mb-1">
            Vendor (optional)
          </label>
          <input
            type="text"
            value={vendorName}
            onChange={(e) => setVendorName(e.target.value)}
            placeholder="Home Depot, etc."
            className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div>
          <label className="block text-xs text-neutral-500 mb-1">
            Cost ($) *
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={costDollars}
            onChange={(e) => setCostDollars(e.target.value)}
            required
            placeholder="0.00"
            className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={isPending}
          className="px-3 py-1.5 bg-brand-600 text-white text-sm rounded hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? "Saving…" : "Add Expense"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 bg-white border border-neutral-300 text-neutral-700 text-sm rounded hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export function JobExpensesTab({ jobId }: JobExpensesTabProps) {
  const [showForm, setShowForm] = useState(false);
  const { data: expenses = [], isLoading } = useJobExpenses(jobId);

  if (isLoading) {
    return (
      <div className="py-6 text-center text-sm text-neutral-500">
        Loading expenses…
      </div>
    );
  }

  const totalCost = expenses.reduce((sum, e) => sum + e.cost_cents, 0);
  const totalBillable = expenses.reduce((sum, e) => sum + e.billable_cents, 0);

  return (
    <div>
      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-neutral-700">
          Expenses ({expenses.length})
          {expenses.length > 0 && (
            <span className="ml-2 text-neutral-500 font-normal">
              · Cost: {centsToDisplay(totalCost)} · Billable:{" "}
              {centsToDisplay(totalBillable)}
            </span>
          )}
        </h3>
        <RoleGate permission="jobs.edit">
          <button
            onClick={() => setShowForm((v) => !v)}
            className="text-sm text-brand-600 hover:text-brand-800 font-medium"
          >
            + Add Expense
          </button>
        </RoleGate>
      </div>

      {showForm && (
        <AddExpenseForm jobId={jobId} onCancel={() => setShowForm(false)} />
      )}

      {expenses.length === 0 ? (
        <EmptyState
          type="no-data"
          title="No expenses yet"
          description="Add materials, permits, subcontractor costs, and other job expenses here."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Category
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Description
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Vendor
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Cost
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Billable
                </th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((expense) => (
                <tr
                  key={expense.id}
                  className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50"
                >
                  <td className="px-3 py-2.5">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-700">
                      {expense.job_expense_category_code}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-900">
                    {expense.description}
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-600">
                    {expense.vendor_name ?? "—"}
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-900 font-medium">
                    {centsToDisplay(expense.cost_cents)}
                  </td>
                  <td className="px-3 py-2.5 text-sm text-neutral-900">
                    {expense.is_billable
                      ? centsToDisplay(expense.billable_cents)
                      : "Not billable"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
