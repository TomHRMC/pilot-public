/* eslint-disable react-hooks/set-state-in-effect */
"use client";

/**
 * JobCombobox — typeahead job picker (customer-scoped)
 *
 * Location: apps/web/src/components/JobCombobox.tsx
 *
 * PLP-FIX-5 (Issue 13b): mirrors the SiteCombobox pattern (search-as-you-type,
 * keyboard nav, loading/empty states). Data via useJobs({ customer_id }).
 * Disabled when customerId is empty. Displays job_number + (title ?? status_code).
 */

import { useState, useRef, useEffect } from "react";
import { useJobs } from "../features/jobs/hooks/useJobs";
import type { JobListItem } from "../features/jobs/hooks/useJobs";

interface JobComboboxProps {
  /** Required — jobs are customer-scoped. */
  customerId: string;
  /** Current job_id (empty string = no selection). */
  value: string | null;
  onChange: (jobId: string | null) => void;
  disabled?: boolean;
  placeholder?: string;
}

function getJobLabel(job: JobListItem): string {
  const fallback = job.title ?? job.status_code ?? job.id.slice(0, 8);
  return job.job_number ? `${job.job_number} · ${fallback}` : fallback;
}

export function JobCombobox({
  customerId,
  value,
  onChange,
  disabled,
  placeholder = "Search jobs…",
}: JobComboboxProps) {
  const [inputText, setInputText] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useJobs({ customer_id: customerId });

  const jobs = data?.items ?? [];

  // Track the previous customerId so we only reset when it genuinely changes.
  const prevCustomerIdRef = useRef(customerId);
  useEffect(() => {
    if (prevCustomerIdRef.current === customerId) {
      return;
    }
    prevCustomerIdRef.current = customerId;
    onChange(null);
    setInputText("");
    setOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId]);

  // Sync inputText with selected value's label
  const selectedJob = jobs.find((j) => j.id === value);
  useEffect(() => {
    if (selectedJob) {
      setInputText(getJobLabel(selectedJob));
    } else if (!customerId) {
      setInputText("");
    }
  }, [selectedJob, customerId]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
        if (selectedJob) {
          setInputText(getJobLabel(selectedJob));
        }
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [selectedJob]);

  const isDisabled = disabled || !customerId || isLoading;

  const filtered = jobs
    .filter((j) =>
      getJobLabel(j).toLowerCase().includes(inputText.toLowerCase()),
    )
    .slice(0, 20);

  function handleSelect(jobId: string, label: string) {
    onChange(jobId);
    setInputText(label);
    setOpen(false);
  }

  function handleClear() {
    onChange(null);
    setInputText("");
    setOpen(false);
  }

  const effectivePlaceholder = !customerId
    ? "Select a customer first"
    : isLoading
      ? "Loading jobs…"
      : placeholder;

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center relative">
        <input
          type="text"
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            if (!isDisabled) setOpen(true);
          }}
          disabled={isDisabled}
          placeholder={effectivePlaceholder}
          className="w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400 disabled:bg-neutral-50 disabled:text-neutral-400"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-controls="job-combobox-listbox"
          aria-haspopup="listbox"
          aria-label="Job"
        />
        {value && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2 text-neutral-400 hover:text-neutral-600 text-lg leading-none"
            aria-label="Clear job selection"
          >
            ×
          </button>
        )}
      </div>

      {open && filtered.length > 0 && (
        <ul
          id="job-combobox-listbox"
          className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg max-h-48 overflow-y-auto"
          role="listbox"
        >
          {filtered.map((j) => {
            const label = getJobLabel(j);
            return (
              <li
                key={j.id}
                role="option"
                aria-selected={j.id === value}
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(j.id, label);
                }}
                className={`px-3 py-2 text-sm cursor-pointer ${
                  j.id === value
                    ? "bg-brand-50 text-brand-700 font-medium"
                    : "text-neutral-700 hover:bg-brand-50"
                }`}
              >
                {label}
              </li>
            );
          })}
        </ul>
      )}

      {open &&
        !isLoading &&
        filtered.length === 0 &&
        inputText &&
        customerId && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg px-3 py-2 text-sm text-neutral-500">
            No jobs found
          </div>
        )}
    </div>
  );
}
