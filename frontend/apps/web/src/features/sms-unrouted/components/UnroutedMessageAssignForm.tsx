/**
 * UnroutedMessageAssignForm — Assign unrouted message to customer + tech
 *
 * Location: apps/web/src/features/sms-unrouted/components/UnroutedMessageAssignForm.tsx
 *
 * Contains:
 *   1. Message preview (body text, received timestamp, sender phone)
 *   2. Customer search (typeahead, GET /api/v1/customers?search=)
 *   3. Tech selector (dropdown of active techs for the tenant)
 *   4. "Create thread and assign" button
 *
 * On success: navigates back to unrouted queue.
 *
 * RULE 6: Caller (route page) must ensure RoleGate(integrations.manage).
 * Submit disabled until both customer + tech selected.
 *
 * Design doc Section A.2.3, Decision 6
 */

"use client";

import React, { useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAssignUnrouted } from "../hooks/useAssignUnrouted";
import type { UnroutedMessage } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";

interface Customer {
  id: string;
  name: string;
  phone: string;
}

interface Tech {
  id: string;
  name: string;
}

async function searchCustomers(query: string): Promise<Customer[]> {
  if (!query.trim()) return [];
  const res = await apiClient.get("/api/v1/customers", {
    params: { search: query, limit: 10 },
  });
  const data = res.data as { customers?: Customer[] };
  return data.customers ?? [];
}

async function fetchTechs(): Promise<Tech[]> {
  const res = await apiClient.get("/api/v1/users", {
    params: { role: "technician", active: true },
  });
  const data = res.data as { users?: Tech[] };
  return data.users ?? [];
}

interface UnroutedMessageAssignFormProps {
  message: UnroutedMessage;
  testID?: string;
}

export function UnroutedMessageAssignForm({
  message,
  testID,
}: UnroutedMessageAssignFormProps) {
  const router = useRouter();
  const { mutateAsync: assign, isPending: isAssigning } = useAssignUnrouted();

  const [customerSearch, setCustomerSearch] = useState("");
  const [customerResults, setCustomerResults] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(
    null,
  );
  const [techs, setTechs] = useState<Tech[]>([]);
  const [selectedTechId, setSelectedTechId] = useState("");
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  // Load techs when component mounts
  React.useEffect(() => {
    void fetchTechs().then(setTechs);
  }, []);

  const handleCustomerSearch = useCallback(async (query: string) => {
    setCustomerSearch(query);
    setSelectedCustomer(null);
    if (query.length < 2) {
      setCustomerResults([]);
      return;
    }
    setIsSearching(true);
    const results = await searchCustomers(query);
    setCustomerResults(results);
    setIsSearching(false);
  }, []);

  const handleSelectCustomer = useCallback((customer: Customer) => {
    setSelectedCustomer(customer);
    setCustomerSearch(customer.name);
    setCustomerResults([]);
  }, []);

  const canSubmit =
    selectedCustomer !== null && selectedTechId.length > 0 && !isAssigning;

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!canSubmit || !selectedCustomer) return;
      setError(null);

      try {
        const result = await assign({
          id: message.unrouted_id,
          request: {
            customer_id: selectedCustomer.id,
            tech_id: selectedTechId,
          },
        });

        setSuccessMessage(
          `Thread created · message assigned to ${result.tech_name}`,
        );
        // Navigate back after a short delay
        setTimeout(() => {
          router.push("/settings/integrations/sms/unrouted");
        }, 1500);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Assignment failed. Try again.",
        );
      }
    },
    [
      canSubmit,
      selectedCustomer,
      selectedTechId,
      assign,
      message.unrouted_id,
      router,
    ],
  );

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="max-w-lg space-y-6"
      data-testid={testID ?? "unrouted-assign-form"}
    >
      {/* Message preview */}
      <div className="border border-neutral-200 rounded-lg p-4 bg-neutral-50">
        <p className="text-caption text-neutral-600 mb-1">
          From {message.from_number} ·{" "}
          {new Date(message.received_at).toLocaleString()}
        </p>
        <p className="text-body text-neutral-900">{message.body}</p>
      </div>

      {/* Customer search */}
      <div className="space-y-2">
        <label
          className="text-body font-medium text-neutral-900"
          htmlFor="customer-search"
        >
          Assign to customer
        </label>
        <div className="relative">
          <input
            id="customer-search"
            type="text"
            value={customerSearch}
            onChange={(e) => void handleCustomerSearch(e.target.value)}
            placeholder="Search by name or phone…"
            className="w-full px-3 py-2 border border-neutral-200 rounded-md text-body text-neutral-900 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:border-transparent"
            data-testid="customer-search-input"
            autoComplete="off"
          />
          {isSearching && (
            <div className="absolute right-3 top-2.5">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-600" />
            </div>
          )}
          {customerResults.length > 0 && (
            <ul
              className="absolute z-10 w-full mt-1 border border-neutral-200 rounded-md bg-white shadow-lg max-h-48 overflow-y-auto"
              data-testid="customer-results-dropdown"
            >
              {customerResults.map((customer) => (
                <li key={customer.id}>
                  <button
                    type="button"
                    className="w-full px-3 py-2 text-left text-body text-neutral-900 hover:bg-neutral-50"
                    onClick={() => handleSelectCustomer(customer)}
                    data-testid={`customer-option-${customer.id}`}
                  >
                    <span className="font-medium">{customer.name}</span>
                    <span className="text-neutral-500 ml-2 text-caption">
                      {customer.phone}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        {selectedCustomer && (
          <p
            className="text-caption text-margin-600"
            data-testid="selected-customer"
          >
            ✓ {selectedCustomer.name}
          </p>
        )}
      </div>

      {/* Tech selector */}
      <div className="space-y-2">
        <label
          className="text-body font-medium text-neutral-900"
          htmlFor="tech-select"
        >
          Assign to tech
        </label>
        <select
          id="tech-select"
          value={selectedTechId}
          onChange={(e) => setSelectedTechId(e.target.value)}
          className="w-full px-3 py-2 border border-neutral-200 rounded-md text-body text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600"
          data-testid="tech-select"
        >
          <option value="">Select a tech…</option>
          {techs.map((tech) => (
            <option key={tech.id} value={tech.id}>
              {tech.name}
            </option>
          ))}
        </select>
      </div>

      {/* Error message */}
      {error && (
        <div
          className="px-4 py-3 bg-fault-50 border border-fault-200 rounded-md text-body text-fault-800"
          data-testid="assign-error"
        >
          {error}
        </div>
      )}

      {/* Success message */}
      {successMessage && (
        <div
          className="px-4 py-3 bg-margin-50 border border-margin-200 rounded-md text-body text-margin-800"
          data-testid="assign-success"
        >
          {successMessage}
        </div>
      )}

      {/* Submit button — disabled until both customer + tech selected */}
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={!canSubmit}
          className="px-4 py-2 bg-brand-600 text-white rounded-md text-body font-medium hover:bg-brand-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          data-testid="assign-submit-btn"
        >
          {isAssigning ? "Creating thread…" : "Create thread and assign"}
        </button>
        <Link
          href="/settings/integrations/sms/unrouted"
          className="text-body text-neutral-600 hover:text-neutral-900"
        >
          Cancel
        </Link>
      </div>
    </form>
  );
}
