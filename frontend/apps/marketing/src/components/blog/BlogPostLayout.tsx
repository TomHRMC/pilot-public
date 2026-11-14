import Link from "next/link";
import Image from "next/image";
import type { BlogPost } from "../../lib/blog";
import { formatDate } from "../../lib/blog";
import BlogToc from "./BlogToc";
import type { TocHeading } from "./BlogToc";
import BlogRelated from "./BlogRelated";
import BlogCta from "./BlogCta";
import { getSiteMode } from "../../lib/useSiteMode";

interface BlogPostLayoutProps {
  post: BlogPost;
  relatedPosts: BlogPost[];
  headings: TocHeading[];
  children: React.ReactNode;
}

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  electrical: {
    bg: "var(--trade-electrical-10)",
    text: "var(--trade-electrical-text)",
  },
  plumbing: {
    bg: "var(--trade-plumbing-10)",
    text: "var(--trade-plumbing-text)",
  },
  hvac: { bg: "var(--trade-hvac-10)", text: "var(--trade-hvac-text)" },
  business: { bg: "var(--brand-50)", text: "var(--brand-800)" },
  product: { bg: "var(--brand-50)", text: "var(--brand-800)" },
};

export default async function BlogPostLayout({
  post,
  relatedPosts,
  headings,
  children,
}: BlogPostLayoutProps) {
  const { isGeneralRelease } = await getSiteMode();
  const catColors = CATEGORY_COLORS[post.category] || CATEGORY_COLORS.product;
  const ctaHref = isGeneralRelease ? "/sign-up" : "/charter";
  const ctaLabel = isGeneralRelease
    ? "Start Free Trial"
    : "Be one of the first twelve";

  return (
    <>
      {/* Post Header Zone */}
      <div className="pt-8 pb-12" style={{ background: "var(--white)" }}>
        <div className="container-marketing">
          {/* Breadcrumb */}
          <nav
            aria-label="Breadcrumb"
            className="flex items-center gap-1.5 text-sm mb-6"
            style={{ color: "var(--neutral-500)" }}
          >
            <Link href="/" style={{ color: "var(--neutral-500)" }}>
              Home
            </Link>
            <span aria-hidden="true">/</span>
            <Link href="/blog" style={{ color: "var(--neutral-500)" }}>
              Blog
            </Link>
            <span aria-hidden="true">/</span>
            <span
              className="capitalize"
              style={{ color: "var(--neutral-500)" }}
            >
              {post.category}
            </span>
          </nav>

          {/* Category badge */}
          <div className="mb-4">
            <span
              className="inline-flex items-center text-xs font-semibold uppercase tracking-wider rounded-full px-3 py-1"
              style={{
                background: catColors.bg,
                color: catColors.text,
              }}
            >
              {post.category.charAt(0).toUpperCase() + post.category.slice(1)}
            </span>
          </div>

          {/* Title */}
          <h1
            className="text-section-title mb-6"
            style={{ color: "var(--neutral-900)" }}
          >
            {post.title}
          </h1>

          {/* Meta line */}
          <div
            className="flex flex-wrap items-center gap-3 text-base mb-8"
            style={{ color: "var(--neutral-500)" }}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
                style={{
                  background: "var(--brand-100)",
                  color: "var(--brand-800)",
                }}
                aria-hidden="true"
              >
                T
              </div>
              <span>{post.author}</span>
            </div>
            <span aria-hidden="true">·</span>
            <time dateTime={post.date}>{formatDate(post.date)}</time>
            <span aria-hidden="true">·</span>
            <span>{post.readingTime} min read</span>
          </div>

          {/* Hero image */}
          <div
            className="w-full rounded-2xl overflow-hidden relative"
            style={{ aspectRatio: "16/7" }}
          >
            <Image
              src={post.image}
              alt={`Hero image for: ${post.title}`}
              fill
              className="object-cover object-center"
              sizes="(max-width: 48rem) 100vw, 75rem"
              priority
            />
          </div>
        </div>
      </div>

      {/* Body + Sidebar */}
      <div className="container-marketing py-12">
        {/* Mobile TOC */}
        <div className="lg:hidden mb-6">
          <BlogToc headings={headings} />
        </div>

        <div className="grid lg:grid-cols-[1fr_300px] gap-12 lg:gap-16 items-start">
          {/* Main content */}
          <article
            className="prose-blog min-w-0"
            style={{
              color: "var(--neutral-700)",
              fontSize: "var(--text-body-lg)",
              lineHeight: "var(--lh-body-lg)",
            }}
          >
            {children}
          </article>

          {/* Sidebar */}
          <aside className="hidden lg:flex flex-col gap-6 sticky top-24">
            <BlogToc headings={headings} />
            {relatedPosts.length > 0 && (
              <BlogRelated posts={relatedPosts} variant="sidebar" />
            )}
            {/* Sidebar CTA */}
            <div
              className="rounded-xl p-5"
              style={{ background: "var(--brand-600)" }}
            >
              <p
                className="text-base font-semibold mb-1"
                style={{ color: "var(--white)" }}
              >
                Try Pilot Free
              </p>
              <p className="text-sm mb-4" style={{ color: "var(--white-8)" }}>
                14-day free trial. No credit card.
              </p>
              <Link
                href={ctaHref}
                className="block text-center text-sm font-semibold rounded-lg px-4 py-2 transition-colors"
                style={{
                  background: "var(--white)",
                  color: "var(--brand-800)",
                }}
              >
                {ctaLabel}
              </Link>
            </div>
          </aside>
        </div>
      </div>

      {/* Related posts — full width */}
      {relatedPosts.length > 0 && (
        <BlogRelated posts={relatedPosts} variant="full" />
      )}

      {/* Footer CTA Banner */}
      <section
        className="section-padding"
        style={{ background: "var(--brand-600)" }}
        aria-labelledby="post-footer-cta"
      >
        <div className="container-marketing text-center max-w-2xl mx-auto">
          <h2
            id="post-footer-cta"
            className="text-section-title mb-4"
            style={{ color: "var(--white)" }}
          >
            Stop Working for Your Business. Let Your Business Work for You.
          </h2>
          <p className="text-body-lg mb-8" style={{ color: "var(--white-82)" }}>
            Voice quoting, real-time profitability, and QuickBooks sync — in one
            tool built for the trades.
          </p>
          <Link href={ctaHref} className="btn-white">
            {ctaLabel}
          </Link>
        </div>
      </section>
    </>
  );
}

export { BlogCta };
// Re-export mode type for consumers
export type { SiteMode } from "../../lib/useSiteMode";
