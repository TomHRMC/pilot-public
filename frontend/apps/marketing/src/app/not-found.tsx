import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "404 — Page Not Found",
  description:
    "The page you're looking for doesn't exist. Return to Pilot for Trades.",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: "var(--white)" }}
      aria-labelledby="notfound-heading"
    >
      <div className="container-marketing text-center max-w-xl">
        {/* Large 404 */}
        <p
          className="text-hero font-extrabold mb-4 select-none"
          style={{ color: "var(--brand-200)" }}
          aria-hidden="true"
        >
          404
        </p>

        <h1
          id="notfound-heading"
          className="text-section-title mb-4"
          style={{ color: "var(--neutral-900)" }}
        >
          Page not found
        </h1>

        <p
          className="text-body-lg mb-10"
          style={{ color: "var(--neutral-600)" }}
        >
          Looks like this page took an early break. Let&apos;s get you back on
          track.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
          <Link href="/" className="btn-primary">
            Go Home
          </Link>
          <Link href="/features" className="btn-secondary">
            See Features
          </Link>
        </div>

        {/* Quick links */}
        <nav aria-label="Quick links from 404 page">
          <p className="text-sm mb-4" style={{ color: "var(--neutral-400)" }}>
            Or go directly to:
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            {[
              { label: "Homepage", href: "/" },
              { label: "Features", href: "/features" },
              { label: "Pricing", href: "/pricing" },
              { label: "Charter", href: "/charter" },
              { label: "Contact", href: "/contact" },
            ].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm no-underline font-medium"
                style={{ color: "var(--brand-600)" }}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </nav>
      </div>
    </div>
  );
}
