/**
 * SettingsSidebarSearch — FE-B11
 *
 * Location: packages/ui/src/setting-control/SettingsSidebarSearch.tsx
 *
 * Search input + type-ahead results dropdown for the web settings sidebar.
 * Client-side filtering over CatalogEntry[]. Uses synonym dictionary for
 * alternate-term matching (Decision 7).
 *
 * Shows: setting name, current value, path breadcrumb.
 * Navigation on click: uses provided onNavigate callback.
 *
 * Mobile: not rendered (per IA framework Decision 7 — mobile tree < 15 leaves).
 */

"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import type { CatalogEntry } from "./types";
import { getSynonymMatches } from "./synonyms";

export interface SettingsSidebarSearchProps {
  catalog: CatalogEntry[];
  onNavigate: (entry: CatalogEntry) => void;
  testID?: string;
}

function formatPath(subSurfacePath: string): string {
  // e.g. '/settings/operations/margin-buckets' → 'Operations > Margin buckets'
  const parts = subSurfacePath.replace(/^\/settings\//, "").split("/");
  return parts
    .map((p) => p.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()))
    .join(" > ");
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "On" : "Off";
  if (Array.isArray(value)) return `[${(value as unknown[]).join(", ")}]`;
  return String(value);
}

export function SettingsSidebarSearch({
  catalog,
  onNavigate,
  testID,
}: SettingsSidebarSearchProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const results: CatalogEntry[] =
    query.trim().length < 1
      ? []
      : (() => {
          const lower = query.toLowerCase().trim();
          const synonymKeys = new Set(getSynonymMatches(lower));

          const matched = catalog.filter((entry) => {
            const labelMatch = entry.label.toLowerCase().includes(lower);
            const descMatch = entry.description.toLowerCase().includes(lower);
            const synonymMatch = synonymKeys.has(entry.key);
            return labelMatch || descMatch || synonymMatch;
          });

          return matched;
        })();

  const handleSelect = useCallback(
    (entry: CatalogEntry) => {
      setQuery("");
      setIsOpen(false);
      onNavigate(entry);
    },
    [onNavigate],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setIsOpen(false);
      setQuery("");
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative"
      data-testid={testID ?? "settings-sidebar-search"}
    >
      <div className="relative">
        {/* Search icon */}
        <span
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
          aria-hidden="true"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </span>

        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(e.target.value.trim().length > 0);
          }}
          onFocus={() => {
            if (query.trim().length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search settings…"
          aria-label="Search settings"
          aria-expanded={isOpen && results.length > 0}
          aria-haspopup="listbox"
          className="w-full rounded-md border border-neutral-200 bg-white py-2 pl-9 pr-3 text-caption text-neutral-900 placeholder:text-neutral-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
          data-testid={testID ? `${testID}-input` : "settings-search-input"}
        />
      </div>

      {/* Dropdown results */}
      {isOpen && results.length > 0 && (
        <div
          role="listbox"
          aria-label="Settings search results"
          className="absolute left-0 right-0 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-md border border-neutral-200 bg-white py-1 shadow-md"
          data-testid={
            testID ? `${testID}-dropdown` : "settings-search-dropdown"
          }
        >
          {results.map((entry) => (
            <button
              key={entry.key}
              role="option"
              type="button"
              onClick={() => handleSelect(entry)}
              className="flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left hover:bg-neutral-50 focus:bg-neutral-50 focus:outline-none"
              data-testid={
                testID
                  ? `${testID}-result-${entry.key}`
                  : `settings-search-result-${entry.key}`
              }
            >
              <span className="text-caption font-medium text-neutral-900">
                {entry.label}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-caption text-neutral-500">
                  {formatPath(entry.subSurfacePath)}
                </span>
                <span className="text-caption text-neutral-400">·</span>
                <span className="text-caption text-neutral-600">
                  {formatValue(entry.currentEffectiveValue)}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* No results */}
      {isOpen && query.trim().length > 0 && results.length === 0 && (
        <div
          className="absolute left-0 right-0 top-full z-50 mt-1 rounded-md border border-neutral-200 bg-white px-3 py-2 shadow-md"
          data-testid={
            testID ? `${testID}-no-results` : "settings-search-no-results"
          }
        >
          <p className="text-caption text-neutral-500">No settings found.</p>
        </div>
      )}
    </div>
  );
}
