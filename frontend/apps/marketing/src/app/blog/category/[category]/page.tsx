// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getPostsByCategory,
  BLOG_CATEGORIES,
  type BlogCategory,
} from "../../../../lib/blog";
import BlogCard from "../../../../components/blog/BlogCard";

/* ─── Static params ──────────────────────────────────── */

/**
 * Always generate pages for ALL known categories regardless of whether
 * they currently have posts. Static export requires every linked param
 * to be pre-generated — category tabs on /blog link to all categories.
 */
export async function generateStaticParams() {
  return BLOG_CATEGORIES.filter((c) => c.slug !== "all").map((c) => ({
    category: c.slug,
  }));
}

/* ─── Metadata ───────────────────────────────────────── */

const CATEGORY_META: Record<string, { title: string; description: string }> = {
  electrical: {
    title: "Electrical Contractor Blog — AI, Quoting & Business Tips",
    description:
      "Guides for electricians: voice quoting, NEC compliance, copper pricing, and growing a profitable electrical contracting business.",
  },
  plumbing: {
    title: "Plumbing Contractor Blog — Estimating, Dispatch & Business Tips",
    description:
      "Guides for plumbers: voice estimating, fixture pricing, emergency dispatch, and running a more profitable plumbing business.",
  },
  hvac: {
    title: "HVAC Contractor Blog — Bidding, Dispatch & Business Tips",
    description:
      "Guides for HVAC contractors: voice quoting, equipment pricing, seasonal dispatch, and building a more profitable HVAC business.",
  },
  business: {
    title: "Contractor Business Blog — Profitability, Pricing & Growth",
    description:
      "Business advice for trade contractors: job profitability tracking, pricing strategy, cash flow, and operational efficiency.",
  },
  product: {
    title: "Pilot for Trades — Product News & Announcements",
    description:
      "Product updates, feature announcements, and insights from the Pilot for Trades team.",
  },
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ category: string }>;
}): Promise<Metadata> {
  const { category } = await params;
  const meta = CATEGORY_META[category];
  if (!meta) return {};

  return {
    title: meta.title,
    description: meta.description,
    openGraph: {
      title: `${meta.title} | Pilot for Trades`,
      description: meta.description,
      url: `https://pilotfortrades.com/blog/category/${category}`,
    },
  };
}

/* ─── Page ───────────────────────────────────────────── */

const CATEGORY_DOT_COLORS: Record<string, string> = {
  electrical: "var(--trade-electrical)",
  plumbing: "var(--trade-plumbing)",
  hvac: "var(--trade-hvac)",
  business: "var(--brand-600)",
  product: "var(--brand-600)",
};

export default async function BlogCategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = await params;

  // Validate category slug
  const validCategory = BLOG_CATEGORIES.find(
    (c) => c.slug === category && c.slug !== "all",
  );
  if (!validCategory) notFound();

  const posts = getPostsByCategory(category as BlogCategory);
  const categoryLabel = category.charAt(0).toUpperCase() + category.slice(1);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: "https://pilotfortrades.com",
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Blog",
        item: "https://pilotfortrades.com/blog",
      },
      {
        "@type": "ListItem",
        position: 3,
        name: categoryLabel,
        item: `https://pilotfortrades.com/blog/category/${category}`,
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Hero */}
      <section
        className="py-16"
        style={{ background: "var(--surface-marketing)" }}
        aria-labelledby="category-heading"
      >
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
            <span style={{ color: "var(--neutral-700)", fontWeight: 500 }}>
              {categoryLabel}
            </span>
          </nav>

          <h1
            id="category-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--neutral-900)" }}
          >
            {categoryLabel} Articles
          </h1>
          {CATEGORY_META[category] && (
            <p
              className="text-section-subtitle max-w-2xl"
              style={{ color: "var(--neutral-600)" }}
            >
              {CATEGORY_META[category].description}
            </p>
          )}
        </div>
      </section>

      {/* Category Filter Tab Bar */}
      <div
        className="py-3 border-b sticky top-16 z-20"
        style={{
          background: "var(--white)",
          borderColor: "var(--neutral-200)",
        }}
      >
        <div className="container-marketing">
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {BLOG_CATEGORIES.map((cat) => {
              const isActive = cat.slug === category;
              return (
                <Link
                  key={cat.slug}
                  href={
                    cat.slug === "all" ? "/blog" : `/blog/category/${cat.slug}`
                  }
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap no-underline transition-colors"
                  style={{
                    background: isActive ? "var(--brand-50)" : "transparent",
                    color: isActive ? "var(--brand-800)" : "var(--neutral-600)",
                  }}
                >
                  {cat.slug !== "all" && CATEGORY_DOT_COLORS[cat.slug] && (
                    <span
                      className="w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: CATEGORY_DOT_COLORS[cat.slug] }}
                      aria-hidden="true"
                    />
                  )}
                  {cat.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      {/* Post Grid */}
      <section
        className="section-padding"
        style={{ background: "var(--white)" }}
        aria-label={`${categoryLabel} blog posts`}
      >
        <div className="container-marketing">
          {posts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {posts.map((post) => (
                <BlogCard key={post.slug} post={post} />
              ))}
            </div>
          ) : (
            <div className="text-center py-24">
              <p
                className="text-xl font-semibold mb-3"
                style={{ color: "var(--neutral-700)" }}
              >
                No {categoryLabel} posts yet
              </p>
              <p className="mb-6" style={{ color: "var(--neutral-500)" }}>
                We&apos;re working on content for this category. Check back
                shortly.
              </p>
              <Link href="/blog" className="btn-primary">
                View All Posts
              </Link>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
