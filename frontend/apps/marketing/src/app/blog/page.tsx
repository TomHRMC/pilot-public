// LAUNCH-DRAFT COPY — written for a launch that never happened; Pilot for Trades
// was never released. See PROVENANCE.md and frontend/apps/marketing/README.md.
import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import {
  getAllPosts,
  getFeaturedPost,
  BLOG_CATEGORIES,
  formatDate,
} from "../../lib/blog";
import BlogCard, { CategoryBadge } from "../../components/blog/BlogCard";
import { getSiteMode } from "../../lib/useSiteMode";

export const metadata: Metadata = {
  title: "Blog — Trade Tips, AI, and Contractor Business Advice",
  description:
    "Practical advice for electricians, plumbers, and HVAC contractors. Learn how AI voice quoting, real-time pricing, and smarter dispatch can grow your trade business.",
  openGraph: {
    title:
      "Blog — Trade Tips, AI, and Contractor Business Advice | Pilot for Trades",
    description:
      "Practical advice for electricians, plumbers, and HVAC contractors. Voice quoting, profitability, and business growth.",
    url: "https://pilotfortrades.com/blog",
  },
};

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
  ],
};

const CATEGORY_DOT_COLORS: Record<string, string> = {
  electrical: "var(--trade-electrical)",
  plumbing: "var(--trade-plumbing)",
  hvac: "var(--trade-hvac)",
  business: "var(--brand-600)",
  product: "var(--brand-600)",
};

export default async function BlogIndexPage() {
  const { isGeneralRelease } = await getSiteMode();
  const ctaText = isGeneralRelease ? "Start Free Trial" : "Be One of the First";
  const ctaHref = isGeneralRelease ? "/sign-up" : "/charter";
  const allPosts = getAllPosts();
  const featuredPost = getFeaturedPost();

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* Blog Hero — Featured Post Spotlight */}
      {featuredPost ? (
        <section
          className="py-16"
          style={{ background: "var(--surface-marketing)" }}
          aria-labelledby="featured-post-heading"
        >
          <div className="container-marketing">
            <div className="flex flex-col lg:flex-row items-center gap-12">
              {/* Left column */}
              <div className="flex-1 max-w-xl">
                <div className="mb-4">
                  <CategoryBadge category={featuredPost.category} />
                </div>
                <h1
                  id="featured-post-heading"
                  className="text-section-title mb-4"
                  style={{ color: "var(--neutral-900)" }}
                >
                  {featuredPost.title}
                </h1>
                <p
                  className="text-body-lg mb-4"
                  style={{ color: "var(--neutral-600)" }}
                >
                  {featuredPost.description}
                </p>
                <p
                  className="text-sm mb-6"
                  style={{ color: "var(--neutral-500)" }}
                >
                  {featuredPost.author} ·{" "}
                  <time dateTime={featuredPost.date}>
                    {formatDate(featuredPost.date)}
                  </time>{" "}
                  · {featuredPost.readingTime} min read
                </p>
                <Link
                  href={featuredPost.href}
                  className="text-base font-semibold"
                  style={{ color: "var(--brand-600)" }}
                >
                  Read Article →
                </Link>
              </div>

              {/* Right column — featured image */}
              <div className="flex-1 w-full max-w-xl">
                <Link
                  href={featuredPost.href}
                  className="block w-full rounded-2xl overflow-hidden no-underline relative"
                  style={{ aspectRatio: "16/9" }}
                  aria-label={`Read: ${featuredPost.title}`}
                >
                  <Image
                    src={featuredPost.image}
                    alt={featuredPost.title}
                    fill
                    className="object-cover object-center"
                    sizes="(max-width: 48rem) 100vw, 50vw"
                    priority
                  />
                </Link>
              </div>
            </div>
          </div>
        </section>
      ) : (
        /* No posts yet — hero fallback */
        <section
          className="py-16"
          style={{ background: "var(--surface-marketing)" }}
          aria-label="Blog"
        >
          <div className="container-marketing text-center">
            <h1
              className="text-section-title mb-4"
              style={{ color: "var(--neutral-900)" }}
            >
              Trade Tips, AI Insights & Business Advice
            </h1>
            <p
              className="text-section-subtitle max-w-2xl mx-auto"
              style={{ color: "var(--neutral-600)" }}
            >
              Practical content for electricians, plumbers, and HVAC contractors
              — written by people who understand the trades.
            </p>
          </div>
        </section>
      )}

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
              const isActive = cat.slug === "all";
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
        aria-label="All blog posts"
      >
        <div className="container-marketing">
          {allPosts.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {allPosts.map((post) => (
                <BlogCard key={post.slug} post={post} />
              ))}
            </div>
          ) : (
            <div className="text-center py-24">
              <p
                className="text-xl font-semibold mb-3"
                style={{ color: "var(--neutral-700)" }}
              >
                Posts coming soon
              </p>
              <p style={{ color: "var(--neutral-500)" }}>
                We&apos;re writing practical guides for trade contractors. Check
                back shortly.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Newsletter CTA Banner */}
      <section
        className="py-16"
        style={{ background: "var(--brand-600)" }}
        aria-labelledby="blog-newsletter-heading"
      >
        <div className="container-marketing text-center max-w-2xl mx-auto">
          <h2
            id="blog-newsletter-heading"
            className="text-section-title mb-4"
            style={{ color: "var(--white)" }}
          >
            Get Trade Tips in Your Inbox
          </h2>
          <p className="text-body-lg mb-8" style={{ color: "var(--white-82)" }}>
            Practical business advice for electricians, plumbers, and HVAC
            contractors. No spam, no fluff — just insights that help you run a
            more profitable shop.
          </p>
          <Link href={ctaHref} className="btn-white">
            {ctaText}
          </Link>
        </div>
      </section>
    </>
  );
}
