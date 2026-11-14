"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import NewsletterForm from "./forms/NewsletterForm";
import type { SiteMode } from "@/lib/useSiteMode";

interface FooterProps {
  siteMode?: SiteMode;
}

export default function Footer({ siteMode = "charter" }: FooterProps) {
  const isGeneral = siteMode === "general";

  // Dark logo: attempt JPG first, fall back to SVG on 404
  const logoDarkSvg = "/brand/logo-primary-dark.svg";
  const [logoDarkSrc, setLogoDarkSrc] = useState(
    logoDarkSvg.replace(/\.svg$/, ".jpg"),
  );

  const footerColumns = [
    {
      heading: "Product",
      links: [
        { label: "Features", href: "/features" },
        { label: "Pricing", href: "/pricing" },
        { label: "Trades", href: "/trades/electrical" },
        // Mode-aware: Charter → Charter, General Release → Start Free Trial
        isGeneral
          ? { label: "Start Free Trial", href: "/sign-up" }
          : { label: "Charter", href: "/charter" },
      ],
    },
    {
      heading: "Company",
      links: [
        { label: "About", href: "/about" },
        { label: "Contact", href: "/contact" },
        { label: "Careers", href: "/careers" },
      ],
    },
    {
      heading: "Resources",
      links: [
        { label: "Blog", href: "/blog" },
        { label: "Help Center", href: "/contact" },
      ],
    },
    {
      heading: "Legal",
      links: [
        { label: "Terms of Service", href: "/legal/terms" },
        { label: "Privacy Policy", href: "/legal/privacy" },
        { label: "EULA", href: "/legal/eula" },
        { label: "SMS Terms", href: "/legal/sms-terms" },
      ],
    },
  ];

  return (
    <footer
      style={{ background: "var(--neutral-900)", color: "var(--neutral-400)" }}
      aria-label="Site footer"
    >
      <div className="container-marketing section-padding">
        {/* Top row: logo + tagline | newsletter form */}
        <div
          className="flex flex-col lg:flex-row lg:items-start justify-between gap-10 pb-12"
          style={{
            borderBottom: "var(--divider-thin) solid var(--neutral-800)",
          }}
        >
          {/* Logo + tagline — use new brand assets */}
          <div className="max-w-xs">
            <Link
              href="/"
              className="inline-flex items-center no-underline mb-3"
              aria-label="Pilot for Trades — Home"
            >
              <Image
                src={logoDarkSrc}
                alt="Pilot for Trades"
                width={160}
                height={36}
                priority={false}
                onError={() => setLogoDarkSrc(logoDarkSvg)}
              />
            </Link>
            <p
              className="text-sm leading-relaxed"
              style={{ color: "var(--neutral-400)" }}
            >
              Master the Craft. Automate the Rest.
            </p>
          </div>

          {/* Newsletter — wired to POST /api/v1/marketing/newsletter */}
          <div className="max-w-sm w-full">
            <p
              className="text-sm font-semibold mb-3 uppercase tracking-wider"
              style={{ color: "var(--neutral-200)" }}
            >
              Stay in the loop
            </p>
            <NewsletterForm
              source="footer"
              showTradeInterest={false}
              dark={true}
            />
          </div>
        </div>

        {/* Footer nav columns */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 py-12">
          {footerColumns.map((col) => (
            <div key={col.heading}>
              <h3
                className="text-xs font-semibold uppercase tracking-wider mb-4"
                style={{ color: "var(--neutral-200)" }}
              >
                {col.heading}
              </h3>
              <ul className="flex flex-col gap-3 list-none p-0 m-0">
                {col.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm no-underline transition-colors"
                      style={{ color: "var(--neutral-400)" }}
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div
          className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-8"
          style={{ borderTop: "var(--divider-thin) solid var(--neutral-800)" }}
        >
          <p className="text-sm" style={{ color: "var(--neutral-600)" }}>
            © 2026 Pilot for Trades. A product of Example Holdings,
            LLC. All rights reserved.
          </p>
          {/* Social icons (X / LinkedIn) hidden during Charter program —
              re-enable after Charter + solid marketing program is in place.
          <div className="flex items-center gap-4">
            <a
              href="https://twitter.com/pilotfortrades"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Pilot for Trades on Twitter"
              className="transition-colors"
              style={{ color: "var(--neutral-600)" }}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>
            <a
              href="https://linkedin.com/company/pilotfortrades"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Pilot for Trades on LinkedIn"
              className="transition-colors"
              style={{ color: "var(--neutral-600)" }}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
              </svg>
            </a>
          </div>
          */}
        </div>
      </div>
    </footer>
  );
}
