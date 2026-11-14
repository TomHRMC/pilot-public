/**
 * JobChangeOrdersTab — change orders list + add/edit/delete
 *
 * Location: apps/web/src/features/jobs/components/JobChangeOrdersTab.tsx
 *
 * Add/Edit/Delete gated to jobs.edit (owner, office_staff, operator).
 * Change order MVP: description only — totals are computed from lines (future).
 */

"use client";

import React, { useState } from "react";
import { EmptyState, RoleGate } from "@pilot/ui";
import { useJobChangeOrders } from "../hooks/useJobChangeOrders";
import { useCreateChangeOrder } from "../hooks/useCreateChangeOrder";
import { useUpdateChangeOrder } from "../hooks/useUpdateChangeOrder";
import { useDeleteChangeOrder } from "../hooks/useDeleteChangeOrder";
import type { ChangeOrderResponse } from "../hooks/useJobChangeOrders";

interface JobChangeOrdersTabProps {
  jobId: string;
}

function centsToDisplay(cents: number): string {
  return `$${(cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

interface ChangeOrderFormProps {
  initialDescription?: string;
  onSubmit: (description: string) => void;
  onCancel: () => void;
  isPending: boolean;
  submitLabel: string;
}

function ChangeOrderForm({
  initialDescription = "",
  onSubmit,
  onCancel,
  isPending,
  submitLabel,
}: ChangeOrderFormProps) {
  const [description, setDescription] = useState(initialDescription);
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) {
      setError("Description is required.");
      return;
    }
    setError(null);
    onSubmit(description.trim());
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="p-4 bg-neutral-50 rounded-lg border border-neutral-200 space-y-3"
    >
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div>
        <label className="block text-xs text-neutral-500 mb-1">
          Description *
        </label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          placeholder="Describe the change order scope"
          className="w-full px-2 py-1.5 border border-neutral-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          autoFocus
        />
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={isPending}
          className="px-3 py-1.5 bg-brand-600 text-white text-sm rounded hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? "Saving…" : submitLabel}
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

interface ChangeOrderRowProps {
  co: ChangeOrderResponse;
  jobId: string;
  onEdit: (co: ChangeOrderResponse) => void;
}

function ChangeOrderRow({ co, jobId, onEdit }: ChangeOrderRowProps) {
  const { mutate: deleteCo, isPending: isDeleting } =
    useDeleteChangeOrder(jobId);

  return (
    <tr className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50">
      <td className="px-3 py-2.5 text-sm text-neutral-900">{co.description}</td>
      <td className="px-3 py-2.5 text-sm text-neutral-900 font-medium">
        {co.total_cents > 0 ? centsToDisplay(co.total_cents) : "TBD"}
      </td>
      <td className="px-3 py-2.5">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
            co.is_active
              ? "bg-green-100 text-green-700"
              : "bg-neutral-100 text-neutral-500"
          }`}
        >
          {co.is_active ? "Active" : "Inactive"}
        </span>
      </td>
      <td className="px-3 py-2.5">
        <RoleGate permission="jobs.edit">
          <div className="flex gap-2">
            <button
              onClick={() => onEdit(co)}
              className="text-xs text-brand-600 hover:text-brand-800 font-medium"
            >
              Edit
            </button>
            <button
              onClick={() => deleteCo(co.id)}
              disabled={isDeleting}
              className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
            >
              {isDeleting ? "…" : "Delete"}
            </button>
          </div>
        </RoleGate>
      </td>
    </tr>
  );
}

export function JobChangeOrdersTab({ jobId }: JobChangeOrdersTabProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingCo, setEditingCo] = useState<ChangeOrderResponse | null>(null);

  const { data: changeOrders = [], isLoading } = useJobChangeOrders(jobId);
  const { mutate: createCo, isPending: isCreating } =
    useCreateChangeOrder(jobId);
  const { mutate: updateCo, isPending: isUpdating } =
    useUpdateChangeOrder(jobId);

  if (isLoading) {
    return (
      <div className="py-6 text-center text-sm text-neutral-500">
        Loading change orders…
      </div>
    );
  }

  function handleCreate(description: string) {
    createCo({ description }, { onSuccess: () => setShowAddForm(false) });
  }

  function handleUpdate(description: string) {
    if (!editingCo) return;
    updateCo(
      { coId: editingCo.id, input: { description } },
      { onSuccess: () => setEditingCo(null) },
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-neutral-700">
          Change Orders ({changeOrders.length})
        </h3>
        <RoleGate permission="jobs.edit">
          <button
            onClick={() => {
              setShowAddForm((v) => !v);
              setEditingCo(null);
            }}
            className="text-sm text-brand-600 hover:text-brand-800 font-medium"
          >
            + Add Change Order
          </button>
        </RoleGate>
      </div>

      {showAddForm && !editingCo && (
        <div className="mb-3">
          <ChangeOrderForm
            onSubmit={handleCreate}
            onCancel={() => setShowAddForm(false)}
            isPending={isCreating}
            submitLabel="Add Change Order"
          />
        </div>
      )}

      {editingCo && (
        <div className="mb-3">
          <ChangeOrderForm
            initialDescription={editingCo.description}
            onSubmit={handleUpdate}
            onCancel={() => setEditingCo(null)}
            isPending={isUpdating}
            submitLabel="Save Changes"
          />
        </div>
      )}

      {changeOrders.length === 0 ? (
        <EmptyState
          type="no-data"
          title="No change orders yet"
          description="Add change orders to capture scope additions or changes approved by the customer."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Description
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Total
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Status
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-neutral-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {changeOrders.map((co) => (
                <ChangeOrderRow
                  key={co.id}
                  co={co}
                  jobId={jobId}
                  onEdit={(c) => {
                    setEditingCo(c);
                    setShowAddForm(false);
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
