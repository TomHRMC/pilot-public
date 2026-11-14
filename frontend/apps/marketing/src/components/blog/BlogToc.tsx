"use client";

import { useEffect, useState } from "react";

export interface TocHeading {
  id: string;
  text: string;
  level: 2 | 3;
}

interface TocListProps {
  headings: TocHeading[];
  activeId: string;
  onLinkClick?: () => void;
}

function TocList({ headings, activeId, onLinkClick }: TocListProps) {
  return (
    <nav aria-label="Table of contents">
      <p
        className="text-xs font-semibold uppercase tracking-wider mb-3"
        style={{ color: "var(--neutral-500)" }}
      >
        On this page
      </p>
      <ul className="flex flex-col gap-0.5 list-none p-0 m-0">
        {headings.map((h) => {
          const isActive = activeId === h.id;
          const paddingLeft =
            h.level === 3
              ? isActive
                ? "calc(1rem + var(--divider-thick))"
                : "1rem"
              : isActive
                ? "var(--divider-thick)"
                : "0";
          return (
            <li key={h.id}>
              <a
                href={`#${h.id}`}
                className="block py-1 text-sm no-underline transition-colors"
                style={{
                  paddingLeft,
                  color: isActive
                    ? "var(--brand-600)"
                    : h.level === 3
                      ? "var(--neutral-500)"
                      : "var(--neutral-700)",
                  fontWeight: isActive ? "600" : "400",
                  borderLeft: isActive
                    ? "var(--divider-thick) solid var(--brand-500)"
                    : "var(--divider-thick) solid transparent",
                }}
                onClick={onLinkClick}
              >
                {h.text}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

interface BlogTocProps {
  headings: TocHeading[];
}

export default function BlogToc({ headings }: BlogTocProps) {
  const [activeId, setActiveId] = useState<string>("");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: "0px 0px -70% 0px", threshold: 0 },
    );

    headings.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [headings]);

  if (headings.length === 0) return null;

  return (
    <>
      {/* Desktop sidebar TOC */}
      <div
        className="hidden lg:block rounded-xl p-5 sticky top-24"
        style={{
          background: "var(--neutral-50)",
          border: "var(--divider-thin) solid var(--neutral-200)",
        }}
      >
        <TocList headings={headings} activeId={activeId} />
      </div>

      {/* Mobile TOC toggle */}
      <div className="lg:hidden mb-6">
        <button
          className="w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold"
          style={{
            background: "var(--neutral-50)",
            border: "var(--divider-thin) solid var(--neutral-200)",
            color: "var(--neutral-700)",
          }}
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-expanded={mobileOpen}
          aria-controls="mobile-toc"
        >
          <span>Table of Contents</span>
          <svg
            width="18"
            height="18"
            viewBox="0 0 20 20"
            fill="none"
            aria-hidden="true"
            style={{
              transition: "transform 0.2s",
              transform: mobileOpen ? "rotate(180deg)" : "rotate(0deg)",
            }}
          >
            <path
              d="M5 8l5 5 5-5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
        {mobileOpen && (
          <div
            id="mobile-toc"
            className="mt-2 rounded-xl p-5"
            style={{
              background: "var(--neutral-50)",
              border: "var(--divider-thin) solid var(--neutral-200)",
            }}
          >
            <TocList
              headings={headings}
              activeId={activeId}
              onLinkClick={() => setMobileOpen(false)}
            />
          </div>
        )}
      </div>
    </>
  );
}
