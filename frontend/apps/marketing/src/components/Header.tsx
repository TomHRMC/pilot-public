"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import type { SiteMode } from "@/lib/useSiteMode";

/**
 * Resolves a logo src — tries the JPG variant first, falls back to SVG.
 * Pass the SVG path; this returns the JPG path (same stem, .jpg extension).
 * The <Image> onError callback swaps back to the SVG if the JPG 404s.
 */
function jpgFirst(svgPath: string): string {
  return svgPath.replace(/\.svg$/, ".jpg");
}

const tradeLinks = [
  { label: "Electrical", href: "/trades/electrical" },
  { label: "Plumbing", href: "/trades/plumbing" },
  { label: "HVAC", href: "/trades/hvac" },
];

interface HeaderProps {
  siteMode?: SiteMode;
}

export default function Header({ siteMode = "charter" }: HeaderProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [tradesOpen, setTradesOpen] = useState(false);
  const [mobileTradesOpen, setMobileTradesOpen] = useState(false);

  // Logos: attempt JPG first (better perf when available), fall back to SVG on 404
  const logoSvg = "/brand/logo-primary.svg";
  const [logoSrc, setLogoSrc] = useState(jpgFirst(logoSvg));

  const logoIconSvg = "/brand/logo-icon.svg";
  const [logoIconSrc, setLogoIconSrc] = useState(jpgFirst(logoIconSvg));

  const isGeneral = siteMode === "general";
  const ctaText = isGeneral ? "Start Free Trial" : "Be one of the first twelve";
  const ctaHref = isGeneral ? "/sign-up" : "/charter";

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 h-16 flex items-center"
      style={{
        background: "var(--white-95)",
        backdropFilter: "blur(8px)",
        borderBottom: "var(--divider-thin) solid var(--neutral-200)",
      }}
    >
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <div className="container-marketing w-full">
        <div className="flex items-center justify-between">
          {/* Logo — JPG if available, SVG fallback */}
          <Link
            href="/"
            className="flex items-center gap-2 no-underline"
            aria-label="Pilot for Trades — Home"
          >
            {/* Desktop: full lockup — try JPG, fall back to SVG on 404 */}
            <span className="hidden sm:inline-flex">
              <Image
                src={logoSrc}
                alt="Pilot for Trades"
                width={160}
                height={36}
                priority
                onError={() => setLogoSrc(logoSvg)}
              />
            </span>
            {/* Mobile: icon only — try JPG, fall back to SVG on 404 */}
            <span className="sm:hidden">
              <Image
                src={logoIconSrc}
                alt="Pilot for Trades"
                width={32}
                height={32}
                priority
                onError={() => setLogoIconSrc(logoIconSvg)}
              />
            </span>
          </Link>

          {/* Desktop nav */}
          <nav
            className="hidden lg:flex items-center gap-1"
            aria-label="Main navigation"
          >
            <Link
              href="/features"
              className="px-3 py-2 rounded-md text-sm font-medium transition-colors"
              style={{ color: "var(--neutral-700)" }}
            >
              Features
            </Link>

            {/* Trades dropdown */}
            <div className="relative">
              <button
                onClick={() => setTradesOpen(!tradesOpen)}
                onBlur={() => setTimeout(() => setTradesOpen(false), 150)}
                className="flex items-center gap-1 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                style={{ color: "var(--neutral-700)" }}
                aria-expanded={tradesOpen}
                aria-haspopup="true"
              >
                Trades
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  aria-hidden="true"
                  style={{
                    transform: tradesOpen ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.2s",
                  }}
                >
                  <path
                    d="M3 5l4 4 4-4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>

              {tradesOpen && (
                <div
                  className="absolute top-full left-0 mt-1 w-48 rounded-lg py-1"
                  style={{
                    background: "var(--white)",
                    border: "var(--divider-thin) solid var(--neutral-200)",
                    boxShadow: "var(--shadow-xl)",
                  }}
                >
                  {tradeLinks.map((t) => (
                    <Link
                      key={t.href}
                      href={t.href}
                      className="block px-4 py-2 text-sm transition-colors"
                      style={{ color: "var(--neutral-700)" }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background = "var(--neutral-50)")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "transparent")
                      }
                    >
                      {t.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>

            <Link
              href="/pricing"
              className="px-3 py-2 rounded-md text-sm font-medium transition-colors"
              style={{ color: "var(--neutral-700)" }}
            >
              Pricing
            </Link>
            <Link
              href="/about"
              className="px-3 py-2 rounded-md text-sm font-medium transition-colors"
              style={{ color: "var(--neutral-700)" }}
            >
              About
            </Link>

            <div className="ml-4">
              <Link href={ctaHref} className="btn-primary py-2 px-5 text-sm">
                {ctaText}
              </Link>
            </div>
          </nav>

          {/* Mobile hamburger */}
          <button
            className="lg:hidden flex flex-col justify-center items-center w-10 h-10 rounded-md"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            style={{ color: "var(--neutral-700)" }}
          >
            {mobileOpen ? (
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M4 4l12 12M16 4L4 16"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            ) : (
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M2 5h16M2 10h16M2 15h16"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden absolute top-16 left-0 right-0 shadow-xl"
          style={{
            background: "var(--white)",
            borderBottom: "var(--divider-thin) solid var(--neutral-200)",
          }}
        >
          <nav
            className="container-marketing py-4 flex flex-col gap-1"
            aria-label="Mobile navigation"
          >
            <Link
              href="/features"
              className="block px-4 py-3 rounded-md text-base font-medium"
              style={{ color: "var(--neutral-900)" }}
              onClick={() => setMobileOpen(false)}
            >
              Features
            </Link>

            {/* Mobile trades accordion */}
            <div>
              <button
                className="w-full flex items-center justify-between px-4 py-3 rounded-md text-base font-medium"
                style={{ color: "var(--neutral-900)" }}
                onClick={() => setMobileTradesOpen(!mobileTradesOpen)}
              >
                Trades
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  aria-hidden="true"
                  style={{
                    transform: mobileTradesOpen
                      ? "rotate(180deg)"
                      : "rotate(0deg)",
                    transition: "transform 0.2s",
                  }}
                >
                  <path
                    d="M4 6l4 4 4-4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              {mobileTradesOpen && (
                <div className="pl-4">
                  {tradeLinks.map((t) => (
                    <Link
                      key={t.href}
                      href={t.href}
                      className="block px-4 py-2 text-sm rounded-md"
                      style={{ color: "var(--neutral-600)" }}
                      onClick={() => setMobileOpen(false)}
                    >
                      {t.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>

            <Link
              href="/pricing"
              className="block px-4 py-3 rounded-md text-base font-medium"
              style={{ color: "var(--neutral-900)" }}
              onClick={() => setMobileOpen(false)}
            >
              Pricing
            </Link>
            <Link
              href="/about"
              className="block px-4 py-3 rounded-md text-base font-medium"
              style={{ color: "var(--neutral-900)" }}
              onClick={() => setMobileOpen(false)}
            >
              About
            </Link>

            <div className="px-4 pt-3 pb-4">
              <Link
                href={ctaHref}
                className="btn-primary w-full text-center"
                onClick={() => setMobileOpen(false)}
              >
                {ctaText}
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
